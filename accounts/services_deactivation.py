"""
Service functions for Pandit deactivation with referral custodianship.

This module handles:
- Soft deactivation of Pandits
- Referral custodianship assignment
- Prevention of hard deletion when referrals exist
- Audit logging
"""
import logging
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

logger = logging.getLogger(__name__)

# Import referral models
try:
    from referrals.models import ReferralUsage, ReferralLink
    from referrals.models_custodianship import ReferralCustodian
except ImportError:
    ReferralUsage = None
    ReferralLink = None
    ReferralCustodian = None


def has_referral_descendants(pandit):
    """
    Check if a Pandit has referred other Pandits.
    
    Args:
        pandit: User instance with role='pandit'
    
    Returns:
        bool: True if pandit has referred others, False otherwise
    """
    if not ReferralUsage:
        return False
    
    # Check if this pandit has created referral links that were used
    referral_links = ReferralLink.objects.filter(created_by=pandit)
    usage_count = ReferralUsage.objects.filter(referral_link__in=referral_links).count()
    
    # Also check if other pandits were referred by this pandit (via referred_by)
    direct_referrals = User.objects.filter(referred_by=pandit, role='pandit').count()
    
    return usage_count > 0 or direct_referrals > 0


def get_referral_descendants_count(pandit):
    """
    Get count of Pandits referred by this Pandit.
    
    Args:
        pandit: User instance with role='pandit'
    
    Returns:
        int: Number of referred Pandits
    """
    if not ReferralUsage:
        return 0
    
    # Count via referral links
    referral_links = ReferralLink.objects.filter(created_by=pandit)
    usage_count = ReferralUsage.objects.filter(referral_link__in=referral_links).count()
    
    # Count direct referrals
    direct_referrals = User.objects.filter(referred_by=pandit, role='pandit').count()
    
    return usage_count + direct_referrals


def deactivate_pandit_with_custodianship(pandit, deactivated_by, reason=None):
    """
    Soft-deactivate a Pandit and assign custodianship for all relationships.
    
    TASKS 2, 3, 4: Handles:
    1. Referral custodianship (if Pandit has referrals)
    2. Approval history preservation (if Admin Pandit approved others)
    3. Page role assignment revocation (if Pandit has page roles)
    4. Page ownership custodianship (if Admin Pandit created pages)
    
    This function:
    1. Checks if Pandit has referral descendants
    2. Checks if Admin Pandit approved others
    3. Checks if Pandit has page role assignments
    4. Checks if Admin Pandit created pages
    5. Assigns appropriate custodianship for each
    6. Sets Pandit status to 'deactivated'
    7. Logs audit entries
    
    Args:
        pandit: User instance (must have role='pandit' or 'admin')
        deactivated_by: User instance (Super Admin who performs deactivation)
        reason: str (optional reason for deactivation)
    
    Returns:
        tuple: (success: bool, message: str, custodianships: dict)
    
    Raises:
        ValidationError: If user is not a Pandit/Admin or deactivated_by is not Super Admin
    """
    if pandit.role not in ['pandit', 'admin']:
        raise ValidationError(f"User {pandit.email} is not a Pandit or Admin. Cannot deactivate.")
    
    if not deactivated_by.is_superuser:
        raise ValidationError("Only Super Admin can deactivate Pandits/Admins with custodianship.")
    
    with transaction.atomic():
        custodianships = {}
        messages = []
        
        # TASK 1: Handle referral custodianship (if Pandit has referrals)
        if pandit.role == 'pandit':
            has_descendants = has_referral_descendants(pandit)
            descendants_count = get_referral_descendants_count(pandit) if has_descendants else 0
            
            if has_descendants and ReferralCustodian:
                reason_text = reason or f"Pandit deactivated. {descendants_count} referral relationship(s) preserved."
                custodianship = ReferralCustodian.assign_custodianship(
                    referrer=pandit,
                    custodian=deactivated_by,
                    reason=reason_text
                )
                custodianships['referral'] = custodianship
                messages.append(f"{descendants_count} referral relationship(s) preserved")
                logger.info(
                    f"Referral custodianship assigned - "
                    f"Referrer: {pandit.email}, Custodian: {deactivated_by.email}, "
                    f"Descendants: {descendants_count}"
                )
        
        # TASK 2: Handle approval history preservation (if Admin Pandit approved others)
        if pandit.role == 'admin':
            try:
                from governance.services_approval import handle_admin_deactivation
                handle_admin_deactivation(pandit, actor=deactivated_by)
                custodianships['approval'] = True
                messages.append("Approval history preserved")
                logger.info(f"Approval custodianship assigned for Admin {pandit.email}")
            except ImportError:
                logger.warning("governance.services_approval not available - skipping approval custodianship")
        
        # TASK 3: Handle page role assignment revocation (if Pandit has page roles)
        try:
            from pages.services_role_assignment import handle_pandit_page_deactivation
            handle_pandit_page_deactivation(pandit, actor=deactivated_by)
            custodianships['page_roles'] = True
            messages.append("Page role assignments revoked, custodianship assigned")
            logger.info(f"Page role custodianship assigned for {pandit.email}")
        except ImportError:
            logger.warning("pages.services_role_assignment not available - skipping page role custodianship")
        except Exception as e:
            # Only handle if Pandit actually has page roles
            if 'no active page role assignments' not in str(e).lower():
                logger.warning(f"Error handling page role deactivation: {e}")
        
        # TASK 4: Handle page ownership custodianship (if Admin Pandit created pages)
        if pandit.role == 'admin':
            try:
                from pages.services_page_ownership import handle_page_creator_deactivation
                handle_page_creator_deactivation(pandit, actor=deactivated_by)
                custodianships['page_ownership'] = True
                messages.append("Page ownership custodianship assigned")
                logger.info(f"Page ownership custodianship assigned for Admin {pandit.email}")
            except ImportError:
                logger.warning("pages.services_page_ownership not available - skipping page ownership custodianship")
            except Exception as e:
                # Only handle if Admin actually created pages
                if 'created no pages' not in str(e).lower():
                    logger.warning(f"Error handling page ownership deactivation: {e}")
        
        # TASK 7: Handle post preservation (if Admin Pandit created posts)
        if pandit.role == 'admin':
            try:
                from pages.services_post_preservation import handle_admin_pandit_post_preservation
                result = handle_admin_pandit_post_preservation(pandit, actor=deactivated_by)
                if result['post_count'] > 0:
                    custodianships['posts'] = result
                    messages.append(f"{result['post_count']} post(s) preserved with attribution")
                    logger.info(f"Posts preserved for Admin {pandit.email}: {result['post_count']} post(s)")
            except ImportError:
                logger.warning("pages.services_post_preservation not available - skipping post preservation")
            except Exception as e:
                logger.warning(f"Error handling post preservation: {e}")
        
        # TASK 8: Handle pinned posts preservation (if Pandit has pinned posts)
        if pandit.role in ['pandit', 'admin']:
            try:
                from pages.services_pinned_posts import preserve_pinned_posts_on_pandit_deactivation
                result = preserve_pinned_posts_on_pandit_deactivation(pandit, actor=deactivated_by)
                if result['post_count'] > 0:
                    custodianships['pinned_posts'] = result
                    messages.append(f"{result['post_count']} pinned post(s) preserved")
                    logger.info(f"Pinned posts preserved for {pandit.email}: {result['post_count']} post(s)")
            except ImportError:
                logger.warning("pages.services_pinned_posts not available - skipping pinned posts preservation")
            except Exception as e:
                logger.warning(f"Error handling pinned posts preservation: {e}")
        
        # TASK 9: Handle reviews preservation (if user has reviews)
        # Note: This applies to all users, not just Pandits
        try:
            from pages.services_review_preservation import preserve_reviews_on_user_deactivation
            result = preserve_reviews_on_user_deactivation(pandit, actor=deactivated_by)
            if result['review_count'] > 0:
                custodianships['reviews'] = result
                messages.append(f"{result['review_count']} review(s) preserved")
                logger.info(f"Reviews preserved for {pandit.email}: {result['review_count']} review(s)")
        except ImportError:
            logger.warning("pages.services_review_preservation not available - skipping reviews preservation")
        except Exception as e:
            logger.warning(f"Error handling reviews preservation: {e}")
        
        # TASK 11: Handle email verification resend authority transfer (if Admin Pandit)
        if pandit.role == 'admin':
            try:
                from accounts.services_email_verification_authority import handle_admin_pandit_verification_authority_transfer
                result = handle_admin_pandit_verification_authority_transfer(pandit, actor=deactivated_by)
                if result['token_count'] > 0:
                    custodianships['email_verification'] = result
                    messages.append(f"{result['token_count']} verification token(s) - Super Admin can resend")
                    logger.info(f"Email verification authority transferred for Admin {pandit.email}: {result['token_count']} token(s)")
            except ImportError:
                logger.warning("accounts.services_email_verification_authority not available - skipping email verification authority transfer")
            except Exception as e:
                logger.warning(f"Error handling email verification authority transfer: {e}")
        
        # TASK 12: Handle moderator access preservation (if Admin Pandit granted roles)
        if pandit.role == 'admin':
            try:
                from pages.services_moderator_access_preservation import preserve_moderator_access_on_grantor_deactivation
                result = preserve_moderator_access_on_grantor_deactivation(pandit, actor=deactivated_by)
                if result['assignment_count'] > 0:
                    custodianships['moderator_access'] = result
                    messages.append(f"{result['assignment_count']} moderator role(s) preserved")
                    logger.info(f"Moderator access preserved for Admin {pandit.email}: {result['assignment_count']} role(s)")
            except ImportError:
                logger.warning("pages.services_moderator_access_preservation not available - skipping moderator access preservation")
            except Exception as e:
                logger.warning(f"Error handling moderator access preservation: {e}")
        
        # TASK 13: Handle access request rerouting (if Admin Pandit has pending requests)
        if pandit.role == 'admin':
            try:
                from pages.services_access_request_rerouting import reroute_access_requests_on_admin_deactivation
                result = reroute_access_requests_on_admin_deactivation(pandit, actor=deactivated_by)
                if result['request_count'] > 0:
                    custodianships['access_requests'] = result
                    messages.append(f"{result['request_count']} access request(s) rerouted to Super Admin")
                    logger.info(f"Access requests rerouted for Admin {pandit.email}: {result['request_count']} request(s)")
            except ImportError:
                logger.warning("pages.services_access_request_rerouting not available - skipping access request rerouting")
            except Exception as e:
                logger.warning(f"Error handling access request rerouting: {e}")
        
        # TASK 21: Handle booking intents when Pandit is deactivated
        if pandit.role == 'pandit':
            try:
                from booking_intent.services_deactivation import handle_pandit_deactivation_booking_intents
                result = handle_pandit_deactivation_booking_intents(pandit, actor=deactivated_by)
                if result['intents_closed'] > 0:
                    custodianships['booking_intents'] = result
                    messages.append(f"{result['intents_closed']} booking intent(s) auto-closed")
                    logger.info(f"Booking intents auto-closed for Pandit {pandit.email}: {result['intents_closed']} intent(s)")
            except ImportError:
                logger.warning("booking_intent.services_deactivation not available - skipping booking intent handling")
            except Exception as e:
                logger.warning(f"Error handling booking intents: {e}")
        
        # Soft-deactivate the Pandit/Admin
        pandit.status = 'deactivated'
        pandit.is_active = False
        pandit.save(update_fields=['status', 'is_active'])
        
        # Log audit entry
        logger.info(
            f"User deactivated - "
            f"User: {pandit.email} (ID: {pandit.id}, Role: {pandit.role}), "
            f"Deactivated by: {deactivated_by.email} (ID: {deactivated_by.id}), "
            f"Reason: {reason or 'Not specified'}, "
            f"Custodianships: {list(custodianships.keys())}"
        )
        
        if messages:
            message = f"User deactivated successfully. {'; '.join(messages)}."
        else:
            message = "User deactivated successfully."
        
        return True, message, custodianships


def can_delete_pandit(pandit):
    """
    Check if a Pandit can be hard-deleted.
    
    Rules:
    - Pandits with referral descendants CANNOT be deleted
    - All Pandits should be soft-deactivated instead
    
    Args:
        pandit: User instance with role='pandit'
    
    Returns:
        tuple: (can_delete: bool, reason: str)
    """
    if pandit.role != 'pandit':
        return True, "User is not a Pandit."
    
    has_descendants = has_referral_descendants(pandit)
    
    if has_descendants:
        descendants_count = get_referral_descendants_count(pandit)
        return False, (
            f"This Pandit has {descendants_count} active referral relationship(s) "
            f"and cannot be deleted. The account will be deactivated instead to preserve trust chain integrity."
        )
    
    # Even without descendants, prefer soft deactivation
    return False, (
        "Pandits should be soft-deactivated, not hard-deleted. "
        "This preserves audit trails and allows future reactivation."
    )




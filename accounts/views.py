"""
Views for accounts app.

This file contains views for user authentication and account management.
"""
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model, authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import ValidationError
from .utils import is_admin, is_pandit, is_user
from .decorators import admin_required
# SECURITY FIX: Rate limiting to prevent brute-force attacks
from .rate_limiting import rate_limit_login

logger = logging.getLogger(__name__)

User = get_user_model()

# Import referral models for validation (Module 3)
try:
    from referrals.models import ReferralLink, ReferralUsage
except ImportError:
    # Fallback if referrals app is not available
    ReferralLink = None
    ReferralUsage = None

# Import email verification service (TASK 3)
from .email_verification import create_email_verification
from .views_email_verification import verify_email_view

# Import resend verification view (TASK 3: Resend capability)
from .views_resend_verification import resend_pandit_verification


@login_required
@require_http_methods(["POST"])
@csrf_protect
def update_theme_preference(request):
    """
    Update user's theme preference (light/dark mode).
    Safe AJAX endpoint - does not break authentication or forms.
    """
    try:
        data = json.loads(request.body)
        theme = data.get('theme', 'light')
        
        if theme not in ['light', 'dark']:
            return JsonResponse({'error': 'Invalid theme'}, status=400)
        
        request.user.theme_preference = theme
        request.user.save(update_fields=['theme_preference'])
        
        return JsonResponse({'success': True, 'theme': theme})
    except Exception as e:
        logger.error(f"Error updating theme preference: {e}", exc_info=True)
        return JsonResponse({'error': 'Failed to update theme preference'}, status=500)


# SECURITY NOTE: csrf_exempt is intentional here because:
# - This endpoint supports referral token via URL (GET/POST with token in path).
# - Server-side validation enforces referral token/code integrity before any state change.
# - No sensitive state change occurs without a valid, active referral link.
# - Rate limiting and referral lifecycle checks are applied.
# DO NOT remove unless replacing with token-based CSRF strategy.
@csrf_exempt
def pandit_register(request, referral_token):
    """
    Pandit registration endpoint (referral-based).
    
    Handles both:
    - GET: Display registration form
    - POST: Process registration (JSON or form data)
    
    This view creates a new Pandit user with:
    - role = 'pandit'
    - status = 'pending'
    - email_verified = False
    
    Registration requires:
    - referral_token (from URL)
    - referral_code (from request data)
    
    Args:
        request: HTTP request object
        referral_token: Referral token from URL path
        
    Returns:
        GET: Rendered HTML form template
        POST: JsonResponse with success/error status
    """
    # Validate referral token is present (from URL)
    if not referral_token or not referral_token.strip():
        logger.warning("Invalid referral attempt", extra={"ip": request.META.get("REMOTE_ADDR"), "reason": "empty_token"})
        messages.error(request, 'Invalid referral token. Please use a valid referral link.')
        return render(request, 'accounts/pandit_register.html', {
            'referral_token': None,
            'referral_valid': False,
            'error': 'Invalid referral token'
        })
    
    # Validate referral link exists and is valid (for GET request or initial validation)
    referral_link = None
    referral_valid = False
    referral_error = None
    
    from referrals.registration_validation import validate_referral_for_pandit_get

    get_validation = validate_referral_for_pandit_get(referral_token)
    referral_link = get_validation.referral_link
    referral_valid = get_validation.is_valid
    referral_error = get_validation.error_message
    
    if referral_error:
        logger.warning("Invalid referral attempt", extra={"ip": request.META.get("REMOTE_ADDR"), "token_prefix": (referral_token or "")[:12], "reason": "validation_failed"})
    
    # GET request: Display registration form
    if request.method == 'GET':
        return render(request, 'accounts/pandit_register.html', {
            'referral_token': referral_token,
            'referral_code': referral_link.referral_code if referral_link else None,
            'referral_valid': referral_valid,
            'referral_error': referral_error,
            'referral_link': referral_link,
        })
    
    # POST request: Process registration
    # Handle both JSON and form data
    if request.content_type == 'application/json':
        # JSON request (API)
        try:
            from core.security_utils import safe_json_loads
            # Define allowed fields for registration
            allowed_fields = ['referral_code', 'email', 'password', 'first_name', 'last_name', 'phone_number', 'phone']
            data = safe_json_loads(request.body, allowed_fields=allowed_fields)
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON',
                'message': 'Request body must be valid JSON'
            }, status=400)
        except ValidationError as e:
            return JsonResponse({
                'error': 'Invalid payload',
                'message': str(e)
            }, status=400)
    else:
        # Form data request (HTML form)
        data = request.POST.copy()
    
    # Extract required fields
    referral_code = data.get('referral_code', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    
    # Validate referral token is present (from URL)
    if not referral_token or not referral_token.strip():
        return JsonResponse({
            'error': 'Invalid referral token',
            'message': 'Referral token is required in URL'
        }, status=400)
    
    # Validate referral code is present (from request data)
    if not referral_code:
        logger.warning("Invalid referral attempt", extra={"ip": request.META.get("REMOTE_ADDR"), "token_prefix": (referral_token or "")[:12], "reason": "missing_code"})
        error_msg = 'Referral code is required'
        if request.content_type == 'application/json':
            return JsonResponse({
                'error': 'Missing referral code',
                'message': error_msg
            }, status=400)
        else:
            messages.error(request, error_msg)
            return render(request, 'accounts/pandit_register.html', {
                'referral_token': referral_token,
                'referral_code': None,
                'referral_valid': referral_valid,
                'referral_error': referral_error,
                'referral_link': referral_link,
                'form_data': {
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                }
            })
    
    # Validate referral token and code are present
    if not referral_token.strip() or not referral_code.strip():
        error_msg = 'Referral token and code must be provided'
        if request.content_type == 'application/json':
            return JsonResponse({
                'error': 'Invalid referral',
                'message': error_msg
            }, status=400)
        else:
            messages.error(request, error_msg)
            return render(request, 'accounts/pandit_register.html', {
                'referral_token': referral_token,
                'referral_code': referral_code,
                'referral_valid': referral_valid,
                'referral_error': referral_error,
                'referral_link': referral_link,
                'form_data': {
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                }
            })
    
    # Referral validation (Module 3 - Task 3.4)
    from referrals.registration_validation import validate_referral_for_pandit_post

    post_validation = validate_referral_for_pandit_post(referral_token, referral_code)
    referral_link = post_validation.referral_link
    if not post_validation.is_valid:
        logger.warning(
            "Invalid referral attempt",
            extra={
                "ip": request.META.get("REMOTE_ADDR"),
                "token_prefix": (referral_token or "")[:12],
                "reason": "validation_failed",
            },
        )
        error_msg = post_validation.error_message or "Invalid referral link."
        json_error = "Invalid referral"
        if "does not match" in error_msg:
            json_error = "Invalid referral code"
        elif "deactivated" in error_msg:
            json_error = "Referral link inactive"
        elif "maximum usage limit" in error_msg:
            json_error = "Referral link expired"
        elif "referrer account is not active" in error_msg:
            json_error = "Referrer inactive"
        elif "does not exist or is invalid" in error_msg:
            json_error = "Invalid referral token"
        elif "expired" in error_msg.lower() and "usage limit" not in error_msg:
            json_error = "Referral link expired"
        elif "cannot be used" in error_msg and post_validation.referral_link is not None:
            json_error = "Referral link inactive"

        if request.content_type == 'application/json':
            return JsonResponse({
                'error': json_error,
                'message': error_msg
            }, status=400)
        messages.error(request, error_msg)
        return render(request, 'accounts/pandit_register.html', {
            'referral_token': referral_token,
            'referral_code': referral_code,
            'referral_valid': False,
            'referral_error': error_msg,
            'referral_link': referral_link,
            'form_data': {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            }
        })
    
    # Validate required user fields
    if not email:
        error_msg = 'Email address is required'
        if request.content_type == 'application/json':
            return JsonResponse({
                'error': 'Missing email',
                'message': error_msg
            }, status=400)
        else:
            messages.error(request, error_msg)
            return render(request, 'accounts/pandit_register.html', {
                'referral_token': referral_token,
                'referral_code': referral_code,
                'referral_valid': referral_valid,
                'referral_error': referral_error,
                'referral_link': referral_link,
                'form_data': {
                    'email': '',
                    'first_name': first_name,
                    'last_name': last_name,
                }
            })
    
    if not password:
        error_msg = 'Password is required'
        if request.content_type == 'application/json':
            return JsonResponse({
                'error': 'Missing password',
                'message': error_msg
            }, status=400)
        else:
            messages.error(request, error_msg)
            return render(request, 'accounts/pandit_register.html', {
                'referral_token': referral_token,
                'referral_code': referral_code,
                'referral_valid': referral_valid,
                'referral_error': referral_error,
                'referral_link': referral_link,
                'form_data': {
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                }
            })
    
    # Check if user with this email already exists
    if User.objects.filter(email=email).exists():
        error_msg = 'A user with this email address already exists'
        if request.content_type == 'application/json':
            return JsonResponse({
                'error': 'Email already exists',
                'message': error_msg
            }, status=400)
        else:
            messages.error(request, error_msg)
            return render(request, 'accounts/pandit_register.html', {
                'referral_token': referral_token,
                'referral_code': referral_code,
                'referral_valid': referral_valid,
                'referral_error': referral_error,
                'referral_link': referral_link,
                'form_data': {
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                }
            })

    phone_number = ''
    if request.content_type == 'application/json':
        phone_number = str(data.get('phone_number') or data.get('phone') or '').strip()
    else:
        phone_number = request.POST.get('phone_number', '').strip() or request.POST.get('phone', '').strip()

    from otp_verification import constants as otp_constants
    from otp_verification.registration.factory import is_registration_otp_required
    from otp_verification.registration.gate import begin_otp_or_continue

    wants_json = request.content_type == 'application/json'
    if is_registration_otp_required(otp_constants.FLOW_PANDIT_REGISTRATION):
        if not phone_number:
            error_msg = 'Phone number is required for SMS verification.'
            if wants_json:
                return JsonResponse({'error': 'phone_required', 'message': error_msg}, status=400)
            messages.error(request, error_msg)
            return render(request, 'accounts/pandit_register.html', {
                'referral_token': referral_token,
                'referral_code': referral_code,
                'referral_valid': referral_valid,
                'referral_error': referral_error,
                'referral_link': referral_link,
                'form_data': {
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone_number': phone_number,
                }
            })
        otp_response = begin_otp_or_continue(
            request,
            flow_type=otp_constants.FLOW_PANDIT_REGISTRATION,
            destination=phone_number,
            payload={
                "email": email,
                "password": password,
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": phone_number,
                "referral_link_id": referral_link.id if referral_link else None,
                "referral_code": referral_code,
            },
            resume_path=request.path,
            wants_json=wants_json,
        )
        if otp_response is not None:
            if otp_response.status_code == 400 and not wants_json:
                return render(request, 'accounts/pandit_register.html', {
                    'referral_token': referral_token,
                    'referral_code': referral_code,
                    'referral_valid': referral_valid,
                    'referral_error': referral_error,
                    'referral_link': referral_link,
                    'form_data': {
                        'email': email,
                        'first_name': first_name,
                        'last_name': last_name,
                        'phone_number': phone_number,
                    }
                })
            return otp_response

            # Create Pandit user with pending status and referral tracking (Module 3 - Task 3.4)
    try:
        with transaction.atomic():
            # Custom manager handles email-based user creation (username not required)
            # TASK 5: Create user with email_verified=False
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role='pandit',  # Set role to pandit
                status='pending',  # Set status to pending (requires admin approval)
                is_active=False,  # CRITICAL: Pending Pandits cannot authenticate until approved
                email_verified=False,  # TASK 5: Email verification required
            )
            
            # Create PanditProfile automatically for new Pandit users (fallback)
            # NOTE: A signal in profiles/signals.py should handle this automatically,
            # but we keep this as a safety net in case signals don't fire
            try:
                from profiles.models import PanditProfile
                # Check if profile was already created by signal
                if not hasattr(user, 'pandit_profile'):
                    try:
                        PanditProfile.objects.create(user=user)
                        logger.info(f"PanditProfile created automatically (fallback) for {user.email}")
                    except Exception as create_error:
                        # Profile might have been created by signal between checks
                        # Refresh user to check if profile exists now
                        user.refresh_from_db()
                        if not hasattr(user, 'pandit_profile'):
                            logger.error(f"Failed to create PanditProfile for {user.email}: {str(create_error)}", exc_info=True)
                        else:
                            logger.debug(f"PanditProfile was created by signal for {user.email}")
            except Exception as profile_error:
                # Log error but don't fail registration
                # Profile can be created later if needed
                logger.error(f"Error checking PanditProfile for {user.email}: {str(profile_error)}", exc_info=True)
            
            # Set referred_by field if referral link is valid (Module 3 - Task 3.4)
            if referral_link is not None:
                # Set trust chain: referred_by = referrer (created_by)
                user.referred_by = referral_link.created_by
                user.save()
                
                # Increment referral usage count
                referral_link.used_count += 1
                
                # Auto-deactivate if usage limit reached
                if referral_link.used_count >= referral_link.max_uses:
                    referral_link.is_active = False
                
                referral_link.save()
                
                # Create ReferralUsage record for audit trail
                ReferralUsage.objects.create(
                    referral_link=referral_link,
                    referred_pandit=user
                )
                
                # TASK 9: Log audit event for referral usage
                try:
                    from analytics.audit_events import log_audit_event
                    from referrals.constants import AUDIT_ACTION_REFERRAL_USED
                    log_audit_event(
                        event_type=AUDIT_ACTION_REFERRAL_USED,
                        user=user,
                        metadata={
                            'referral_link_id': referral_link.id,
                            'referred_pandit_id': user.id,
                            'referred_pandit_email': user.email,
                        }
                    )
                except Exception:
                    # Audit logging is optional
                    pass
            
            # TASK 5: Create email verification token and send email
            # STEP 2: Email is called - ensure it's not gated behind is_active
            # STEP 1: Registration flow entry point logging
            logger.warning(f"[EMAIL DEBUG] ========================================")
            logger.warning(f"[EMAIL DEBUG] REGISTRATION FLOW: Creating email verification")
            logger.warning(f"[EMAIL DEBUG] ========================================")
            logger.warning(f"[EMAIL DEBUG] User email: {user.email}")
            logger.warning(f"[EMAIL DEBUG] User ID: {user.id}")
            logger.warning(f"[EMAIL DEBUG] User is_active={user.is_active}, email_verified={user.email_verified}")
            logger.warning(f"[EMAIL DEBUG] User role: {user.role}, status: {user.status}")
            logger.warning(f"[EMAIL DEBUG] About to call create_email_verification()...")
            logger.warning(f"[EMAIL DEBUG] ========================================")
            try:
                verification_token = create_email_verification(user)
                # Email sent in create_email_verification() via transaction.on_commit()
                logger.warning(f"[EMAIL DEBUG] ✓ create_email_verification() completed")
                logger.warning(f"[EMAIL DEBUG] Token ID: {verification_token.id if verification_token else 'None'}")
                logger.warning(f"[EMAIL DEBUG] Pandit verification email scheduled for {user.email}")
                logger.warning(f"[EMAIL DEBUG] Email will be sent after transaction commits (via on_commit)")
                logger.info(f"Email verification token created and email sent to {user.email}")
            except Exception as e:
                # Log error but don't fail registration
                # User can request resend later
                # Note: logger is already defined at module level, no need to redefine
                logger.error(f"Failed to create/send email verification for {user.email}: {str(e)}", exc_info=True)
                # Check if using console backend
                from django.conf import settings
                if hasattr(settings, 'EMAIL_BACKEND') and 'console' in settings.EMAIL_BACKEND:
                    logger.warning(f"Email backend is console - verification email will be printed to terminal, not sent via SMTP.")
                # Token is still created even if email fails (user can resend)
                # But we should still try to create the token
                try:
                    from .models import EmailVerificationToken
                    verification_token = EmailVerificationToken.objects.create(user=user)
                    logger.info(f"Email verification token created (without email) for {user.email}")
                except Exception as token_error:
                    logger.error(f"Failed to create email verification token: {str(token_error)}", exc_info=True)
            
            # TASK 9: Log audit event for pandit registration
            try:
                from analytics.audit_events import log_audit_event
                from referrals.constants import AUDIT_ACTION_PANDIT_REGISTRATION_CREATED
                log_audit_event(
                    event_type=AUDIT_ACTION_PANDIT_REGISTRATION_CREATED,
                    user=user,
                    metadata={
                        'pandit_id': user.id,
                        'pandit_email': user.email,
                        'referral_link_id': referral_link.id if referral_link else None,
                        'referred_by': referral_link.created_by.email if referral_link else None,
                    }
                )
            except Exception:
                # Audit logging is optional
                pass
            
            # Optional: notify admins of new Pandit registration (production-safe; fail_silently)
            try:
                from django.conf import settings as django_settings
                from django.core.mail import send_mail
                admins = getattr(django_settings, 'ADMINS', ())
                if admins and user.email:
                    recipient_list = [email for _, email in admins]
                    if recipient_list:
                        try:
                            # NOTE:
                            # If Redis is UP but Celery worker is DOWN,
                            # tasks will queue and NOT execute immediately.
                            # This is expected Celery behavior.
                            from core.tasks_email import send_email_task

                            send_email_task.delay(
                                '[Nitya Dharma] New Pandit registration',
                                f'A new Pandit has registered: {user.email}. Please review in the admin.',
                                django_settings.DEFAULT_FROM_EMAIL,
                                recipient_list,
                            )
                        except Exception:
                            send_mail(
                                subject='[Nitya Dharma] New Pandit registration',
                                message=f'A new Pandit has registered: {user.email}. Please review in the admin.',
                                from_email=django_settings.DEFAULT_FROM_EMAIL,
                                recipient_list=recipient_list,
                                fail_silently=True,
                            )
            except Exception:
                pass
            
            # Return success response
            # TASK 5: Update message to include email verification step
            response_data = {
                'success': True,
                'message': 'Pandit registration successful. Please check your email to verify your address. Your account is pending admin approval.',
                'user_id': user.id,
                'email': user.email,
                'role': user.role,
                'status': user.status,
                'email_verified': user.email_verified,  # TASK 5: Include verification status
                'note': 'Please verify your email address. You will be able to access platform features after email verification and admin approval.'
            }
            
            # Include referral information if available
            if referral_link is not None:
                response_data['referral'] = {
                    'referral_link_id': referral_link.id,
                    'referred_by': referral_link.created_by.email,
                    'usage_count': referral_link.used_count,
                    'max_uses': referral_link.max_uses,
                    'is_active': referral_link.is_active
                }
            
            # Return response based on request type
            from otp_verification.registration.session import consume_phone_verified_session
            consume_phone_verified_session(request)
            if request.content_type == 'application/json':
                return JsonResponse(response_data, status=201)
            else:
                # HTML form submission - show success message
                messages.success(request, response_data['message'])
                return render(request, 'accounts/pandit_register.html', {
                    'referral_token': referral_token,
                    'referral_code': referral_link.referral_code if referral_link else None,
                    'referral_valid': True,
                    'referral_link': referral_link,
                    'registration_success': True,
                    'user_email': user.email,
                })
        
    except Exception as e:
        error_message = f'An error occurred during registration: {str(e)}'
        
        # Return response based on request type
        if request.content_type == 'application/json':
            return JsonResponse({
                'error': 'Registration failed',
                'message': error_message
            }, status=500)
        else:
            # HTML form submission - show error message
            messages.error(request, error_message)
            return render(request, 'accounts/pandit_register.html', {
                'referral_token': referral_token,
                'referral_code': referral_code,
                'referral_valid': referral_valid,
                'referral_error': referral_error,
                'referral_link': referral_link,
                'form_data': {
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                }
            })


# CSRF enforced for same-origin browser; frontend must send X-CSRFToken header or csrfmiddlewaretoken in form
@csrf_protect
@require_http_methods(["POST"])
def approve_pandit(request, user_id):
    """
    Approve a pending Pandit user (Admin & Super Admin only).
    
    This view:
    - Changes status from 'pending' to 'active'
    - Sets is_active=True (allows authentication)
    - Only works on users with role='pandit' and status='pending'
    - Prevents self-approval
    - Access restricted to: role='admin' OR is_superuser=True
    
    Args:
        request: HTTP request object (must be from admin/superuser)
        user_id: ID of the Pandit user to approve
        
    Returns:
        JsonResponse with success/error status
    """
    # Access control: Admin role OR superuser required
    if not request.user.is_authenticated:
        return JsonResponse({
            'error': 'Authentication required',
            'message': 'You must be logged in to perform this action'
        }, status=401)
    
    if not (is_admin(request.user) or request.user.is_superuser):
        return JsonResponse({
            'error': 'Access denied',
            'message': 'Admin role or superuser status required',
            'user_role': request.user.role,
            'is_superuser': request.user.is_superuser
        }, status=403)
    # Get the target user
    try:
        target_user = get_object_or_404(User, id=user_id)
    except ValueError:
        return JsonResponse({
            'error': 'Invalid user ID',
            'message': 'User ID must be a valid integer'
        }, status=400)
    
    # Validate target user is a Pandit
    if target_user.role != 'pandit':
        return JsonResponse({
            'error': 'Invalid user role',
            'message': f'Cannot approve user with role "{target_user.role}". Only Pandits can be approved.',
            'user_role': target_user.role
        }, status=400)
    
    # Validate target user is pending
    if target_user.status != 'pending':
        return JsonResponse({
            'error': 'Invalid user status',
            'message': f'Cannot approve user with status "{target_user.status}". Only pending Pandits can be approved.',
            'current_status': target_user.status,
            'allowed_status': 'pending'
        }, status=400)
    
    # Prevent self-approval
    if target_user.id == request.user.id:
        return JsonResponse({
            'error': 'Self-approval not allowed',
            'message': 'Users cannot approve themselves'
        }, status=400)
    
    # Approve the Pandit
    try:
        target_user.status = 'active'
        target_user.is_active = True  # CRITICAL: Allow authentication after approval
        target_user.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Pandit {target_user.email} has been approved successfully.',
            'user_id': target_user.id,
            'email': target_user.email,
            'role': target_user.role,
            'status': target_user.status,
            'is_active': target_user.is_active,
            'note': 'Pandit can now authenticate and access platform features.'
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'error': 'Approval failed',
            'message': f'An error occurred during approval: {str(e)}'
        }, status=500)


# CSRF enforced for same-origin browser; frontend must send X-CSRFToken header or csrfmiddlewaretoken in form
@csrf_protect
@require_http_methods(["POST"])
def reject_pandit(request, user_id):
    """
    Reject a pending Pandit user (Admin & Super Admin only).
    
    This view:
    - Changes status from 'pending' to 'rejected'
    - Keeps is_active=False (blocks authentication)
    - Only works on users with role='pandit' and status='pending'
    - Prevents self-rejection
    - Access restricted to: role='admin' OR is_superuser=True
    
    Args:
        request: HTTP request object (must be from admin/superuser)
        user_id: ID of the Pandit user to reject
        
    Returns:
        JsonResponse with success/error status
    """
    # Access control: Admin role OR superuser required
    if not request.user.is_authenticated:
        return JsonResponse({
            'error': 'Authentication required',
            'message': 'You must be logged in to perform this action'
        }, status=401)
    
    if not (is_admin(request.user) or request.user.is_superuser):
        return JsonResponse({
            'error': 'Access denied',
            'message': 'Admin role or superuser status required',
            'user_role': request.user.role,
            'is_superuser': request.user.is_superuser
        }, status=403)
    # Get the target user
    try:
        target_user = get_object_or_404(User, id=user_id)
    except ValueError:
        return JsonResponse({
            'error': 'Invalid user ID',
            'message': 'User ID must be a valid integer'
        }, status=400)
    
    # Validate target user is a Pandit
    if target_user.role != 'pandit':
        return JsonResponse({
            'error': 'Invalid user role',
            'message': f'Cannot reject user with role "{target_user.role}". Only Pandits can be rejected.',
            'user_role': target_user.role
        }, status=400)
    
    # Validate target user is pending
    if target_user.status != 'pending':
        return JsonResponse({
            'error': 'Invalid user status',
            'message': f'Cannot reject user with status "{target_user.status}". Only pending Pandits can be rejected.',
            'current_status': target_user.status,
            'allowed_status': 'pending'
        }, status=400)
    
    # Prevent self-rejection
    if target_user.id == request.user.id:
        return JsonResponse({
            'error': 'Self-rejection not allowed',
            'message': 'Users cannot reject themselves'
        }, status=400)
    
    # Reject the Pandit
    try:
        target_user.status = 'rejected'
        target_user.is_active = False  # Ensure authentication remains blocked
        target_user.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Pandit {target_user.email} has been rejected.',
            'user_id': target_user.id,
            'email': target_user.email,
            'role': target_user.role,
            'status': target_user.status,
            'is_active': target_user.is_active,
            'note': 'Pandit cannot authenticate or access platform features. Admin can reactivate later if needed.'
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'error': 'Rejection failed',
            'message': f'An error occurred during rejection: {str(e)}'
        }, status=500)


@csrf_protect
@rate_limit_login()
def login_view(request):
    """
    User login view (email-based authentication).
    
    This view handles user login using email and password.
    Uses Django's authentication system with email as USERNAME_FIELD.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered login template or redirect to next page
    """
    if request.user.is_authenticated:
        # User is already logged in, redirect to home
        return redirect('core:home')
    
    if request.method == 'POST':
        # CSRF protection is handled by @csrf_protect decorator and Django middleware
        # If CSRF fails, Django will raise CSRF error before reaching here
        # Log CSRF token for debugging
        logger.debug(f"[LOGIN] CSRF token present: {'csrfmiddlewaretoken' in request.POST}")
        logger.debug(f"[LOGIN] Request META CSRF_COOKIE: {request.META.get('CSRF_COOKIE', 'NOT SET')}")
        
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        next_url = request.POST.get('next', request.GET.get('next', ''))
        
        if not email or not password:
            messages.error(request, 'Email and password are required.')
            return render(request, 'accounts/login.html', {
                'email': email,
                'next': next_url,
            })
        
        # Authenticate using email (USERNAME_FIELD)
        user = authenticate(request, username=email, password=password)
        
        # Better error handling: Check if user exists first (for better error messages)
        user_exists = False
        if email:
            try:
                existing_user = User.objects.get(email=email)
                user_exists = True
                logger.debug(f"[LOGIN] User exists: {email}, is_active: {existing_user.is_active}, status: {existing_user.status}, role: {existing_user.role}")
            except User.DoesNotExist:
                user_exists = False
                logger.debug(f"[LOGIN] User does not exist: {email}")
        
        if user is not None:
            # TASK 16: Check if user is active (login blocked for inactive users)
            if user.is_active and user.status != 'deactivated':
                # TASK 6: Login guards for Pandits - block if email_verified == False or status == pending
                if user.role == 'pandit':
                    if not user.email_verified:
                        messages.error(request, 'Please verify your email address to continue.')
                        return render(request, 'accounts/login.html', {
                            'email': email,
                            'next': next_url,
                        })
                    if user.status == 'pending':
                        messages.error(request, 'Your profile is under review by an Admin Pandit. You will be notified upon approval.')
                        return render(request, 'accounts/login.html', {
                            'email': email,
                            'next': next_url,
                        })
                
                if user.role != 'pandit':
                    # Expert guard: stop before session creation when expert approval is pending
                    from core.models import ExpertProfile

                    pending_expert = ExpertProfile.objects.filter(
                        email__iexact=user.email,
                        is_active=False
                    ).first()

                    active_expert = ExpertProfile.objects.filter(
                        email__iexact=user.email,
                        is_active=True
                    ).first()

                    if pending_expert and not active_expert:
                        messages.error(request, "Your expert profile is pending admin approval.")
                        return redirect("expert_pending")

                login(request, user)
                # SECURITY FIX: Regenerate session ID to prevent session fixation
                request.session.cycle_key()
                
                # Safety: Ensure PanditProfile exists for pandit users
                if user.role == 'pandit':
                    try:
                        from profiles.models import PanditProfile
                        # 🔒 SAFE: Use filter().first() instead of get_or_create to avoid M2M issues
                        profile = PanditProfile.objects.filter(user=user).first()
                        if not profile:
                            # Create new profile
                            profile = PanditProfile(user=user)
                            # Save immediately to get primary key
                            profile.save()
                        
                        # Show "Complete Your Profile" message for new or incomplete profiles
                        # Only check completion if profile has been saved (has primary key)
                        if profile.pk:
                            try:
                                is_complete = profile.is_profile_complete()
                                is_approved = profile.is_profile_approved
                                if not is_complete or not is_approved:
                                    completion = profile.get_completion_percentage()
                                    if completion < 100:
                                        from django.urls import reverse
                                        edit_url = reverse('profiles:profile_edit')
                                        messages.info(
                                            request, 
                                            f'Welcome! Please complete your profile ({completion}% complete) to make it visible to the public. '
                                            f'<a href="{edit_url}" class="alert-link">Complete Profile →</a>',
                                            extra_tags='safe'
                                        )
                                    elif not is_approved:
                                        messages.info(
                                            request,
                                            'Your profile is complete! It is pending admin approval to be visible to the public.'
                                        )
                            except Exception as e:
                                # If completion check fails, log but don't block login
                                logger.warning(f"Failed to check profile completion for {user.email}: {str(e)}")
                    except Exception as e:
                        # Log error but don't block login - profile can be created manually later
                        logger.warning(f"Failed to ensure PanditProfile for {user.email}: {str(e)}")
                
                messages.success(request, f'Welcome back, {user.get_full_name() or user.email}!')
                
                # Log user details for debugging
                logger.info(f"[LOGIN REDIRECT] User: {user.email}, Role: {user.role}, is_superuser: {user.is_superuser}, is_staff: {user.is_staff}")
                
                # Redirect to next URL or role-based dashboard
                if next_url:
                    logger.info(f"[LOGIN REDIRECT] Redirecting to next_url: {next_url}")
                    return redirect(next_url)
                
                # Role-based redirect
                # IMPORTANT: Check is_superuser FIRST, then role
                # Order matters: superuser > admin > pandit > user
                
                # 1. Superuser always goes to Super Admin Dashboard
                if user.is_superuser:
                    logger.info(f"[LOGIN REDIRECT] User {user.email} is superuser → dashboard_super_admin")
                    return redirect('module5_dashboards:dashboard_super_admin')
                
                # 2. Admin Pandit (role='admin' but NOT superuser) → Admin Pandit Dashboard
                # NOTE: Admin Pandits have role='admin' and manage other Pandits
                elif user.role == 'admin':
                    logger.info(f"[LOGIN REDIRECT] User {user.email} has role='admin' (not superuser) → dashboard_admin_pandit")
                    return redirect('module5_dashboards:dashboard_admin_pandit')
                
                # 3. Regular Pandit (role='pandit') → Pandit Dashboard
                # NOTE: Regular Pandits have role='pandit' and manage their own profile
                elif user.role == 'pandit':
                    logger.info(f"[LOGIN REDIRECT] User {user.email} has role='pandit' → dashboard_pandit")
                    return redirect('module5_dashboards:dashboard_pandit')
                
                # 4. End User (role='user') → Home Page (not dashboard)
                else:
                    logger.info(f"[LOGIN REDIRECT] User {user.email} has role='{user.role}' → core:home")
                    return redirect('core:home')
            else:
                # TASK 16: Clear error message for inactive/deactivated accounts
                if user.status == 'deactivated':
                    messages.error(
                        request,
                        'Your account has been deactivated. Please contact support to reactivate your account.'
                    )
                else:
                    messages.error(request, 'Your account is inactive. Please contact support.')
                
                # Log blocked login attempt
                logger.warning(
                    f"Login blocked for inactive/deactivated account - "
                    f"User: {user.email} (ID: {user.id}), "
                    f"Is Active: {user.is_active}, "
                    f"Status: {user.status}"
                )
                
                # Log audit event
                from core.audit import log_deactivation
                log_deactivation(
                    user,
                    actor=None,
                    reason="LOGIN_BLOCKED_INACTIVE_ACCOUNT - Account inactive or deactivated"
                )
        else:
            # Provide more helpful error message based on whether user exists
            if user_exists:
                try:
                    existing_user = User.objects.get(email=email)
                    if not existing_user.is_active:
                        messages.error(request, 'Your account is inactive. Please contact support to activate your account.')
                    elif existing_user.status == 'deactivated':
                        messages.error(request, 'Your account has been deactivated. Please contact support to reactivate your account.')
                    elif existing_user.role == 'pandit' and not existing_user.email_verified:
                        messages.error(request, 'Please verify your email address to continue. Check your inbox for the verification link.')
                    elif existing_user.role == 'pandit' and existing_user.status == 'pending':
                        messages.error(request, 'Your profile is under review by an Admin Pandit. You will be notified upon approval.')
                    else:
                        messages.error(request, 'Invalid password. Please check your password and try again.')
                except User.DoesNotExist:
                    messages.error(request, 'Invalid email or password.')
            else:
                messages.error(request, 'Invalid email or password. Please check your email address and try again.')
        
        return render(request, 'accounts/login.html', {
            'email': email,
            'next': next_url,
        })
    
    # GET request - show login form
    return render(request, 'accounts/login.html', {
        'next': request.GET.get('next', ''),
    })


def register_view(request):
    """
    End User registration view.

    Flow (when OTP enabled):
      Validate form → create user (is_phone_verified=False) → return / show OTP UI.
    OTP send/verify still uses existing /otp/registration/* endpoints.
    """
    from otp_verification import constants as otp_constants
    from otp_verification.registration.factory import is_registration_otp_required

    from .phone_utils import normalize_phone_number, phone_already_registered

    wants_json = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in (request.headers.get("Accept") or "")
    )
    otp_required = is_registration_otp_required(otp_constants.FLOW_USER_REGISTRATION)

    # Logged-in unverified users should verify from profile, not re-register.
    if request.user.is_authenticated:
        if (
            getattr(request.user, "role", None) == "user"
            and not getattr(request.user, "is_phone_verified", True)
            and otp_required
        ):
            return redirect("accounts:profile_settings")
        return redirect("core:home")

    def _form_context(**extra):
        ctx = {
            "email": extra.get("email", ""),
            "first_name": extra.get("first_name", ""),
            "last_name": extra.get("last_name", ""),
            "phone_number": extra.get("phone_number", ""),
            "otp_required": otp_required,
            "post_register_otp": False,
        }
        ctx.update(extra)
        return ctx

    def _error_response(message, status=400, **fields):
        if wants_json:
            return JsonResponse(
                {
                    "status": "error",
                    "error": "validation_error",
                    "error_code": "validation_error",
                    "result": None,
                    "message": message,
                },
                status=status,
            )
        messages.error(request, message)
        return render(request, "accounts/register.html", _form_context(**fields))

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        phone_raw = request.POST.get("phone_number", "").strip()

        if not email:
            return _error_response(
                "Email address is required.",
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_raw,
            )
        if not password:
            return _error_response(
                "Password is required.",
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_raw,
            )
        if password != password_confirm:
            return _error_response(
                "Passwords do not match.",
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_raw,
            )
        if User.objects.filter(email__iexact=email).exists():
            return _error_response(
                "A user with this email address already exists.",
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_raw,
            )

        normalized_phone = ""
        if otp_required or phone_raw:
            if not phone_raw:
                return _error_response(
                    "Phone number is required for SMS verification.",
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=phone_raw,
                )
            normalized_phone = normalize_phone_number(phone_raw)
            if not normalized_phone:
                return _error_response(
                    "Phone number format is invalid.",
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=phone_raw,
                )
            if phone_already_registered(normalized_phone):
                logger.warning(
                    "Duplicate phone registration attempt",
                    extra={"email": email, "phone": normalized_phone},
                )
                return _error_response(
                    "Phone number already registered",
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=phone_raw,
                )

        try:
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role="user",
                status="active",
                is_active=True,
                email_verified=False,
                phone_number=normalized_phone or None,
                is_phone_verified=False,
            )
        except Exception as e:
            logger.exception("User registration failed for %s", email)
            return _error_response(
                f"Registration failed: {str(e)}",
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_raw,
            )

        try:
            create_email_verification(user)
        except Exception as e:
            logger.error(
                "Failed to send verification email for %s: %s",
                user.email,
                str(e),
                exc_info=True,
            )

        # Log in so post-registration OTP can bind to this account.
        login(request, user)

        if otp_required:
            display_phone = (
                normalized_phone[2:]
                if normalized_phone.startswith("91") and len(normalized_phone) == 12
                else (normalized_phone or phone_raw)
            )
            if wants_json:
                return JsonResponse(
                    {
                        "status": "created_unverified",
                        "message": "Profile created. Please verify mobile.",
                        "phone_number": display_phone,
                        "flow_type": otp_constants.FLOW_USER_REGISTRATION,
                        "result": {
                            "phone_number": display_phone,
                            "flow_type": otp_constants.FLOW_USER_REGISTRATION,
                        },
                        "error_code": None,
                    }
                )
            messages.success(
                request,
                "Your profile has been created. Please verify your mobile number.",
            )
            return render(
                request,
                "accounts/register.html",
                _form_context(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=display_phone,
                    post_register_otp=True,
                    otp_required=True,
                ),
            )

        messages.success(
            request,
            "Account created successfully! Please check your email to verify your address before logging in.",
        )
        if wants_json:
            return JsonResponse(
                {
                    "status": "created",
                    "message": "Account created successfully.",
                    "redirect": "/accounts/login/",
                    "result": {"redirect": "/accounts/login/"},
                    "error_code": None,
                }
            )
        return redirect("accounts:login")

    return render(
        request,
        "accounts/register.html",
        {"otp_required": otp_required, "post_register_otp": False},
    )


def logout_view(request):
    """
    User logout view.
    
    This view handles user logout and destroys the session.
    
    Args:
        request: HTTP request object
        
    Returns:
        Redirect to home page
    """
    logout(request)
    # SECURITY FIX: Invalidate session server-side to prevent reuse
    request.session.flush()
    messages.success(request, 'You have been logged out successfully.')
    return redirect('core:home')


def password_reset_request(request):
    """
    Password reset request view.
    
    Allows users to request a password reset by entering their email.
    Sends a password reset email if the email exists in the system.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered password reset request template or redirect
    """
    if request.user.is_authenticated:
        # User is already logged in, redirect to home
        return redirect('core:home')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, 'Email address is required.')
            return render(request, 'accounts/password_reset_request.html')
        
        # Check if user exists
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            # Don't reveal if email exists or not (security best practice)
            messages.success(request, 'If an account exists with this email, a password reset link has been sent.')
            return render(request, 'accounts/password_reset_request.html')
        
        # Generate password reset token
        # SECURITY NOTE: Using Django's default_token_generator which:
        # - Generates secure random tokens
        # - Enforces token expiry (default: 1 day)
        # - Validates tokens are single-use
        # No custom implementation needed - Django handles security
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.core.mail import send_mail
        from django.conf import settings
        
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build reset URL
        reset_url = request.build_absolute_uri(
            f'/accounts/password-reset-confirm/{uid}/{token}/'
        )
        
        # Send email
        subject = 'Password Reset Request - Nitya Dharma'
        message = f'''
Hello {user.get_full_name() or user.email},

You requested a password reset for your Nitya Dharma account.

Please click the link below to reset your password:
{reset_url}

This link will expire in 24 hours.

If you did not request this password reset, please ignore this email.

Best regards,
Nitya Dharma Team
        '''
        
        try:
            try:
                # NOTE:
                # If Redis is UP but Celery worker is DOWN,
                # tasks will queue and NOT execute immediately.
                # This is expected Celery behavior.
                from core.tasks_email import send_email_task

                send_email_task.delay(
                    subject,
                    message,
                    getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nityadharma.com'),
                    [user.email],
                )
            except Exception:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nityadharma.com'),
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            messages.success(request, 'If an account exists with this email, a password reset link has been sent.')
        except Exception as e:
            messages.error(request, f'Failed to send email: {str(e)}')
        
        return render(request, 'accounts/password_reset_request.html')
    
    # GET request - show password reset form
    return render(request, 'accounts/password_reset_request.html')


def password_reset_confirm(request, uidb64, token):
    """
    Password reset confirmation view.
    
    Validates the reset token and allows user to set a new password.
    
    Args:
        request: HTTP request object
        uidb64: Base64 encoded user ID
        token: Password reset token
        
    Returns:
        Rendered password reset confirm template or redirect
    """
    if request.user.is_authenticated:
        # User is already logged in, redirect to home
        return redirect('core:home')
    
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str
    
    try:
        # Decode user ID
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid, is_active=True)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    # Validate token
    if user is not None and default_token_generator.check_token(user, token):
        # Token is valid
        if request.method == 'POST':
            password = request.POST.get('password', '')
            password_confirm = request.POST.get('password_confirm', '')
            
            if not password:
                messages.error(request, 'Password is required.')
                return render(request, 'accounts/password_reset_confirm.html', {
                    'valid_link': True,
                    'uidb64': uidb64,
                    'token': token,
                })
            
            if password != password_confirm:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'accounts/password_reset_confirm.html', {
                    'valid_link': True,
                    'uidb64': uidb64,
                    'token': token,
                })
            
            # Validate password strength
            from django.contrib.auth.password_validation import validate_password
            try:
                validate_password(password, user)
            except Exception as e:
                messages.error(request, f'Password validation failed: {", ".join(e.messages)}')
                return render(request, 'accounts/password_reset_confirm.html', {
                    'valid_link': True,
                    'uidb64': uidb64,
                    'token': token,
                })
            
            # Set new password
            user.set_password(password)
            user.save()
            
            messages.success(request, 'Your password has been reset successfully. Please login with your new password.')
            return redirect('accounts:login')
        
        # GET request - show password reset form
        return render(request, 'accounts/password_reset_confirm.html', {
            'valid_link': True,
            'uidb64': uidb64,
            'token': token,
        })
    else:
        # Invalid token
        messages.error(request, 'Invalid or expired password reset link. Please request a new one.')
        return render(request, 'accounts/password_reset_confirm.html', {
            'valid_link': False,
        })


# ============================================================================
# Account Settings Views (My Account)
# ============================================================================

@login_required
def account_settings_base(request):
    """
    Base view for account settings - redirects to profile settings.
    """
    return redirect('accounts:profile_settings')


@login_required
def profile_settings(request):
    """
    Profile Settings page - allows user to update basic personal info.
    
    UI-only view - backend handles validation and save logic.
    """
    from otp_verification.registration.factory import is_registration_otp_required
    from otp_verification import constants as otp_constants

    from .phone_utils import normalize_phone_number, phone_already_registered

    needs_phone_otp = (
        getattr(request.user, "role", None) == "user"
        and not getattr(request.user, "is_phone_verified", True)
        and is_registration_otp_required(otp_constants.FLOW_USER_REGISTRATION)
    )

    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        whatsapp_number = request.POST.get('whatsapp_number', '').strip()
        delete_picture = request.POST.get('delete_picture', '0') == '1'
        
        # Update user fields
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        
        # Update phone numbers (if fields exist)
        if hasattr(user, 'phone_number'):
            normalized = normalize_phone_number(phone_number) if phone_number else None
            if phone_number and not normalized:
                messages.error(request, 'Phone number format is invalid.')
                return render(request, 'account/profile_settings.html', {
                    'user': request.user,
                    'active_tab': 'profile',
                    'user_id': request.user.id,
                    'needs_phone_otp': needs_phone_otp,
                    'display_phone': phone_number,
                })
            if normalized:
                if phone_already_registered(normalized, exclude_user_id=user.pk):
                    messages.error(request, 'Phone number already registered')
                    return render(request, 'account/profile_settings.html', {
                        'user': request.user,
                        'active_tab': 'profile',
                        'user_id': request.user.id,
                        'needs_phone_otp': needs_phone_otp,
                        'display_phone': phone_number,
                    })
                old = normalize_phone_number(str(user.phone_number or ""))
                if old != normalized:
                    user.is_phone_verified = False
                    user.phone_verified_at = None
                user.phone_number = normalized
            else:
                user.phone_number = None
                user.is_phone_verified = False
                user.phone_verified_at = None
        if hasattr(user, 'whatsapp_number'):
            user.whatsapp_number = whatsapp_number if whatsapp_number else None
        
        # Handle profile picture upload/delete
        if delete_picture:
            # Delete existing profile picture
            if user.profile_picture:
                user.profile_picture.delete(save=False)
            user.profile_picture = None
        elif 'profile_picture' in request.FILES:
            # Upload new profile picture
            uploaded_file = request.FILES['profile_picture']
            
            # PART 4 FIX: Centralized file upload validation
            try:
                from core.file_upload_security import validate_image_upload
                sanitized_filename, validated_file = validate_image_upload(uploaded_file)
                uploaded_file = validated_file  # Use validated file
            except ValidationError as e:
                messages.error(request, f'File upload validation failed: {str(e)}')
                user_id = getattr(request, 'user_id', request.user.id)
                return render(request, 'account/profile_settings.html', {
                    'user': request.user,
                    'active_tab': 'profile',
                    'user_id': user_id,
                    'needs_phone_otp': needs_phone_otp,
                })
            
            # Delete old picture if exists
            if user.profile_picture:
                user.profile_picture.delete(save=False)
            
            # Save new picture
            user.profile_picture = uploaded_file
        
        try:
            user.save()
            messages.success(request, 'Profile updated successfully!')
            user_id = getattr(request, 'user_id', None)
            if user_id:
                return redirect('accounts:profile_settings_with_id', user_id=user_id)
            return redirect('accounts:profile_settings')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
    
    # GET request - show form
    raw_phone = str(getattr(request.user, "phone_number", "") or "")
    display_phone = (
        raw_phone[2:]
        if raw_phone.startswith("91") and len(raw_phone) == 12 and raw_phone.isdigit()
        else raw_phone
    )
    needs_phone_otp = (
        getattr(request.user, "role", None) == "user"
        and not getattr(request.user, "is_phone_verified", True)
        and is_registration_otp_required(otp_constants.FLOW_USER_REGISTRATION)
    )
    return render(request, 'account/profile_settings.html', {
        'user': request.user,
        'active_tab': 'profile',
        'user_id': request.user.id,
        'needs_phone_otp': needs_phone_otp,
        'display_phone': display_phone,
    })


@login_required
def security_settings(request):
    """
    Security Settings page - allows user to change password.
    
    UI-only view - backend handles validation and password hashing.
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'change_password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            
            # Validate passwords match
            if new_password != confirm_password:
                messages.error(request, 'New password and confirm password do not match.')
                user_id = getattr(request, 'user_id', request.user.id)
                return render(request, 'account/security_settings.html', {
                    'user': request.user,
                    'active_tab': 'security',
                    'user_id': user_id,
                })
            
            # Verify current password
            user = request.user
            if not user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
                user_id = getattr(request, 'user_id', request.user.id)
                return render(request, 'account/security_settings.html', {
                    'user': request.user,
                    'active_tab': 'security',
                    'user_id': user_id,
                })
            
            # Update password
            try:
                user.set_password(new_password)
                user.save()
                # Update session to prevent logout
                update_session_auth_hash(request, user)
                messages.success(request, 'Password updated successfully!')
                user_id = getattr(request, 'user_id', None)
                if user_id:
                    return redirect('accounts:security_settings_with_id', user_id=user_id)
                return redirect('accounts:security_settings')
            except Exception as e:
                messages.error(request, f'Error updating password: {str(e)}')
    
    # GET request - show form
    return render(request, 'account/security_settings.html', {
        'user': request.user,
        'active_tab': 'security',
        'user_id': request.user.id,
    })


@login_required
def account_notifications(request):
    """
    Account Notifications page - redirects to role-specific notification settings.
    """
    user = request.user
    user_id = user.id
    
    # Redirect to role-specific notification settings
    if user.is_superuser or (user.role == 'admin' and not user.is_superuser):
        return redirect('accounts:admin_notification_settings', user_id=user_id)
    elif user.role == 'pandit':
        return redirect('accounts:pandit_notification_settings', user_id=user_id)
    else:
        return redirect('accounts:user_notification_settings', user_id=user_id)


@login_required
def user_notification_settings(request, user_id):
    """
    User-specific notification settings page.
    
    Only the user themselves can access their own settings.
    """
    from notifications.models import NotificationPreference
    
    # Verify user can only access their own settings
    if request.user.id != user_id:
        messages.error(request, 'You can only access your own notification settings.')
        return redirect('accounts:user_notification_settings', user_id=request.user.id)
    
    user = request.user
    
    # Get or create notification preferences
    preferences, created = NotificationPreference.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        # Update user-specific preferences
        preferences.booking_intent_enabled = request.POST.get('booking_intent_enabled') == 'on'
        preferences.review_notifications_enabled = request.POST.get('review_notifications_enabled') == 'on'
        preferences.user_booking_updates_enabled = request.POST.get('user_booking_updates_enabled') == 'on'
        preferences.user_review_reminders_enabled = request.POST.get('user_review_reminders_enabled') == 'on'
        preferences.in_app_enabled = request.POST.get('in_app_enabled') == 'on'
        preferences.email_enabled = request.POST.get('email_enabled') == 'on'
        preferences.save()
        messages.success(request, 'Notification preferences updated successfully!')
        return redirect('accounts:user_notification_settings', user_id=user_id)
    
    return render(request, 'account/user_notification_settings.html', {
        'user': user,
        'preferences': preferences,
        'active_tab': 'notifications',
        'user_id': user_id,
    })


@login_required
def pandit_notification_settings(request, user_id):
    """
    Pandit-specific notification settings page.
    
    Only the pandit themselves can access their own settings.
    """
    from notifications.models import NotificationPreference
    
    # Verify user can only access their own settings
    if request.user.id != user_id:
        messages.error(request, 'You can only access your own notification settings.')
        return redirect('accounts:pandit_notification_settings', user_id=request.user.id)
    
    # Verify user is a pandit
    if request.user.role != 'pandit':
        messages.error(request, 'Access denied. Pandit role required.')
        return redirect('core:home')
    
    user = request.user
    
    # Get or create notification preferences
    preferences, created = NotificationPreference.objects.get_or_create(user=user)
    
    # Get pandit profile if exists
    pandit_profile = None
    if hasattr(user, 'pandit_profile'):
        pandit_profile = user.pandit_profile
    
    if request.method == 'POST':
        # Update pandit-specific preferences
        preferences.booking_intent_enabled = request.POST.get('booking_intent_enabled') == 'on'
        preferences.review_notifications_enabled = request.POST.get('review_notifications_enabled') == 'on'
        preferences.pandit_booking_requests_enabled = request.POST.get('pandit_booking_requests_enabled') == 'on'
        preferences.pandit_profile_updates_enabled = request.POST.get('pandit_profile_updates_enabled') == 'on'
        preferences.pandit_review_submissions_enabled = request.POST.get('pandit_review_submissions_enabled') == 'on'
        preferences.in_app_enabled = request.POST.get('in_app_enabled') == 'on'
        preferences.email_enabled = request.POST.get('email_enabled') == 'on'
        preferences.save()
        messages.success(request, 'Notification preferences updated successfully!')
        return redirect('accounts:pandit_notification_settings', user_id=user_id)
    
    return render(request, 'account/pandit_notification_settings.html', {
        'user': user,
        'preferences': preferences,
        'pandit_profile': pandit_profile,
        'active_tab': 'notifications',
        'user_id': user_id,
        'profile_id': pandit_profile.id if pandit_profile else None,
    })


@login_required
def admin_notification_settings(request, user_id):
    """
    Admin Pandit-specific notification settings page.
    
    Only the admin themselves can access their own settings.
    """
    from notifications.models import NotificationPreference
    
    # Verify user can only access their own settings
    if request.user.id != user_id:
        messages.error(request, 'You can only access your own notification settings.')
        return redirect('accounts:admin_notification_settings', user_id=request.user.id)
    
    # Verify user is an admin
    if not (request.user.is_superuser or request.user.role == 'admin'):
        messages.error(request, 'Access denied. Admin role required.')
        return redirect('core:home')
    
    user = request.user
    
    # Get or create notification preferences
    preferences, created = NotificationPreference.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        # Update admin-specific preferences
        preferences.booking_intent_enabled = request.POST.get('booking_intent_enabled') == 'on'
        preferences.review_notifications_enabled = request.POST.get('review_notifications_enabled') == 'on'
        preferences.admin_pandit_approval_requests_enabled = request.POST.get('admin_pandit_approval_requests_enabled') == 'on'
        preferences.admin_pandit_profile_approvals_enabled = request.POST.get('admin_pandit_profile_approvals_enabled') == 'on'
        preferences.admin_pandit_partial_blocks_enabled = request.POST.get('admin_pandit_partial_blocks_enabled') == 'on'
        preferences.admin_pandit_referral_usage_enabled = request.POST.get('admin_pandit_referral_usage_enabled') == 'on'
        preferences.in_app_enabled = request.POST.get('in_app_enabled') == 'on'
        preferences.email_enabled = request.POST.get('email_enabled') == 'on'
        preferences.save()
        messages.success(request, 'Notification preferences updated successfully!')
        return redirect('accounts:admin_notification_settings', user_id=user_id)
    
    return render(request, 'account/admin_notification_settings.html', {
        'user': user,
        'preferences': preferences,
        'active_tab': 'notifications',
        'user_id': user_id,
    })


@login_required
def admin_notification_list(request, user_id):
    """
    Admin Pandit Notification List page with tabs for different notification sources.
    
    Shows notifications from:
    - Users (booking intents, reviews)
    - Other Pandits (approval requests, profile updates)
    - Temples (page updates, management)
    """
    from notifications.models import Notification
    from django.db.models import Q
    from django.utils import timezone
    
    # Verify user can only access their own notifications
    if request.user.id != user_id:
        messages.error(request, 'You can only access your own notifications.')
        return redirect('accounts:admin_notification_list', user_id=request.user.id)
    
    # Verify user is an admin
    if not (request.user.is_superuser or request.user.role == 'admin'):
        messages.error(request, 'Access denied. Admin role required.')
        return redirect('core:home')
    
    user = request.user
    
    # Get all notifications for this admin
    all_notifications = Notification.objects.filter(
        recipient=user
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    ).order_by('-created_at')
    
    # Categorize notifications by source
    # User notifications: booking intents, reviews, and contact form submissions
    user_notifications = all_notifications.filter(
        Q(source_module='booking_intent') |
        Q(source_module='reviews') |
        Q(source_module='support') |
        Q(notification_type='booking_intent') |
        Q(notification_type='review')
    )
    
    # Pandit notifications: approval requests, profile updates, governance actions
    # Filter by source_module and notification_type (not payload since it's JSONField)
    pandit_notifications = all_notifications.filter(
        Q(source_module='accounts') |
        Q(source_module='profiles') |
        Q(source_module='governance') |
        Q(notification_type='governance')
    ).exclude(
        # Exclude user-related notifications that might match
        Q(source_module='booking_intent') |
        Q(source_module='reviews') |
        Q(source_module='pages') |
        Q(source_module='support')
    )
    
    # Temple notifications: page updates and temple announcements
    temple_notifications = all_notifications.filter(
        Q(source_module='pages') |
        Q(notification_type='page_update') |
        Q(notification_type='temple_announcement')
    )
    
    # Get unread counts (badge clears only when user explicitly marks as read)
    user_unread_count = user_notifications.filter(is_read=False).count()
    pandit_unread_count = pandit_notifications.filter(is_read=False).count()
    temple_unread_count = temple_notifications.filter(is_read=False).count()

    return render(request, 'account/admin_notification_list.html', {
        'user': user,
        'user_id': user_id,
        'user_notifications': user_notifications[:50],
        'pandit_notifications': pandit_notifications[:50],
        'temple_notifications': temple_notifications[:50],
        'user_unread_count': user_unread_count,
        'pandit_unread_count': pandit_unread_count,
        'temple_unread_count': temple_unread_count,
        'total_unread_count': user_unread_count + pandit_unread_count + temple_unread_count,
    })


@login_required
def profile_settings_with_id(request, user_id):
    """
    Profile Settings page with user_id identifier.
    Wrapper that calls profile_settings with user_id.
    """
    if request.user.id != user_id:
        messages.error(request, 'You can only access your own profile settings.')
        return redirect('accounts:profile_settings_with_id', user_id=request.user.id)
    # Call the main profile_settings view with user_id
    return profile_settings(request)


@login_required
def security_settings_with_id(request, user_id):
    """
    Security Settings page with user_id identifier.
    Wrapper that calls security_settings.
    """
    if request.user.id != user_id:
        messages.error(request, 'You can only access your own security settings.')
        return redirect('accounts:security_settings_with_id', user_id=request.user.id)
    # Call the main security_settings view
    return security_settings(request)


@login_required
def account_delete(request):
    """
    Delete Account page - dangerous action with confirmation.
    
    UI-only view - backend handles soft delete / hard delete logic.
    """
    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm_delete = request.POST.get('confirm_delete')
        
        # Validate confirmation
        if not confirm_delete:
            messages.error(request, 'You must confirm that you understand this action is irreversible.')
            return render(request, 'account/account_delete.html', {
                'user': request.user,
                'active_tab': 'delete',
            })
        
        # Verify password
        user = request.user
        if not user.check_password(password):
            messages.error(request, 'Password is incorrect.')
            return render(request, 'account/account_delete.html', {
                'user': request.user,
                'active_tab': 'delete',
            })
        
        # Delete account (soft delete - set is_active=False)
        try:
            user.is_active = False
            user.save()
            messages.success(request, 'Your account has been deactivated. We are sorry to see you go.')
            logout(request)
            return redirect('core:home')
        except Exception as e:
            messages.error(request, f'Error deleting account: {str(e)}')
    
    # GET request - show confirmation form
    return render(request, 'account/account_delete.html', {
        'user': request.user,
        'active_tab': 'delete',
    })

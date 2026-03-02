"""
Referral link generation and lifecycle management views.

This module provides backend endpoints for:
- Generating referral links (Admin Pandit/Super Admin only)
- Deactivating referral links
- Enforcing referral lifecycle rules
- Referral policy (GET for Admin; edit for Super Admin only)

All endpoints return JSON responses and enforce strict access control.
Creation and revoke logic live in referrals.services; views call service only.
"""

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied

from accounts.decorators import admin_required
from accounts.utils import is_admin
from .models import ReferralLink, ReferralPolicy
from .constants import AUDIT_ACTION_REFERRAL_CREATED
from . import services

User = get_user_model()


def _can_generate_referral(user):
    """
    Check if user can generate referral links.
    
    Requirements:
    - Must be Admin Pandit (role='admin', status='active') OR Super Admin
    - Must be active (is_active=True)
    - Must not be fully blocked (status='active')
    
    Args:
        user: User instance
        
    Returns:
        tuple: (can_generate: bool, error_message: str or None)
    """
    if not user or not user.is_authenticated:
        return False, "Authentication required"
    
    # Super Admin can always generate
    if user.is_superuser:
        return True, None
    
    # Admin Pandit must have active status
    if is_admin(user) and user.status == 'active' and user.is_active:
        return True, None
    
    # Regular Pandits cannot generate
    if user.role == 'pandit' and user.status != 'admin':
        return False, "Only Admin Pandits and Super Admins can generate referral links"
    
    # Pending/Rejected admins cannot generate
    if is_admin(user) and user.status != 'active':
        return False, f"Admin Pandits with status '{user.status}' cannot generate referral links. Status must be 'active'."
    
    # Inactive users cannot generate
    if not user.is_active:
        return False, "Inactive users cannot generate referral links"
    
    return False, "Access denied. Only Admin Pandits (active) and Super Admins can generate referral links."


# CSRF enforced for same-origin browser; frontend must send X-CSRFToken header or csrfmiddlewaretoken in form
@csrf_protect
@admin_required
@require_http_methods(["POST"])
def generate_referral_link(request):
    """
    Generate a new referral link with unique token and hexadecimal code.
    
    Access: Admin Pandit (role='admin', status='active') or Super Admin only
    
    Request: POST with optional JSON body (currently no parameters needed)
    Response: JSON with referral link details
    
    Returns:
        JsonResponse: Referral link data including token, code, and URL
    """
    # Check if user can generate referral links
    can_generate, error_message = _can_generate_referral(request.user)
    if not can_generate:
        return JsonResponse({
            'error': 'Access denied',
            'message': error_message or 'Only Admin Pandits (active) and Super Admins can generate referral links',
            'user_role': request.user.role if request.user.is_authenticated else 'anonymous',
            'user_status': request.user.status if request.user.is_authenticated else 'unknown',
            'is_superuser': request.user.is_superuser if request.user.is_authenticated else False
        }, status=403)
    
    try:
        policy = ReferralPolicy.load()
        try:
            body = json.loads(request.body) if request.body else {}
        except (json.JSONDecodeError, TypeError):
            body = {}
        tiers = list(policy.allowed_max_use_tiers) if isinstance(policy.allowed_max_use_tiers, (list, tuple)) else []
        if not tiers:
            tiers = [min(policy.max_allowed_uses, 100)]
        expiry_days = body.get('expiry_days')
        if expiry_days is None:
            expiry_days = policy.default_expiry_days
        max_uses = body.get('max_uses')
        if max_uses is None:
            max_uses = tiers[0]

        try:
            referral_link = services.create_referral_link(
                creator=request.user,
                max_uses=max_uses,
                expiry_days=expiry_days,
            )
        except ValueError as e:
            return JsonResponse({
                'error': 'Invalid tier' if 'max_uses' in str(e).lower() else 'Validation failed',
                'message': str(e),
                'allowed_max_use_tiers': tiers,
                'max_allowed_uses': policy.max_allowed_uses,
            }, status=400)

        # TASK 9: Log audit event
        try:
            from analytics.audit_events import log_audit_event
            log_audit_event(
                event_type=AUDIT_ACTION_REFERRAL_CREATED,
                user=request.user,
                metadata={
                    'referral_link_id': referral_link.id,
                    'token': (referral_link.token or '')[:8] + '...',
                    'expires_at': referral_link.expires_at.isoformat(),
                    'expiry_days': (referral_link.expires_at - referral_link.created_at).days if referral_link.created_at else 0,
                    'max_uses': referral_link.max_uses,
                }
            )
        except Exception:
            pass

        # Behavior tracking: log referral_link_generated for Super Admin analytics
        try:
            from behavior_engine.models import BehaviorEvent
            session_key = (getattr(request, 'session', None) and request.session.session_key) or ''
            BehaviorEvent.objects.create(
                user=request.user,
                session_id=(session_key or '')[:120],
                event_type='referral_link_generated',
                entity_type='referral_link',
                entity_id=str(referral_link.id),
                page_url='',
                page_title='',
                metadata={
                    'tier': referral_link.max_uses,
                    'expiry_days': (referral_link.expires_at - referral_link.created_at).days if referral_link.created_at else 0,
                    'created_by': request.user.id,
                },
            )
        except Exception:
            pass

        referral_url = f"/accounts/pandit/register/{referral_link.token}/"
        
        return JsonResponse({
            'success': True,
            'message': 'Referral link generated successfully',
            'referral_link': {
                'id': referral_link.id,
                'token': referral_link.token,
                'referral_code': referral_link.referral_code,
                'url': referral_url,
                'max_uses': referral_link.max_uses,
                'used_count': referral_link.used_count,
                'is_active': referral_link.is_active,
                'created_at': referral_link.created_at.isoformat(),
                'created_by': {
                    'id': referral_link.created_by.id,
                    'email': referral_link.created_by.email,
                    'role': referral_link.created_by.role,
                    'status': referral_link.created_by.status
                }
            }
        }, status=201)
        
    except Exception as e:
        return JsonResponse({
            'error': 'Generation failed',
            'message': f'An error occurred while generating referral link: {str(e)}'
        }, status=500)


@admin_required
@require_http_methods(["GET"])
def get_referral_policy(request):
    """
    Return current referral policy for Admin Pandit dashboard (dropdowns).
    Read-only; policy edit is Super Admin only.
    """
    can_generate, _ = _can_generate_referral(request.user)
    if not can_generate:
        return JsonResponse({'error': 'Access denied'}, status=403)
    policy = ReferralPolicy.load()
    tiers = policy.allowed_max_use_tiers
    if not isinstance(tiers, (list, tuple)):
        tiers = [5]
    return JsonResponse({
        'default_expiry_days': policy.default_expiry_days,
        'allowed_max_use_tiers': list(tiers),
        'max_allowed_expiry_days': policy.max_allowed_expiry_days,
        'max_allowed_uses': policy.max_allowed_uses,
    })


def referral_policy_edit(request):
    """Super Admin only: edit referral policy. Policy applies only to newly created links."""
    if not request.user.is_authenticated or not request.user.is_superuser:
        raise PermissionDenied
    from django.shortcuts import redirect
    policy = ReferralPolicy.load()
    if request.method == 'POST':
        try:
            default_expiry = int(request.POST.get('default_expiry_days', policy.default_expiry_days))
            max_expiry = int(request.POST.get('max_allowed_expiry_days', policy.max_allowed_expiry_days))
            max_uses_cap = int(request.POST.get('max_allowed_uses', policy.max_allowed_uses))
            tiers_raw = request.POST.get('allowed_max_use_tiers', '')
            tiers = []
            for part in tiers_raw.replace(' ', '').split(','):
                part = part.strip()
                if part.isdigit():
                    n = int(part)
                    if 1 <= n <= 100 and n not in tiers:
                        tiers.append(n)
            if not tiers:
                tiers = [5]
            tiers.sort()
            policy.default_expiry_days = min(max(1, default_expiry), 365)
            policy.max_allowed_expiry_days = min(max(1, max_expiry), 365)
            policy.max_allowed_uses = min(max(1, max_uses_cap), 100)
            policy.allowed_max_use_tiers = tiers
            policy.save()
            messages.success(request, 'Referral policy updated. Changes apply only to new links.')
            return redirect('referrals:referral_policy_edit')
        except (ValueError, TypeError):
            messages.error(request, 'Invalid values. Please enter numbers only.')
    tiers_display = ','.join(str(t) for t in (policy.allowed_max_use_tiers or [5]))
    return render(request, 'referrals/referral_policy_edit.html', {
        'policy': policy,
        'tiers_display': tiers_display,
    })


# CSRF enforced for same-origin browser; frontend must send X-CSRFToken header or csrfmiddlewaretoken in form
@csrf_protect
@admin_required
@require_http_methods(["POST"])
def deactivate_referral_link(request, referral_link_id):
    """
    Deactivate an existing referral link.
    
    Access: Admin Pandit (role='admin', status='active') or Super Admin only
    
    Args:
        referral_link_id: ID of the referral link to deactivate
        
    Returns:
        JsonResponse: Success or error message
    """
    # Check if user can manage referral links
    can_generate, error_message = _can_generate_referral(request.user)
    if not can_generate:
        return JsonResponse({
            'error': 'Access denied',
            'message': error_message or 'Only Admin Pandits (active) and Super Admins can manage referral links',
            'user_role': request.user.role if request.user.is_authenticated else 'anonymous',
            'user_status': request.user.status if request.user.is_authenticated else 'unknown',
            'is_superuser': request.user.is_superuser if request.user.is_authenticated else False
        }, status=403)
    
    try:
        referral_link = services.revoke_referral_link(referral_link_id, request.user)
        return JsonResponse({
            'success': True,
            'message': f'Referral link {referral_link_id} deactivated successfully',
            'referral_link': {
                'id': referral_link.id,
                'token': (referral_link.token or '')[:8] + '...',
                'is_active': referral_link.is_active,
                'used_count': referral_link.used_count,
                'max_uses': referral_link.max_uses,
                'deactivated_at': referral_link.updated_at.isoformat()
            }
        }, status=200)
    except ValueError as e:
        if "already inactive" in str(e).lower():
            referral_link = get_object_or_404(ReferralLink, id=referral_link_id)
            return JsonResponse({
                'error': 'Already inactive',
                'message': f'Referral link {referral_link_id} is already inactive',
                'referral_link': {
                    'id': referral_link.id,
                    'token': (referral_link.token or '')[:8] + '...',
                    'is_active': referral_link.is_active,
                    'used_count': referral_link.used_count,
                    'max_uses': referral_link.max_uses
                }
            }, status=400)
        return JsonResponse({
            'error': 'Invalid referral link ID',
            'message': 'Referral link ID must be a valid integer'
        }, status=400)
    except PermissionDenied:
        return JsonResponse({
            'error': 'Access denied',
            'message': 'Only Admin Pandits (active) and Super Admins can manage referral links'
        }, status=403)
    except ReferralLink.DoesNotExist:
        return JsonResponse({
            'error': 'Not found',
            'message': f'Referral link {referral_link_id} not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': 'Deactivation failed',
            'message': f'An error occurred while deactivating referral link: {str(e)}'
        }, status=500)

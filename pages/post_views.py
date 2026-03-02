"""
Views for PagePost management (posts, announcements, events).

UNIT TASK 6: Temple Posts, Events & Announcements
"""
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError, PermissionDenied
from core.public_id import resolve_public_id, reject_bigint_id
from .models import Page, PagePost
from .page_permissions import can_create_post, can_pin_post, can_edit_post, can_edit_page_media
from engagement.services import record_view
from engagement.constants import ENTITY_PAGE_POST, INTERACTION_PIN, INTERACTION_UNPIN, INTERACTION_VIEW
from engagement.models import UserInteractionEvent


# PART 3 HARDENING: Explicit HTTP method declaration
from django.views.decorators.http import require_http_methods

@login_required
@require_http_methods(["GET", "POST"])
def create_post(request, page_public_id):
    """
    Create a new post for a page.
    
    Rules:
    - Admin Pandit: Can create posts for their own pages
    - Super Admin: Can create posts for any page
    """
    if reject_bigint_id(page_public_id):
        raise Http404("Invalid page ID format")
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        raise Http404("Page not found")
    
    # TASK 6: Check permissions using permission service (allows moderators)
    if not can_create_post(request.user, page):
        messages.error(request, "You do not have permission to create posts for this page.")
        return redirect('pages:page_detail', page_public_id=page_public_id)
    
    if request.method == 'POST':
        post_type = request.POST.get('post_type', '').strip()
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        event_date = request.POST.get('event_date', '').strip()
        event_location = request.POST.get('event_location', '').strip()
        
        if not title or not content:
            messages.error(request, "Title and content are required.")
            return redirect('pages:page_detail', page_public_id=page_public_id)
        
        if post_type not in PagePost.POST_TYPES:
            messages.error(request, "Invalid post type.")
            return redirect('pages:page_detail', page_public_id=page_public_id)
        
        try:
            # Parse event_date if provided (convert string to datetime)
            parsed_event_date = None
            if event_date:
                try:
                    from django.utils.dateparse import parse_datetime
                    parsed_event_date = parse_datetime(event_date)
                except:
                    # If parsing fails, try to use the string as-is (Django will handle it)
                    parsed_event_date = event_date
            
            post = PagePost.objects.create(
                page=page,
                post_type=post_type,
                title=title,
                content=content,
                event_date=parsed_event_date if parsed_event_date else None,
                event_location=event_location if event_location else '',
                created_by=request.user
            )
            messages.success(request, f"Post '{post.title}' created successfully!")
            
            # TEMPLE-SCOPED NOTIFICATION: Send notification for ALL post types (ANNOUNCEMENT, EVENT, UPDATE)
            # All post types send notifications to keep users informed
            try:
                from notifications.services import NotificationService
                
                # Refresh post from database to ensure event_date is a datetime object
                post.refresh_from_db()
                
                # Build message based on post type
                if post_type == PagePost.POST_TYPE_EVENT:
                    # For events, include event date and location in the message
                    event_info = []
                    if post.event_date:
                        # Handle both datetime objects and string dates
                        if isinstance(post.event_date, str):
                            # If it's still a string, use it as-is
                            event_info.append(f"Date: {post.event_date}")
                        else:
                            # It's a datetime object - format it
                            try:
                                event_info.append(f"Date: {post.event_date.strftime('%B %d, %Y at %I:%M %p')}")
                            except (AttributeError, ValueError) as e:
                                # Fallback if strftime fails
                                event_info.append(f"Date: {str(post.event_date)}")
                    if post.event_location:
                        event_info.append(f"Location: {post.event_location}")
                    event_details = "\n".join(event_info)
                    full_message = f"{content}\n\n{event_details}" if event_details else content
                else:
                    # For announcements and updates, use content as-is
                    full_message = content
                
                # Send notification for ALL post types — ONLY to followers of this temple (core.Follow + PageFollow)
                NotificationService.send_temple_notification(
                    sender=request.user,
                    page=page,
                    title=title,
                    message=full_message[:200] if len(full_message) > 200 else full_message  # Truncate if too long
                )
                # Announcement created → notify Super Admin + Admin Pandits (for dashboard/badge)
                if post_type == PagePost.POST_TYPE_ANNOUNCEMENT:
                    from django.contrib.auth import get_user_model
                    from django.db.models import Q
                    from notifications.constants import NOTIFICATION_TYPE_SYSTEM
                    User = get_user_model()
                    admin_users = User.objects.filter(
                        Q(is_superuser=True) | Q(role='admin'),
                        is_active=True
                    ).distinct()
                    safe_title = (title or 'Announcement')[:200]
                    for admin_user in admin_users:
                        try:
                            NotificationService.create_notification(
                                recipient=admin_user,
                                notification_type=NOTIFICATION_TYPE_SYSTEM,
                                source_module='pages',
                                payload={
                                    'title': 'New Announcement Created',
                                    'message': f"Announcement '{safe_title}' has been created.",
                                },
                            )
                        except Exception:
                            pass  # Non-blocking
            except Exception as e:
                # Non-blocking: log error but don't fail the post creation
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send temple notification for post {post.id} (type: {post_type}): {e}", exc_info=True)
                # Also show a warning message to the user (non-blocking)
                messages.warning(request, f"Post created successfully, but notification could not be sent. Error: {str(e)}")
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error creating post: {str(e)}")
    
    return redirect('pages:page_detail', page_public_id=page_public_id)


@login_required
@require_POST
@csrf_protect
def toggle_post_pin(request, page_public_id, post_public_id):
    """
    Pin/unpin a post.
    
    Rules:
    - Admin Pandit: Can pin/unpin posts on their own pages
    - Super Admin: Can pin/unpin posts on any page
    - Max 5 pinned posts per page (enforced in model)
    """
    if reject_bigint_id(page_public_id) or reject_bigint_id(post_public_id):
        return JsonResponse({'success': False, 'error': 'Invalid ID format'}, status=400)
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        return JsonResponse({'success': False, 'error': 'Page not found'}, status=404)
    
    post = resolve_public_id(PagePost, post_public_id)
    if not post or post.page != page:
        return JsonResponse({'success': False, 'error': 'Post not found'}, status=404)
    
    # TASK 6: Check permissions using permission service (allows moderators)
    if not can_pin_post(request.user, page):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        # Toggle pin status
        was_pinned = post.is_pinned
        post.is_pinned = not post.is_pinned
        post.save()
        
        # Log engagement event
        try:
            interaction_type = INTERACTION_PIN if post.is_pinned else INTERACTION_UNPIN
            UserInteractionEvent.objects.create(
                user=request.user,
                entity_type=ENTITY_PAGE_POST,
                entity_public_id=post.public_id,
                interaction_type=interaction_type,
                metadata=None
            )
        except Exception:
            pass  # Don't fail if logging fails
        
        return JsonResponse({
            'success': True,
            'is_pinned': post.is_pinned,
            'message': 'Post pinned' if post.is_pinned else 'Post unpinned'
        })
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
@csrf_protect
def hide_post(request, page_public_id, post_public_id):
    """
    Hide a post (Super Admin only).
    
    Rules:
    - Super Admin: Can hide any post
    - Admin Pandit: Cannot hide posts
    """
    if reject_bigint_id(page_public_id) or reject_bigint_id(post_public_id):
        return JsonResponse({'success': False, 'error': 'Invalid ID format'}, status=400)
    
    if not _is_super_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Only Super Admin can hide posts'}, status=403)
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        return JsonResponse({'success': False, 'error': 'Page not found'}, status=404)
    
    post = resolve_public_id(PagePost, post_public_id)
    if not post or post.page != page:
        return JsonResponse({'success': False, 'error': 'Post not found'}, status=404)
    
    post.is_hidden = True
    post.save(update_fields=['is_hidden'])
    
    return JsonResponse({'success': True, 'message': 'Post hidden successfully'})


@login_required
@require_POST
@csrf_protect
def delete_post(request, page_public_id, post_public_id):
    """
    Delete (hide) a post.
    
    Rules:
    - Admin Pandit: Can delete (hide) only their own posts
    - Super Admin: Cannot delete (use hide instead)
    """
    if reject_bigint_id(page_public_id) or reject_bigint_id(post_public_id):
        return JsonResponse({'success': False, 'error': 'Invalid ID format'}, status=400)
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        return JsonResponse({'success': False, 'error': 'Page not found'}, status=404)
    
    post = resolve_public_id(PagePost, post_public_id)
    if not post or post.page != page:
        return JsonResponse({'success': False, 'error': 'Post not found'}, status=404)
    
    # TASK 6: Check permissions using permission service
    # Moderators can only delete their own posts
    if not can_edit_post(request.user, page, post_creator=post.created_by):
        return JsonResponse({'success': False, 'error': 'Permission denied. You can only delete posts you created.'}, status=403)
    
    # Soft delete: hide (no hard deletes)
    post.is_hidden = True
    post.save(update_fields=['is_hidden'])
    return JsonResponse({'success': True, 'message': 'Post hidden successfully'})


def view_post(request, page_public_id, post_public_id):
    """
    View a single post (public).
    
    Logs VIEW interaction event.
    """
    if reject_bigint_id(page_public_id) or reject_bigint_id(post_public_id):
        raise Http404("Invalid ID format")
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        raise Http404("Page not found")
    
    post = resolve_public_id(PagePost, post_public_id)
    if not post or post.page != page or post.is_hidden:
        raise Http404("Post not found")
    
    # Log view (engagement logging - UNIT TASK 7)
    if request.user.is_authenticated:
        try:
            record_view(
                user=request.user,
                entity_type=ENTITY_PAGE_POST,
                entity_public_id=post.public_id,
                metadata=None
            )
        except Exception:
            pass  # Don't fail if logging fails
    
    return render(request, 'pages/post_detail.html', {
        'page': page,
        'post': post,
    })


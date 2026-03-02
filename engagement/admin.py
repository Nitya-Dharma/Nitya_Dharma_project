"""
Admin configuration for engagement app.

READ-ONLY view only. Events are immutable (append-only).
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import UserInteractionEvent, PostComment, PostLike


@admin.register(UserInteractionEvent)
class UserInteractionEventAdmin(admin.ModelAdmin):
    """
    Admin for UserInteractionEvent.
    
    READ-ONLY: Events are immutable (append-only log).
    """
    list_display = ['id', 'public_id_short', 'user_email', 'interaction_type', 'entity_type', 'entity_public_id_short', 'created_at']
    list_filter = ['interaction_type', 'entity_type', 'created_at']
    search_fields = ['user__email', 'entity_public_id', 'public_id']
    readonly_fields = ['id', 'public_id', 'user', 'entity_type', 'entity_public_id', 'interaction_type', 'metadata', 'created_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    def public_id_short(self, obj):
        """Display short version of public_id."""
        if obj.public_id:
            return obj.public_id[:8] + '...'
        return '-'
    public_id_short.short_description = 'Public ID'
    
    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = 'User'
    
    def entity_public_id_short(self, obj):
        """Display short version of entity public_id."""
        if obj.entity_public_id:
            return obj.entity_public_id[:8] + '...'
        return '-'
    entity_public_id_short.short_description = 'Entity ID'
    
    def has_add_permission(self, request):
        """Disable adding events via admin (use services)."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing events (immutable)."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deleting events (append-only)."""
        return False


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    """
    Admin for PostComment.
    
    READ-ONLY view. Comments can be moderated via status field.
    """
    list_display = ['id', 'public_id_short', 'user_email', 'post_public_id_short', 'comment_preview', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__email', 'post_public_id', 'comment_text', 'public_id']
    readonly_fields = ['id', 'public_id', 'user', 'post_public_id', 'parent_comment', 'comment_text', 'created_at', 'updated_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Comment Info', {
            'fields': ('id', 'public_id', 'user', 'post_public_id', 'parent_comment')
        }),
        ('Content', {
            'fields': ('comment_text', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def public_id_short(self, obj):
        """Display short version of public_id."""
        if obj.public_id:
            return obj.public_id[:8] + '...'
        return '-'
    public_id_short.short_description = 'Public ID'
    
    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = 'User'
    
    def post_public_id_short(self, obj):
        """Display short version of post public_id."""
        if obj.post_public_id:
            return obj.post_public_id[:8] + '...'
        return '-'
    post_public_id_short.short_description = 'Post ID'
    
    def comment_preview(self, obj):
        """Display preview of comment text."""
        preview = obj.comment_text[:50] + '...' if len(obj.comment_text) > 50 else obj.comment_text
        return preview
    comment_preview.short_description = 'Comment'
    
    def has_add_permission(self, request):
        """Disable adding comments via admin (use services)."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Comments are soft-deleted via status. No hard delete."""
        return False


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    """
    Admin for PostLike.
    
    READ-ONLY view. Used for fast counting only.
    """
    list_display = ['id', 'user_email', 'post_public_id_short', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email', 'post_public_id']
    readonly_fields = ['id', 'user', 'post_public_id', 'created_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = 'User'
    
    def post_public_id_short(self, obj):
        """Display short version of post public_id."""
        if obj.post_public_id:
            return obj.post_public_id[:8] + '...'
        return '-'
    post_public_id_short.short_description = 'Post ID'
    
    def has_add_permission(self, request):
        """Disable adding likes via admin (use services)."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing likes (immutable)."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Likes are deleted via unlike service. No manual delete."""
        return False

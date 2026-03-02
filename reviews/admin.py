from django.contrib import admin
from .models import Review
from .models_advanced import ReviewHelpfulVote, ReviewReport


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'pandit', 'rating', 'helpful_count', 'reported_count', 'is_hidden', 'is_verified', 'visibility_state', 'created_at')
    list_filter = ('visibility_state', 'is_hidden', 'is_verified', 'is_reported', 'created_at')
    search_fields = ('user__email', 'pandit__email', 'review_text', 'title')
    readonly_fields = ('public_id', 'created_at', 'updated_at', 'helpful_count', 'reported_count')
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'pandit', 'public_id')
        }),
        ('Review Content', {
            'fields': ('title', 'rating', 'review_text')
        }),
        ('Status', {
            'fields': ('visibility_state', 'is_hidden', 'is_verified', 'is_reported', 'reported_at', 'reported_reason')
        }),
        ('Statistics', {
            'fields': ('helpful_count', 'reported_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_visibility_change_at')
        }),
    )


@admin.register(ReviewHelpfulVote)
class ReviewHelpfulVoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('review__id', 'user__email')
    readonly_fields = ('created_at',)


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'user', 'reason', 'review_action', 'created_at', 'reviewed_at')
    list_filter = ('reason', 'review_action', 'created_at', 'reviewed_at')
    search_fields = ('review__id', 'user__email', 'reason_text')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Report Information', {
            'fields': ('review', 'user', 'reason', 'reason_text')
        }),
        ('Moderation', {
            'fields': ('review_action', 'reviewed_by', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

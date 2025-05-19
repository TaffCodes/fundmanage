# landing/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Transaction, Trader, PortfolioSnapshot, Notification, PlatformAnnouncement, UserDocument, KYCProfile
from django.utils import timezone


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    # Added new fields, making them readonly as they are cached/calculated
    fields = ('selected_tier', 'phone_number', 'current_balance_cached', 'total_earnings_cached')
    readonly_fields = ('current_balance_cached', 'total_earnings_cached')


class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_selected_tier', 'date_joined')
    list_select_related = ('profile',)
    readonly_fields = ('date_joined', 'last_login')

    def get_selected_tier(self, instance):
        try:
            return instance.profile.get_selected_tier_display()
        except UserProfile.DoesNotExist:
            return None
    get_selected_tier.short_description = 'Selected Tier'

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'transaction_id', 'type', 'amount', 'currency', 'status')
    list_filter = ('type', 'status', 'currency', 'timestamp')
    search_fields = ('user__username', 'user__email', 'transaction_id', 'description')
    readonly_fields = ('transaction_id', 'timestamp')
    date_hierarchy = 'timestamp'

@admin.register(Trader)
class TraderAdmin(admin.ModelAdmin):
    list_display = ('name', 'trader_id_display', 'strategy', 'current_roi_monthly', 'risk_level', 'is_active', 'experience_years')
    list_filter = ('strategy', 'risk_level', 'is_active', 'joined_platform_date')
    search_fields = ('name', 'trader_id_display', 'strategy_description', 'bio')
    list_editable = ('is_active',) # Allows quick activation/deactivation from list view

@admin.register(PortfolioSnapshot)
class PortfolioSnapshotAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'balance', 'profit_loss_since_last')
    list_filter = ('date', 'user')
    search_fields = ('user__username',)
    date_hierarchy = 'date'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'message_summary', 'timestamp', 'is_read')
    list_filter = ('type', 'is_read', 'timestamp', 'user')
    search_fields = ('user__username', 'message')
    actions = ['mark_as_read', 'mark_as_unread']

    def message_summary(self, obj):
        return obj.message[:75] + '...' if len(obj.message) > 75 else obj.message
    message_summary.short_description = 'Message'

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected notifications as read"

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
    mark_as_unread.short_description = "Mark selected notifications as unread"


@admin.register(PlatformAnnouncement)
class PlatformAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'publish_date', 'expiry_date', 'is_active')
    list_filter = ('level', 'is_active', 'publish_date')
    search_fields = ('title', 'content')
    list_editable = ('is_active',)


@admin.register(UserDocument)
class UserDocumentAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'filename', 'upload_date')
    list_filter = ('document_type', 'upload_date', 'user')
    search_fields = ('user__username', 'description', 'file')
    raw_id_fields = ('user',) # Better for selecting users if many

# KYCProfile can be inlined into UserProfile or User admin if preferred
class KYCProfileInline(admin.StackedInline): # Similar to UserProfileInline
    model = KYCProfile
    can_delete = False
    verbose_name_plural = 'KYC Profile'
    fk_name = 'user'
    fields = ('status', 'full_legal_name', 'date_of_birth', 'country_of_residence', 'address_line1', 'city', 'postal_code', 'id_document_type', 'id_document_file', 'proof_of_address_file', 'submission_date', 'review_date', 'reviewer_notes')
    readonly_fields = ('submission_date', 'review_date') # These might be auto-set


class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline, KYCProfileInline)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_selected_tier', 'date_joined')
    list_select_related = ('profile',)
    readonly_fields = ('date_joined', 'last_login')

    def get_selected_tier(self, instance):
        try:
            return instance.profile.get_selected_tier_display()
        except UserProfile.DoesNotExist:
            return None
    get_selected_tier.short_description = 'Selected Tier'

# Make sure this only appears once
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
# Update UserProfileInline in admin to show new notification preferences
class UserProfileInline(admin.StackedInline): # Re-declare to add new fields
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = ('selected_tier', 'phone_number', 
              'current_balance_cached', 'total_earnings_cached', 'assigned_trader', # From Phase 3
              'notify_email_payouts', 'notify_email_platform_updates', 'notify_email_security_alerts') # New
    readonly_fields = ('current_balance_cached', 'total_earnings_cached')
    raw_id_fields = ('assigned_trader',) # If many traders

@admin.register(KYCProfile)
class KYCProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_legal_name', 'status', 'submission_date', 'review_date')
    list_filter = ('status', 'submission_date', 'review_date', 'country_of_residence')
    search_fields = ('user__username', 'user__email', 'full_legal_name', 'address_line1')
    raw_id_fields = ('user',)
    readonly_fields = ('submission_date',)
    date_hierarchy = 'submission_date'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'status')
        }),
        ('Personal Details', {
            'fields': ('full_legal_name', 'date_of_birth', 'country_of_residence')
        }),
        ('Address Information', {
            'fields': ('address_line1', 'city', 'postal_code')
        }),
        ('Verification Documents', {
            'fields': ('id_document_type', 'id_document_file', 'proof_of_address_file')
        }),
        ('Review Information', {
            'fields': ('submission_date', 'review_date', 'reviewer_notes')
        }),
    )
    
    actions = ['mark_as_approved', 'mark_as_rejected']
    
    def mark_as_approved(self, request, queryset):
        queryset.update(status='APPROVED', review_date=timezone.now())
    mark_as_approved.short_description = "Mark selected profiles as approved"
    
    def mark_as_rejected(self, request, queryset):
        queryset.update(status='REJECTED', review_date=timezone.now())
    mark_as_rejected.short_description = "Mark selected profiles as rejected"
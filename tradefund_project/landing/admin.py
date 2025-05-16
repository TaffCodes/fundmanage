from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = ('selected_tier',) # Specify fields to show in admin inline

class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_selected_tier', 'date_joined')
    list_select_related = ('profile',)
    readonly_fields = ('date_joined', 'last_login') # Make these read-only as they are auto-managed

    def get_selected_tier(self, instance):
        try:
            return instance.profile.get_selected_tier_display() # Use get_..._display for choice fields
        except UserProfile.DoesNotExist:
            return None
    get_selected_tier.short_description = 'Selected Tier'


admin.site.unregister(User) # Unregister the original User admin
admin.site.register(User, CustomUserAdmin) # Register the custom one

# Optional: If you want a separate admin view for UserProfiles
# @admin.register(UserProfile)
# class UserProfileAdmin(admin.ModelAdmin):
# list_display = ('user', 'get_selected_tier_display')
#
#     def get_selected_tier_display(self, obj):
#         return obj.get_selected_tier_display()
#     get_selected_tier_display.short_description = 'Selected Tier'
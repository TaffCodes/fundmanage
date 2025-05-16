from django.shortcuts import render, get_object_or_404
# from django.contrib.auth.decorators import staff_member_required # For protection
from django.contrib.auth.models import User
from .models import UserProfile
def home_page(request):
    return render(request, 'landing_page.html')

# You can add views for terms, privacy etc. if needed
# def terms_page(request):
#     return render(request, 'terms.html')

# def privacy_page(request):
#     return render(request, 'privacy.html')
# ...existing code...
from django.contrib.auth.decorators import user_passes_test

# Create a custom staff member required decorator
def staff_member_required(view_func=None, redirect_field_name='next', login_url=None):
    """
    Decorator for views that checks that the user is logged in and is a staff
    member, redirecting to the login page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_active and u.is_staff,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator

@staff_member_required
def dashboard_home(request):
    """
    Homepage for the staff dashboard.
    """
    # You can add context data here if needed, e.g., counts
    total_users = User.objects.count()
    users_basic = UserProfile.objects.filter(selected_tier='basic').count()
    users_standard = UserProfile.objects.filter(selected_tier='standard').count()
    users_premium = UserProfile.objects.filter(selected_tier='premium').count()

    context = {
        'page_title': 'Dashboard',
        'total_users': total_users,
        'users_basic': users_basic,
        'users_standard': users_standard,
        'users_premium': users_premium,
        'tier_choices': UserProfile.TIER_CHOICES # Pass choices for links
    }
    return render(request, 'dashboard/dashboard_home.html', context)

@staff_member_required
def dashboard_all_users(request):
    """
    Displays all registered users with their tier.
    """
    users = User.objects.select_related('profile').all().order_by('date_joined')
    context = {
        'users': users,
        'page_title': 'All Registered Users'
    }
    return render(request, 'dashboard/user_list.html', context)

@staff_member_required
def dashboard_users_by_tier(request, tier_key):
    """
    Displays users filtered by a specific investment tier.
    """
    # Validate tier_key against actual choices to prevent arbitrary queries
    valid_tiers = [key for key, name in UserProfile.TIER_CHOICES if key] # Get only valid tier keys
    if tier_key not in valid_tiers:
        # Handle invalid tier, e.g., redirect to dashboard home or show an error
        # For now, let's just show an empty list or redirect
        return render(request, 'dashboard/user_list.html', {
            'users': [],
            'page_title': f'Users in Invalid Tier: {tier_key}',
            'tier_name': 'Invalid Tier'
        })

    users = User.objects.select_related('profile').filter(profile__selected_tier=tier_key).order_by('date_joined')
    tier_name = dict(UserProfile.TIER_CHOICES).get(tier_key, tier_key.capitalize())
    context = {
        'users': users,
        'page_title': f'Users in {tier_name}',
        'tier_name': tier_name
    }
    return render(request, 'dashboard/user_list.html', context)
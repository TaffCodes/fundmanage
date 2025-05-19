from django.shortcuts import render, get_object_or_404, redirect
# from django.contrib.auth.decorators import staff_member_required # For protection
from django.contrib.auth.models import User
from .models import UserProfile, Transaction, Trader, PortfolioSnapshot, Notification, PlatformAnnouncement, UserDocument, KYCProfile, DailyProfitLog
from django.contrib.auth.decorators import login_required
from .forms import UserProfileUpdateForm, NotificationPreferencesForm, KYCForm
from django.contrib import messages
from django.db.models import Q, Sum, Count
from datetime import datetime, timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.conf import settings
from django.urls import reverse
from django.contrib.admin.sites import site as admin_site
from decimal import Decimal



# You can place this in landing/utils.py or at the top of landing/views.py

TIER_CONFIG = {
    'basic': {'price': 500.00, 'name': 'Basic Package', 'bi_weekly_roi_percent': 0.025},  # 2.5% every 2 weeks
    'standard': {'price': 1500.00, 'name': 'Standard Package', 'bi_weekly_roi_percent': 0.035}, # 3.5% every 2 weeks
    'premium': {'price': 2000.00, 'name': 'Premium Package', 'bi_weekly_roi_percent': 0.05},   # 5.0% every 2 weeks
    '': {'price': 0.00, 'name': 'No Tier', 'bi_weekly_roi_percent': 0.00}, # For users with no tier
}
NETWORK_DAYS_IN_TWO_WEEKS = 10 # Typical (Mon-Fri for 2 weeks)

def count_network_days(start_date, end_date):
    """
    Counts the number of network days (Mon-Fri) between start_date and end_date, inclusive of start.
    """
    if start_date > end_date:
        return 0
    network_days = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5: # Monday is 0 and Sunday is 6
            network_days += 1
        current_date += timedelta(days=1)
    return network_days


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
def staff_dashboard_home(request): # Renamed from dashboard_home to avoid confusion
    total_users = User.objects.count()
    # Tier counts (same as before)
    tier_counts = UserProfile.objects.values('selected_tier').annotate(count=Count('selected_tier')).order_by('selected_tier')
    
    # New Stats
    total_traders = Trader.objects.count()
    active_traders = Trader.objects.filter(is_active=True).count()
    kyc_pending_review = KYCProfile.objects.filter(status='SUBMITTED').count()
    active_announcements = PlatformAnnouncement.objects.filter(is_active=True, publish_date__lte=timezone.now()).filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=timezone.now())).count()
    
    # Calculate total platform AUM (sum of current_balance_cached)
    total_aum = UserProfile.objects.aggregate(total=Sum('current_balance_cached'))['total'] or 0.00

    context = {
        'page_title': 'Staff Dashboard Overview',
        'total_users': total_users,
        'tier_counts': {tc['selected_tier']: tc['count'] for tc in tier_counts if tc['selected_tier']},
        'tier_choices': UserProfile.TIER_CHOICES, # For sidebar
        'total_traders': total_traders,
        'active_traders': active_traders,
        'kyc_pending_review': kyc_pending_review,
        'active_announcements': active_announcements,
        'total_aum': total_aum,
    }
    return render(request, 'staff_dashboard/staff_home.html', context) # Changed template name

@staff_member_required
def staff_all_users_list(request): # Renamed from dashboard_all_users
    users_list = User.objects.select_related('profile', 'profile__assigned_trader', 'kyc_profile').all().order_by('-date_joined')
    context = {
        'users_list': users_list, # Changed context variable name
        'page_title': 'All Registered Users',
        'tier_choices': UserProfile.TIER_CHOICES, # For sidebar
    }
    return render(request, 'staff_dashboard/staff_user_list.html', context) # Changed template name

@staff_member_required
def staff_users_by_tier_list(request, tier_key): # Renamed from dashboard_users_by_tier
    valid_tiers = [key for key, name in UserProfile.TIER_CHOICES if key]
    if tier_key not in valid_tiers:
        messages.error(request, f"Invalid tier key: {tier_key}")
        return redirect('staff_dashboard:home') # Use staff_dashboard namespace

    users_list = User.objects.select_related('profile', 'profile__assigned_trader', 'kyc_profile').filter(profile__selected_tier=tier_key).order_by('-date_joined')
    tier_name = dict(UserProfile.TIER_CHOICES).get(tier_key, tier_key.capitalize())
    context = {
        'users_list': users_list, # Changed context variable name
        'page_title': f'Users in {tier_name}',
        'tier_name': tier_name,
        'tier_choices': UserProfile.TIER_CHOICES, # For sidebar
    }
    return render(request, 'staff_dashboard/staff_user_list.html', context) # Changed template name

# New views for Phase 3 & 4 related features

@staff_member_required
def staff_trader_list_view(request):
    traders = Trader.objects.all().order_by('name')
    # Link to Django Admin for adding a new trader
    add_trader_url = reverse('admin:landing_trader_add')
    context = {
        'page_title': 'Manage Traders',
        'traders': traders,
        'add_trader_url': add_trader_url,
        'tier_choices': UserProfile.TIER_CHOICES, # For sidebar
    }
    return render(request, 'staff_dashboard/staff_trader_list.html', context)

@staff_member_required
def staff_platform_announcements_list_view(request):
    announcements = PlatformAnnouncement.objects.all().order_by('-publish_date')
    # Link to Django Admin for adding a new announcement
    add_announcement_url = reverse('admin:landing_platformannouncement_add')
    context = {
        'page_title': 'Manage Platform Announcements',
        'announcements': announcements,
        'add_announcement_url': add_announcement_url,
        'tier_choices': UserProfile.TIER_CHOICES, # For sidebar
    }
    return render(request, 'staff_dashboard/staff_announcements_list.html', context)

@staff_member_required
def staff_kyc_review_list_view(request):
    # Users who have submitted KYC and are pending review
    kyc_profiles_pending = KYCProfile.objects.filter(status='SUBMITTED').select_related('user').order_by('submission_date')
    # Optionally, also list those needing resubmission or recently rejected/approved
    kyc_profiles_attention = KYCProfile.objects.filter(
        status__in=['NEEDS_RESUBMISSION', 'REJECTED']
    ).select_related('user').order_by('-review_date')[:10] # Last 10 needing attention

    context = {
        'page_title': 'KYC Review Queue',
        'kyc_profiles_pending': kyc_profiles_pending,
        'kyc_profiles_attention': kyc_profiles_attention,
        'tier_choices': UserProfile.TIER_CHOICES, # For sidebar
    }
    return render(request, 'staff_dashboard/staff_kyc_review_list.html', context)

# Placeholder for managing user documents if needed outside Django Admin
@staff_member_required
def staff_user_documents_overview_view(request):
    # This could be a more complex view with search, filters etc.
    # For now, just a placeholder linking to Django Admin sections for User & UserDocument
    user_admin_url = reverse('admin:auth_user_changelist')
    userdocument_admin_url = reverse('admin:landing_userdocument_changelist')
    context = {
        'page_title': 'User Documents Overview',
        'user_admin_url': user_admin_url,
        'userdocument_admin_url': userdocument_admin_url,
        'tier_choices': UserProfile.TIER_CHOICES, # For sidebar
    }
    return render(request, 'staff_dashboard/staff_user_documents_overview.html', context)



@login_required
def user_dashboard_main(request):
    profile = request.user.profile
    user = request.user
    today = timezone.now().date()

    # Fetch latest snapshot for current balance
    latest_snapshot = PortfolioSnapshot.objects.filter(user=user).order_by('-date').first()
    current_balance = latest_snapshot.balance if latest_snapshot else profile.initial_investment_amount or Decimal(0.00)

    # Fetch latest daily profit for "Last Trade Profit"
    latest_profit_log = DailyProfitLog.objects.filter(user=user).order_by('-date').first()
    last_trade_profit = latest_profit_log.profit_amount if latest_profit_log else Decimal(0.00)

    # Calculate total earnings from DailyProfitLog
    total_earnings = DailyProfitLog.objects.filter(
        user=user, date__lte=today # Sum up to today
    ).aggregate(total=Sum('profit_amount'))['total'] or Decimal(0.00)
    
    # Update profile cached fields (optional, but good for quick access elsewhere if needed)
    profile.current_balance_cached = current_balance
    profile.total_earnings_cached = total_earnings
    profile.save(update_fields=['current_balance_cached', 'total_earnings_cached'])

    user_share_percentage, _ = profile.get_profit_split_percentages()
    gross_profit_for_user_share = Decimal(0.00)
    if user_share_percentage > 0 and total_earnings > 0:
        gross_profit_for_user_share = total_earnings / (Decimal(user_share_percentage) / Decimal(100.0))

    context = {
        'page_title': 'My Dashboard',
        'current_balance': current_balance, # Directly from latest snapshot or initial
        'total_earnings': total_earnings,   # Sum from DailyProfitLog
        'last_trade_profit': last_trade_profit, # From latest DailyProfitLog
        'user_share_percentage': user_share_percentage,
        'gross_profit_for_user_share': gross_profit_for_user_share,
        'can_upgrade': profile.selected_tier != 'premium',
    }
    return render(request, 'user_dashboard/dashboard_main.html', context)

@login_required
def user_transaction_history(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-timestamp')
    context = {
        'page_title': 'Transaction History',
        'transactions': transactions,
    }
    return render(request, 'user_dashboard/transaction_history.html', context)

@login_required
def user_settings_page(request):
    context = {
        'page_title': 'Account Settings',
    }
    return render(request, 'user_dashboard/user_settings.html', context)

@login_required
def user_profile_update(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('user_dashboard:settings') # Or back to profile update page
    else:
        form = UserProfileUpdateForm(instance=profile)
    
    context = {
        'page_title': 'Update Profile',
        'form': form,
    }
    return render(request, 'user_dashboard/profile_update_form.html', context)


@login_required
def user_trader_details_view(request): # Renamed to avoid clash with a potential Trader model detail view
    """
    Displays details of the user's assigned trader.
    If you implement a page for ANY trader, you'd pass a trader_id.
    """
    profile = request.user.profile
    trader = profile.assigned_trader
    context = {
        'page_title': 'My Assigned Trader',
        'trader': trader,
    }
    return render(request, 'user_dashboard/trader_details.html', context)



@login_required
def portfolio_history_api(request):
    days_filter_str = request.GET.get('days', '30')
    if days_filter_str == '14d': # For "2 Weeks"
        days_to_show = 14
    else:
        try:
            days_to_show = int(days_filter_str)
        except ValueError:
            days_to_show = 30

    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days_to_show -1)

    snapshots = PortfolioSnapshot.objects.filter(
        user=request.user,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')

    labels = [snapshot.date.strftime('%Y-%m-%d') for snapshot in snapshots]
    data = [float(snapshot.balance) for snapshot in snapshots]
    
    # Fallback dummy data if no snapshots exist for the period (useful for initial setup/testing)
    if not snapshots and settings.DEBUG:
        self.stdout.write(self.style.WARNING(f"No PortfolioSnapshot data for user {request.user.username} in range, serving dummy data.")) # Requires self for management command style
        print(f"WARNING: No PortfolioSnapshot data for user {request.user.username} in range, serving dummy data.") # For runserver console
        
        dummy_labels = []
        dummy_data_points = []
        current_dummy_date = start_date
        # Try to get a base balance from profile or default to a tier price
        base_bal = request.user.profile.initial_investment_amount or TIER_CONFIG.get(request.user.profile.selected_tier, {}).get('price', 1000.00)
        base_bal = float(base_bal)

        for i in range(days_to_show):
            dummy_labels.append(current_dummy_date.strftime('%Y-%m-%d'))
            # Simple fluctuation for dummy data
            fluctuation = (i % 7 - 3) * (base_bal * 0.001) # Small daily fluctuation
            base_bal += fluctuation
            dummy_data_points.append(round(base_bal, 2))
            current_dummy_date += timedelta(days=1)
        return JsonResponse({'labels': dummy_labels, 'data': dummy_data_points})

    return JsonResponse({'labels': labels, 'data': data})


@login_required
def user_notifications_view(request):
    # Fetch unread notifications first, then read ones
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-timestamp')
    read_notifications = Notification.objects.filter(user=request.user, is_read=True).order_by('-timestamp')[:20] # Limit read history
    
    # Fetch active platform announcements (not expired and active)
    now = timezone.now()
    platform_announcements = PlatformAnnouncement.objects.filter(
        is_active=True, 
        publish_date__lte=now
    ).filter(
        Q(expiry_date__isnull=True) | Q(expiry_date__gte=now)
    ).order_by('-publish_date')

    # Example: Mark a specific notification as read via GET param (better via POST/AJAX for real app)
    mark_read_id = request.GET.get('mark_read')
    if mark_read_id:
        try:
            notification_to_read = Notification.objects.get(id=mark_read_id, user=request.user)
            notification_to_read.is_read = True
            notification_to_read.save()
            return redirect('user_dashboard:notifications') # Refresh
        except Notification.DoesNotExist:
            pass # Or handle error

    context = {
        'page_title': 'Notifications & Announcements',
        'unread_notifications': unread_notifications,
        'read_notifications': read_notifications,
        'platform_announcements': platform_announcements,
    }
    return render(request, 'user_dashboard/notifications.html', context)

@login_required
def mark_notification_as_read_api(request, notification_id): # AJAX endpoint
    if request.method == 'POST':
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            return JsonResponse({'success': True, 'message': 'Notification marked as read.'})
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Notification not found.'}, status=404)
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)


@login_required
def user_documents_view(request):
    documents = UserDocument.objects.filter(user=request.user).order_by('-upload_date')
    context = {
        'page_title': 'My Documents',
        'documents': documents,
    }
    return render(request, 'user_dashboard/documents.html', context)


@login_required
def user_kyc_view(request):
    kyc_profile, created = KYCProfile.objects.get_or_create(user=request.user) # Ensure KYC profile exists

    if request.method == 'POST':
        # Allow submission only if status allows (e.g., NOT_SUBMITTED, NEEDS_RESUBMISSION)
        if kyc_profile.status in ['NOT_SUBMITTED', 'NEEDS_RESUBMISSION', 'PENDING_SUBMISSION']:
            form = KYCForm(request.POST, request.FILES, instance=kyc_profile)
            if form.is_valid():
                kyc_instance = form.save(commit=False)
                kyc_instance.status = 'SUBMITTED' # Update status on new submission/resubmission
                kyc_instance.submission_date = timezone.now()
                kyc_instance.save()
                messages.success(request, 'Your KYC information has been submitted for review.')
                return redirect('user_dashboard:kyc')
            else:
                messages.error(request, 'Please correct the errors in the form.')
        else:
            messages.warning(request, f'Your KYC profile cannot be edited at this time (Status: {kyc_profile.get_status_display()}).')
            form = KYCForm(instance=kyc_profile) # Show current data
            # Disable form fields if not editable based on status
            for field_name in form.fields:
                form.fields[field_name].widget.attrs['disabled'] = True
    else:
        form = KYCForm(instance=kyc_profile)
        if kyc_profile.status not in ['NOT_SUBMITTED', 'NEEDS_RESUBMISSION', 'PENDING_SUBMISSION']:
             for field_name in form.fields:
                form.fields[field_name].widget.attrs['disabled'] = True
                form.fields[field_name].widget.attrs['class'] = form.fields[field_name].widget.attrs.get('class', '') + ' bg-gray-100 cursor-not-allowed'


    context = {
        'page_title': 'KYC Verification',
        'form': form,
        'kyc_profile': kyc_profile,
        'can_edit_kyc': kyc_profile.status in ['NOT_SUBMITTED', 'NEEDS_RESUBMISSION', 'PENDING_SUBMISSION'],
    }
    return render(request, 'user_dashboard/kyc_form.html', context)


@login_required
def user_notification_preferences_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = NotificationPreferencesForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Notification preferences updated successfully.')
            return redirect('user_dashboard:notification_preferences')
    else:
        form = NotificationPreferencesForm(instance=profile)
    
    context = {
        'page_title': 'Notification Preferences',
        'form': form,
    }
    return render(request, 'user_dashboard/notification_preferences.html', context)


from django.template.loader import get_template
from django.template import TemplateDoesNotExist
from django.http import HttpResponse

def test_template(request):
    try:
        template = get_template('account/email_confirm.html')
        content = template.render({}, request)
        return HttpResponse(f"Template found and rendered. Content starts with: {content[:100]}...")
    except TemplateDoesNotExist:
        return HttpResponse("Template 'account/email_confirm.html' not found!")
from django.shortcuts import render, get_object_or_404, redirect
# from django.contrib.auth.decorators import staff_member_required # For protection
from django.contrib.auth.models import User
from .models import UserProfile, Transaction, Trader, PortfolioSnapshot, Notification, PlatformAnnouncement, UserDocument, KYCProfile, DailyProfitLog, DailyLedgerEntry
from django.utils.decorators import method_decorator
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
from landing.utils import TIER_CONFIG, NETWORK_DAYS_IN_INVESTMENT_CYCLE, count_network_days




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

    # Current Balance from latest snapshot or initial if no snapshots yet for today
    latest_snapshot = PortfolioSnapshot.objects.filter(user=user, date__lte=today).order_by('-date').first()
    current_balance = latest_snapshot.balance if latest_snapshot else profile.initial_investment_amount or Decimal('0.00')
    profile.current_balance_cached = current_balance # Update cache

    # Last Trade Profit & Total Earnings from DailyLedgerEntry
    latest_profit_log = DailyLedgerEntry.objects.filter(user=user, date__lte=today, user_profit_amount__gt=0).order_by('-date').first() # Get log with actual profit
    last_trade_profit = latest_profit_log.user_profit_amount if latest_profit_log else Decimal('0.00')
    
    total_earnings = DailyLedgerEntry.objects.filter(user=user, date__lte=today).aggregate(total=Sum('user_profit_amount'))['total'] or Decimal('0.00')
    profile.total_earnings_cached = total_earnings # Update cache
    profile.save(update_fields=['current_balance_cached', 'total_earnings_cached'])

    user_share_percentage = profile.get_user_profit_split_percentage()
    gross_profit_for_user_share = Decimal('0.00')
    if user_share_percentage > 0 and total_earnings > 0:
        gross_profit_for_user_share = total_earnings / (Decimal(user_share_percentage) / Decimal('100.0'))

    # Reinvestment eligibility
    eligible_for_reinvestment = False
    current_cycle_end_date_approx = None
    if profile.current_cycle_start_date:
        # Calculate when roughly N network days pass
        # This is a rough UI hint; the management command sets the precise is_awaiting_reinvestment_action flag
        temp_date = profile.current_cycle_start_date
        network_days_count = 0
        calendar_days_count = 0
        while network_days_count < NETWORK_DAYS_IN_INVESTMENT_CYCLE and calendar_days_count < 30: # Safety break
            if temp_date.weekday() < 5:
                network_days_count += 1
            temp_date += timedelta(days=1)
            calendar_days_count += 1
        current_cycle_end_date_approx = profile.current_cycle_start_date + timedelta(days=calendar_days_count -1)

        if profile.is_awaiting_reinvestment_action or (current_cycle_end_date_approx and today > current_cycle_end_date_approx) :
            eligible_for_reinvestment = True
            if not profile.is_awaiting_reinvestment_action: # If flag not yet set by nightly job, but date passed
                # Note: this is for UI only, command is the source of truth for the flag
                 pass
    

    print(f"User: {user.username}")
    print(f"Profile initial investment: {profile.initial_investment_amount}")
    print(f"Latest snapshot: {latest_snapshot.balance if latest_snapshot else 'No snapshot'}")
    print(f"Calculated current_balance: {current_balance}")
    print(f"Latest profit log: {latest_profit_log.user_profit_amount if latest_profit_log else 'No profit log with >0 profit'}")
    print(f"Calculated last_trade_profit: {last_trade_profit}")
    print(f"Calculated total_earnings: {total_earnings}")
    print(f"User share percentage: {user_share_percentage}")
    print(f"Calculated gross_profit_for_user_share: {gross_profit_for_user_share}")


    context = {
        'page_title': 'My Dashboard',
        'current_balance': current_balance,
        'total_earnings': total_earnings,
        'last_trade_profit': last_trade_profit,
        'user_share_percentage': user_share_percentage,
        'gross_profit_for_user_share': gross_profit_for_user_share,
        'can_upgrade': profile.selected_tier != 'premium', # Assuming 'premium' is highest
        'eligible_for_reinvestment': eligible_for_reinvestment,
        'current_cycle_start_date': profile.current_cycle_start_date,
        'current_cycle_end_date_approx': current_cycle_end_date_approx,
        'days_in_cycle_config': NETWORK_DAYS_IN_INVESTMENT_CYCLE,
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
    if days_filter_str == '14d':
        days_to_show = 14
    else:
        try:
            days_to_show = int(days_filter_str)
        except ValueError:
            days_to_show = 30

    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days_to_show -1) # Inclusive

    snapshots = PortfolioSnapshot.objects.filter(
        user=request.user,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')

    labels = [snapshot.date.strftime('%Y-%m-%d') for snapshot in snapshots]
    data = [float(snapshot.balance) for snapshot in snapshots]
    
    # Fallback dummy data only if no snapshots AND in DEBUG mode
    if not snapshots and settings.DEBUG:
        print(f"WARNING: No PortfolioSnapshot data for user {request.user.username} in range {start_date} to {end_date}. Serving dummy data for chart.")
        dummy_labels = []
        dummy_data_points = []
        current_dummy_date = start_date
        base_bal = float(request.user.profile.initial_investment_amount or TIER_CONFIG.get(request.user.profile.selected_tier, {}).get('price', 1000.00))

        for i in range(days_to_show):
            dummy_labels.append(current_dummy_date.strftime('%Y-%m-%d'))
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
    
@login_required
def user_reinvest_funds_view(request):
    profile = request.user.profile
    today = timezone.now().date()

    # Calculate when the current cycle should have ended
    if not profile.current_cycle_start_date:
        messages.error(request, "Investment cycle information is missing. Please contact support.")
        return redirect('user_dashboard:home')

    # Check if enough network days have passed in the current cycle
    network_days_passed_in_cycle = count_network_days(profile.current_cycle_start_date, today - timedelta(days=1)) # up to yesterday

    can_reinvest = False
    if profile.is_awaiting_reinvestment_action: # If flag is set
        can_reinvest = True
    elif network_days_passed_in_cycle >= NETWORK_DAYS_IN_INVESTMENT_CYCLE:
        # Cycle has just ended, flag might not be set if command hasn't run for today yet
        # Or it means the user can proactively reinvest if the period is met
        can_reinvest = True 


    if request.method == 'POST':
        if not can_reinvest:
            messages.error(request, "Not yet eligible for reinvestment or action already taken.")
            return redirect('user_dashboard:home')

        latest_ledger_entry = DailyLedgerEntry.objects.filter(user=request.user).order_by('-date').first()
        if not latest_ledger_entry:
            messages.error(request, "Cannot determine current balance for reinvestment. Please contact support.")
            return redirect('user_dashboard:home')

        reinvestment_amount = latest_ledger_entry.user_closing_balance
        
        profile.current_cycle_principal = reinvestment_amount
        profile.current_cycle_start_date = today
        profile.is_awaiting_reinvestment_action = False # Action taken
        profile.save()
        
        # Log this reinvestment action as a "new" start in ledger/snapshot
        # (The management command will pick up from here for daily profits on the new principal)
        # Create an initial ledger entry for the new cycle start day
        DailyLedgerEntry.objects.update_or_create(
            user=request.user,
            date=today,
            defaults={
                'opening_gross_managed_capital': reinvestment_amount,
                'daily_gross_profit': Decimal('0.00'), # Profit starts next network day
                'user_profit_split_percentage': profile.get_user_profit_split_percentage(),
                'user_profit_amount': Decimal('0.00'),
                'platform_profit_amount': Decimal('0.00'),
                'user_opening_balance': reinvestment_amount, # Opening balance for the new cycle is the reinvested amount
                'user_closing_balance': reinvestment_amount  # Closing balance for today (reinvestment day) is same
            }
        )
        PortfolioSnapshot.objects.update_or_create(
            user=request.user,
            date=today,
            defaults={
                'balance': reinvestment_amount,
                'profit_loss_since_last': Decimal('0.00')
            }
        )

        messages.success(request, f"Successfully reinvested ${reinvestment_amount:,.2f}. Your new investment cycle has started.")
        return redirect('user_dashboard:home')

    # This view is primarily for the POST action. 
    # The button to trigger this should only be shown in dashboard_main.html if eligible.
    # If accessed via GET, just redirect.
    messages.info(request, "Reinvestment action should be triggered from your dashboard when available.")
    return redirect('user_dashboard:home')
# landing/management/commands/record_daily_snapshots.py
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from landing.models import UserProfile, PortfolioSnapshot, DailyLedgerEntry
# Import constants from where you defined them (e.g., landing.utils or landing.models)
from landing.utils import TIER_CONFIG, NETWORK_DAYS_IN_INVESTMENT_CYCLE, DAILY_GROSS_COMPOUNDING_RATE
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
from django.db.models import Sum, Max

# Import count_network_days helper
# from landing.utils import count_network_days
# If not in utils, define it here:
def count_network_days(start_date, end_date):
    if start_date > end_date: return 0
    days = 0
    curr = start_date
    while curr <= end_date:
        if curr.weekday() < 5: days += 1
        curr += timedelta(days=1)
    return days

class Command(BaseCommand):
    help = 'Records daily simulated profit snapshots and ledger entries for active users.'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='Optional: Specific date (YYYY-MM-DD) to process. Defaults to today.')
        parser.add_argument('--user_id', type=int, help='Optional: Process only for a specific user ID.')
        parser.add_argument('--force_recalculate_from', type=str, help='Use with --user_id and --date. Recalculates from YYYY-MM-DD up to --date.')

    def handle(self, *args, **options):
        processing_date = date.fromisoformat(options['date']) if options['date'] else timezone.now().date()
        user_id = options['user_id']
        force_recalculate_from_str = options['force_recalculate_from']

        if user_id:
            users_to_process = User.objects.filter(id=user_id, is_active=True)
        else:
            users_to_process = User.objects.filter(is_active=True, profile__isnull=False).exclude(profile__selected_tier__in=['', None])

        self.stdout.write(self.style.SUCCESS(f"Processing daily records for {processing_date} on {users_to_process.count()} user(s)..."))

        for user in users_to_process:
            try:
                profile = user.profile
            except UserProfile.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"User {user.username}: No profile. Skipping."))
                continue

            if not profile.investment_start_date or profile.initial_investment_amount is None or \
               not profile.current_cycle_start_date or profile.current_cycle_principal is None:
                self.stdout.write(self.style.WARNING(f"User {user.username}: Missing initial investment/cycle data. Skipping."))
                continue

            # Determine date range for this user if recalculating
            dates_to_process_for_user = [processing_date]
            if force_recalculate_from_str and user_id:
                try:
                    recalc_start_date = date.fromisoformat(force_recalculate_from_str)
                    if recalc_start_date > processing_date:
                        self.stdout.write(self.style.ERROR(f"User {user.username}: Recalc start date after target. Aborting for user."))
                        continue
                    
                    # Delete existing records in range for recalculation
                    DailyLedgerEntry.objects.filter(user=user, date__gte=recalc_start_date, date__lte=processing_date).delete()
                    PortfolioSnapshot.objects.filter(user=user, date__gte=recalc_start_date, date__lte=processing_date).delete()
                    
                    dates_to_process_for_user = []
                    temp_date = recalc_start_date
                    while temp_date <= processing_date:
                        dates_to_process_for_user.append(temp_date)
                        temp_date += timedelta(days=1)
                    self.stdout.write(self.style.NOTICE(f"User {user.username}: Recalculating from {recalc_start_date} to {processing_date}."))
                except ValueError:
                    raise CommandError("Invalid date format for --force_recalculate_from.")
            
            for current_date_in_loop in dates_to_process_for_user:
                if current_date_in_loop < profile.investment_start_date:
                    self.stdout.write(f"  User {user.username}, Date {current_date_in_loop}: Before investment start. Skipping.")
                    continue
                
                self.process_user_for_date(user, profile, current_date_in_loop)

            # Update overall cached values on profile after processing all dates for the user (up to target_date)
            latest_ledger_entry = DailyLedgerEntry.objects.filter(user=user, date__lte=processing_date).order_by('-date').first()
            if latest_ledger_entry:
                profile.current_balance_cached = latest_ledger_entry.user_closing_balance
            
            total_earnings = DailyLedgerEntry.objects.filter(user=user, date__lte=processing_date).aggregate(total=Sum('user_profit_amount'))['total'] or Decimal('0.00')
            profile.total_earnings_cached = total_earnings
            profile.save(update_fields=['current_balance_cached', 'total_earnings_cached', 'is_awaiting_reinvestment_action'])


        self.stdout.write(self.style.SUCCESS("Daily recording process finished."))

    def process_user_for_date(self, user, profile, current_date):
        self.stdout.write(f"  Processing User: {user.username} for Date: {current_date}")

        is_network_day = current_date.weekday() < 5
        user_tier_share_percent = profile.get_user_profit_split_percentage()

        # Determine opening balances for today
        if current_date == profile.investment_start_date:
            # Very first day of any investment for this user
            user_opening_balance_today = profile.initial_investment_amount
            opening_gross_managed_capital_today = profile.initial_investment_amount
        elif current_date == profile.current_cycle_start_date:
            # First day of a new (or potentially the first if investment_start_date = current_cycle_start_date) cycle
            # The base capital for this cycle was set at current_cycle_principal
            # The user's opening balance is their balance from end of previous day, or current_cycle_principal if that was just updated
            prev_day_ledger = DailyLedgerEntry.objects.filter(user=user, date=current_date - timedelta(days=1)).first()
            user_opening_balance_today = prev_day_ledger.user_closing_balance if prev_day_ledger else profile.current_cycle_principal # Fallback if no prev day (e.g. after reinvestment)
            opening_gross_managed_capital_today = profile.current_cycle_principal
        else:
            # Mid-cycle day
            prev_day_ledger = DailyLedgerEntry.objects.filter(user=user, date=current_date - timedelta(days=1)).first()
            if not prev_day_ledger:
                self.stdout.write(self.style.WARNING(f"    User {user.username}, Date {current_date}: Missing previous day's ledger. Cannot calculate. May need to run for previous day or use --force_recalculate_from."))
                # If this happens and it's unexpected, it means a day was missed and not backfilled.
                # For a robust solution, this case needs careful handling, e.g. erroring or attempting to fill gap.
                # For now, we'll skip if critical previous data is missing.
                return 
            user_opening_balance_today = prev_day_ledger.user_closing_balance
            opening_gross_managed_capital_today = prev_day_ledger.opening_gross_managed_capital + prev_day_ledger.daily_gross_profit
        
        daily_gross_profit_today = Decimal('0.00')
        user_profit_amount_today = Decimal('0.00')
        platform_profit_amount_today = Decimal('0.00')

        # Check if current investment cycle has ended and awaiting user action
        network_days_into_current_cycle = count_network_days(profile.current_cycle_start_date, current_date)
        
        if profile.is_awaiting_reinvestment_action and current_date > profile.current_cycle_start_date : # If cycle ended and user hasn't acted
            self.stdout.write(f"    User {user.username}, Date {current_date}: Awaiting reinvestment. No profit generated.")
            # Balance remains same as user_opening_balance_today
        elif is_network_day:
            daily_gross_profit_today = opening_gross_managed_capital_today * DAILY_GROSS_COMPOUNDING_RATE
            user_profit_amount_today = daily_gross_profit_today * (user_tier_share_percent / Decimal('100.0'))
            platform_profit_amount_today = daily_gross_profit_today - user_profit_amount_today
        # else (not a network day and not awaiting reinvestment): profits are 0, balance carries over.

        user_closing_balance_today = user_opening_balance_today + user_profit_amount_today

        # Create/Update DailyLedgerEntry
        ledger_entry, created_ledger = DailyLedgerEntry.objects.update_or_create(
            user=user, date=current_date,
            defaults={
                'opening_gross_managed_capital': opening_gross_managed_capital_today,
                'daily_gross_profit': daily_gross_profit_today,
                'user_profit_share_percentage': user_tier_share_percent,
                'user_profit_amount': user_profit_amount_today,
                'platform_profit_amount': platform_profit_amount_today,
                'user_opening_balance': user_opening_balance_today,
                'user_closing_balance': user_closing_balance_today,
            }
        )
        # Create/Update PortfolioSnapshot
        snapshot, created_snap = PortfolioSnapshot.objects.update_or_create(
            user=user, date=current_date,
            defaults={
                'balance': user_closing_balance_today,
                'profit_loss_since_last': user_profit_amount_today
            }
        )
        
        self.stdout.write(f"    User {user.username}, Tier{profile.selected_tier} Date {current_date}: Gross Profit: {daily_gross_profit_today:.2f}, User Share: {user_profit_amount_today:.2f}, Closing Bal: {user_closing_balance_today:.2f}")

        # Check if cycle just ended today
        if network_days_into_current_cycle >= NETWORK_DAYS_IN_INVESTMENT_CYCLE and not profile.is_awaiting_reinvestment_action:
            profile.is_awaiting_reinvestment_action = True
            # profile.save(update_fields=['is_awaiting_reinvestment_action']) # Save will happen at end of user loop
            self.stdout.write(self.style.SUCCESS(f"    User {user.username}: Investment cycle ending {current_date}. Awaiting reinvestment decision."))
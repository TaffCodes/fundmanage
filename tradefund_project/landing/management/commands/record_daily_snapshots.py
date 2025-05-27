# landing/management/commands/record_daily_snapshots.py
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from landing.models import UserProfile, PortfolioSnapshot, DailyLedgerEntry, Transaction
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

    def process_user_for_date(self, user, profile, current_date): # Added profile as argument
        self.stdout.write(f"  Processing User: {user.username} for Date: {current_date}")

        is_network_day = current_date.weekday() < 5
        user_tier_share_percent = profile.get_user_profit_split_percentage()

        if current_date == profile.investment_start_date:
            user_opening_balance_today = profile.initial_investment_amount
            opening_gross_managed_capital_today = profile.initial_investment_amount
        elif current_date == profile.current_cycle_start_date and current_date != profile.investment_start_date:
            # This is the start of a new cycle *after* a reinvestment
            prev_day_ledger = DailyLedgerEntry.objects.filter(user=user, date=current_date - timedelta(days=1)).first()
            user_opening_balance_today = prev_day_ledger.user_closing_balance if prev_day_ledger else profile.current_cycle_principal
            opening_gross_managed_capital_today = profile.current_cycle_principal
        else:
            prev_day_ledger = DailyLedgerEntry.objects.filter(user=user, date=current_date - timedelta(days=1)).first()
            if not prev_day_ledger:
                self.stdout.write(self.style.WARNING(f"    User {user.username}, Date {current_date}: Missing previous day's ledger. Cannot calculate. This might be the first day of investment."))
                # If it's truly the investment_start_date, this case should be handled by the first if block.
                # If it's after investment_start_date but no previous ledger, that's an issue or it's current_cycle_start_date handled above.
                # For robustness, if investment_start_date == current_date, this block should not be hit.
                # Let's assume if it's investment_start_date, it's caught. If it's current_cycle_start_date, it's caught.
                # If we are here, it means a day was missed and not backfilled, or an error.
                # Fallback to cycle principal if prev_day_ledger is none and not a cycle start.
                if current_date > profile.current_cycle_start_date: # Check if it's after the current cycle started
                    self.stdout.write(self.style.WARNING(f"    User {user.username}, Date {current_date}: Missing previous day's ledger unexpectedly. Using cycle principal as base."))
                    user_opening_balance_today = profile.current_cycle_principal 
                    opening_gross_managed_capital_today = profile.current_cycle_principal
                else: # Should not happen if logic is correct for start dates.
                    self.stdout.write(self.style.ERROR(f"    User {user.username}, Date {current_date}: Critical error, previous ledger missing and not a recognized start date."))
                    return # Stop processing this date for this user
            else:
                user_opening_balance_today = prev_day_ledger.user_closing_balance
                opening_gross_managed_capital_today = prev_day_ledger.opening_gross_managed_capital + prev_day_ledger.daily_gross_profit
        
        daily_gross_profit_today = Decimal('0.00')
        user_profit_amount_today = Decimal('0.00')
        platform_profit_amount_today = Decimal('0.00')

        network_days_into_current_cycle = count_network_days(profile.current_cycle_start_date, current_date)
        
        if profile.is_awaiting_reinvestment_action and current_date > profile.current_cycle_start_date:
            self.stdout.write(f"    User {user.username}, Date {current_date}: Awaiting reinvestment. No profit generated.")
        elif is_network_day and network_days_into_current_cycle <= NETWORK_DAYS_IN_INVESTMENT_CYCLE : # Only generate profit within the cycle duration
            daily_gross_profit_today = opening_gross_managed_capital_today * DAILY_GROSS_COMPOUNDING_RATE
            user_profit_amount_today = daily_gross_profit_today * (user_tier_share_percent / Decimal('100.0'))
            platform_profit_amount_today = daily_gross_profit_today - user_profit_amount_today
        
        user_closing_balance_today = user_opening_balance_today + user_profit_amount_today

        # Ensure rounding for monetary values
        daily_gross_profit_today = daily_gross_profit_today.quantize(Decimal('0.01'))
        user_profit_amount_today = user_profit_amount_today.quantize(Decimal('0.01'))
        platform_profit_amount_today = platform_profit_amount_today.quantize(Decimal('0.01'))
        user_closing_balance_today = user_closing_balance_today.quantize(Decimal('0.01'))
        opening_gross_managed_capital_today = opening_gross_managed_capital_today.quantize(Decimal('0.01'))
        user_opening_balance_today = user_opening_balance_today.quantize(Decimal('0.01'))


        ledger_entry, _ = DailyLedgerEntry.objects.update_or_create(
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
        PortfolioSnapshot.objects.update_or_create(
            user=user, date=current_date,
            defaults={'balance': user_closing_balance_today, 'profit_loss_since_last': user_profit_amount_today}
        )
        
        # Log Daily Simulated Profit as a Transaction if profit was made
        if user_profit_amount_today > Decimal('0.00'):
            Transaction.objects.update_or_create(
                user=user,
                type='DAILY_SIMULATED_PROFIT',
                # Create a unique identifier for this specific daily profit transaction if needed,
                # or rely on timestamp + user + type to be unique enough for get_or_create/update_or_create.
                # For simplicity, if we run this once per day, type+date+user is unique for this transaction.
                # We can use a specific timestamp for the transaction log for this day.
                timestamp = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.min.time())) + timedelta(hours=23, minutes=59), # End of day
                defaults={
                    'amount': user_profit_amount_today,
                    'status': 'COMPLETED',
                    'description': f"Simulated daily profit. Closing balance: ${user_closing_balance_today:,.2f}",
                    'currency': 'USD' # Assuming USD
                }
            )
        
        self.stdout.write(f"    User {user.username}, Date {current_date}: GrossP: {daily_gross_profit_today:.2f}, UserP: {user_profit_amount_today:.2f}, ClosingBal: {user_closing_balance_today:.2f}")

        if network_days_into_current_cycle >= NETWORK_DAYS_IN_INVESTMENT_CYCLE and not profile.is_awaiting_reinvestment_action:
            profile.is_awaiting_reinvestment_action = True
            # profile.save(update_fields=['is_awaiting_reinvestment_action']) # Saved at the end of user loop
            self.stdout.write(self.style.SUCCESS(f"    User {user.username}: Investment cycle ending {current_date}. Flagged for reinvestment decision."))
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from landing.models import UserProfile, PortfolioSnapshot, DailyProfitLog, TIER_CONFIG, NETWORK_DAYS_IN_TWO_WEEKS
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
from django.db.models import Sum

# Helper function (can be moved to landing/utils.py)
def count_network_days_for_command(start_date, end_date):
    if start_date > end_date:
        return 0
    network_days = 0
    current_day = start_date
    while current_day <= end_date:
        if current_day.weekday() < 5:  # Monday is 0 and Sunday is 6
            network_days += 1
        current_day += timedelta(days=1)
    return network_days

class Command(BaseCommand):
    help = 'Records daily simulated profit snapshots and logs for active users.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Optional: Specific date to record snapshots for (YYYY-MM-DD). Defaults to today.',
        )
        parser.add_argument(
            '--user_id',
            type=int,
            help='Optional: Process only for a specific user ID.',
        )
        parser.add_argument(
            '--force_recalculate_from',
            type=str,
            help='Optional: Force recalculation for a user from a specific start date (YYYY-MM-DD) up to --date or today. Use with --user_id.',
        )


    def handle(self, *args, **options):
        target_date_str = options['date']
        target_date = timezone.now().date()
        if target_date_str:
            try:
                target_date = date.fromisoformat(target_date_str)
            except ValueError:
                raise CommandError('Invalid date format for --date. Please use YYYY-MM-DD.')

        user_id = options['user_id']
        force_recalculate_from_str = options['force_recalculate_from']

        if user_id:
            users_to_process = User.objects.filter(id=user_id, is_active=True)
            if not users_to_process.exists():
                self.stdout.write(self.style.ERROR(f"User with ID {user_id} not found or not active."))
                return
        else:
            # Process all active users with a profile and a selected tier
            users_to_process = User.objects.filter(is_active=True, profile__isnull=False).exclude(profile__selected_tier__in=['', None])

        self.stdout.write(self.style.SUCCESS(f"Starting snapshot recording for {target_date} for {users_to_process.count()} user(s)..."))

        for user in users_to_process:
            try:
                profile = user.profile
            except UserProfile.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Skipping user {user.username}: No UserProfile found."))
                continue

            if not profile.selected_tier or not profile.investment_start_date or profile.initial_investment_amount is None:
                self.stdout.write(self.style.WARNING(f"Skipping user {user.username}: Missing tier, investment start date, or initial amount."))
                continue

            # Determine the range of dates to process for this user
            dates_to_process = [target_date]
            if force_recalculate_from_str and user_id: # Only allow force recalc for specific user
                try:
                    recalc_start_date = date.fromisoformat(force_recalculate_from_str)
                    if recalc_start_date > target_date:
                         self.stdout.write(self.style.WARNING(f"Recalculate start date {recalc_start_date} is after target date {target_date} for user {user.username}. Skipping recalculation."))
                    else:
                        # Delete existing snapshots/logs in the recalc range for this user
                        PortfolioSnapshot.objects.filter(user=user, date__gte=recalc_start_date, date__lte=target_date).delete()
                        DailyProfitLog.objects.filter(user=user, date__gte=recalc_start_date, date__lte=target_date).delete()

                        temp_date = recalc_start_date
                        dates_to_process = []
                        while temp_date <= target_date:
                            dates_to_process.append(temp_date)
                            temp_date += timedelta(days=1)
                        self.stdout.write(self.style.NOTICE(f"Recalculating for user {user.username} from {recalc_start_date} to {target_date}."))
                except ValueError:
                    raise CommandError('Invalid date format for --force_recalculate_from. Please use YYYY-MM-DD.')

            for current_processing_date in dates_to_process:
                if current_processing_date < profile.investment_start_date:
                    self.stdout.write(self.style.NOTICE(f"Skipping date {current_processing_date} for user {user.username} (before investment start)."))
                    continue
                
                tier_info = TIER_CONFIG.get(profile.selected_tier) or TIER_CONFIG.get('') or {'price': 0.00, 'name': 'No Tier', 'bi_weekly_roi_percent': 0.00}
                initial_investment = Decimal(profile.initial_investment_amount) # Ensure Decimal
                bi_weekly_roi = Decimal(tier_info.get('bi_weekly_roi_percent', 0.0))

                daily_fixed_profit_on_network_day = Decimal(0.00)
                if NETWORK_DAYS_IN_TWO_WEEKS > 0 and initial_investment > 0 and bi_weekly_roi > 0:
                    daily_fixed_profit_on_network_day = (initial_investment * bi_weekly_roi) / Decimal(NETWORK_DAYS_IN_TWO_WEEKS)

                # Determine if current_processing_date is a network day
                is_network_day = current_processing_date.weekday() < 5
                actual_daily_profit = daily_fixed_profit_on_network_day if is_network_day else Decimal(0.00)

                # Get previous day's balance
                # If force_recalculating, and it's the recalc_start_date, previous balance is initial_investment
                # Otherwise, query DB for previous day's snapshot
                previous_balance = initial_investment
                if current_processing_date > profile.investment_start_date and (not (force_recalculate_from_str and current_processing_date == recalc_start_date)):
                    prev_snapshot_date = current_processing_date - timedelta(days=1)
                    previous_snapshot = PortfolioSnapshot.objects.filter(user=user, date=prev_snapshot_date).first()
                    if previous_snapshot:
                        previous_balance = previous_snapshot.balance
                    # else: it's the first day after investment_start_date if no snapshot, so use initial_investment

                current_day_balance = previous_balance + actual_daily_profit

                # Create/Update PortfolioSnapshot
                snapshot, created_snap = PortfolioSnapshot.objects.update_or_create(
                    user=user,
                    date=current_processing_date,
                    defaults={
                        'balance': current_day_balance,
                        'profit_loss_since_last': actual_daily_profit
                    }
                )

                # Create/Update DailyProfitLog
                log, created_log = DailyProfitLog.objects.update_or_create(
                    user=user,
                    date=current_processing_date,
                    defaults={
                        'profit_amount': actual_daily_profit,
                        'closing_balance': current_day_balance
                    }
                )
                action_snap = "Created" if created_snap else "Updated"
                action_log = "Created" if created_log else "Updated"
                self.stdout.write(f"  {action_snap} snapshot, {action_log} profit log for {user.username} on {current_processing_date}. Profit: {actual_daily_profit:.2f}, Balance: {current_day_balance:.2f}")

            # Update UserProfile cached fields with the latest values for the target_date
            latest_log_for_target = DailyProfitLog.objects.filter(user=user, date=target_date).first()
            if latest_log_for_target:
                profile.current_balance_cached = latest_log_for_target.closing_balance

            total_earnings_to_date = DailyProfitLog.objects.filter(
                user=user, date__lte=target_date
            ).aggregate(total=Sum('profit_amount'))['total'] or Decimal(0.00)
            profile.total_earnings_cached = total_earnings_to_date
            profile.save(update_fields=['current_balance_cached', 'total_earnings_cached'])

        self.stdout.write(self.style.SUCCESS("Finished snapshot recording."))
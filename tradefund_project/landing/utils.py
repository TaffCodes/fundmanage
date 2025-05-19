# landing/utils.py (or another central place)
from decimal import Decimal

TIER_CONFIG = {
    'basic': {'price': Decimal('500.00'), 'name': 'Basic Package', 'user_profit_share_percent': Decimal('30.0')},
    'standard': {'price': Decimal('1500.00'), 'name': 'Standard Package', 'user_profit_share_percent': Decimal('50.0')},
    'premium': {'price': Decimal('2000.00'), 'name': 'Premium Package', 'user_profit_share_percent': Decimal('70.0')},
    '': {'price': Decimal('0.00'), 'name': 'No Tier', 'user_profit_share_percent': Decimal('0.0')},
    None: {'price': Decimal('0.00'), 'name': 'No Tier', 'user_profit_share_percent': Decimal('0.0')},
}

# Universal Gross Growth Target
BI_WEEKLY_GROSS_TARGET_ROI = Decimal('0.35')  # 35%
NETWORK_DAYS_IN_INVESTMENT_CYCLE = 10  # Standard 10 business days for a 2-week cycle

# Calculated Daily Gross Compounding Rate
# r_daily_gross = (1 + Target_BiWeekly_Gross_Growth_Rate)^(1/N) - 1
# Ensure N is not zero if it's calculated dynamically later.
if NETWORK_DAYS_IN_INVESTMENT_CYCLE > 0:
    DAILY_GROSS_COMPOUNDING_RATE = (Decimal('1.0') + BI_WEEKLY_GROSS_TARGET_ROI)**(Decimal('1.0') / Decimal(NETWORK_DAYS_IN_INVESTMENT_CYCLE)) - Decimal('1.0')
else:
    DAILY_GROSS_COMPOUNDING_RATE = Decimal('0.0')

# Helper for network days (as defined before)
from datetime import timedelta

def count_network_days(start_date, end_date):
    if start_date > end_date:
        return 0
    network_days = 0
    current_day = start_date
    while current_day <= end_date:
        if current_day.weekday() < 5:  # Monday is 0 and Sunday is 6
            network_days += 1
        current_day += timedelta(days=1)
    return network_days
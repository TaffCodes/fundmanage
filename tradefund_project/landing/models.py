from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import uuid
from django_countries.fields import CountryField
from decimal import Decimal
from datetime import timedelta
from .utils import TIER_CONFIG, BI_WEEKLY_GROSS_TARGET_ROI, NETWORK_DAYS_IN_INVESTMENT_CYCLE, DAILY_GROSS_COMPOUNDING_RATE



class Trader(models.Model):
    RISK_LEVEL_CHOICES = [
        ('LOW', 'Low Risk'),
        ('MEDIUM', 'Medium Risk'),
        ('HIGH', 'High Risk'),
    ]
    STRATEGY_CHOICES = [
        ('SCALPING', 'Scalping'),
        ('SWING', 'Swing Trading'),
        ('POSITION', 'Position Trading'),
        ('ALGORITHMIC', 'Algorithmic'),
        ('DAY_TRADING', 'Day Trading'),
        ('OTHER', 'Other'),
    ]

    name = models.CharField(max_length=100, unique=True) # Or use a User model instance if traders are also users
    trader_id_display = models.CharField(max_length=20, unique=True, help_text="Publicly visible Trader ID")
    profile_image = models.ImageField(upload_to='trader_profiles/', null=True, blank=True, help_text="Optional: 200x200px recommended")
    strategy = models.CharField(max_length=50, choices=STRATEGY_CHOICES, default='OTHER')
    strategy_description = models.TextField(blank=True, help_text="More detailed description of the trading strategy.")
    current_roi_monthly = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Current estimated monthly ROI %")
    win_rate_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Historical win rate %")
    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES, default='MEDIUM')
    bio = models.TextField(blank=True)
    experience_years = models.PositiveIntegerField(default=1)
    joined_platform_date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True, help_text="Is this trader currently active and available for assignment?")

    def __str__(self):
        return f"{self.name} ({self.trader_id_display})"

    class Meta:
        ordering = ['name']


class UserProfile(models.Model):
    TIER_CHOICES = [
        ('', 'No tier selected'),
        ('basic', 'Basic Package'),
        ('standard', 'Standard Package'),
        ('premium', 'Premium Package'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    selected_tier = models.CharField(max_length=50, choices=TIER_CHOICES, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    agreed_to_terms = models.BooleanField(default=False)
    current_balance_cached = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_earnings_cached = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    assigned_trader = models.ForeignKey(Trader, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_users')
    notify_email_payouts = models.BooleanField(default=True, help_text="Receive email notifications for profit payouts.")
    notify_email_platform_updates = models.BooleanField(default=True, help_text="Receive email notifications for important platform updates.")
    notify_email_security_alerts = models.BooleanField(default=True, help_text="Receive email notifications for security alerts.")
    initial_investment_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    investment_start_date = models.DateField(null=True, blank=True)
    current_cycle_principal = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Principal for the current active cycle's growth calculation.")
    current_cycle_start_date = models.DateField(null=True, blank=True, help_text="Start date of the current active investment cycle.")
    is_awaiting_reinvestment_action = models.BooleanField(default=False, help_text="True if current cycle ended and user needs to decide on reinvestment.")
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def get_tier_config(self):
        # Import TIER_CONFIG here or ensure it's globally accessible
        # For now, assuming TIER_CONFIG is defined in this module or imported properly
        return TIER_CONFIG.get(self.selected_tier, TIER_CONFIG.get('', TIER_CONFIG[None]))

    def get_user_profit_split_percentage(self):
        tier_config = self.get_tier_config()
        return tier_config.get('user_profit_share_percent', Decimal('0.0'))

    def get_tier_icon(self): # Example, adjust as needed
        if self.selected_tier == 'premium': return '🥇'
        if self.selected_tier == 'standard': return '🥈'
        if self.selected_tier == 'basic': return '🥉'
        return ''
    
    def get_current_cycle_end_date_approx(self):
        # This is an approximation, as it depends on N network days
        # A more accurate calculation would count network days
        if self.current_cycle_start_date:
            # For simplicity, let's just add 14 calendar days as an estimate for UI
            # The management command will use precise network day counting.
            return self.current_cycle_start_date + timedelta(days=13) # Approx 2 weeks
        return None
    
    def get_tier_display_name(self):
        return dict(self.TIER_CHOICES).get(self.selected_tier, 'N/A')

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist: # Handle case where profile might not exist yet if signal fires too early
        UserProfile.objects.create(user=instance)


class DailyLedgerEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ledger_entries')
    date = models.DateField()
    
    # Gross capital figures
    opening_gross_managed_capital = models.DecimalField(max_digits=12, decimal_places=2)
    daily_gross_profit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Profit split details
    user_profit_share_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="e.g., 50.00 for 50%")
    user_profit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    platform_profit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # User's net balance
    user_opening_balance = models.DecimalField(max_digits=12, decimal_places=2) # User's balance at start of this day
    user_closing_balance = models.DecimalField(max_digits=12, decimal_places=2) # User's balance at end of this day

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['user', 'date']
        verbose_name_plural = "Daily Ledger Entries"

    def __str__(self):
        return f"{self.user.username} - {self.date} - User Profit: {self.user_profit_amount} - Closing Bal: {self.user_closing_balance}"

class PortfolioSnapshot(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portfolio_snapshots')
    date = models.DateField()
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    profit_loss_since_last = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="P/L since the previous snapshot for this user")

    class Meta:
        unique_together = ('user', 'date') # One snapshot per user per day
        ordering = ['user', 'date']

    def __str__(self):
        return f"{self.user.username} - {self.date} - Balance: {self.balance}"

class DailyProfitLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profit_logs')
    date = models.DateField()
    profit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Simulated profit for this day")
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, help_text="Simulated portfolio balance at end of this day")

    class Meta:
        unique_together = ('user', 'date') # One log per user per day
        ordering = ['user', 'date']

    def __str__(self):
        return f"{self.user.username} - {self.date} - Profit: {self.profit_amount} - Balance: {self.closing_balance}"
    
    
    

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('PROFIT_PAYOUT', 'Profit Payout'), # Actual payout by platform
        ('FEE', 'Fee'),
        ('INITIAL_INVESTMENT', 'Initial Investment'), # Changed from 'INVESTMENT' for clarity
        ('DAILY_SIMULATED_PROFIT', 'Daily Simulated Profit'), # New
        ('REINVESTMENT_START', 'Reinvestment Cycle Start'), # New
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_id = models.CharField(max_length=100, default=uuid.uuid4, unique=True, editable=False)
    # Ensure timestamp defaults to an aware datetime if settings.USE_TZ is True
    timestamp = models.DateTimeField(default=timezone.now) 
    type = models.CharField(max_length=30, choices=TRANSACTION_TYPES) # Increased max_length
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_type_display()} - {self.user.username} - {self.amount} {self.currency} ({self.get_status_display()})"
# Signal to update cached balances (Optional but recommended for performance)
# For simplicity in this comprehensive response, balance calculation will be done in the view.
# If you want to use signals:
# from django.db.models import Sum, Q
# @receiver(post_save, sender=Transaction)
# def update_user_balances_on_transaction(sender, instance, created, **kwargs):
#     if instance.status == 'COMPLETED': # Only update for completed transactions
#         profile = instance.user.profile
#         # Recalculate total earnings
#         earnings = Transaction.objects.filter(
#             user=instance.user, type='PROFIT_PAYOUT', status='COMPLETED'
#         ).aggregate(total=Sum('amount'))['total'] or 0.00
#         profile.total_earnings_cached = earnings

#         # Recalculate current balance
#         deposits_and_payouts = Transaction.objects.filter(
#             user=instance.user, status='COMPLETED', type__in=['DEPOSIT', 'PROFIT_PAYOUT', 'INVESTMENT']
#         ).aggregate(total=Sum('amount'))['total'] or 0.00
#         withdrawals_and_fees = Transaction.objects.filter(
#             user=instance.user, status='COMPLETED', type__in=['WITHDRAWAL', 'FEE']
#         ).aggregate(total=Sum('amount'))['total'] or 0.00
#         profile.current_balance_cached = deposits_and_payouts - withdrawals_and_fees
#         profile.save()

# landing/models.py
# ... (User, UserProfile, Transaction, Trader, PortfolioSnapshot models remain) ...

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('PAYOUT', 'Profit Payout'),
        ('TRADE_SUMMARY', 'Trade Summary'),
        ('PLATFORM', 'Platform Update'),
        ('SECURITY', 'Security Alert'),
        ('TIER_CHANGE', 'Tier Change'),
        ('GENERAL', 'General Info'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    link = models.URLField(blank=True, null=True, help_text="Optional link related to the notification")
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='GENERAL')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Notification for {self.user.username} - {self.type} ({'Read' if self.is_read else 'Unread'})"

class PlatformAnnouncement(models.Model):
    LEVEL_CHOICES = [
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('CRITICAL', 'Critical'),
        ('SUCCESS', 'Success'),
    ]
    is_global = models.BooleanField(default=True, help_text="If True, announcement is for all users. If False, select specific users below.")
    users = models.ManyToManyField(
        User,
        related_name='platform_announcements',
        blank=True,
        help_text="If is_global is False, select one or more users to target this announcement."
    ),
    title = models.CharField(max_length=200)
    content = models.TextField()
    publish_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField(null=True, blank=True, help_text="Optional: When this announcement should no longer be prominently displayed.")
    is_active = models.BooleanField(default=True, help_text="Controls if the announcement is currently displayed to users.")
    is_read = models.BooleanField(default=False, help_text="Indicates if the user has read this announcement.")
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='INFO')

    class Meta:
        ordering = ['-publish_date']

    def __str__(self):
        return self.title

class UserDocument(models.Model):
    DOCUMENT_TYPES = [
        ('AGREEMENT_INVESTMENT', 'Investment Agreement'),
        ('STATEMENT_TAX', 'Tax Statement'),
        ('STATEMENT_EARNINGS', 'Earnings Statement'),
        ('REPORT_PERFORMANCE', 'Performance Report'),
        ('OTHER', 'Other Document'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='user_documents/%Y/%m/') # Files stored in media/user_documents/YYYY/MM/
    description = models.CharField(max_length=255, blank=True)
    upload_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.get_document_type_display()} for {self.user.username} (Uploaded: {self.upload_date.strftime('%Y-%m-%d')})"

    @property
    def filename(self):
        import os
        return os.path.basename(self.file.name)

class KYCProfile(models.Model):
    STATUS_CHOICES = [
        ('NOT_SUBMITTED', 'Not Submitted'),
        ('PENDING_SUBMISSION', 'Pending Submission (User to complete)'), # Might not be needed if form handles this
        ('SUBMITTED', 'Submitted (Pending Review)'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
        ('NEEDS_RESUBMISSION', 'Needs Resubmission'),
    ]
    ID_DOC_TYPES = [
        ('PASSPORT', 'Passport'),
        ('NATIONAL_ID', 'National ID Card'),
        ('DRIVERS_LICENSE', 'Driver\'s License'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='kyc_profile')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NOT_SUBMITTED')
    full_legal_name = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    country_of_residence = CountryField(blank_label='(select country)', blank=True, null=True) # From django-countries
    address_line1 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    
    id_document_type = models.CharField(max_length=20, choices=ID_DOC_TYPES, blank=True, null=True)
    id_document_file = models.FileField(upload_to='kyc_documents/ids/', null=True, blank=True)
    proof_of_address_file = models.FileField(upload_to='kyc_documents/address_proofs/', null=True, blank=True)
    
    submission_date = models.DateTimeField(null=True, blank=True)
    review_date = models.DateTimeField(null=True, blank=True)
    reviewer_notes = models.TextField(blank=True, help_text="Notes from admin/staff after review.")

    def __str__(self):
        return f"KYC for {self.user.username} - Status: {self.get_status_display()}"

# Signal to create KYCProfile when UserProfile (and thus User) is created
@receiver(post_save, sender=UserProfile)
def create_kyc_profile(sender, instance, created, **kwargs):
    if created:
        KYCProfile.objects.get_or_create(user=instance.user)


class AnnouncementView(models.Model):
    """Tracks which platform announcements a user has viewed."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcement_views')
    announcement = models.ForeignKey(PlatformAnnouncement, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'announcement')
        verbose_name = 'Announcement View'
        verbose_name_plural = 'Announcement Views'
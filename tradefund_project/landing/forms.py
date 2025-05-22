# landing/forms.py
from django import forms
from allauth.account.forms import SignupForm
from django.contrib.auth.models import User
from .models import UserProfile, KYCProfile, Transaction, PortfolioSnapshot, DailyProfitLog, DailyLedgerEntry
from datetime import datetime, timedelta
from django.utils import timezone
from decimal import Decimal
from .utils import TIER_CONFIG


class CustomSignupForm(SignupForm):
    TIER_CHOICES_FORM = [
        ('', 'Select a Tier (Optional)'),
        ('basic', 'Basic Package - $500'),
        ('standard', 'Standard Package - $1,500'),
        ('premium', 'Premium Package - $2,000'),
    ]
    selected_tier = forms.ChoiceField(
        choices=TIER_CHOICES_FORM,
        required=False,
        label="Investment Tier",
        widget=forms.Select(attrs={'class': 'w-full border border-gray-300 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary'})
    )
    agree_terms = forms.BooleanField(
        label='I agree to the <a href="/terms" class="text-secondary hover:underline">Terms of Service</a> and <a href="/privacy" class="text-secondary hover:underline">Privacy Policy</a>',
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'mr-2 h-4 w-4 text-secondary focus:ring-secondary border-gray-300 rounded'})
    )

    
    
    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        tier_key = self.cleaned_data.get('selected_tier', '')
        profile.selected_tier = tier_key
        
        tier_info = TIER_CONFIG.get(tier_key, TIER_CONFIG.get('', TIER_CONFIG[None]))
        initial_amount = Decimal(tier_info['price'])

        if not profile.investment_start_date: # Set only if not already set (e.g. for first time)
            profile.initial_investment_amount = initial_amount
            profile.investment_start_date = timezone.now().date()
            profile.current_cycle_principal = initial_amount
            profile.current_cycle_start_date = profile.investment_start_date
            profile.is_awaiting_reinvestment_action = False # Start active
            
            profile.current_balance_cached = initial_amount
            profile.total_earnings_cached = Decimal('0.00')
            profile.save()

            # Create initial Transaction, PortfolioSnapshot, and DailyLedgerEntry
            if initial_amount > 0:
                # Initial Transaction for the investment
                Transaction.objects.get_or_create(
                    user=user,
                    type='INVESTMENT',
                    amount=initial_amount,
                    status='COMPLETED',
                    description=f"{tier_info.get('name', 'Tier')} Initial Investment",
                    timestamp=timezone.make_aware(timezone.datetime.combine(profile.investment_start_date, timezone.datetime.min.time()))
                )
                # Initial DailyLedgerEntry (day 0 of investment)
                DailyLedgerEntry.objects.get_or_create(
                    user=user,
                    date=profile.investment_start_date,
                    defaults={
                        'opening_gross_managed_capital': initial_amount,
                        'daily_gross_profit': Decimal('0.00'),
                        'user_profit_share_percentage': profile.get_user_profit_split_percentage(),
                        'user_profit_amount': Decimal('0.00'),
                        'platform_profit_amount': Decimal('0.00'),
                        'user_opening_balance': initial_amount,
                        'user_closing_balance': initial_amount
                    }
                )
                # Initial PortfolioSnapshot
                PortfolioSnapshot.objects.get_or_create(
                    user=user,
                    date=profile.investment_start_date,
                    defaults={
                        'balance': initial_amount,
                        'profit_loss_since_last': Decimal('0.00')
                    }
                )
        else: # If profile existed, just save selected_tier (handle upgrades differently if needed)
            profile.save(update_fields=['selected_tier'])
            
        return user

class UserProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-secondary focus:border-secondary sm:text-sm'}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-secondary focus:border-secondary sm:text-sm'}))
    # Email is handled by django-allauth for changes, so typically not in this form directly
    # email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-input-style', 'readonly': 'readonly'}))


    class Meta:
        model = UserProfile
        fields = ['phone_number']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-secondary focus:border-secondary sm:text-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].initial = self.instance.user.first_name
        self.fields['last_name'].initial = self.instance.user.last_name
        # self.fields['email'].initial = self.instance.user.email # Make email read-only or direct to allauth

    def save(self, commit=True):
        user = self.instance.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        # user.email = self.cleaned_data['email'] # If allowing email change here (not recommended without re-verification)
        if commit:
            user.save()
        return super().save(commit=commit)
    
class NotificationPreferencesForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['notify_email_payouts', 'notify_email_platform_updates', 'notify_email_security_alerts']
        widgets = {
            'notify_email_payouts': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-secondary focus:ring-secondary border-gray-300 rounded'}),
            'notify_email_platform_updates': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-secondary focus:ring-secondary border-gray-300 rounded'}),
            'notify_email_security_alerts': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-secondary focus:ring-secondary border-gray-300 rounded'}),
        }

class KYCForm(forms.ModelForm):
    class Meta:
        model = KYCProfile
        fields = [
            'full_legal_name', 'date_of_birth', 'country_of_residence', 
            'address_line1', 'city', 'postal_code',
            'id_document_type', 'id_document_file', 'proof_of_address_file'
        ]
        widgets = {
            'full_legal_name': forms.TextInput(attrs={'class': 'form-input-style', 'placeholder': 'As it appears on your ID'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-input-style', 'type': 'date'}),
            'country_of_residence': forms.Select(attrs={'class': 'form-select-style'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-input-style', 'placeholder': 'Street address'}),
            'city': forms.TextInput(attrs={'class': 'form-input-style'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-input-style'}),
            'id_document_type': forms.Select(attrs={'class': 'form-select-style'}),
            'id_document_file': forms.ClearableFileInput(attrs={'class': 'form-file-style'}),
            'proof_of_address_file': forms.ClearableFileInput(attrs={'class': 'form-file-style'}),
        }
        # Add help_texts if needed
        help_texts = {
            'id_document_file': 'Upload a clear copy of your ID document.',
            'proof_of_address_file': 'E.g., Utility bill or bank statement (last 3 months).',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Tailwind classes dynamically if not using widget_tweaks or custom widget definitions
        # For simplicity, common classes are added in widgets above.
        # You'd define 'form-input-style', 'form-select-style', 'form-file-style' in your global CSS or a <style> block.
        # Example for general styling (can be put in base.html or a CSS file):
        # .form-input-style { @apply appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-secondary focus:border-secondary sm:text-sm; }
        # .form-select-style { @apply mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-secondary focus:border-secondary sm:text-sm rounded-md; }
        # .form-file-style { @apply block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-secondary file:text-primary hover:file:bg-opacity-90; }

    def clean(self):
        cleaned_data = super().clean()
        # Add any cross-field validation for KYC if needed
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.pk: # If updating
            # If files are re-submitted, old ones are typically handled by Django's FileField
            pass
        if not instance.submission_date: # Set submission date only once
             instance.submission_date = timezone.now()
        instance.status = 'SUBMITTED' # Or update based on changes
        if commit:
            instance.save()
        return instance
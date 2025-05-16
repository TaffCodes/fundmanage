from django import forms
from allauth.account.forms import SignupForm
from .models import UserProfile # To use TIER_CHOICES

class CustomSignupForm(SignupForm):
    # Define choices directly or import from model if they are identical
    TIER_CHOICES_FORM = [
        ('', 'Select a Tier (Optional)'), # Make it optional or provide a default
        ('basic', 'Basic Package - $500'),
        ('standard', 'Standard Package - $1,500'),
        ('premium', 'Premium Package - $2,000'),
    ]
    selected_tier = forms.ChoiceField(
        choices=TIER_CHOICES_FORM,
        required=False, # Make this false if it's optional or handle default
        label="Investment Tier",
        widget=forms.Select(attrs={'class': 'w-full border border-gray-300 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary'})
    )
    agree_terms = forms.BooleanField(
        label='I agree to the <a href="/terms" class="text-secondary hover:underline">Terms of Service</a> and <a href="/privacy" class="text-secondary hover:underline">Privacy Policy</a>',
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'mr-2 h-4 w-4 text-secondary focus:ring-secondary border-gray-300 rounded'})
    )


    def __init__(self, *args, **kwargs):
        super(CustomSignupForm, self).__init__(*args, **kwargs)
        # Pre-fill tier if passed in URL query parameters
        # This requires the request object, which allauth might not pass by default to form __init__
        # So, we'll handle pre-filling via JavaScript in the template for simplicity.
        # Or, you can create a custom adapter to pass the request to the form.

    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        user.profile.selected_tier = self.cleaned_data.get('selected_tier')
        # user.profile.agreed_to_terms = self.cleaned_data.get('agree_terms') # If you add this field to UserProfile
        user.profile.save()
        return user
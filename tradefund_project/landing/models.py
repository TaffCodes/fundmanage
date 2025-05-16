from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    TIER_CHOICES = [
        ('basic', 'Basic Package'),
        ('standard', 'Standard Package'),
        ('premium', 'Premium Package'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    selected_tier = models.CharField(max_length=50, choices=TIER_CHOICES, blank=True, null=True)
    # Add other profile fields here if needed, e.g.:
    # phone_number = models.CharField(max_length=20, blank=True, null=True)
    agreed_to_terms = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def get_tier_display_name(self):
        return dict(self.TIER_CHOICES).get(self.selected_tier, 'N/A')

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    # Ensure profile is saved, especially if User model is updated elsewhere
    # instance.profile.save() # Can cause recursion if not handled carefully, usually not needed if created.
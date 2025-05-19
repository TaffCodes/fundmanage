from .models import KYCProfile, Notification

def staff_dashboard_context(request):
    if request.user.is_authenticated and request.user.is_staff:
        return {
            'kyc_pending_review_count': KYCProfile.objects.filter(status='SUBMITTED').count()
        }
    return {}

def unread_notifications_context(request):
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return {'unread_notifications_count': unread_count}
    return {}
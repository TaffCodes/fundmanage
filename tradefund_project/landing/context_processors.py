from .models import KYCProfile, Notification, PlatformAnnouncement, AnnouncementView

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

def unread_notifications_context(request):
    """Add unread notification count to context."""
    if request.user.is_authenticated:
        try:
            # Debug statement - remove in production
            count = request.user.notifications.filter(is_read=False).count()

            print(f"Unread notifications for {request.user.username}: {count}")
            return {'unread_notifications_count': count}
        except Exception as e:
            # Log the error
            print(f"Error in notification context processor: {e}")
            return {'unread_notifications_count': 0}
    return {'unread_notifications_count': 0}
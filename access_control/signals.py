from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

@receiver(post_migrate)
def ensure_admin_exists(sender, **kwargs):
    # Only run this once for the access_control app
    if sender.name == 'access_control':
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            profile = admin.profile
            profile.is_admin_user = True
            profile.is_employee = False
            profile.save()
            print("--- Automated Setup: Admin user 'admin' created with password 'admin123' ---")

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
def ensure_admin_and_departments_exist(sender, **kwargs):
    # Only run this once for the access_control app
    if sender.name == 'access_control':
        from .models import Department
        
        # 1. Create Default Departments if they don't exist
        default_depts = [
            ('IT Support', 'IT infrastructure and technical support.'),
            ('HR', 'Human resources and employee relations.'),
            ('Finance', 'Financial management and accounting.'),
            ('Security', 'Physical and electronic security monitoring.'),
            ('Engineering', 'Software and hardware development.')
        ]
        for name, desc in default_depts:
            Department.objects.get_or_create(name=name, defaults={'description': desc})

        # 2. Create Admin if it doesn't exist
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            profile = admin.profile
            profile.is_admin_user = True
            profile.is_employee = False
            profile.save()
            print("--- Automated Setup: Admin and Departments created ---")

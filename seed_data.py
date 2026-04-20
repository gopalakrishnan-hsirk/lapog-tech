import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'face_access.settings')
django.setup()

from django.contrib.auth.models import User
from access_control.models import Department, UserProfile

def seed():
    # Create Departments
    depts = [
        ('IT Support', 'IT infrastructure and technical support.'),
        ('HR', 'Human resources and employee relations.'),
        ('Finance', 'Financial management and accounting.'),
        ('Security', 'Physical and electronic security monitoring.'),
        ('Engineering', 'Software and hardware development.')
    ]
    
    for name, desc in depts:
        Department.objects.get_or_create(name=name, defaults={'description': desc})
        print(f"Department {name} created.")

    # Create Admin
    if not User.objects.filter(username='admin').exists():
        admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        profile = admin_user.profile
        profile.is_admin_user = True
        profile.is_employee = False
        profile.has_setup_face = True # Admin doesn't need face setup by default in this flow
        profile.save()
        print("Admin user 'admin' created with password 'admin123'.")
    else:
        print("Admin user already exists.")

if __name__ == '__main__':
    seed()

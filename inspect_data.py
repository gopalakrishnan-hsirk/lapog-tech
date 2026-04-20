
import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'face_access.settings')
django.setup()

from django.contrib.auth.models import User
from access_control.models import UserProfile, AccessLog

def inspect_user_data(username):
    try:
        user = User.objects.get(username=username)
        print(f"Inspecting data for user: {user.username}")
        
        now = timezone.now()
        today = now.date()
        print(f"Today is: {today}")
        
        # Check logs for today
        logs = AccessLog.objects.filter(user=user, status='SUCCESS', timestamp__date=today).order_by('-timestamp')
        print(f"Found {logs.count()} logs for today.")
        
        if logs.exists():
            print("Logs:")
            for log in logs:
                print(f"  - {log.timestamp}")
            
            first = logs.last()
            last = logs.first()
            diff = last.timestamp - first.timestamp
            hours = diff.total_seconds() / 3600
            print(f"Calculated Hours: {hours:.2f}")
            print(f"Expected Salary ({user.profile.hourly_rate}/hr): {hours * float(user.profile.hourly_rate)}")
        else:
            print("No logs found for today, so 0 hours is expected.")
            
        print("-" * 30)
        # Check logs for past month
        print("Checking past 5 days...")
        for i in range(5):
            d = today - timedelta(days=i)
            cnt = AccessLog.objects.filter(user=user, status='SUCCESS', timestamp__date=d).count()
            print(f"  {d}: {cnt} logs")

    except User.DoesNotExist:
        print(f"User {username} not found")

# Inspect the user 'gopalakrish' as seen in screenshot
inspect_user_data('gopalakrish')

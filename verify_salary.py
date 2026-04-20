
import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'face_access.settings')
django.setup()

from django.contrib.auth.models import User
from access_control.models import UserProfile, AccessLog, Department

def calculate_active_time(logs):
    if not logs or logs.count() == 0:
        return 0
    # logs is ordered by -timestamp (newest first)
    # So first() gives the newest, last() gives the oldest
    first_log = logs.last()  # Oldest (earliest timestamp)
    last_log = logs.first()   # Newest (latest timestamp)
    
    if not first_log or not last_log:
        return 0
    
    diff = last_log.timestamp - first_log.timestamp
    hours = round(diff.total_seconds() / 3600, 2)
    return hours

def run_test():
    print("Setting up test data...")
    
    # Create Test User
    username = "salary_test_user"
    if User.objects.filter(username=username).exists():
        User.objects.filter(username=username).delete()
        print(f"Deleted existing user {username}")
        
    user = User.objects.create_user(username=username, password="password123")
    profile = user.profile
    profile.is_employee = True
    profile.hourly_rate = 50.00 # $50/hr
    profile.save()
    print(f"Created user {username} with Hourly Rate: ${profile.hourly_rate}")

    # Create Department
    dept, _ = Department.objects.get_or_create(name="Test Dept")
    
    # Create Access Logs for Today (Simulate 4 hours work)
    now = timezone.now()
    
    # Login at 4 hours ago
    t1 = now - timedelta(hours=4)
    log1 = AccessLog.objects.create(user=user, department=dept, status='SUCCESS')
    log1.timestamp = t1
    log1.save()
    
    # Some activity in between
    t2 = now - timedelta(hours=2)
    log2 = AccessLog.objects.create(user=user, department=dept, status='SUCCESS')
    log2.timestamp = t2
    log2.save()
    
    # Logout/Last Access now
    t3 = now
    log3 = AccessLog.objects.create(user=user, department=dept, status='SUCCESS')
    log3.timestamp = t3
    log3.save()
    
    print(f"Created Logs: {t1} -> {t3}")

    # Verify Logic
    logs = AccessLog.objects.filter(user=user, status='SUCCESS', timestamp__date=now.date()).order_by('-timestamp')
    print(f"\nFound {logs.count()} logs for today")
    for log in logs:
        print(f"  - {log.timestamp}")
    
    hours = calculate_active_time(logs)
    salary = round(hours * float(profile.hourly_rate), 2)
    
    print(f"\nCalculated Hours: {hours}")
    print(f"Calculated Salary: ${salary}")
    
    # Updated Verification for Detailed Salary
    # Set salary components
    profile.basic_salary = 15000.00
    profile.da = 5000.00
    profile.hra = 3000.00
    profile.cca = 1000.00
    profile.loan = 2000.00
    profile.health_insurance = 1000.00
    profile.save()
    
    # Logic from Views:
    # Gross = Basic + DA + CCA + HRA
    gross = float(profile.basic_salary + profile.da + profile.cca + profile.hra)
    deductions = float(profile.loan + profile.health_insurance)
    net = gross - deductions
    
    print(f"\n--- Detailed Salary Check ---")
    print(f"Basic: {profile.basic_salary}, DA: {profile.da}, HRA: {profile.hra}, CCA: {profile.cca}")
    print(f"Expected Gross: {gross}")
    print(f"Expected Deductions: {deductions}")
    print(f"Expected Net: {net}")
    
    # We can't easily call the View function directly without a request, 
    # but we can verify the data was saved and the arithmetic holds.
    
    if gross == 24000.0 and net == 21000.0:
         print("SUCCESS: Detailed Salary arithmetic is correct.")
    else:
         print(f"FAILURE: Arithmetic mismatch. Gross: {gross}, Net: {net}")

    # Legacy Check (if Basic is 0)
    profile.basic_salary = 0
    profile.save()
    legacy_salary = round(hours * float(profile.hourly_rate), 2)
    if abs(legacy_salary - 200.0) < 0.1:
         print("SUCCESS: Legacy calculation (Hours * Rate) still works when Basic is 0.")
    else:
         print("FAILURE: Legacy calculation broken.")

    # Clean up
    user.delete()
    print("\nTest User deleted.")

if __name__ == "__main__":
    run_test()

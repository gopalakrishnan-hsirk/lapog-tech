from django.db import models
from django.contrib.auth.models import User
import json

class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    head = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_departments') # Department Head Link
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    department_access = models.ManyToManyField(Department, blank=True)
    is_employee = models.BooleanField(default=True)
    is_admin_user = models.BooleanField(default=False)
    face_data = models.TextField(null=True, blank=True) # Stored as JSON string of encodings
    failed_attempts = models.IntegerField(default=0)
    is_locked = models.BooleanField(default=False)
    has_setup_face = models.BooleanField(default=False)
    face_image = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    captured_face = models.ImageField(upload_to='captured_faces/', null=True, blank=True)
    captured_face_base64 = models.TextField(null=True, blank=True) # Binary storage in SQLite as base64
    
    # New Personal Details
    address = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    MARITAL_STATUS_CHOICES = [
        ('SINGLE', 'Single'),
        ('MARRIED', 'Married'),
        ('DIVORCED', 'Divorced'),
        ('WIDOWED', 'Widowed'),
    ]
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True, null=True)
    employee_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Salary Components
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    da = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # Dearness Allowance
    hra = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # House Rent Allowance
    cca = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # City Compensatory Allowance
    
    # Deductions
    loan = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    health_insurance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        # Auto-calculate salary components if they are 0.00
        # converting to float for calculation if needed, though Decimal handles most
        basic = float(self.basic_salary)
        
        if basic > 0:
            if float(self.da) == 0.00:
                self.da = round(basic * 0.40, 2)
            if float(self.hra) == 0.00:
                self.hra = round(basic * 0.30, 2)
            if float(self.cca) == 0.00:
                self.cca = round(basic * 0.10, 2)
        
        super().save(*args, **kwargs)

    @property
    def active_time(self):
        from django.utils.timesince import timesince
        from django.utils import timezone
        from datetime import timedelta
        if self.user.last_login:
            # Only show "Active" duration if they logged in within the last 12 hours
            if timezone.now() - self.user.last_login < timedelta(hours=12):
                return timesince(self.user.last_login)
        return None

    def get_monthly_stats(self):
        from django.utils import timezone
        from django.apps import apps
        AccessLog = apps.get_model('access_control', 'AccessLog')
        
        now = timezone.now()
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get all logs for this month for this user
        logs = AccessLog.objects.filter(
            user=self.user, 
            status='SUCCESS', 
            timestamp__gte=start_date
        ).order_by('timestamp')
        
        # Calculate unique days present
        dates = logs.dates('timestamp', 'day')
        days_present = dates.count()

        # Calculate Salary based on daily rate
        current_salary = round(days_present * float(self.daily_rate), 2)
        basic_pay = float(self.basic_salary) if self.basic_salary > 0 else current_salary
        
        da = float(self.da)
        if da == 0 and basic_pay > 0: da = round(basic_pay * 0.40, 2)
        
        hra = float(self.hra)
        if hra == 0 and basic_pay > 0: hra = round(basic_pay * 0.30, 2)
        
        cca = float(self.cca)
        if cca == 0 and basic_pay > 0: cca = round(basic_pay * 0.10, 2)
        
        gross_pay = basic_pay + da + cca + hra
        
        return {
            'days_present': days_present,
            'salary': round(gross_pay, 2)
        }

    def set_face_encodings(self, encodings):
        self.face_data = json.dumps(encodings)
    
    def get_face_encodings(self):
        if self.face_data:
            return json.loads(self.face_data)
        return []

class AccessLog(models.Model):
    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('FACE_MISMATCH', 'Face Mismatch'),
        ('LOCKED', 'Account Locked'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    snapshot = models.ImageField(upload_to='access_logs/', null=True, blank=True)
    snapshot_base64 = models.TextField(null=True, blank=True) # Binary storage in SQLite as base64

    def __str__(self):
        return f"{self.user} - {self.status} at {self.timestamp}"

class Alert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alert for {self.user.username} - {self.created_at}"

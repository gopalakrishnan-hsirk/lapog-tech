import json
import base64 # Added for decoding
from django.core.files.base import ContentFile # Added for file saving
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse # Added for PDF response
from django.core.paginator import Paginator # Added for pagination
from django.views import View
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
from .models import UserProfile, Department, AccessLog, Alert
from .utils import get_grayscale_face, verify_face, send_system_email, validate_password

class HomeView(View):
    def get(self, request):
        # Lapog Tech Stats (Scrolling Bar) - Visible to everyone
        all_department_stats = Department.objects.select_related('head').annotate(
            emp_count=Count('userprofile', distinct=True)
        ).all()
        
        url_name = request.resolver_match.url_name
        is_landing = (url_name == 'home')
        
        context = {
            'all_department_stats': all_department_stats,
            'is_landing': is_landing,
        }
        
        if is_landing:
            return render(request, 'access_control/home.html', context)
            
        if not request.user.is_authenticated:
            if url_name == 'admin_dashboard':
                return redirect('admin_login')
            return redirect('login')
            
        if request.user.is_authenticated:
            profile = request.user.profile
            if not profile.is_admin_user and not profile.has_setup_face:
                return redirect('face_setup')
            
            departments = profile.department_access.all()
            
            # Calculate Active Time Stats For Employees
            stats = {}
            
            if not profile.is_admin_user:
                now = timezone.now()
                
                def calculate_active_time(logs):
                    if not logs or logs.count() == 0:
                        return 0
                    # logs is ordered by -timestamp (newest first)
                    first_log = logs.last()  # Oldest
                    last_log = logs.first()  # Newest
                    
                    if not first_log or not last_log:
                        return 0
                        
                    diff = last_log.timestamp - first_log.timestamp
                    return round(diff.total_seconds() / 3600, 2)
                
                # Day Data
                day_data = []
                day_labels = []
                for i in range(23, -1, -1):
                    h_start = now - timezone.timedelta(hours=i+1)
                    h_end = now - timezone.timedelta(hours=i)
                    count = AccessLog.objects.filter(user=request.user, status='SUCCESS', timestamp__range=(h_start, h_end)).count()
                    day_data.append(1 if count > 0 else 0)
                    day_labels.append(h_start.strftime("%H:00"))
                
                # Week Data
                week_data = []
                week_labels = []
                for i in range(6, -1, -1):
                    date = (now - timezone.timedelta(days=i)).date()
                    logs = AccessLog.objects.filter(user=request.user, status='SUCCESS', timestamp__date=date).order_by('-timestamp')
                    week_data.append(calculate_active_time(logs))
                    week_labels.append(date.strftime("%a"))
                
                # Month Data & Detailed Logs Report
                month_data = []
                month_labels = []
                current_month_hours = 0
                daily_records = []
                
                # 1. Calculate Chart Data (Last 30 Days)
                for i in range(29, -1, -1):
                    target_date = (now - timezone.timedelta(days=i)).date()
                    logs = AccessLog.objects.filter(user=request.user, status='SUCCESS', timestamp__date=target_date).order_by('timestamp')
                    
                    hours = 0
                    if logs.exists():
                        first = logs.first()
                        last = logs.last()
                        if first != last:
                            diff = last.timestamp - first.timestamp
                            hours = round(diff.total_seconds() / 3600, 2)
                    
                    month_data.append(hours)
                    if target_date.month == now.month and target_date.year == now.year:
                        current_month_hours += hours
                    
                    if i % 5 == 0: month_labels.append(target_date.strftime("%d %b"))
                    else: month_labels.append("")

                # 2. Calculate Full History Table (All Dates)
                # Get all unique dates where user has logs
                unique_dates = AccessLog.objects.filter(user=request.user, status='SUCCESS').dates('timestamp', 'day', order='DESC')
                
                for log_date in unique_dates:
                    # Query for that specific day
                    day_logs = AccessLog.objects.filter(user=request.user, status='SUCCESS', timestamp__date=log_date).order_by('timestamp')
                    
                    hours = 0
                    daily_salary = 0.0
                    first_log = None
                    last_log = None
                    
                    if day_logs.exists():
                        first_log = day_logs.first()
                        last_log = day_logs.last()
                        
                        if first_log != last_log:
                            diff = last_log.timestamp - first_log.timestamp
                            hours = round(diff.total_seconds() / 3600, 2)
                        
                        # Daily Salary is just the daily rate since they were present
                        daily_salary = float(profile.daily_rate)
                        
                        daily_records.append({
                            'date': log_date,
                            'first_log': first_log.timestamp,
                            'last_log': last_log.timestamp,
                            'hours': hours,
                            'salary': daily_salary
                        })
                
                stats = {
                    'day': {'labels': day_labels, 'data': day_data},
                    'week': {'labels': week_labels, 'data': week_data},
                    'month': {'labels': month_labels, 'data': month_data},
                }

                # Calculate days present in current month for salary
                current_month_days = 0
                for d in unique_dates:
                    if d.month == now.month and d.year == now.year:
                        current_month_days += 1

                current_salary = round(current_month_days * float(profile.daily_rate), 2)
                
                # Detailed Salary Calculation
                # Basic Salary: if > 0 use fixed basic, else calculated from days
                basic_pay = float(profile.basic_salary) if profile.basic_salary > 0 else current_salary
                
                # Auto-calculate components if they are 0 in the profile
                da = float(profile.da)
                if da == 0 and basic_pay > 0:
                    da = round(basic_pay * 0.40, 2)
                    
                hra = float(profile.hra)
                if hra == 0 and basic_pay > 0:
                    hra = round(basic_pay * 0.30, 2)
                    
                cca = float(profile.cca)
                if cca == 0 and basic_pay > 0:
                    cca = round(basic_pay * 0.10, 2)
                
                # Gross Pay logic: Basic + DA + CCA + HRA
                gross_pay = basic_pay + da + cca + hra
                
                loan = float(profile.loan)
                insurance = float(profile.health_insurance)
                
                total_deductions = loan + insurance
                net_pay = gross_pay - total_deductions
                
                salary_breakdown = {
                    'basic': basic_pay,
                    'da': da,
                    'hra': hra,
                    'cca': cca,
                    'gross': gross_pay,
                    'loan': loan,
                    'insurance': insurance,
                    'total_deductions': total_deductions,
                    'net': net_pay
                }

                context.update({
                    'departments': departments,
                    'stats': stats,
                    'current_month_days': current_month_days, # Changed from hours
                    'current_salary': current_salary, 
                    'salary_breakdown': salary_breakdown,
                    'daily_records': daily_records, 
                })
                return render(request, 'access_control/home.html', context)
                
            else:
                # Admin Data
                all_employees = UserProfile.objects.filter(is_employee=True)
                analytics_data = []
                for emp in all_employees:
                    stats = emp.get_monthly_stats()
                    analytics_data.append({
                        'name': emp.user.username,
                        'emp_id': emp.employee_id or 'N/A',
                        'days_present': stats['days_present'], # Changed from hours
                        'salary': stats['salary']
                    })

                admin_data = {
                    'total_employees': all_employees.count(),
                    'total_departments': Department.objects.count(),
                    'recent_logs': AccessLog.objects.order_by('-timestamp')[:10],
                    'alerts': Alert.objects.filter(is_resolved=False).order_by('-created_at'),
                    'dept_stats': AccessLog.objects.values('department__name').annotate(count=Count('id')),
                    'recent_logins': User.objects.filter(profile__is_employee=True).exclude(last_login=None).order_by('-last_login')[:5],
                    'analytics_data_json': json.dumps(analytics_data), # Pass as JSON string
                }
                
                context.update(admin_data)
                context.update({'departments': departments})
                return render(request, 'access_control/admin_dashboard.html', context)

class AdminLoginView(View):
    def get(self, request):
        if request.user.is_authenticated and request.user.profile.is_admin_user:
            return redirect('admin_dashboard')
        return render(request, 'access_control/admin_login.html')
    
    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user:
            profile = user.profile
            if not profile.is_admin_user:
                messages.error(request, "Access denied. This portal is for Administrators only.")
                return redirect('admin_login')
                
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Invalid admin credentials.")
            return redirect('admin_login')

class EmployeeLoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, 'access_control/login.html')
    
    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user:
            profile = user.profile
            if profile.is_admin_user:
                # Redirect admins to their portal if they try to use employee login
                messages.info(request, "Administrators should use the Admin Portal.")
                return redirect('admin_login')
                
            if profile.is_locked:
                messages.error(request, "Your account is locked. Please contact Admin.")
                return redirect('login')
            
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid employee credentials.")
            return redirect('login')

class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')



class FaceSetupView(LoginRequiredMixin, View):
    def get(self, request):
        if request.user.profile.has_setup_face:
            return redirect('dashboard')
        return render(request, 'access_control/face_setup.html')
    
    def post(self, request):
        image_data = request.POST.get('image_data')
        if not image_data:
            return render(request, 'access_control/face_setup.html', {'error': 'No image data received'})
        
        face_img, err = get_grayscale_face(image_data)
        if face_img is None:
            return render(request, 'access_control/face_setup.html', {'error': f'Face detection failed: {err}'})
        
        # Store base64 samples
        profile = request.user.profile
        profile.set_face_encodings([image_data])
        
        # Save the actual face image for admin view
        format, imgstr = image_data.split(';base64,') 
        ext = format.split('/')[-1] 
        data = ContentFile(base64.b64decode(imgstr), name=f'{request.user.username}_setup.{ext}')
        profile.captured_face = data
        
        profile.has_setup_face = True
        profile.captured_face_base64 = image_data # Save to DB as base64
        profile.save()
        
        messages.success(request, "Face setup successful!")
        return redirect('dashboard')

class VerifyAccessView(LoginRequiredMixin, View):
    def get(self, request, dept_id):
        department = get_object_or_404(Department, id=dept_id)
        if department not in request.user.profile.department_access.all():
            messages.error(request, "You do not have permission to access this department.")
            return redirect('dashboard')
        
        return render(request, 'access_control/verify_access.html', {'department': department})
    
    def post(self, request, dept_id):
        department = get_object_or_404(Department, id=dept_id)
        image_data = request.POST.get('image_data')
        profile = request.user.profile
        
        if profile.is_locked:
            return redirect('login')

        stored_samples = profile.get_face_encodings()
        match, msg = verify_face(stored_samples, image_data)
        
        # Prepare for saving to file (common for both success and fail now)
        snapshot_file = None
        attachment_content = None
        attachment_filename = None

        if image_data:
            try:
                if ';base64,' in image_data:
                    format, imgstr = image_data.split(';base64,') 
                    ext = format.split('/')[-1] 
                    # Use unique name
                    filename = f'{request.user.username}_access_{timezone.now().timestamp()}.{ext}'
                    snapshot_file = ContentFile(base64.b64decode(imgstr), name=filename)
                    
                    # Prepare for potential email attachment
                    attachment_content = base64.b64decode(imgstr)
                    attachment_filename = f"access_{request.user.username}.{ext}"
                elif 'base64,' in image_data:
                     # Fallback
                    imgstr = image_data.split('base64,')[1]
                    filename = f'{request.user.username}_access_{timezone.now().timestamp()}.jpg'
                    snapshot_file = ContentFile(base64.b64decode(imgstr), name=filename)
                    attachment_content = base64.b64decode(imgstr)
                    attachment_filename = f"access_{request.user.username}.jpg"
            except Exception as e:
                print(f"Error processing image data: {e}")
                pass

        if match:
            profile.failed_attempts = 0
            profile.save()
            AccessLog.objects.create(
                user=request.user, 
                department=department, 
                status='SUCCESS', 
                snapshot=snapshot_file,
                snapshot_base64=image_data # Save to DB as base64
            )
            return render(request, 'access_control/access_granted.html', {'department': department, 'now': timezone.now()})
        else:
            profile.failed_attempts += 1
            profile.save()
            
            status = 'FACE_MISMATCH'
            
            AccessLog.objects.create(
                user=request.user, 
                department=department, 
                status=status, 
                snapshot=snapshot_file,
                snapshot_base64=image_data # Save to DB as base64
            )
            
            if profile.failed_attempts >= 3:
                profile.is_locked = True
                profile.save()
                
                msg = f"your account was locked because repeated face mismatch for {request.user.username},attempt:{profile.failed_attempts}"
                Alert.objects.create(user=request.user, message=msg)
                
                send_system_email("Security Alert: Account Locked", msg, [settings.ADMIN_EMAIL], attachment_content, attachment_filename)
                
                logout(request)
                messages.error(request, "Account locked due to multiple failed attempts.")
                return redirect('login')

            return render(request, 'access_control/verify_access.html', {
                'department': department,
                'error': f'Face mismatch. Attempt {profile.failed_attempts}/3'
            })

class ManageEmployeesView(LoginRequiredMixin, View):
    def get(self, request):
        if not request.user.profile.is_admin_user:
            return redirect('dashboard')
        employees = UserProfile.objects.filter(is_employee=True)
        return render(request, 'access_control/manage_employees.html', {'employees': employees})

class CreateEmployeeView(LoginRequiredMixin, View):
    def get(self, request):
        if not request.user.profile.is_admin_user:
            return redirect('dashboard')
        departments = Department.objects.all()
        return render(request, 'access_control/employee_form_v2.html', {
            'all_departments': departments,
            'employee_profile': None,
            'access_depts': [],
            'led_depts': []
        })
    
    def post(self, request):
        if not request.user.profile.is_admin_user:
            return redirect('dashboard')
        
        data = request.POST
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')

        # Password Validation
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            messages.error(request, error_msg)
            return redirect('create_employee')
        dept_ids = request.POST.getlist('departments')
        head_dept_ids = request.POST.getlist('head_depts') # New: Departments this user leads

        if not dept_ids:
            messages.error(request, "Please select at least one department.")
            return redirect('create_employee')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('create_employee')
        
        if not all([data.get('employee_id'), data.get('designation')]):
             messages.error(request, "Employee ID and Designation are required.")
             return redirect('create_employee')

        if UserProfile.objects.filter(employee_id=data.get('employee_id')).exists():
            messages.error(request, "Employee ID already exists.")
            return redirect('create_employee')

        # Phone validation
        import re
        phone = data.get('phone_number')
        if phone and not re.match(r'^\d{10}$', phone):
             messages.error(request, "Invalid phone number. Must be exactly 10 digits.")
             return redirect('create_employee')

        # Date validation
        dob = data.get('date_of_birth')
        if dob:
            try:
                from datetime import datetime
                d = datetime.strptime(dob, '%Y-%m-%d')
                if d.year > 9999 or d.year < 1900:
                    raise ValueError("Year out of range")
            except ValueError:
                messages.error(request, "Invalid date of birth format. Use YYYY-MM-DD.")
                return redirect('create_employee')

        user = User.objects.create_user(username=username, password=password, email=email)
        # Fix: email was passed to create_user but explicitly setting it to ensure
        user.email = email 
        user.save()
        
        profile = user.profile
        profile.department_access.set(dept_ids)
        
        # Personal Details
        profile.address = data.get('address')
        profile.phone_number = phone # validated
        profile.date_of_birth = dob or None
        profile.marital_status = data.get('marital_status')
        profile.employee_id = data.get('employee_id') or None
        profile.designation = data.get('designation')
        profile.employee_id = data.get('employee_id') or None
        profile.designation = data.get('designation')
        profile.daily_rate = data.get('daily_rate') or 0.00
        
        # Salary Components
        profile.basic_salary = data.get('basic_salary') or 0.00
        profile.loan = data.get('loan') or 0.00
        profile.health_insurance = data.get('health_insurance') or 0.00
        
        face_image = request.FILES.get('face_image')
        if face_image:
            profile.face_image = face_image
            
        profile.save()

        # Update Department Head status
        # Clear any departments this user might already head (though unlikely for new user)
        # Then set the ones selected
        Department.objects.filter(head=user).update(head=None)
        if head_dept_ids:
            Department.objects.filter(id__in=head_dept_ids).update(head=user)

        # Send creation email
        subject = "Account Created - SecureFace Access System"
        message = f"Hello {username},\n\nYour account has been created.\nUsername: {username}\nPassword: {password}\n\nPlease login to the system to complete your profile."
        send_system_email(subject, message, [email])
        
        messages.success(request, f"Employee {username} created and email sent.")
        return redirect('manage_employees')

class UserProfileView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'access_control/profile_v2.html')
    
    def post(self, request):
        user = request.user
        email = request.POST.get('email')
        new_password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        email_changed = False
        pass_changed = False
        
        if email and email != user.email:
            user.email = email
            email_changed = True
            
        if new_password:
            if new_password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return redirect('profile')
            
            # Password Validation
            is_valid, error_msg = validate_password(new_password)
            if not is_valid:
                messages.error(request, error_msg)
                return redirect('profile')

            user.set_password(new_password)
            pass_changed = True
            
        face_image = request.FILES.get('face_image')
        if face_image:
            user.profile.face_image = face_image
            
        # Personal Details Update
        user.profile.address = request.POST.get('address')
        user.profile.phone_number = request.POST.get('phone_number')
        user.profile.date_of_birth = request.POST.get('date_of_birth') or None
        user.profile.marital_status = request.POST.get('marital_status')
        user.profile.save()
            
        if email_changed or pass_changed:
            user.save()
            if pass_changed:
                login(request, user) # Re-login
            
            # Notifications
            if email_changed:
                send_system_email("Email Updated", f"Your SecureFace account email has been updated to {email}.", [user.email])
            if pass_changed:
                send_system_email("Password Updated", "Your SecureFace account password has been successfully changed.", [user.email])
                
            messages.success(request, "Profile updated successfully.")
        else:
            messages.info(request, "No changes made.")
            
        return redirect('profile')

class EditEmployeeView(LoginRequiredMixin, View):
    def get(self, request, user_id):
        if not request.user.profile.is_admin_user:
            return redirect('dashboard')
        
        employee_user = get_object_or_404(User, id=user_id)
        departments = Department.objects.all()
        return render(request, 'access_control/employee_form_v2.html', {
            'edit_mode': True,
            'employee_user': employee_user,
            'employee_profile': employee_user.profile,
            'all_departments': departments,
            'access_depts': employee_user.profile.department_access.values_list('id', flat=True),
            'led_depts': employee_user.led_departments.values_list('id', flat=True) # New: IDs of depts they lead
        })
    
    def post(self, request, user_id):
        if not request.user.profile.is_admin_user:
            return redirect('dashboard')
        
        employee_user = get_object_or_404(User, id=user_id)
        profile = employee_user.profile
        
        dept_ids = request.POST.getlist('departments')
        head_dept_ids = request.POST.getlist('head_depts') # New: Departments this user leads
        if not dept_ids:
            messages.error(request, "Please select at least one department.")
            return redirect('edit_employee', user_id=user_id)

        is_locked = 'is_locked' in request.POST
        reset_face = 'reset_face' in request.POST
        
        emp_id = request.POST.get('employee_id')
        if not emp_id:
             messages.error(request, "Employee ID is required.")
             return redirect('edit_employee', user_id=user_id)

        # check for duplicate emp_id explicitly excluding current user
        if UserProfile.objects.filter(employee_id=emp_id).exclude(user=employee_user).exists():
             messages.error(request, f"Employee ID {emp_id} is already assigned to another user.")
             return redirect('edit_employee', user_id=user_id)

        # Phone validation
        import re
        phone = request.POST.get('phone_number')
        if phone and not re.match(r'^\d{10}$', phone):
             messages.error(request, "Invalid phone number. Must be exactly 10 digits.")
             return redirect('edit_employee', user_id=user_id)

        # Date validation
        dob = request.POST.get('date_of_birth')
        if dob:
            try:
                from datetime import datetime
                d = datetime.strptime(dob, '%Y-%m-%d')
                if d.year > 9999 or d.year < 1900:
                    raise ValueError("Year out of range")
            except ValueError:
                messages.error(request, "Invalid date of birth format. Use YYYY-MM-DD.")
                return redirect('edit_employee', user_id=user_id)

        profile.department_access.set(dept_ids)
        profile.is_locked = is_locked
        if is_locked:
            profile.failed_attempts = 4 # Keep it locked
        else:
            profile.failed_attempts = 0 # Reset if admin unlocks
            
        if reset_face:
            profile.face_data = None
            profile.has_setup_face = False
            profile.captured_face = None
            
        # Personal Details Update
        profile.address = request.POST.get('address')
        profile.phone_number = phone # validated
        profile.date_of_birth = dob or None
        profile.marital_status = request.POST.get('marital_status')
        profile.employee_id = request.POST.get('employee_id') or None
        profile.designation = request.POST.get('designation')
        profile.daily_rate = request.POST.get('daily_rate') or 0.00
        
        # Salary Components
        profile.basic_salary = request.POST.get('basic_salary') or 0.00
        profile.loan = request.POST.get('loan') or 0.00
        profile.health_insurance = request.POST.get('health_insurance') or 0.00

        face_image = request.FILES.get('face_image')
        if face_image:
            profile.face_image = face_image
            
        profile.save()
        
        # Update Department Head status
        # Clear existing headships for this user and set new ones
        Department.objects.filter(head=employee_user).update(head=None)
        if head_dept_ids:
            Department.objects.filter(id__in=head_dept_ids).update(head=employee_user)
        
        # FIX: Also update email in User model
        email = request.POST.get('email')
        if email and email != employee_user.email:
             employee_user.email = email
             employee_user.save()

        messages.success(request, f"Employee {employee_user.username} updated.")
        return redirect('manage_employees')

class AccessLogView(LoginRequiredMixin, View):
    def get(self, request):
        if not request.user.profile.is_admin_user:
            return redirect('dashboard')
        
        logs_list = AccessLog.objects.all().order_by('-timestamp')
        paginator = Paginator(logs_list, 20) # Show 20 logs per page

        page_number = request.GET.get('page')
        logs = paginator.get_page(page_number)

        return render(request, 'access_control/logs.html', {'logs': logs})

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

class DailyReportView(LoginRequiredMixin, View):
    def get(self, request):
        if not request.user.profile.is_admin_user:
            return redirect('dashboard')
            
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="daily_report_{timezone.now().date()}.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph(f"Daily Access Report - {timezone.now().date()}", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Data
        today = timezone.now().date()
        logs = AccessLog.objects.filter(timestamp__date=today).order_by('-timestamp')
        
        data = [['Timestamp', 'User', 'Department', 'Status']]
        for log in logs:
            user_str = log.user.username if log.user else "Unknown"
            dept_str = log.department.name if log.department else "N/A"
            data.append([
                log.timestamp.strftime("%H:%M:%S"),
                user_str,
                dept_str,
                log.status
            ])
            
        if not logs:
             elements.append(Paragraph("No logs found for today.", styles['Normal']))
        else:
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(table)
            
        doc.build(elements)
        return response

class DeleteEmployeeView(LoginRequiredMixin, View):
    def get(self, request, user_id):
        if not request.user.profile.is_admin_user:
            return redirect('dashboard')
        employee_user = get_object_or_404(User, id=user_id)
        if employee_user.profile.is_admin_user:
            messages.error(request, "Cannot delete admin users.")
            return redirect('manage_employees')
        return render(request, 'access_control/delete_employee_confirm.html', {'employee_user': employee_user})

    def post(self, request, user_id):
        if not request.user.profile.is_admin_user:
            return redirect('dashboard')
        
        employee_user = get_object_or_404(User, id=user_id)
        if employee_user.profile.is_admin_user:
            messages.error(request, "Cannot delete admin users.")
            return redirect('manage_employees')

        reason = request.POST.get('reason')
        username = employee_user.username
        email = employee_user.email

        # Send notification email before deleting
        subject = "Account Removed - SecureFace Access System"
        message = f"Hello {username},\n\nYour account has been removed from the SecureFace Access System.\n\nReason for Removal:\n{reason}\n\nIf you believe this is an error, please contact the administrator."
        send_system_email(subject, message, [email])

        # Delete the user (this cascadingly deletes the profile)
        employee_user.delete()

        messages.success(request, f"Employee {username} has been removed and notified.")
        return redirect('manage_employees')

class EmployeeAnalyticsView(LoginRequiredMixin, View):
    def get(self, request, user_id):
        if not request.user.profile.is_admin_user:
            return redirect('dashboard')
            
        target_user = get_object_or_404(User, id=user_id)
        profile = target_user.profile
        
        # Reuse logic from HomeView for stats calculation
        now = timezone.now()
        
        def calculate_active_time(logs):
            if not logs or logs.count() == 0:
                return 0
            first = logs.last()
            last = logs.first()
            if not first or not last: return 0
            diff = last.timestamp - first.timestamp
            return round(diff.total_seconds() / 3600, 2)
        
        # Day Data
        day_data = []
        day_labels = []
        for i in range(23, -1, -1):
            h_start = now - timezone.timedelta(hours=i+1)
            h_end = now - timezone.timedelta(hours=i)
            c = AccessLog.objects.filter(user=target_user, status='SUCCESS', timestamp__range=(h_start, h_end)).count()
            day_data.append(1 if c > 0 else 0)
            day_labels.append(h_start.strftime("%H:00"))
        
        # Week Data
        week_data = []
        week_labels = []
        for i in range(6, -1, -1):
            date = (now - timezone.timedelta(days=i)).date()
            logs = AccessLog.objects.filter(user=target_user, status='SUCCESS', timestamp__date=date).order_by('-timestamp')
            week_data.append(calculate_active_time(logs))
            week_labels.append(date.strftime("%a"))
        
        # Month Data
        month_data = []
        month_labels = []
        current_month_hours = 0
        
        for i in range(29, -1, -1):
            target_date = (now - timezone.timedelta(days=i)).date()
            logs = AccessLog.objects.filter(user=target_user, status='SUCCESS', timestamp__date=target_date).order_by('timestamp')
            
            hours = 0
            if logs.exists():
                first = logs.first()
                last = logs.last()
                if first != last:
                    diff = last.timestamp - first.timestamp
                    hours = round(diff.total_seconds() / 3600, 2)
            
            month_data.append(hours)
            if target_date.month == now.month and target_date.year == now.year:
                current_month_hours += hours
            
            if i % 5 == 0: month_labels.append(target_date.strftime("%d %b"))
            else: month_labels.append("")

        stats = {
            'day': {'labels': day_labels, 'data': day_data},
            'week': {'labels': week_labels, 'data': week_data},
            'month': {'labels': month_labels, 'data': month_data},
        }

        # Salary Calculation
        current_salary = round(float(current_month_hours) * float(profile.hourly_rate), 2)
        basic_pay = float(profile.basic_salary) if profile.basic_salary > 0 else current_salary
        
        da = float(profile.da)
        if da == 0 and basic_pay > 0: da = round(basic_pay * 0.40, 2)
            
        hra = float(profile.hra)
        if hra == 0 and basic_pay > 0: hra = round(basic_pay * 0.30, 2)
            
        cca = float(profile.cca)
        if cca == 0 and basic_pay > 0: cca = round(basic_pay * 0.10, 2)
        
        gross_pay = basic_pay + da + cca + hra
        loan = float(profile.loan)
        insurance = float(profile.health_insurance)
        total_deductions = loan + insurance
        net_pay = gross_pay - total_deductions
        
        salary_breakdown = {
            'basic': basic_pay,
            'da': da,
            'hra': hra,
            'cca': cca,
            'gross': gross_pay,
            'loan': loan,
            'insurance': insurance,
            'total_deductions': total_deductions,
            'net': net_pay
        }
        
        # Calculate full history (same as HomeView) -- NEEDED FOR REPORTS
        daily_records = []
        unique_dates = AccessLog.objects.filter(user=target_user, status='SUCCESS').dates('timestamp', 'day', order='DESC')
        for log_date in unique_dates:
            day_logs = AccessLog.objects.filter(user=target_user, status='SUCCESS', timestamp__date=log_date).order_by('timestamp')
            hours = 0
            daily_salary = 0.0
            first_log = None
            last_log = None
            if day_logs.exists():
                first_log = day_logs.first()
                last_log = day_logs.last()
                if first_log != last_log:
                    diff = last_log.timestamp - first_log.timestamp
                    hours = round(diff.total_seconds() / 3600, 2)
                daily_salary = round(hours * float(profile.hourly_rate), 2)
                daily_records.append({
                    'date': log_date,
                    'first_log': first_log.timestamp,
                    'last_log': last_log.timestamp,
                    'hours': hours,
                    'salary': daily_salary
                })

        # Recent Logs specific to user
        recent_logs = AccessLog.objects.filter(user=target_user).order_by('-timestamp')[:20]

        return render(request, 'access_control/admin_employee_analytics.html', {
            'target_user': target_user,
            'profile': profile,
            'stats': stats,
            'current_month_hours': round(current_month_hours, 2),
            'current_salary': current_salary,
            'salary_breakdown': salary_breakdown,
            'daily_records': daily_records,
            'recent_logs': recent_logs
        })

class EmployeeAnalyticsView(LoginRequiredMixin, View):
    def get(self, request, user_id):
        if not request.user.profile.is_admin_user:
            return redirect('dashboard')
            
        target_user = get_object_or_404(User, id=user_id)
        profile = target_user.profile
        
        # Reuse logic from HomeView for stats calculation
        now = timezone.now()
        
        def calculate_active_time(logs):
            if not logs or logs.count() == 0:
                return 0
            first = logs.last()
            last = logs.first()
            if not first or not last: return 0
            diff = last.timestamp - first.timestamp
            return round(diff.total_seconds() / 3600, 2)
        
        # Day Data
        day_data = []
        day_labels = []
        for i in range(23, -1, -1):
            h_start = now - timezone.timedelta(hours=i+1)
            h_end = now - timezone.timedelta(hours=i)
            c = AccessLog.objects.filter(user=target_user, status='SUCCESS', timestamp__range=(h_start, h_end)).count()
            day_data.append(1 if c > 0 else 0)
            day_labels.append(h_start.strftime("%H:00"))
        
        # Week Data
        week_data = []
        week_labels = []
        for i in range(6, -1, -1):
            date = (now - timezone.timedelta(days=i)).date()
            logs = AccessLog.objects.filter(user=target_user, status='SUCCESS', timestamp__date=date).order_by('-timestamp')
            week_data.append(calculate_active_time(logs))
            week_labels.append(date.strftime("%a"))
        
        # Month Data
        month_data = []
        month_labels = []
        current_month_hours = 0
        
        for i in range(29, -1, -1):
            target_date = (now - timezone.timedelta(days=i)).date()
            logs = AccessLog.objects.filter(user=target_user, status='SUCCESS', timestamp__date=target_date).order_by('timestamp')
            
            hours = 0
            if logs.exists():
                first = logs.first()
                last = logs.last()
                if first != last:
                    diff = last.timestamp - first.timestamp
                    hours = round(diff.total_seconds() / 3600, 2)
            
            month_data.append(hours)
            if target_date.month == now.month and target_date.year == now.year:
                current_month_hours += hours
            
            if i % 5 == 0: month_labels.append(target_date.strftime("%d %b"))
            else: month_labels.append("")

        # Calculate Full History & Salary based on daily rate
        daily_records = []
        unique_dates = AccessLog.objects.filter(user=target_user, status='SUCCESS').dates('timestamp', 'day', order='DESC')
        
        current_month_days = 0
        
        for log_date in unique_dates:
            day_logs = AccessLog.objects.filter(user=target_user, status='SUCCESS', timestamp__date=log_date).order_by('timestamp')
            
            hours = 0
            daily_salary = 0.0
            first_log = None
            last_log = None
            
            if day_logs.exists():
                first_log = day_logs.first()
                last_log = day_logs.last()
                
                if first_log != last_log:
                    diff = last_log.timestamp - first_log.timestamp
                    hours = round(diff.total_seconds() / 3600, 2)
                
                # Daily Salary is just the daily rate since they were present
                daily_salary = float(profile.daily_rate)
                
                daily_records.append({
                    'date': log_date,
                    'first_log': first_log.timestamp,
                    'last_log': last_log.timestamp,
                    'hours': hours,
                    'salary': daily_salary
                })
                
            if log_date.month == now.month and log_date.year == now.year:
                current_month_days += 1

        stats = {
            'day': {'labels': day_labels, 'data': day_data},
            'week': {'labels': week_labels, 'data': week_data},
            'month': {'labels': month_labels, 'data': month_data},
        }

        # Salary Calculation
        current_salary = round(current_month_days * float(profile.daily_rate), 2)
        basic_pay = float(profile.basic_salary) if profile.basic_salary > 0 else current_salary
        
        da = float(profile.da)
        if da == 0 and basic_pay > 0: da = round(basic_pay * 0.40, 2)
            
        hra = float(profile.hra)
        if hra == 0 and basic_pay > 0: hra = round(basic_pay * 0.30, 2)
            
        cca = float(profile.cca)
        if cca == 0 and basic_pay > 0: cca = round(basic_pay * 0.10, 2)
        
        gross_pay = basic_pay + da + cca + hra
        loan = float(profile.loan)
        insurance = float(profile.health_insurance)
        total_deductions = loan + insurance
        net_pay = gross_pay - total_deductions
        
        salary_breakdown = {
            'basic': basic_pay,
            'da': da,
            'hra': hra,
            'cca': cca,
            'gross': gross_pay,
            'loan': loan,
            'insurance': insurance,
            'total_deductions': total_deductions,
            'net': net_pay
        }

        # Recent Logs specific to user
        recent_logs = AccessLog.objects.filter(user=target_user).order_by('-timestamp')[:20]

        return render(request, 'access_control/admin_employee_analytics.html', {
            'target_user': target_user,
            'profile': profile,
            'stats': stats,
            'current_month_days': current_month_days,
            'current_salary': current_salary,
            'salary_breakdown': salary_breakdown,
            'daily_records': daily_records,
            'recent_logs': recent_logs
        })

class AttendanceReportView(LoginRequiredMixin, View):
    def get(self, request):
        if not request.user.profile.is_admin_user:
            return redirect('dashboard')
            
        # Get all unique (user, date) combinations where status is SUCCESS
        # Optimization: Use values() to get distinct user_id and dates
        # order_by is required for distinct() to work reliably on some DB backends with pagination
        # We need to manually aggregate because distinct on fields is Postgres only, 
        # but here we can just get all success logs and process.
        # Better approach for SQLite/General:
        # Get all logs, then group in python or use a raw query.
        # Let's try a distinct query on date+user which works if we order by them.
        
        # Simpler approach: Get all logs order by date desc, user
        all_logs = AccessLog.objects.filter(status='SUCCESS').values('user__id', 'timestamp__date').distinct().order_by('-timestamp__date', 'user__id')
        
        # Paginator on the unique combinations
        paginator = Paginator(all_logs, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        report_data = []
        for entry in page_obj:
            user_id = entry['user__id']
            date = entry['timestamp__date']
            
            # Fetch user details - optimized to use IN clause if we collected IDs first, 
            # but for 20 items loop is fine.
            try:
                user = User.objects.get(id=user_id)
                profile = user.profile
            except User.DoesNotExist:
                continue

            # Get logs for this specific user and day to calc duration
            day_logs = AccessLog.objects.filter(user_id=user_id, status='SUCCESS', timestamp__date=date).order_by('timestamp')
            
            if not day_logs.exists():
                continue
                
            first_log = day_logs.first()
            last_log = day_logs.last()
            
            hours = 0
            if first_log and last_log and first_log != last_log:
                diff = last_log.timestamp - first_log.timestamp
                hours = round(diff.total_seconds() / 3600, 2)
            
            # Daily Salary is just the daily rate since they were present
            daily_salary = float(profile.daily_rate)
            
            report_data.append({
                'date': date,
                'user': user,
                'employee_id': profile.employee_id,
                'department': first_log.department.name if first_log.department else "-",
                'first_log': first_log.timestamp,
                'last_log': last_log.timestamp,
                'hours': hours,
                'daily_salary': daily_salary,
                'status': 'Present'
            })
            
        return render(request, 'access_control/attendance_report.html', {
            'report_data': report_data,
            'page_obj': page_obj
        })

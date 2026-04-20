from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('login/', views.EmployeeLoginView.as_view(), name='login'),
    path('admin/login/', views.AdminLoginView.as_view(), name='admin_login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.HomeView.as_view(), name='dashboard'),
    path('portal/', views.HomeView.as_view(), name='portal'),
    path('face-setup/', views.FaceSetupView.as_view(), name='face_setup'),
    path('verify-access/<int:dept_id>/', views.VerifyAccessView.as_view(), name='verify_access'),
    
    # Admin views
    path('admin-dashboard/', views.HomeView.as_view(), name='admin_dashboard'),
    path('manage-employees/', views.ManageEmployeesView.as_view(), name='manage_employees'),
    path('create-employee/', views.CreateEmployeeView.as_view(), name='create_employee'),
    path('edit-employee/<int:user_id>/', views.EditEmployeeView.as_view(), name='edit_employee'),
    path('delete-employee/<int:user_id>/', views.DeleteEmployeeView.as_view(), name='delete_employee'),
    path('logs/', views.AccessLogView.as_view(), name='logs'),
    path('daily-report/', views.DailyReportView.as_view(), name='daily_report'),
    path('attendance-report/', views.AttendanceReportView.as_view(), name='attendance_report'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('admin/employee/<int:user_id>/analytics/', views.EmployeeAnalyticsView.as_view(), name='admin_employee_analytics'),
]

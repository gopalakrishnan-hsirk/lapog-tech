from django.contrib import admin
from .models import UserProfile, Department, AccessLog, Alert

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'head', 'description', 'created_at')
    search_fields = ('name', 'head')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'designation', 'is_employee', 'is_admin_user')
    search_fields = ('user__username', 'employee_id', 'designation')
    list_filter = ('is_employee', 'is_admin_user', 'department_access')

@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'department', 'timestamp')
    list_filter = ('status', 'department')
    readonly_fields = ('timestamp',)

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_resolved', 'created_at')
    list_filter = ('is_resolved',)

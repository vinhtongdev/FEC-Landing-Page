from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ['-date_joined',]
    list_display = ('email','full_name','is_staff','is_active','date_joined')
    search_fields = ('email','full_name','phone')
    
    readonly_fields = ('last_login','date_joined')
    
    fieldsets = (
        (None, {'fields': ('email','password')}),
        ('Thông tin', {'fields': ('full_name','phone')}),
        ('Quyền', {'fields': ('is_active','is_staff','is_superuser','groups','user_permissions')}),
        ('Khác', {'fields': ('last_login','date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email','password1','password2','is_staff','is_superuser','is_active')}
        ),
    )
    
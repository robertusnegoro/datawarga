from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    Warga,
    Kompleks,
    TransaksiIuranBulanan,
    WargaPermissionGroup,
    UserPermission,
)


class PermissionGroupInline(admin.StackedInline):
    model = UserPermission
    can_delete = False
    verbose_name_plural = "group"


# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = [PermissionGroupInline]


# Register your models here.
admin.site.register(Warga)
admin.site.register(Kompleks)
admin.site.register(TransaksiIuranBulanan)
admin.site.register(WargaPermissionGroup)

# reregister the user
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

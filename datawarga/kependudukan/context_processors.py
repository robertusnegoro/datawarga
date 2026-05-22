from .version import VERSION


def app_version(request):
    return {"app_version": VERSION}


def kas_permissions(request):
    if not request.user.is_authenticated:
        return {"is_kas_user": False}

    if request.user.is_superuser:
        return {"is_kas_user": True}

    from kependudukan.models import UserPermission

    try:
        user_perm = UserPermission.objects.get(user=request.user)
        if user_perm.permission_group:
            group_name = str(user_perm.permission_group.group_name).lower()
            if group_name in ["bendahara", "rt_pic", "rt pic"]:
                return {"is_kas_user": True}
    except UserPermission.DoesNotExist:
        pass

    return {"is_kas_user": False}

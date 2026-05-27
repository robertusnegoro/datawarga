from __future__ import annotations
import logging
import time
import uuid
from datetime import timedelta
from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from kependudukan.forms import UserAddForm, UserEditForm
from kependudukan.models import UserProfile, UserInvitation, Warga
from kependudukan.utils.auth_guards import admin_or_petugas_required

logger = logging.getLogger(__name__)


def superuser_required(view_func):
    """
    Decorator that checks if the logged-in user is a superuser.
    Fails closed by raising a PermissionDenied exception.
    """

    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("Hanya super admin yang dapat mengakses fitur ini.")

    return _wrapped_view


@superuser_required
def user_management(request: HttpRequest) -> HttpResponse:
    correlation_id = str(uuid.uuid4())
    start_time = time.time()
    user = request.user

    logger.info(
        "Operation started",
        extra={
            "operation": "user_management_list",
            "userId": user.id,
            "correlationId": correlation_id,
        },
    )

    # Pop one-time token from session so it only displays once
    new_user_token = request.session.pop("new_user_invitation_token", None)

    from django.core.paginator import Paginator

    users_qs = User.objects.all().order_by("-id")
    paginator = Paginator(users_qs, 15)  # 15 users per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    user_data = []

    for u in page_obj:
        # Determine status
        profile, _ = UserProfile.objects.get_or_create(user=u)

        # Check active invitations
        try:
            invitation = u.invitation
        except UserInvitation.DoesNotExist:
            invitation = None

        status = "Active"
        if profile.is_permanently_locked or not u.is_active:
            if invitation and not invitation.is_used:
                status = "Pending"
            else:
                status = "Blocked"

        user_data.append(
            {
                "user": u,
                "profile": profile,
                "invitation": invitation,
                "status": status,
            }
        )

    # Get invitation template text with placeholders to be formatted in Javascript/HTML
    invitation_template = (
        "Halo {name},\n\n"
        "Anda telah diundang untuk bergabung di portal Data Warga.\n"
        "Silakan klik tautan berikut untuk membuat kata sandi Anda dan mengaktifkan akun Anda:\n"
        "{link}\n\n"
        "Tautan ini berlaku selama 24 jam (sampai dengan {expires_at}).\n\n"
        "Terima kasih,\n"
        "Administrator Data Warga"
    )

    context = {
        "user_data": user_data,
        "page_obj": page_obj,
        "new_user_invitation_token": new_user_token,
        "invitation_template": invitation_template,
    }

    duration = int((time.time() - start_time) * 1000)
    logger.info(
        "Operation success",
        extra={
            "operation": "user_management_list",
            "userId": user.id,
            "correlationId": correlation_id,
            "duration": duration,
        },
    )
    return render(request, "admin/user_management.html", context)


@superuser_required
def user_add(request: HttpRequest) -> HttpResponse:
    correlation_id = str(uuid.uuid4())
    start_time = time.time()
    user = request.user

    logger.info(
        "Operation started",
        extra={
            "operation": "user_add",
            "userId": user.id,
            "correlationId": correlation_id,
        },
    )

    if request.method == "POST":
        form = UserAddForm(request.POST)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.is_active = False  # Inactive until they set their password
            new_user.save()

            # Ensure profile is created (signal should have created it, but get_or_create to be safe)
            UserProfile.objects.get_or_create(user=new_user)

            # Create invitation link
            token = uuid.uuid4().hex
            expires_at = timezone.now() + timedelta(days=1)
            UserInvitation.objects.create(
                user=new_user, token=token, expires_at=expires_at, is_used=False
            )

            duration = int((time.time() - start_time) * 1000)
            logger.info(
                "Operation success",
                extra={
                    "operation": "user_add",
                    "userId": user.id,
                    "newUserId": new_user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                },
            )
            messages.success(
                request,
                f"User {new_user.username} berhasil dibuat. Silakan salin tautan undangan untuk mengaktifkan akun.",
            )

            # Put the newly created user's token in session so the template can auto-show the copy modal
            request.session["new_user_invitation_token"] = token
            return redirect("kependudukan:user_management")
        else:
            duration = int((time.time() - start_time) * 1000)
            logger.error(
                "Operation failure: invalid form",
                extra={
                    "operation": "user_add",
                    "userId": user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                    "error": str(form.errors),
                },
            )
    else:
        form = UserAddForm()

    context = {
        "form": form,
        "title": "Tambah User Baru",
    }
    return render(request, "admin/user_form.html", context)


@superuser_required
def user_edit(request: HttpRequest, user_id: int) -> HttpResponse:
    correlation_id = str(uuid.uuid4())
    start_time = time.time()
    current_user = request.user
    target_user = get_object_or_404(User, pk=user_id)

    logger.info(
        "Operation started",
        extra={
            "operation": "user_edit",
            "userId": current_user.id,
            "targetUserId": target_user.id,
            "correlationId": correlation_id,
        },
    )

    if request.method == "POST":
        form = UserEditForm(request.POST, instance=target_user)
        if form.is_valid():
            form.save()
            duration = int((time.time() - start_time) * 1000)
            logger.info(
                "Operation success",
                extra={
                    "operation": "user_edit",
                    "userId": current_user.id,
                    "targetUserId": target_user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                },
            )
            messages.success(
                request, f"User {target_user.username} berhasil diperbarui."
            )
            return redirect("kependudukan:user_management")
        else:
            duration = int((time.time() - start_time) * 1000)
            logger.error(
                "Operation failure: invalid form",
                extra={
                    "operation": "user_edit",
                    "userId": current_user.id,
                    "targetUserId": target_user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                    "error": str(form.errors),
                },
            )
    else:
        form = UserEditForm(instance=target_user)

    context = {
        "form": form,
        "title": f"Edit User: {target_user.username}",
    }
    return render(request, "admin/user_form.html", context)


@superuser_required
def user_block(request: HttpRequest, user_id: int) -> HttpResponse:
    correlation_id = str(uuid.uuid4())
    start_time = time.time()
    current_user = request.user
    target_user = get_object_or_404(User, pk=user_id)

    logger.info(
        "Operation started",
        extra={
            "operation": "user_block",
            "userId": current_user.id,
            "targetUserId": target_user.id,
            "correlationId": correlation_id,
        },
    )

    if request.method != "POST":
        return redirect("kependudukan:user_management")

    if target_user.is_superuser:
        duration = int((time.time() - start_time) * 1000)
        logger.error(
            "Operation failure: cannot block superuser",
            extra={
                "operation": "user_block",
                "userId": current_user.id,
                "targetUserId": target_user.id,
                "correlationId": correlation_id,
                "duration": duration,
            },
        )
        messages.error(request, "Anda tidak dapat memblokir sesama super admin.")
        return redirect("kependudukan:user_management")

    profile, _ = UserProfile.objects.get_or_create(user=target_user)
    profile.is_permanently_locked = True
    profile.save()

    target_user.is_active = False
    target_user.save()

    duration = int((time.time() - start_time) * 1000)
    logger.info(
        "Operation success",
        extra={
            "operation": "user_block",
            "userId": current_user.id,
            "targetUserId": target_user.id,
            "correlationId": correlation_id,
            "duration": duration,
        },
    )
    messages.success(request, f"User {target_user.username} berhasil diblokir.")
    return redirect("kependudukan:user_management")


@superuser_required
def user_unblock(request: HttpRequest, user_id: int) -> HttpResponse:
    correlation_id = str(uuid.uuid4())
    start_time = time.time()
    current_user = request.user
    target_user = get_object_or_404(User, pk=user_id)

    logger.info(
        "Operation started",
        extra={
            "operation": "user_unblock",
            "userId": current_user.id,
            "targetUserId": target_user.id,
            "correlationId": correlation_id,
        },
    )

    if request.method != "POST":
        return redirect("kependudukan:user_management")

    profile, _ = UserProfile.objects.get_or_create(user=target_user)
    profile.is_permanently_locked = False
    profile.failed_login_attempts = 0
    profile.shadow_ban_expires_at = None
    profile.save()

    target_user.is_active = True
    target_user.save()

    duration = int((time.time() - start_time) * 1000)
    logger.info(
        "Operation success",
        extra={
            "operation": "user_unblock",
            "userId": current_user.id,
            "targetUserId": target_user.id,
            "correlationId": correlation_id,
            "duration": duration,
        },
    )
    messages.success(
        request, f"User {target_user.username} berhasil diaktifkan kembali."
    )
    return redirect("kependudukan:user_management")


@superuser_required
def user_reset_mfa(request: HttpRequest, user_id: int) -> HttpResponse:
    correlation_id = str(uuid.uuid4())
    start_time = time.time()
    current_user = request.user
    target_user = get_object_or_404(User, pk=user_id)

    logger.info(
        "Operation started",
        extra={
            "operation": "user_reset_mfa",
            "userId": current_user.id,
            "targetUserId": target_user.id,
            "correlationId": correlation_id,
        },
    )

    if request.method != "POST":
        return redirect("kependudukan:user_management")

    profile, _ = UserProfile.objects.get_or_create(user=target_user)
    profile.mfa_enabled = False
    profile.totp_secret = None
    profile.save()

    duration = int((time.time() - start_time) * 1000)
    logger.info(
        "Operation success",
        extra={
            "operation": "user_reset_mfa",
            "userId": current_user.id,
            "targetUserId": target_user.id,
            "correlationId": correlation_id,
            "duration": duration,
        },
    )
    messages.success(
        request, f"MFA untuk user {target_user.username} berhasil di-reset."
    )
    return redirect("kependudukan:user_management")


@superuser_required
def user_reset_password(request: HttpRequest, user_id: int) -> HttpResponse:
    correlation_id = str(uuid.uuid4())
    start_time = time.time()
    current_user = request.user
    target_user = get_object_or_404(User, pk=user_id)

    logger.info(
        "Operation started",
        extra={
            "operation": "user_reset_password",
            "userId": current_user.id,
            "targetUserId": target_user.id,
            "correlationId": correlation_id,
        },
    )

    if request.method == "POST":
        form = SetPasswordForm(user=target_user, data=request.POST)
        if form.is_valid():
            form.save()
            duration = int((time.time() - start_time) * 1000)
            logger.info(
                "Operation success",
                extra={
                    "operation": "user_reset_password",
                    "userId": current_user.id,
                    "targetUserId": target_user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                },
            )
            messages.success(
                request,
                f"Kata sandi untuk user {target_user.username} berhasil di-reset.",
            )
            return redirect("kependudukan:user_management")
        else:
            duration = int((time.time() - start_time) * 1000)
            logger.error(
                "Operation failure: invalid form",
                extra={
                    "operation": "user_reset_password",
                    "userId": current_user.id,
                    "targetUserId": target_user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                    "error": str(form.errors),
                },
            )
    else:
        form = SetPasswordForm(user=target_user)

    context = {
        "form": form,
        "target_user": target_user,
    }
    return render(request, "admin/user_reset_password.html", context)


@superuser_required
def invitation_expire(request: HttpRequest, user_id: int) -> HttpResponse:
    correlation_id = str(uuid.uuid4())
    start_time = time.time()
    current_user = request.user
    target_user = get_object_or_404(User, pk=user_id)

    logger.info(
        "Operation started",
        extra={
            "operation": "invitation_expire",
            "userId": current_user.id,
            "targetUserId": target_user.id,
            "correlationId": correlation_id,
        },
    )

    if request.method != "POST":
        return redirect("kependudukan:user_management")

    invitation = get_object_or_404(UserInvitation, user=target_user)
    invitation.expires_at = timezone.now() - timedelta(seconds=1)
    invitation.save()

    duration = int((time.time() - start_time) * 1000)
    logger.info(
        "Operation success",
        extra={
            "operation": "invitation_expire",
            "userId": current_user.id,
            "targetUserId": target_user.id,
            "correlationId": correlation_id,
            "duration": duration,
        },
    )
    messages.success(
        request,
        f"Undangan untuk user {target_user.username} berhasil di-expire secara manual.",
    )
    return redirect("kependudukan:user_management")


@superuser_required
def invitation_recreate(request: HttpRequest, user_id: int) -> HttpResponse:
    correlation_id = str(uuid.uuid4())
    start_time = time.time()
    current_user = request.user
    target_user = get_object_or_404(User, pk=user_id)

    logger.info(
        "Operation started",
        extra={
            "operation": "invitation_recreate",
            "userId": current_user.id,
            "targetUserId": target_user.id,
            "correlationId": correlation_id,
        },
    )

    if request.method != "POST":
        return redirect("kependudukan:user_management")

    token = uuid.uuid4().hex
    expires_at = timezone.now() + timedelta(days=1)

    invitation, created = UserInvitation.objects.get_or_create(
        user=target_user,
        defaults={"token": token, "expires_at": expires_at, "is_used": False},
    )

    if not created:
        invitation.token = token
        invitation.expires_at = expires_at
        invitation.is_used = False
        invitation.save()

    duration = int((time.time() - start_time) * 1000)
    logger.info(
        "Operation success",
        extra={
            "operation": "invitation_recreate",
            "userId": current_user.id,
            "targetUserId": target_user.id,
            "correlationId": correlation_id,
            "duration": duration,
        },
    )
    messages.success(
        request, f"Tautan undangan baru untuk {target_user.username} berhasil dibuat."
    )
    request.session["new_user_invitation_token"] = token
    return redirect("kependudukan:user_management")


def user_activate(request: HttpRequest, token: str) -> HttpResponse:
    """
    Public endpoint for invited users to set their password and activate their account.
    """
    correlation_id = str(uuid.uuid4())
    start_time = time.time()

    logger.info(
        "Operation started",
        extra={
            "operation": "user_activate",
            "token": token,
            "correlationId": correlation_id,
        },
    )

    # Validate token
    try:
        invitation = UserInvitation.objects.get(token=token)
    except UserInvitation.DoesNotExist:
        duration = int((time.time() - start_time) * 1000)
        logger.warning(
            "Operation failure: token not found",
            extra={
                "operation": "user_activate",
                "token": token,
                "correlationId": correlation_id,
                "duration": duration,
            },
        )
        return render(
            request,
            "registration/invite_activate.html",
            {"error": "Tautan undangan tidak valid."},
        )

    if not invitation.is_valid():
        duration = int((time.time() - start_time) * 1000)
        error_msg = (
            "Tautan undangan sudah digunakan."
            if invitation.is_used
            else "Tautan undangan sudah kedaluwarsa."
        )
        logger.warning(
            f"Operation failure: {error_msg}",
            extra={
                "operation": "user_activate",
                "userId": invitation.user.id,
                "correlationId": correlation_id,
                "duration": duration,
            },
        )
        return render(
            request, "registration/invite_activate.html", {"error": error_msg}
        )

    target_user = invitation.user

    # If the user is permanently locked (blocked), block activation
    profile, _ = UserProfile.objects.get_or_create(user=target_user)
    if profile.is_permanently_locked:
        duration = int((time.time() - start_time) * 1000)
        logger.warning(
            "Operation failure: blocked user attempting activation",
            extra={
                "operation": "user_activate",
                "userId": target_user.id,
                "correlationId": correlation_id,
                "duration": duration,
            },
        )
        return render(
            request,
            "registration/invite_activate.html",
            {"error": "Akun ini telah dinonaktifkan secara permanen."},
        )

    if request.method == "POST":
        form = SetPasswordForm(user=target_user, data=request.POST)
        if form.is_valid():
            # Save new password
            form.save()

            # Activate user
            target_user.is_active = True
            target_user.save()

            # Mark invitation as used
            invitation.is_used = True
            invitation.save()

            duration = int((time.time() - start_time) * 1000)
            logger.info(
                "Operation success",
                extra={
                    "operation": "user_activate",
                    "userId": target_user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                },
            )
            messages.success(
                request,
                "Akun Anda berhasil diaktifkan! Silakan masuk dengan kata sandi baru Anda.",
            )
            return redirect("login")
    else:
        form = SetPasswordForm(user=target_user)

    context = {
        "form": form,
        "target_user": target_user,
        "token": token,
    }
    return render(request, "registration/invite_activate.html", context)


@admin_or_petugas_required
def admin_approvals(request: HttpRequest) -> HttpResponse:
    """
    Unified dashboard for admins to process pending profile updates,
    document requests, vehicle registrations, and iuran payment proofs.
    """
    correlation_id = str(uuid.uuid4())
    start_time = time.time()
    user = request.user

    logger.info(
        "Operation started",
        extra={
            "operation": "admin_approvals",
            "userId": user.id,
            "correlationId": correlation_id,
        },
    )

    from kependudukan.models import (
        WargaUpdateRequest,
        Surat,
        TransaksiIuranBulanan,
        Kendaraan,
        Penandatangan,
    )
    from kependudukan.services.warga_service import (
        approve_warga_update_request,
        reject_warga_update_request,
        approve_surat,
        reject_surat,
        approve_iuran,
        reject_iuran,
        approve_kendaraan,
        reject_kendaraan,
    )
    from kependudukan.errors import ValidationError
    from django.conf import settings

    if request.method == "POST":
        action = request.POST.get("action")
        target_id = int(request.POST.get("id", 0))
        reason = request.POST.get("reason", "").strip()

        try:
            if action == "approve_warga":
                approve_warga_update_request(target_id, user)
                messages.success(request, "Perubahan data warga berhasil disetujui.")
            elif action == "reject_warga":
                if not reason:
                    raise ValidationError("Alasan penolakan harus diisi.")
                reject_warga_update_request(target_id, user, reason)
                messages.success(request, "Perubahan data warga berhasil ditolak.")

            elif action == "approve_surat":
                nomor_surat = request.POST.get("nomor_surat", "").strip()
                penandatangan_id = request.POST.get("penandatangan")
                if penandatangan_id:
                    penandatangan_id = int(penandatangan_id)
                approve_surat(target_id, user, nomor_surat, penandatangan_id)
                messages.success(request, "Permohonan surat berhasil disetujui.")
            elif action == "reject_surat":
                if not reason:
                    raise ValidationError("Alasan penolakan harus diisi.")
                reject_surat(target_id, user, reason)
                messages.success(request, "Permohonan surat berhasil ditolak.")

            elif action == "approve_iuran":
                approve_iuran(target_id, user)
                messages.success(request, "Bukti pembayaran iuran berhasil disetujui.")
            elif action == "reject_iuran":
                if not reason:
                    raise ValidationError("Alasan penolakan harus diisi.")
                reject_iuran(target_id, user, reason)
                messages.success(request, "Bukti pembayaran iuran berhasil ditolak.")

            elif action == "approve_kendaraan":
                approve_kendaraan(target_id, user)
                messages.success(request, "Registrasi kendaraan berhasil disetujui.")
            elif action == "reject_kendaraan":
                if not reason:
                    raise ValidationError("Alasan penolakan harus diisi.")
                reject_kendaraan(target_id, user, reason)
                messages.success(request, "Registrasi kendaraan berhasil ditolak.")

        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(
                f"Failed to process approval action {action} on ID {target_id}: {str(e)}",
                exc_info=True,
            )
            messages.error(
                request, "Terjadi kesalahan sistem saat memproses persetujuan."
            )

        return redirect("kependudukan:admin_approvals")

    # Fetch pending requests
    pending_warga = WargaUpdateRequest.objects.filter(status="PENDING").order_by(
        "-created_at"
    )
    pending_surat = Surat.objects.filter(status="PENDING").order_by("-tanggal_surat")
    pending_iuran = TransaksiIuranBulanan.objects.filter(status="PENDING").order_by(
        "-id"
    )
    pending_kendaraan = Kendaraan.objects.filter(status="PENDING").order_by("-id")

    penandatangan_choices = Penandatangan.objects.filter(aktif=True)

    context = {
        "pending_warga": pending_warga,
        "pending_surat": pending_surat,
        "pending_iuran": pending_iuran,
        "pending_kendaraan": pending_kendaraan,
        "penandatangan_choices": penandatangan_choices,
        "MEDIA_URL": settings.MEDIA_URL,
    }

    duration = int((time.time() - start_time) * 1000)
    logger.info(
        "Operation success",
        extra={
            "operation": "admin_approvals",
            "userId": user.id,
            "correlationId": correlation_id,
            "duration": duration,
        },
    )
    return render(request, "admin/admin_approvals.html", context)


@admin_or_petugas_required
def warga_invite_login(request: HttpRequest, idwarga: int) -> HttpResponse:
    """
    Creates and issues an activation invitation for a registered resident (warga).
    """
    correlation_id = str(uuid.uuid4())
    start_time = time.time()
    user = request.user

    logger.info(
        "Operation started",
        extra={
            "operation": "warga_invite_login",
            "userId": user.id,
            "wargaId": idwarga,
            "correlationId": correlation_id,
        },
    )

    warga = get_object_or_404(Warga, pk=idwarga)
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        if not email:
            messages.error(request, "Email wajib diisi.")
            return redirect(
                reverse("kependudukan:detailWarga", kwargs={"idwarga": idwarga})
            )

        from kependudukan.services.warga_service import create_warga_invitation
        from kependudukan.errors import ValidationError

        try:
            activation_link = create_warga_invitation(idwarga, email, request)

            # Keep compatibility with existing javascript clipboard copy modal
            token = activation_link.split("/")[-2]
            request.session["new_user_invitation_token"] = token

            messages.success(
                request,
                f"Undangan untuk {warga.nama_lengkap} berhasil dibuat. Silakan salin tautan undangan.",
            )
        except ValidationError as e:
            duration = int((time.time() - start_time) * 1000)
            logger.warning(
                "Operation failed validation",
                extra={
                    "operation": "warga_invite_login",
                    "userId": user.id,
                    "wargaId": idwarga,
                    "correlationId": correlation_id,
                    "duration": duration,
                    "error": str(e),
                },
            )
            messages.error(request, str(e))
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            logger.error(
                "Operation failed",
                extra={
                    "operation": "warga_invite_login",
                    "userId": user.id,
                    "wargaId": idwarga,
                    "correlationId": correlation_id,
                    "duration": duration,
                    "error": str(e),
                },
                exc_info=True,
            )
            messages.error(request, "Terjadi kesalahan saat membuat undangan.")

        duration = int((time.time() - start_time) * 1000)
        logger.info(
            "Operation success",
            extra={
                "operation": "warga_invite_login",
                "userId": user.id,
                "wargaId": idwarga,
                "correlationId": correlation_id,
                "duration": duration,
            },
        )

    return redirect(reverse("kependudukan:detailWarga", kwargs={"idwarga": idwarga}))

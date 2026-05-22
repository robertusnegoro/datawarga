from __future__ import annotations
import base64
import io
import logging
import time
import uuid
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone
import pyotp
import qrcode
from .forms import UserUpdateForm, UserProfileUpdateForm, MfaVerifyForm

logger = logging.getLogger(__name__)


@login_required
def profile_edit(request: HttpRequest) -> HttpResponse:
    correlation_id = str(uuid.uuid4())
    user = request.user
    profile = user.profile

    logger.info(
        "Operation started",
        extra={
            "operation": "profile_edit",
            "userId": user.id,
            "correlationId": correlation_id,
        },
    )
    start_time = time.time()

    user_form = UserUpdateForm(instance=user)
    profile_form = UserProfileUpdateForm(instance=profile)
    password_form = PasswordChangeForm(user=user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update_profile":
            user_form = UserUpdateForm(request.POST, instance=user)
            profile_form = UserProfileUpdateForm(
                request.POST, request.FILES, instance=profile
            )

            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()

                duration = int((time.time() - start_time) * 1000)
                logger.info(
                    "Operation success",
                    extra={
                        "operation": "update_profile",
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "duration": duration,
                    },
                )

                messages.success(request, "Profil Anda berhasil diperbarui.")
                return redirect("kependudukan:profile_edit")
            else:
                duration = int((time.time() - start_time) * 1000)
                errors = {**user_form.errors, **profile_form.errors}
                logger.error(
                    "Operation failure",
                    extra={
                        "operation": "update_profile",
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "duration": duration,
                        "error": str(errors),
                    },
                )
                messages.error(
                    request,
                    "Terjadi kesalahan saat memperbarui profil. Silakan periksa kembali isian Anda.",
                )

        elif action == "change_password":
            password_form = PasswordChangeForm(user=user, data=request.POST)
            if password_form.is_valid():
                user_with_new_password = password_form.save()
                update_session_auth_hash(request, user_with_new_password)

                duration = int((time.time() - start_time) * 1000)
                logger.info(
                    "Operation success",
                    extra={
                        "operation": "change_password",
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "duration": duration,
                    },
                )

                messages.success(request, "Kata sandi Anda berhasil diperbarui.")
                return redirect("kependudukan:profile_edit")
            else:
                duration = int((time.time() - start_time) * 1000)
                logger.error(
                    "Operation failure",
                    extra={
                        "operation": "change_password",
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "duration": duration,
                        "error": str(password_form.errors),
                    },
                )
                messages.error(
                    request,
                    "Gagal mengubah kata sandi. Silakan periksa kembali isian Anda.",
                )

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "password_form": password_form,
    }

    duration = int((time.time() - start_time) * 1000)
    logger.info(
        "Operation success",
        extra={
            "operation": "render_profile",
            "userId": user.id,
            "correlationId": correlation_id,
            "duration": duration,
        },
    )
    return render(request, "profile.html", context)


def custom_login(request: HttpRequest) -> HttpResponse:
    correlation_id = str(uuid.uuid4())
    start_time = time.time()

    logger.info(
        "Operation started",
        extra={
            "operation": "custom_login",
            "correlationId": correlation_id,
        },
    )

    if request.user.is_authenticated:
        duration = int((time.time() - start_time) * 1000)
        logger.info(
            "Operation success: user already authenticated",
            extra={
                "operation": "custom_login",
                "userId": request.user.id,
                "correlationId": correlation_id,
                "duration": duration,
            },
        )
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            profile = user.profile
            if profile.mfa_enabled:
                request.session["pre_mfa_user_id"] = user.id
                request.session["pre_mfa_next"] = request.POST.get("next", "")

                duration = int((time.time() - start_time) * 1000)
                logger.info(
                    "Operation success: credentials verified, redirecting to MFA verification",
                    extra={
                        "operation": "custom_login",
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "duration": duration,
                        "mfa_required": True,
                    },
                )
                return redirect("kependudukan:mfa_verify")
            else:
                auth_login(request, user)
                next_url = request.POST.get("next", "") or settings.LOGIN_REDIRECT_URL

                duration = int((time.time() - start_time) * 1000)
                logger.info(
                    "Operation success: user logged in successfully without MFA",
                    extra={
                        "operation": "custom_login",
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "duration": duration,
                        "mfa_required": False,
                    },
                )
                return redirect(next_url)
        else:
            username = request.POST.get("username")
            if username:
                try:
                    user = User.objects.get(username=username)
                    profile = user.profile
                    now = timezone.now()

                    warning_msg = None
                    if (
                        getattr(profile, "is_permanently_locked", False)
                        or not user.is_active
                    ):
                        warning_msg = "Akun Anda telah dikunci secara permanen. Silakan hubungi administrator."
                    elif (
                        profile.shadow_ban_expires_at
                        and now < profile.shadow_ban_expires_at
                    ):
                        warning_msg = "Akun Anda sedang dibekukan sementara selama 30 menit karena 3 kali salah memasukkan kata sandi."
                    elif profile.failed_login_attempts == 2:
                        warning_msg = "Peringatan: 1 kali salah lagi akun Anda akan dibekukan sementara selama 30 menit."
                    elif profile.failed_login_attempts == 5:
                        warning_msg = "Peringatan: 1 kali salah lagi akun Anda akan dikunci secara permanen."

                    if warning_msg:
                        form.errors["__all__"] = form.error_class([warning_msg])
                except User.DoesNotExist:
                    pass

            duration = int((time.time() - start_time) * 1000)
            logger.warning(
                "Operation failure: login credentials invalid or locked out",
                extra={
                    "operation": "custom_login",
                    "correlationId": correlation_id,
                    "duration": duration,
                    "error": str(form.errors),
                },
            )
    else:
        form = AuthenticationForm(request)

    next_url = request.GET.get("next", "")
    context = {"form": form, "next": next_url}

    duration = int((time.time() - start_time) * 1000)
    logger.info(
        "Operation success: render login page",
        extra={
            "operation": "render_login",
            "correlationId": correlation_id,
            "duration": duration,
        },
    )
    return render(request, "registration/login.html", context)


def mfa_verify(request: HttpRequest) -> HttpResponse:
    correlation_id = str(uuid.uuid4())
    start_time = time.time()

    logger.info(
        "Operation started",
        extra={
            "operation": "mfa_verify",
            "correlationId": correlation_id,
        },
    )

    user_id = request.session.get("pre_mfa_user_id")
    if not user_id:
        duration = int((time.time() - start_time) * 1000)
        logger.warning(
            "Operation failure: no user in pre_mfa session",
            extra={
                "operation": "mfa_verify",
                "correlationId": correlation_id,
                "duration": duration,
                "error": "No pre_mfa_user_id in session",
            },
        )
        return redirect("login")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        duration = int((time.time() - start_time) * 1000)
        logger.error(
            "Operation failure: user not found",
            extra={
                "operation": "mfa_verify",
                "correlationId": correlation_id,
                "duration": duration,
                "error": "User with pre_mfa_user_id not found",
            },
        )
        return redirect("login")

    profile = user.profile

    now = timezone.now()
    if getattr(profile, "is_permanently_locked", False) or not user.is_active:
        duration = int((time.time() - start_time) * 1000)
        logger.warning(
            "Operation failure: user locked out during MFA verification",
            extra={
                "operation": "mfa_verify",
                "userId": user.id,
                "correlationId": correlation_id,
                "duration": duration,
                "error": "User is permanently locked or inactive",
            },
        )
        messages.error(
            request,
            "Akun Anda telah dikunci secara permanen. Silakan hubungi administrator.",
        )
        return redirect("login")

    if profile.shadow_ban_expires_at and now < profile.shadow_ban_expires_at:
        duration = int((time.time() - start_time) * 1000)
        logger.warning(
            "Operation failure: user shadow banned during MFA verification",
            extra={
                "operation": "mfa_verify",
                "userId": user.id,
                "correlationId": correlation_id,
                "duration": duration,
                "error": "User is temporarily shadow banned",
            },
        )
        messages.error(
            request,
            "Akun Anda sedang dibekukan sementara selama 30 menit karena 3 kali salah memasukkan kata sandi.",
        )
        return redirect("login")

    if request.method == "POST":
        form = MfaVerifyForm(request.POST)
        if form.is_valid():
            token = form.cleaned_data["token"].strip()
            totp = pyotp.TOTP(profile.totp_secret)
            if totp.verify(token):
                auth_login(request, user)
                # Cleanup session
                del request.session["pre_mfa_user_id"]
                next_url = (
                    request.session.pop("pre_mfa_next", "")
                    or settings.LOGIN_REDIRECT_URL
                )

                duration = int((time.time() - start_time) * 1000)
                logger.info(
                    "Operation success: MFA code verified, user logged in",
                    extra={
                        "operation": "mfa_verify",
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "duration": duration,
                    },
                )
                messages.success(request, "Selamat datang kembali!")
                return redirect(next_url)
            else:
                duration = int((time.time() - start_time) * 1000)
                logger.warning(
                    "Operation failure: incorrect MFA token",
                    extra={
                        "operation": "mfa_verify",
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "duration": duration,
                        "error": "Invalid TOTP token supplied",
                    },
                )
                messages.error(request, "Kode verification salah. Silakan coba lagi.")
        else:
            duration = int((time.time() - start_time) * 1000)
            logger.warning(
                "Operation failure: invalid MFA verification form",
                extra={
                    "operation": "mfa_verify",
                    "userId": user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                    "error": str(form.errors),
                },
            )
            messages.error(
                request, "Terjadi kesalahan. Pastikan Anda memasukkan 6 digit angka."
            )
    else:
        form = MfaVerifyForm()

    context = {"form": form}
    duration = int((time.time() - start_time) * 1000)
    logger.info(
        "Operation success: render MFA verification page",
        extra={
            "operation": "render_mfa_verify",
            "userId": user.id,
            "correlationId": correlation_id,
            "duration": duration,
        },
    )
    return render(request, "registration/mfa_verify.html", context)


@login_required
def mfa_setup(request: HttpRequest) -> HttpResponse:
    correlation_id = str(uuid.uuid4())
    start_time = time.time()
    user = request.user

    logger.info(
        "Operation started",
        extra={
            "operation": "mfa_setup",
            "userId": user.id,
            "correlationId": correlation_id,
        },
    )

    profile = user.profile
    if profile.mfa_enabled:
        duration = int((time.time() - start_time) * 1000)
        logger.warning(
            "Operation failure: MFA already enabled",
            extra={
                "operation": "mfa_setup",
                "userId": user.id,
                "correlationId": correlation_id,
                "duration": duration,
                "error": "MFA is already enabled for this user",
            },
        )
        messages.warning(request, "MFA sudah aktif pada akun Anda.")
        return redirect("kependudukan:profile_edit")

    # Get or generate temporary secret in session
    temp_secret = request.session.get("mfa_temp_secret")
    if not temp_secret:
        temp_secret = pyotp.random_base32()
        request.session["mfa_temp_secret"] = temp_secret

    totp = pyotp.TOTP(temp_secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.username, issuer_name="DataWarga"
    )

    # Generate QR Code offline using the python qrcode package
    qr = qrcode.QRCode(version=1, box_size=5, border=3)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()

    if request.method == "POST":
        form = MfaVerifyForm(request.POST)
        if form.is_valid():
            token = form.cleaned_data["token"].strip()
            if totp.verify(token):
                # Token verified! Save secret and enable MFA.
                profile.totp_secret = temp_secret
                profile.mfa_enabled = True
                profile.save()

                # Cleanup session
                if "mfa_temp_secret" in request.session:
                    del request.session["mfa_temp_secret"]

                duration = int((time.time() - start_time) * 1000)
                logger.info(
                    "Operation success: MFA enabled successfully",
                    extra={
                        "operation": "mfa_setup",
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "duration": duration,
                    },
                )
                messages.success(
                    request, "Multi-Factor Authentication (MFA) berhasil diaktifkan."
                )
                return redirect("kependudukan:profile_edit")
            else:
                duration = int((time.time() - start_time) * 1000)
                logger.warning(
                    "Operation failure: invalid token for setup verification",
                    extra={
                        "operation": "mfa_setup",
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "duration": duration,
                        "error": "Invalid verification token supplied during setup",
                    },
                )
                messages.error(request, "Kode verification salah. Silakan coba lagi.")
        else:
            duration = int((time.time() - start_time) * 1000)
            logger.warning(
                "Operation failure: invalid setup verification form",
                extra={
                    "operation": "mfa_setup",
                    "userId": user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                    "error": str(form.errors),
                },
            )
            messages.error(
                request, "Terjadi kesalahan. Pastikan Anda memasukkan 6 digit angka."
            )
    else:
        form = MfaVerifyForm()

    context = {
        "form": form,
        "qr_base64": qr_base64,
        "secret_key": temp_secret,
    }

    duration = int((time.time() - start_time) * 1000)
    logger.info(
        "Operation success: render MFA setup page",
        extra={
            "operation": "render_mfa_setup",
            "userId": user.id,
            "correlationId": correlation_id,
            "duration": duration,
        },
    )
    return render(request, "registration/mfa_setup.html", context)


@login_required
def mfa_disable(request: HttpRequest) -> HttpResponse:
    correlation_id = str(uuid.uuid4())
    start_time = time.time()
    user = request.user

    logger.info(
        "Operation started",
        extra={
            "operation": "mfa_disable",
            "userId": user.id,
            "correlationId": correlation_id,
        },
    )

    profile = user.profile
    if not profile.mfa_enabled:
        duration = int((time.time() - start_time) * 1000)
        logger.warning(
            "Operation failure: MFA is not enabled",
            extra={
                "operation": "mfa_disable",
                "userId": user.id,
                "correlationId": correlation_id,
                "duration": duration,
                "error": "MFA is not enabled for this user",
            },
        )
        messages.warning(request, "MFA tidak aktif pada akun Anda.")
        return redirect("kependudukan:profile_edit")

    if request.method == "POST":
        form = MfaVerifyForm(request.POST)
        if form.is_valid():
            token = form.cleaned_data["token"].strip()
            totp = pyotp.TOTP(profile.totp_secret)
            if totp.verify(token):
                # Token verified! Disable MFA.
                profile.mfa_enabled = False
                profile.totp_secret = None
                profile.save()

                duration = int((time.time() - start_time) * 1000)
                logger.info(
                    "Operation success: MFA disabled successfully",
                    extra={
                        "operation": "mfa_disable",
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "duration": duration,
                    },
                )
                messages.success(
                    request,
                    "Multi-Factor Authentication (MFA) berhasil dinonaktifkan.",
                )
                return redirect("kependudukan:profile_edit")
            else:
                duration = int((time.time() - start_time) * 1000)
                logger.warning(
                    "Operation failure: invalid token for disabling MFA",
                    extra={
                        "operation": "mfa_disable",
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "duration": duration,
                        "error": "Invalid verification token supplied during disable attempt",
                    },
                )
                messages.error(request, "Kode verification salah. Silakan coba lagi.")
        else:
            duration = int((time.time() - start_time) * 1000)
            logger.warning(
                "Operation failure: invalid disable confirmation form",
                extra={
                    "operation": "mfa_disable",
                    "userId": user.id,
                    "correlationId": correlation_id,
                    "duration": duration,
                    "error": str(form.errors),
                },
            )
            messages.error(
                request, "Terjadi kesalahan. Pastikan Anda memasukkan 6 digit angka."
            )
    else:
        form = MfaVerifyForm()

    context = {"form": form}
    duration = int((time.time() - start_time) * 1000)
    logger.info(
        "Operation success: render MFA disable confirmation page",
        extra={
            "operation": "render_mfa_disable",
            "userId": user.id,
            "correlationId": correlation_id,
            "duration": duration,
        },
    )
    return render(request, "registration/mfa_disable.html", context)

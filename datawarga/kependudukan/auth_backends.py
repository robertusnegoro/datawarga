import logging
import uuid
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from kependudukan.models import UserProfile

logger = logging.getLogger(__name__)


class LockoutBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            return None

        correlation_id = str(uuid.uuid4())

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Standard behaviour for security: return None to avoid username enumeration timing attacks
            return None

        profile, _ = UserProfile.objects.get_or_create(user=user)

        # 1. If permanently locked, block immediately
        if getattr(profile, "is_permanently_locked", False) or not user.is_active:
            logger.warning(
                "Login attempt blocked: user account is permanently locked",
                extra={
                    "operation": "login_lockout_block",
                    "username": username,
                    "userId": user.id,
                    "correlationId": correlation_id,
                    "status": "permanently_locked",
                },
            )
            return None

        # 2. If currently shadow banned, block immediately
        if (
            profile.shadow_ban_expires_at
            and timezone.now() < profile.shadow_ban_expires_at
        ):
            logger.warning(
                "Login attempt blocked: user account is temporarily shadow banned",
                extra={
                    "operation": "login_lockout_block",
                    "username": username,
                    "userId": user.id,
                    "correlationId": correlation_id,
                    "status": "shadow_ban_active",
                    "expires_at": str(profile.shadow_ban_expires_at),
                },
            )
            return None

        # 3. Perform credentials check
        authenticated_user = super().authenticate(
            request, username=username, password=password, **kwargs
        )

        if authenticated_user:
            # Successful authentication: reset failed login attempts
            if (
                profile.failed_login_attempts > 0
                or profile.shadow_ban_expires_at is not None
            ):
                profile.failed_login_attempts = 0
                profile.shadow_ban_expires_at = None
                profile.save()
                logger.info(
                    "User authenticated successfully: lockout status reset",
                    extra={
                        "operation": "login_lockout_reset",
                        "username": username,
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "status": "reset",
                    },
                )
        else:
            # Wrong credentials: increment failed attempts
            # Since we got past the lockout check, this is a new failure
            profile.failed_login_attempts += 1

            if profile.failed_login_attempts == 3:
                profile.shadow_ban_expires_at = timezone.now() + timedelta(minutes=30)
                logger.warning(
                    "Security lockout triggered: user is shadow banned for 30 minutes",
                    extra={
                        "operation": "login_lockout_trigger",
                        "username": username,
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "failed_attempts": profile.failed_login_attempts,
                        "status": "shadow_ban",
                        "expires_at": str(profile.shadow_ban_expires_at),
                    },
                )
            elif profile.failed_login_attempts >= 6:
                profile.is_permanently_locked = True
                user.is_active = False
                user.save()
                logger.warning(
                    "Security lockout triggered: user is permanently locked",
                    extra={
                        "operation": "login_lockout_trigger",
                        "username": username,
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "failed_attempts": profile.failed_login_attempts,
                        "status": "permanently_locked",
                    },
                )
            else:
                logger.warning(
                    "Login attempt failed: invalid credentials",
                    extra={
                        "operation": "login_failed",
                        "username": username,
                        "userId": user.id,
                        "correlationId": correlation_id,
                        "failed_attempts": profile.failed_login_attempts,
                        "status": "failure",
                    },
                )

            profile.save()

        return authenticated_user

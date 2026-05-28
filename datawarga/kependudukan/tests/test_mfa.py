import pyotp
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class MfaTestCase(TestCase):
    def setUp(self):
        self.username = "mfauser"
        self.password = "Secr3tP@ssw0rd!"
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email="mfauser@example.com",
        )
        # UserProfile should be automatically created via post_save signal
        self.profile = self.user.profile

    def test_mfa_setup_requires_login(self):
        """Test that unauthenticated users are redirected to login when accessing setup."""
        response = self.client.get(reverse("kependudukan:mfa_setup"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_mfa_setup_get(self):
        """Test GET request to MFA setup page generates temporary secret and renders QR code."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse("kependudukan:mfa_setup"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/mfa_setup.html")

        # Verify secret is generated in session
        temp_secret = self.client.session.get("mfa_temp_secret")
        self.assertIsNotNone(temp_secret)
        self.assertEqual(len(temp_secret), 32)

        # Verify QR Code and secret are in context
        self.assertIn("qr_base64", response.context)
        self.assertIn("secret_key", response.context)
        self.assertEqual(response.context["secret_key"], temp_secret)

    def test_mfa_setup_post_success(self):
        """Test successful MFA activation with correct TOTP token."""
        self.client.login(username=self.username, password=self.password)
        # Call GET first to initialize temp_secret in session
        self.client.get(reverse("kependudukan:mfa_setup"))

        temp_secret = self.client.session["mfa_temp_secret"]
        totp = pyotp.TOTP(temp_secret)
        valid_token = totp.now()

        response = self.client.post(
            reverse("kependudukan:mfa_setup"), data={"token": valid_token}
        )
        self.assertRedirects(response, reverse("kependudukan:profile_edit"))

        # Verify user profile has been updated
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.mfa_enabled)
        self.assertEqual(self.profile.totp_secret, temp_secret)

        # Verify session is cleaned up
        self.assertNotIn("mfa_temp_secret", self.client.session)

    def test_mfa_setup_post_invalid_token(self):
        """Test MFA setup fails when posting incorrect token."""
        self.client.login(username=self.username, password=self.password)
        self.client.get(reverse("kependudukan:mfa_setup"))

        response = self.client.post(
            reverse("kependudukan:mfa_setup"),
            data={"token": "000000"},  # Invalid token
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/mfa_setup.html")

        # Verify profile has not enabled MFA
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.mfa_enabled)
        self.assertIsNone(self.profile.totp_secret)

    def test_mfa_setup_already_enabled(self):
        """Test accessing setup page when MFA is already enabled redirects to profile."""
        self.profile.mfa_enabled = True
        self.profile.totp_secret = pyotp.random_base32()
        self.profile.save()

        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse("kependudukan:mfa_setup"))
        self.assertRedirects(response, reverse("kependudukan:profile_edit"))

    def test_login_interception_mfa_disabled(self):
        """Test login with correct credentials does not intercept when MFA is disabled."""
        response = self.client.post(
            reverse("login"),
            data={"username": self.username, "password": self.password},
        )
        # Should redirect to index or success page since MFA is disabled
        self.assertEqual(response.status_code, 302)
        # Check if user is authenticated
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_interception_mfa_enabled(self):
        """Test login with correct credentials redirects to MFA verification when MFA is enabled."""
        secret = pyotp.random_base32()
        self.profile.mfa_enabled = True
        self.profile.totp_secret = secret
        self.profile.save()

        response = self.client.post(
            reverse("login"),
            data={"username": self.username, "password": self.password},
        )
        self.assertRedirects(response, reverse("kependudukan:mfa_verify"))

        # User is NOT logged in fully yet
        self.assertNotIn("_auth_user_id", self.client.session)
        # Pre-MFA variables are in session
        self.assertEqual(self.client.session["pre_mfa_user_id"], self.user.id)

    def test_mfa_verify_requires_pre_mfa_session(self):
        """Test that accessing verify view without pre_mfa session redirects to login."""
        response = self.client.get(reverse("kependudukan:mfa_verify"))
        self.assertRedirects(response, reverse("login"))

    def test_mfa_verify_success(self):
        """Test successful token verification logs the user in."""
        secret = pyotp.random_base32()
        self.profile.mfa_enabled = True
        self.profile.totp_secret = secret
        self.profile.save()

        # Populate session with pre-MFA details
        session = self.client.session
        session["pre_mfa_user_id"] = self.user.id
        session["pre_mfa_next"] = "/profile/"
        session.save()

        totp = pyotp.TOTP(secret)
        valid_token = totp.now()

        response = self.client.post(
            reverse("kependudukan:mfa_verify"), data={"token": valid_token}
        )
        # Redirect to the target next URL
        self.assertRedirects(response, "/profile/")

        # User should now be logged in fully
        self.assertIn("_auth_user_id", self.client.session)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)
        # Pre-MFA variables should be cleaned up
        self.assertNotIn("pre_mfa_user_id", self.client.session)

    def test_mfa_verify_invalid_token(self):
        """Test unsuccessful token verification keeps the user logged out."""
        secret = pyotp.random_base32()
        self.profile.mfa_enabled = True
        self.profile.totp_secret = secret
        self.profile.save()

        session = self.client.session
        session["pre_mfa_user_id"] = self.user.id
        session.save()

        response = self.client.post(
            reverse("kependudukan:mfa_verify"), data={"token": "000000"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/mfa_verify.html")

        # Still not logged in
        self.assertNotIn("_auth_user_id", self.client.session)
        # Pre-MFA details remain
        self.assertEqual(self.client.session["pre_mfa_user_id"], self.user.id)

    def test_mfa_disable_requires_login(self):
        """Test that unauthenticated users cannot access disable view."""
        response = self.client.get(reverse("kependudukan:mfa_disable"))
        self.assertEqual(response.status_code, 302)

    def test_mfa_disable_not_enabled(self):
        """Test that if MFA is not enabled, disable view redirects to profile."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse("kependudukan:mfa_disable"))
        self.assertRedirects(response, reverse("kependudukan:profile_edit"))

    def test_mfa_disable_success(self):
        """Test successfully disabling MFA with correct token."""
        secret = pyotp.random_base32()
        self.profile.mfa_enabled = True
        self.profile.totp_secret = secret
        self.profile.save()

        self.client.login(username=self.username, password=self.password)

        totp = pyotp.TOTP(secret)
        valid_token = totp.now()

        response = self.client.post(
            reverse("kependudukan:mfa_disable"), data={"token": valid_token}
        )
        self.assertRedirects(response, reverse("kependudukan:profile_edit"))

        self.profile.refresh_from_db()
        self.assertFalse(self.profile.mfa_enabled)
        self.assertIsNone(self.profile.totp_secret)

    def test_mfa_disable_invalid_token(self):
        """Test disabling MFA fails with incorrect token."""
        secret = pyotp.random_base32()
        self.profile.mfa_enabled = True
        self.profile.totp_secret = secret
        self.profile.save()

        self.client.login(username=self.username, password=self.password)

        response = self.client.post(
            reverse("kependudukan:mfa_disable"), data={"token": "000000"}
        )
        self.assertEqual(response.status_code, 200)

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.mfa_enabled)
        self.assertEqual(self.profile.totp_secret, secret)

    def test_mfa_verify_blocked_when_permanently_locked(self):
        """Test that if user becomes permanently locked/inactive during MFA, they are redirected and blocked."""
        secret = pyotp.random_base32()
        self.profile.mfa_enabled = True
        self.profile.totp_secret = secret
        self.profile.is_permanently_locked = True
        self.profile.save()
        self.user.is_active = False
        self.user.save()

        session = self.client.session
        session["pre_mfa_user_id"] = self.user.id
        session.save()

        totp = pyotp.TOTP(secret)
        valid_token = totp.now()

        response = self.client.post(
            reverse("kependudukan:mfa_verify"), data={"token": valid_token}
        )
        self.assertRedirects(response, reverse("login"))

        # Verify flash message error
        messages_list = list(response.wsgi_request._messages)
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(
            str(messages_list[0]),
            "Akun Anda telah dikunci secara permanen. Silakan hubungi administrator.",
        )

    def test_mfa_verify_blocked_when_shadow_banned(self):
        """Test that if user is shadow banned during MFA, they are redirected and blocked."""
        from django.utils import timezone
        from datetime import timedelta

        secret = pyotp.random_base32()
        self.profile.mfa_enabled = True
        self.profile.totp_secret = secret
        self.profile.shadow_ban_expires_at = timezone.now() + timedelta(minutes=30)
        self.profile.save()

        session = self.client.session
        session["pre_mfa_user_id"] = self.user.id
        session.save()

        totp = pyotp.TOTP(secret)
        valid_token = totp.now()

        response = self.client.post(
            reverse("kependudukan:mfa_verify"), data={"token": valid_token}
        )
        self.assertRedirects(response, reverse("login"))

        # Verify flash message error
        messages_list = list(response.wsgi_request._messages)
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(
            str(messages_list[0]),
            "Akun Anda sedang dibekukan sementara selama 30 menit karena 3 kali salah memasukkan kata sandi.",
        )

    def test_api_token_mfa_required(self):
        """Test that the API token endpoint requires MFA token if MFA is enabled."""
        secret = pyotp.random_base32()
        self.profile.mfa_enabled = True
        self.profile.totp_secret = secret
        self.profile.save()

        response = self.client.post(
            reverse("kependudukan:token_obtain_pair"),
            data={"username": self.username, "password": self.password},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("mfa_token", response.json())
        self.assertEqual(response.json()["mfa_token"][0], "MFA token is required for this account.")

    def test_api_token_mfa_invalid(self):
        """Test that the API token endpoint rejects invalid MFA tokens."""
        secret = pyotp.random_base32()
        self.profile.mfa_enabled = True
        self.profile.totp_secret = secret
        self.profile.save()

        response = self.client.post(
            reverse("kependudukan:token_obtain_pair"),
            data={
                "username": self.username,
                "password": self.password,
                "mfa_token": "000000",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("mfa_token", response.json())
        self.assertEqual(response.json()["mfa_token"][0], "Invalid MFA token.")

    def test_api_token_mfa_valid(self):
        """Test that the API token endpoint issues a token when valid MFA token is provided."""
        secret = pyotp.random_base32()
        self.profile.mfa_enabled = True
        self.profile.totp_secret = secret
        self.profile.save()

        totp = pyotp.TOTP(secret)
        valid_token = totp.now()

        response = self.client.post(
            reverse("kependudukan:token_obtain_pair"),
            data={
                "username": self.username,
                "password": self.password,
                "mfa_token": valid_token,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())

    def test_api_token_mfa_disabled(self):
        """Test that the API token endpoint works without MFA token if MFA is disabled."""
        self.profile.mfa_enabled = False
        self.profile.save()

        response = self.client.post(
            reverse("kependudukan:token_obtain_pair"),
            data={"username": self.username, "password": self.password},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())

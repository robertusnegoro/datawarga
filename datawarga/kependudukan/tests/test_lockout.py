from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import authenticate
from django.urls import reverse


class LockoutBackendTestCase(TestCase):
    def setUp(self):
        self.username = "testlockoutuser"
        self.password = "CorrectP@ssword123!"
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email="lockouttest@example.com",
        )
        self.profile = self.user.profile

    def test_initial_state(self):
        """Test that a new user starts with 0 failed attempts and no lockout."""
        self.assertEqual(self.profile.failed_login_attempts, 0)
        self.assertIsNone(self.profile.shadow_ban_expires_at)
        self.assertFalse(self.profile.is_permanently_locked)

    def test_successful_login_does_not_increment_counter(self):
        """Test that successful login keeps failed attempts at 0."""
        user = authenticate(username=self.username, password=self.password)
        self.assertIsNotNone(user)
        self.assertEqual(user.username, self.username)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.failed_login_attempts, 0)

    def test_failed_login_increments_counter(self):
        """Test that failing logins increments failed_login_attempts."""
        # 1st fail
        user = authenticate(username=self.username, password="wrong-password")
        self.assertIsNone(user)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.failed_login_attempts, 1)

        # 2nd fail
        user = authenticate(username=self.username, password="wrong-password")
        self.assertIsNone(user)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.failed_login_attempts, 2)

    def test_third_failed_login_triggers_shadow_ban(self):
        """Test that the 3rd failed login triggers a 30-minute shadow ban."""
        for _ in range(3):
            authenticate(username=self.username, password="wrong-password")

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.failed_login_attempts, 3)
        self.assertIsNotNone(self.profile.shadow_ban_expires_at)

        # Check that it's set to expire around 30 minutes from now
        now = timezone.now()
        self.assertTrue(
            now < self.profile.shadow_ban_expires_at <= now + timedelta(minutes=30)
        )

    def test_active_shadow_ban_blocks_login(self):
        """Test that during shadow ban, even correct password login is blocked."""
        # Trigger shadow ban
        for _ in range(3):
            authenticate(username=self.username, password="wrong-password")

        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.shadow_ban_expires_at)

        # Try to login with correct password - should return None (blocked)
        user = authenticate(username=self.username, password=self.password)
        self.assertIsNone(user)

        # Check that attempts did not increment further (should remain 3)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.failed_login_attempts, 3)

    def test_expired_shadow_ban_allows_login(self):
        """Test that after shadow ban expires, user can login and status is reset."""
        # Trigger shadow ban
        for _ in range(3):
            authenticate(username=self.username, password="wrong-password")

        self.profile.refresh_from_db()

        # Manually expire the shadow ban by setting it to the past
        self.profile.shadow_ban_expires_at = timezone.now() - timedelta(minutes=1)
        self.profile.save()

        # Login with correct password should succeed now
        user = authenticate(username=self.username, password=self.password)
        self.assertIsNotNone(user)

        # Profile fields should be reset
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.failed_login_attempts, 0)
        self.assertIsNone(self.profile.shadow_ban_expires_at)

    def test_permanent_lockout_after_another_three_failures(self):
        """Test that failing 3 more times after shadow ban expires triggers permanent lockout."""
        # 1. Trigger shadow ban (3 failures)
        for _ in range(3):
            authenticate(username=self.username, password="wrong-password")

        # 2. Expire shadow ban
        self.profile.refresh_from_db()
        self.profile.shadow_ban_expires_at = timezone.now() - timedelta(minutes=1)
        self.profile.save()

        # 3. Fail 3 more times (attempts 4, 5, 6)
        # Attempt 4
        user = authenticate(username=self.username, password="wrong-password")
        self.assertIsNone(user)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.failed_login_attempts, 4)

        # Attempt 5
        user = authenticate(username=self.username, password="wrong-password")
        self.assertIsNone(user)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.failed_login_attempts, 5)

        # Attempt 6
        user = authenticate(username=self.username, password="wrong-password")
        self.assertIsNone(user)

        # 4. User should now be permanently locked
        self.profile.refresh_from_db()
        self.user.refresh_from_db()

        self.assertEqual(self.profile.failed_login_attempts, 6)
        self.assertTrue(self.profile.is_permanently_locked)
        self.assertFalse(self.user.is_active)

        # Subsequent attempts are blocked immediately
        user = authenticate(username=self.username, password=self.password)
        self.assertIsNone(user)

    def test_admin_reactivation_resets_lockout_status(self):
        """Test that setting is_active=True on User automatically resets profile lockout state."""
        # 1. Trigger permanent lock
        for _ in range(3):
            authenticate(username=self.username, password="wrong-password")
        self.profile.refresh_from_db()
        self.profile.shadow_ban_expires_at = timezone.now() - timedelta(minutes=1)
        self.profile.save()
        for _ in range(3):
            authenticate(username=self.username, password="wrong-password")

        self.profile.refresh_from_db()
        self.user.refresh_from_db()
        self.assertTrue(self.profile.is_permanently_locked)
        self.assertFalse(self.user.is_active)

        # 2. Reactivate user (admin action)
        self.user.is_active = True
        self.user.save()

        # 3. Verify profile lockout fields are reset via post_save signal
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.failed_login_attempts, 0)
        self.assertIsNone(self.profile.shadow_ban_expires_at)
        self.assertFalse(self.profile.is_permanently_locked)

        # 4. Correct password login should now work again
        user = authenticate(username=self.username, password=self.password)
        self.assertIsNotNone(user)

    def test_warning_almost_shadow_ban(self):
        """Test that login view shows warning when user is 1 attempt away from shadow ban (2 failures)."""
        # 1st fail
        self.client.post(
            reverse("login"), {"username": self.username, "password": "wrong-password"}
        )
        # 2nd fail
        response = self.client.post(
            reverse("login"), {"username": self.username, "password": "wrong-password"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Peringatan: 1 kali salah lagi akun Anda akan dibekukan sementara selama 30 menit.",
        )

    def test_warning_shadow_banned(self):
        """Test that login view shows warning when user is currently shadow banned."""
        # Trigger shadow ban (3 failures)
        for _ in range(3):
            self.client.post(
                reverse("login"),
                {"username": self.username, "password": "wrong-password"},
            )

        # Try to log in (correct password) - should be blocked and show warning
        response = self.client.post(
            reverse("login"), {"username": self.username, "password": self.password}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Akun Anda sedang dibekukan sementara selama 30 menit karena 3 kali salah memasukkan kata sandi.",
        )

    def test_warning_almost_permanently_locked(self):
        """Test that login view shows warning when user is 1 attempt away from permanent lock (5 failures)."""
        # Trigger shadow ban
        for _ in range(3):
            self.client.post(
                reverse("login"),
                {"username": self.username, "password": "wrong-password"},
            )

        # Expire ban
        self.profile.refresh_from_db()
        self.profile.shadow_ban_expires_at = timezone.now() - timedelta(minutes=1)
        self.profile.save()

        # 4th and 5th failures
        self.client.post(
            reverse("login"), {"username": self.username, "password": "wrong-password"}
        )
        response = self.client.post(
            reverse("login"), {"username": self.username, "password": "wrong-password"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Peringatan: 1 kali salah lagi akun Anda akan dikunci secara permanen.",
        )

    def test_warning_permanently_locked(self):
        """Test that login view shows warning when user is permanently locked."""
        # Trigger shadow ban
        for _ in range(3):
            self.client.post(
                reverse("login"),
                {"username": self.username, "password": "wrong-password"},
            )

        # Expire ban
        self.profile.refresh_from_db()
        self.profile.shadow_ban_expires_at = timezone.now() - timedelta(minutes=1)
        self.profile.save()

        # Trigger permanent lock (3 more failures)
        for _ in range(3):
            self.client.post(
                reverse("login"),
                {"username": self.username, "password": "wrong-password"},
            )

        # Try to log in
        response = self.client.post(
            reverse("login"), {"username": self.username, "password": self.password}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Akun Anda telah dikunci secara permanen. Silakan hubungi administrator.",
        )

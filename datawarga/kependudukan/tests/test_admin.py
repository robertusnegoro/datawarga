from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from kependudukan.models import UserInvitation


class UserAdminTestCase(TestCase):
    def setUp(self):
        # Create super admin
        self.admin_username = "superadmin"
        self.admin_password = "AdminP@ssword123!"
        self.admin = User.objects.create_superuser(
            username=self.admin_username,
            password=self.admin_password,
            email="admin@example.com",
        )

        # Create normal user
        self.user_username = "normaluser"
        self.user_password = "UserP@ssword123!"
        self.user = User.objects.create_user(
            username=self.user_username,
            password=self.user_password,
            email="user@example.com",
        )

        # Target user for modification actions
        self.target_username = "targetuser"
        self.target = User.objects.create_user(
            username=self.target_username,
            password="TargetP@ssword123!",
            email="target@example.com",
        )

    def test_permission_denied_for_normal_users(self):
        """Verify normal users are rejected with 403 or redirected to login for admin endpoints."""
        self.client.login(username=self.user_username, password=self.user_password)

        urls = [
            reverse("kependudukan:user_management"),
            reverse("kependudukan:user_add"),
            reverse("kependudukan:user_edit", kwargs={"user_id": self.target.id}),
            reverse(
                "kependudukan:user_reset_password", kwargs={"user_id": self.target.id}
            ),
        ]

        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

        post_urls = [
            reverse("kependudukan:user_block", kwargs={"user_id": self.target.id}),
            reverse("kependudukan:user_unblock", kwargs={"user_id": self.target.id}),
            reverse("kependudukan:user_reset_mfa", kwargs={"user_id": self.target.id}),
            reverse(
                "kependudukan:invitation_expire", kwargs={"user_id": self.target.id}
            ),
            reverse(
                "kependudukan:invitation_recreate", kwargs={"user_id": self.target.id}
            ),
        ]

        for url in post_urls:
            response = self.client.post(url)
            self.assertEqual(response.status_code, 403)

    def test_user_management_view_get(self):
        """Verify superuser can access user management dashboard and it lists users."""
        self.client.login(username=self.admin_username, password=self.admin_password)
        response = self.client.get(reverse("kependudukan:user_management"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/user_management.html")
        self.assertIn("user_data", response.context)

        # Verify users are listed
        usernames = [item["user"].username for item in response.context["user_data"]]
        self.assertIn(self.admin_username, usernames)
        self.assertIn(self.user_username, usernames)
        self.assertIn(self.target_username, usernames)

    def test_user_add_success(self):
        """Verify superuser can add a new user and a valid invitation is created."""
        self.client.login(username=self.admin_username, password=self.admin_password)
        data = {
            "username": "newinviteduser",
            "email": "newinvited@example.com",
            "first_name": "New",
            "last_name": "Invited",
        }

        response = self.client.post(reverse("kependudukan:user_add"), data=data)
        self.assertIn("new_user_invitation_token", self.client.session)
        self.assertRedirects(response, reverse("kependudukan:user_management"))

        # Verify user is created as inactive
        new_user = User.objects.get(username="newinviteduser")
        self.assertFalse(new_user.is_active)
        self.assertEqual(new_user.email, "newinvited@example.com")
        self.assertEqual(new_user.first_name, "New")
        self.assertEqual(new_user.last_name, "Invited")

        # Verify invitation token is generated
        invitation = UserInvitation.objects.filter(user=new_user).first()
        self.assertIsNotNone(invitation)
        self.assertFalse(invitation.is_used)
        self.assertTrue(invitation.is_valid())

    def test_user_add_duplicate_username_or_email(self):
        """Verify adding a user fails when username or email is already taken."""
        self.client.login(username=self.admin_username, password=self.admin_password)

        # Taken username
        data = {
            "username": self.user_username,
            "email": "unique@example.com",
            "first_name": "Unique",
            "last_name": "Name",
        }
        response = self.client.post(reverse("kependudukan:user_add"), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "username",
            "Seorang pengguna dengan nama pengguna tersebut sudah ada.",
        )

        # Taken email (custom validation)
        data = {
            "username": "uniqueusername",
            "email": self.user.email,
            "first_name": "Unique",
            "last_name": "Name",
        }
        response = self.client.post(reverse("kependudukan:user_add"), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "email", "Email ini sudah terdaftar."
        )

    def test_user_edit_success(self):
        """Verify user information can be edited."""
        self.client.login(username=self.admin_username, password=self.admin_password)
        data = {
            "email": "updatedtarget@example.com",
            "first_name": "Updated",
            "last_name": "Target",
        }
        response = self.client.post(
            reverse("kependudukan:user_edit", kwargs={"user_id": self.target.id}),
            data=data,
        )
        self.assertRedirects(response, reverse("kependudukan:user_management"))

        self.target.refresh_from_db()
        self.assertEqual(self.target.email, "updatedtarget@example.com")
        self.assertEqual(self.target.first_name, "Updated")
        self.assertEqual(self.target.last_name, "Target")

    def test_user_block_and_unblock(self):
        """Verify target user can be blocked and unblocked."""
        self.client.login(username=self.admin_username, password=self.admin_password)

        # 1. Block user
        response = self.client.post(
            reverse("kependudukan:user_block", kwargs={"user_id": self.target.id})
        )
        self.assertRedirects(response, reverse("kependudukan:user_management"))

        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)
        self.assertTrue(self.target.profile.is_permanently_locked)

        # 2. Unblock user
        response = self.client.post(
            reverse("kependudukan:user_unblock", kwargs={"user_id": self.target.id})
        )
        self.assertRedirects(response, reverse("kependudukan:user_management"))

        self.target.refresh_from_db()
        self.assertTrue(self.target.is_active)
        self.assertFalse(self.target.profile.is_permanently_locked)

    def test_user_reset_mfa(self):
        """Verify superadmin can disable user's MFA."""
        self.client.login(username=self.admin_username, password=self.admin_password)

        # Setup fake MFA
        profile = self.target.profile
        profile.mfa_enabled = True
        profile.totp_secret = "JBSWY3DPEHPK3PXP"
        profile.save()

        response = self.client.post(
            reverse("kependudukan:user_reset_mfa", kwargs={"user_id": self.target.id})
        )
        self.assertRedirects(response, reverse("kependudukan:user_management"))

        profile.refresh_from_db()
        self.assertFalse(profile.mfa_enabled)
        self.assertIsNone(profile.totp_secret)

    def test_user_reset_password_directly(self):
        """Verify superadmin can reset a user's password directly."""
        self.client.login(username=self.admin_username, password=self.admin_password)

        new_pass = "SuperS3cretNewP@ss!"
        data = {
            "new_password1": new_pass,
            "new_password2": new_pass,
        }

        response = self.client.post(
            reverse(
                "kependudukan:user_reset_password", kwargs={"user_id": self.target.id}
            ),
            data=data,
        )
        self.assertRedirects(response, reverse("kependudukan:user_management"))

        # Verify password is updated
        self.target.refresh_from_db()
        self.assertTrue(self.target.check_password(new_pass))

    def test_invitation_expire_and_recreate(self):
        """Verify invitation links can be expired manually and recreated."""
        self.client.login(username=self.admin_username, password=self.admin_password)

        # 1. Create invitation first
        invitation = UserInvitation.objects.create(
            user=self.target,
            token="testtoken123",
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.assertTrue(invitation.is_valid())

        # 2. Expire invitation
        response = self.client.post(
            reverse(
                "kependudukan:invitation_expire", kwargs={"user_id": self.target.id}
            )
        )
        self.assertRedirects(response, reverse("kependudukan:user_management"))
        invitation.refresh_from_db()
        self.assertTrue(invitation.is_expired())
        self.assertFalse(invitation.is_valid())

        # 3. Recreate invitation
        response = self.client.post(
            reverse(
                "kependudukan:invitation_recreate", kwargs={"user_id": self.target.id}
            )
        )
        self.assertRedirects(response, reverse("kependudukan:user_management"))

        invitation.refresh_from_db()
        self.assertFalse(invitation.is_expired())
        self.assertFalse(invitation.is_used)
        self.assertTrue(invitation.is_valid())
        self.assertNotEqual(invitation.token, "testtoken123")

    def test_user_activate_public_flow(self):
        """Verify public activation endpoint allows new user to set password and activates account."""
        # 1. Create invitation for target
        self.target.is_active = False
        self.target.save()

        inv = UserInvitation.objects.create(
            user=self.target,
            token="activationtokenabc",
            expires_at=timezone.now() + timedelta(days=1),
        )

        # GET request to activation page
        url = reverse(
            "kependudukan:user_activate", kwargs={"token": "activationtokenabc"}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/invite_activate.html")

        # POST new password to activate
        new_pass = "Activat3dP@ssw0rd!"
        data = {
            "new_password1": new_pass,
            "new_password2": new_pass,
        }

        response = self.client.post(url, data=data)
        self.assertRedirects(response, reverse("login"))

        # Verify account activated
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_active)
        self.assertTrue(self.target.check_password(new_pass))

        # Verify invitation used
        inv.refresh_from_db()
        self.assertTrue(inv.is_used)
        self.assertFalse(inv.is_valid())

    def test_user_activate_invalid_expired_used_blocked(self):
        """Verify activation fails for invalid, expired, used, or blocked users."""
        url_nonexistent = reverse(
            "kependudukan:user_activate", kwargs={"token": "nonexistent"}
        )
        response = self.client.get(url_nonexistent)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tautan undangan tidak valid.")

        # Expired token
        UserInvitation.objects.filter(user=self.target).delete()
        UserInvitation.objects.create(
            user=self.target,
            token="expiredtoken",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        url_expired = reverse(
            "kependudukan:user_activate", kwargs={"token": "expiredtoken"}
        )
        response = self.client.get(url_expired)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tautan undangan sudah kedaluwarsa.")

        # Used token
        UserInvitation.objects.filter(user=self.target).delete()
        UserInvitation.objects.create(
            user=self.target,
            token="usedtoken",
            expires_at=timezone.now() + timedelta(days=1),
            is_used=True,
        )
        url_used = reverse("kependudukan:user_activate", kwargs={"token": "usedtoken"})
        response = self.client.get(url_used)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tautan undangan sudah digunakan.")

        # Blocked user activation attempt
        UserInvitation.objects.filter(user=self.target).delete()
        self.target.profile.is_permanently_locked = True
        self.target.profile.save()
        UserInvitation.objects.create(
            user=self.target,
            token="blockedtoken",
            expires_at=timezone.now() + timedelta(days=1),
        )
        url_blocked = reverse(
            "kependudukan:user_activate", kwargs={"token": "blockedtoken"}
        )
        response = self.client.get(url_blocked)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Akun ini telah dinonaktifkan secara permanen.")

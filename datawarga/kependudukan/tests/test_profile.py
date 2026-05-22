import shutil
import tempfile
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from kependudukan.models import UserProfile

# Create a temporary directory for media files during tests
TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class UserProfileTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        # Clean up temporary media directory after all tests run
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.username = "testprofileuser"
        self.password = "Secr3tP@ssw0rd!"
        # This will trigger the post_save signal and create the UserProfile automatically
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email="testuser@example.com",
            first_name="Test",
            last_name="User",
        )

    def test_user_profile_creation_signal(self):
        """Test that UserProfile is automatically created via post_save signal."""
        profile = UserProfile.objects.filter(user=self.user).first()
        self.assertIsNotNone(profile)
        self.assertEqual(str(profile), f"Profile for {self.username}")

    def test_profile_edit_requires_login(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(reverse("kependudukan:profile_edit"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_profile_edit_get(self):
        """Test GET request to the profile edit page when logged in."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse("kependudukan:profile_edit"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "profile.html")
        self.assertIn("user_form", response.context)
        self.assertIn("profile_form", response.context)
        self.assertIn("password_form", response.context)

    def test_profile_update_success(self):
        """Test updating profile information (names and email) successfully."""
        self.client.login(username=self.username, password=self.password)
        data = {
            "action": "update_profile",
            "first_name": "UpdatedFirst",
            "last_name": "UpdatedLast",
            "email": "updated@example.com",
        }
        response = self.client.post(reverse("kependudukan:profile_edit"), data=data)
        # Should redirect back to profile edit view
        self.assertRedirects(response, reverse("kependudukan:profile_edit"))

        # Reload user from DB and check fields
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "UpdatedFirst")
        self.assertEqual(self.user.last_name, "UpdatedLast")
        self.assertEqual(self.user.email, "updated@example.com")

    def test_profile_update_invalid(self):
        """Test profile update fails with invalid email format."""
        self.client.login(username=self.username, password=self.password)
        data = {
            "action": "update_profile",
            "first_name": "UpdatedFirst",
            "last_name": "UpdatedLast",
            "email": "not-an-email",
        }
        response = self.client.post(reverse("kependudukan:profile_edit"), data=data)
        # Should stay on page and show form validation error
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["user_form"].errors)

    def test_profile_photo_upload(self):
        """Test uploading a new profile picture."""
        self.client.login(username=self.username, password=self.password)
        # A tiny valid 1x1 pixel GIF image
        small_gif = (
            b"GIF89a\x01\x00\x01\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00"
            b"\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        uploaded_file = SimpleUploadedFile(
            "avatar.gif", small_gif, content_type="image/gif"
        )

        data = {
            "action": "update_profile",
            "first_name": "Test",
            "last_name": "User",
            "email": "testuser@example.com",
            "foto": uploaded_file,
        }
        response = self.client.post(reverse("kependudukan:profile_edit"), data=data)
        self.assertRedirects(response, reverse("kependudukan:profile_edit"))

        # Verify that photo was saved
        profile = UserProfile.objects.get(user=self.user)
        self.assertTrue(profile.foto)
        self.assertTrue(profile.foto.name.startswith("profile_pics/avatar"))

    def test_change_password_success(self):
        """Test updating password successfully and remaining logged in."""
        self.client.login(username=self.username, password=self.password)
        new_password = "NewS3cureP@ssword!"
        data = {
            "action": "change_password",
            "old_password": self.password,
            "new_password1": new_password,
            "new_password2": new_password,
        }
        response = self.client.post(reverse("kependudukan:profile_edit"), data=data)
        self.assertRedirects(response, reverse("kependudukan:profile_edit"))

        # Check that user can still access page (meaning the session auth hash was updated and didn't log out)
        response = self.client.get(reverse("kependudukan:profile_edit"))
        self.assertEqual(response.status_code, 200)

        # Confirm the password changed in database
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

    def test_change_password_mismatch(self):
        """Test changing password fails when confirmation mismatch occurs."""
        self.client.login(username=self.username, password=self.password)
        data = {
            "action": "change_password",
            "old_password": self.password,
            "new_password1": "NewPass1!",
            "new_password2": "NewPass2Different!",
        }
        response = self.client.post(reverse("kependudukan:profile_edit"), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("new_password2", response.context["password_form"].errors)

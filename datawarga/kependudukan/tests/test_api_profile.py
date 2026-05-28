import shutil
import tempfile
import pyotp
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class UserProfileApiTestCase(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.username = "testapiuser"
        self.password = "Secr3tP@ssw0rd!"
        self.email = "testapiuser@example.com"
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email=self.email,
            first_name="Test",
            last_name="API",
        )
        self.profile = self.user.profile

        # Create another user for conflict tests
        self.other_user = User.objects.create_user(
            username="otheruser",
            password="OtherPassword123!",
            email="other@example.com",
        )

    def test_get_profile_unauthenticated(self):
        url = reverse("kependudukan:profile-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile_success(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("kependudukan:profile-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.username)
        self.assertEqual(response.data["email"], self.email)
        self.assertEqual(response.data["first_name"], "Test")
        self.assertEqual(response.data["last_name"], "API")
        self.assertFalse(response.data["mfa_enabled"])

    def test_update_profile_success(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("kependudukan:profile-update-profile")
        data = {
            "first_name": "NewFirst",
            "last_name": "NewLast",
            "email": "newemail@example.com",
        }
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "NewFirst")
        self.assertEqual(self.user.last_name, "NewLast")
        self.assertEqual(self.user.email, "newemail@example.com")

    def test_update_profile_email_already_exists(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("kependudukan:profile-update-profile")
        data = {
            "first_name": "NewFirst",
            "last_name": "NewLast",
            "email": "other@example.com",
        }
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertEqual(response.data["email"][0], "Email ini sudah terdaftar.")

    def test_update_profile_photo(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("kependudukan:profile-update-profile")

        small_gif = (
            b"GIF89a\x01\x00\x01\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00"
            b"\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        uploaded_file = SimpleUploadedFile(
            "api_avatar.gif", small_gif, content_type="image/gif"
        )
        data = {
            "first_name": "Test",
            "last_name": "API",
            "email": self.email,
            "foto": uploaded_file,
        }
        response = self.client.put(url, data=data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.foto)
        self.assertTrue(self.profile.foto.name.startswith("profile_pics/api_avatar"))

    def test_change_password_success(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("kependudukan:profile-change-password")
        data = {
            "old_password": self.password,
            "new_password": "NewS3curePassword123!",
            "confirm_password": "NewS3curePassword123!",
        }
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify password is changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewS3curePassword123!"))

    def test_change_password_mismatch(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("kependudukan:profile-change-password")
        data = {
            "old_password": self.password,
            "new_password": "NewS3curePassword123!",
            "confirm_password": "DifferentPassword123!",
        }
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", response.data)
        self.assertEqual(
            response.data["confirm_password"][0], "Konfirmasi kata sandi tidak cocok."
        )

    def test_change_password_incorrect_old(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("kependudukan:profile-change-password")
        data = {
            "old_password": "WrongOldPassword",
            "new_password": "NewS3curePassword123!",
            "confirm_password": "NewS3curePassword123!",
        }
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("old_password", response.data)
        self.assertEqual(response.data["old_password"][0], "Kata sandi lama salah.")

    def test_mfa_setup_success(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("kependudukan:profile-mfa-setup")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("secret_key", response.data)
        self.assertIn("provisioning_uri", response.data)
        self.assertIn("qr_base64", response.data)
        self.assertEqual(len(response.data["secret_key"]), 32)

    def test_mfa_setup_already_enabled(self):
        self.profile.mfa_enabled = True
        self.profile.totp_secret = pyotp.random_base32()
        self.profile.save()

        self.client.force_authenticate(user=self.user)
        url = reverse("kependudukan:profile-mfa-setup")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "MFA sudah aktif pada akun Anda.")

    def test_mfa_enable_success(self):
        self.client.force_authenticate(user=self.user)
        secret_key = pyotp.random_base32()
        totp = pyotp.TOTP(secret_key)
        token = totp.now()

        url = reverse("kependudukan:profile-mfa-enable")
        data = {
            "secret_key": secret_key,
            "token": token,
        }
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"],
            "Multi-Factor Authentication (MFA) berhasil diaktifkan.",
        )

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.mfa_enabled)
        self.assertEqual(self.profile.totp_secret, secret_key)

    def test_mfa_enable_invalid_token(self):
        self.client.force_authenticate(user=self.user)
        secret_key = pyotp.random_base32()

        url = reverse("kependudukan:profile-mfa-enable")
        data = {
            "secret_key": secret_key,
            "token": "000000",
        }
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("token", response.data)
        self.assertEqual(
            response.data["token"][0], "Kode verification salah. Silakan coba lagi."
        )

        self.profile.refresh_from_db()
        self.assertFalse(self.profile.mfa_enabled)
        self.assertIsNone(self.profile.totp_secret)

    def test_mfa_enable_already_enabled(self):
        self.profile.mfa_enabled = True
        self.profile.totp_secret = pyotp.random_base32()
        self.profile.save()

        self.client.force_authenticate(user=self.user)
        url = reverse("kependudukan:profile-mfa-enable")
        data = {
            "secret_key": pyotp.random_base32(),
            "token": "123456",
        }
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "MFA sudah aktif pada akun Anda.")

    def test_mfa_disable_success(self):
        secret_key = pyotp.random_base32()
        self.profile.mfa_enabled = True
        self.profile.totp_secret = secret_key
        self.profile.save()

        self.client.force_authenticate(user=self.user)
        totp = pyotp.TOTP(secret_key)
        token = totp.now()

        url = reverse("kependudukan:profile-mfa-disable")
        data = {
            "token": token,
        }
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"],
            "Multi-Factor Authentication (MFA) berhasil dinonaktifkan.",
        )

        self.profile.refresh_from_db()
        self.assertFalse(self.profile.mfa_enabled)
        self.assertIsNone(self.profile.totp_secret)

    def test_mfa_disable_invalid_token(self):
        secret_key = pyotp.random_base32()
        self.profile.mfa_enabled = True
        self.profile.totp_secret = secret_key
        self.profile.save()

        self.client.force_authenticate(user=self.user)
        url = reverse("kependudukan:profile-mfa-disable")
        data = {
            "token": "000000",
        }
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("token", response.data)
        self.assertEqual(
            response.data["token"][0], "Kode verification salah. Silakan coba lagi."
        )

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.mfa_enabled)
        self.assertEqual(self.profile.totp_secret, secret_key)

    def test_mfa_disable_not_enabled(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("kependudukan:profile-mfa-disable")
        data = {
            "token": "123456",
        }
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "MFA tidak aktif pada akun Anda.")

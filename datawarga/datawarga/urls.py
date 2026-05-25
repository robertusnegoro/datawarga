"""datawarga URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from kependudukan.views.errors import permission_denied_view, not_found_view
from kependudukan.views import profile as views_profile

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", views_profile.custom_login, name="login"),
    path("", include("kependudukan.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers — active in production (DEBUG=False / WG_ENV != "dev")
handler403 = permission_denied_view
handler404 = not_found_view

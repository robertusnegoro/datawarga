from django.apps import AppConfig


class KependudukanConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "kependudukan"

    def ready(self) -> None:
        from . import signals  # noqa: F401

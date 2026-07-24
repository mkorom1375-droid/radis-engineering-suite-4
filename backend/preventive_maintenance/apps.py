from django.apps import AppConfig


class PreventiveMaintenanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "preventive_maintenance"
    verbose_name = "نگهداری و تعمیرات پیشگیرانه"

    def ready(self):
        import preventive_maintenance.signals  # noqa: F401
from django.apps import AppConfig


class WorkOrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "work_orders"
    verbose_name = "دستورکارها"

    def ready(self):
        try:
            import work_orders.signals  # noqa: F401
        except ImportError:
            pass
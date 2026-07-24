from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import (
    WorkOrder,
    WorkOrderStatusHistory,
)


@receiver(post_save, sender=WorkOrder)
def create_initial_status(sender, instance, created, **kwargs):
    if not created:
        return

    WorkOrderStatusHistory.objects.create(
        work_order=instance,
        previous_status="",
        new_status=instance.status,
        changed_by=instance.created_by,
        notes="Initial status",
    )
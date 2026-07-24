from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PreventiveMaintenancePlan


@receiver(
    post_save,
    sender=PreventiveMaintenancePlan,
    dispatch_uid=(
        "preventive_maintenance."
        "initialize_plan_next_due_date"
    ),
)
def initialize_plan_next_due_date(
    sender,
    instance,
    created,
    raw,
    **kwargs,
):
    """
    Initialize next_due_date after creating a PM plan.

    The queryset update prevents recursive post_save signals.
    """

    if raw:
        return

    if not created:
        return

    if instance.next_due_date:
        return

    instance.initialize_next_due_date()

    if not instance.next_due_date:
        return

    sender.objects.filter(
        pk=instance.pk,
        next_due_date__isnull=True,
    ).update(
        next_due_date=instance.next_due_date,
    )
from datetime import datetime

from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.utils import timezone

from preventive_maintenance.services import (
    PreventiveMaintenanceService,
)


class Command(BaseCommand):
    help = (
        "Generate work orders for due preventive "
        "maintenance plans."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            dest="generation_date",
            type=str,
            help=(
                "Generation date in YYYY-MM-DD format. "
                "Defaults to the current local date."
            ),
        )

    def handle(self, *args, **options):
        generation_date = self._parse_generation_date(
            options.get("generation_date")
        )

        self.stdout.write(
            self.style.NOTICE(
                "Starting preventive maintenance generation "
                f"for {generation_date}..."
            )
        )

        results = (
            PreventiveMaintenanceService
            .generate_due_work_orders(
                generation_date=generation_date,
            )
        )

        generated = results["generated"]
        skipped = results["skipped"]
        failed = results["failed"]

        for generation in generated:
            self.stdout.write(
                self.style.SUCCESS(
                    "Generated: "
                    f"{generation.plan.plan_number} -> "
                    f"{generation.work_order.work_order_number}"
                )
            )

        for generation in skipped:
            self.stdout.write(
                self.style.WARNING(
                    "Skipped: "
                    f"{generation.plan.plan_number} - "
                    f"{generation.notes}"
                )
            )

        for failure in failed:
            if isinstance(failure, dict):
                plan_identifier = failure.get(
                    "plan_id",
                    "unknown",
                )
                error_message = failure.get(
                    "error",
                    "Unknown error",
                )
            else:
                plan_identifier = (
                    failure.plan.plan_number
                    if failure.plan_id
                    else "unknown"
                )
                error_message = (
                    failure.error_message
                    or "Unknown error"
                )

            self.stdout.write(
                self.style.ERROR(
                    "Failed: "
                    f"{plan_identifier} - "
                    f"{error_message}"
                )
            )

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Preventive maintenance generation completed."
            )
        )

        self.stdout.write(
            f"Generated: {len(generated)}"
        )
        self.stdout.write(
            f"Skipped: {len(skipped)}"
        )
        self.stdout.write(
            f"Failed: {len(failed)}"
        )

        if failed:
            raise CommandError(
                "One or more preventive maintenance "
                "plans failed to generate."
            )

    @staticmethod
    def _parse_generation_date(value):
        if not value:
            return timezone.localdate()

        try:
            return datetime.strptime(
                value,
                "%Y-%m-%d",
            ).date()
        except ValueError as exc:
            raise CommandError(
                "Invalid --date value. "
                "Use YYYY-MM-DD format."
            ) from exc
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class WarehouseType(models.TextChoices):
    MAIN = "main", _("انبار اصلی")
    SPARE_PARTS = "spare_parts", _("انبار قطعات یدکی")
    TOOLS = "tools", _("انبار ابزار")
    CONSUMABLES = "consumables", _("انبار اقلام مصرفی")
    TEMPORARY = "temporary", _("انبار موقت")
    QUARANTINE = "quarantine", _("انبار قرنطینه")
    SCRAP = "scrap", _("انبار ضایعات")
    OTHER = "other", _("سایر")


class ItemType(models.TextChoices):
    SPARE_PART = "spare_part", _("قطعه یدکی")
    CONSUMABLE = "consumable", _("کالای مصرفی")
    TOOL = "tool", _("ابزار")
    LUBRICANT = "lubricant", _("روانکار")
    SAFETY = "safety", _("تجهیزات ایمنی")
    ELECTRICAL = "electrical", _("کالای برقی")
    MECHANICAL = "mechanical", _("کالای مکانیکی")
    INSTRUMENTATION = "instrumentation", _("ابزار دقیق")
    RAW_MATERIAL = "raw_material", _("مواد اولیه")
    OTHER = "other", _("سایر")


class UnitOfMeasure(models.TextChoices):
    EACH = "each", _("عدد")
    PIECE = "piece", _("قطعه")
    SET = "set", _("ست")
    PAIR = "pair", _("جفت")
    BOX = "box", _("جعبه")
    PACK = "pack", _("بسته")
    KILOGRAM = "kg", _("کیلوگرم")
    GRAM = "g", _("گرم")
    TON = "ton", _("تن")
    LITER = "l", _("لیتر")
    MILLILITER = "ml", _("میلی‌لیتر")
    METER = "m", _("متر")
    CENTIMETER = "cm", _("سانتی‌متر")
    MILLIMETER = "mm", _("میلی‌متر")
    SQUARE_METER = "m2", _("مترمربع")
    CUBIC_METER = "m3", _("مترمکعب")
    ROLL = "roll", _("رول")
    SHEET = "sheet", _("ورق")
    OTHER = "other", _("سایر")


class StockTransactionType(models.TextChoices):
    RECEIPT = "receipt", _("رسید انبار")
    ISSUE = "issue", _("حواله خروج")
    RETURN = "return", _("برگشت به انبار")
    ADJUSTMENT_IN = "adjustment_in", _("اصلاح افزایشی")
    ADJUSTMENT_OUT = "adjustment_out", _("اصلاح کاهشی")
    TRANSFER_IN = "transfer_in", _("انتقال ورودی")
    TRANSFER_OUT = "transfer_out", _("انتقال خروجی")
    RESERVATION = "reservation", _("رزرو موجودی")
    RESERVATION_RELEASE = "reservation_release", _("آزادسازی رزرو")
    CONSUMPTION = "consumption", _("مصرف قطعه")


class Warehouse(models.Model):
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="warehouses",
        verbose_name=_("پروژه"),
    )
    code = models.CharField(max_length=50, verbose_name=_("کد انبار"))
    name = models.CharField(max_length=200, verbose_name=_("نام انبار"))
    warehouse_type = models.CharField(
        max_length=30,
        choices=WarehouseType.choices,
        default=WarehouseType.SPARE_PARTS,
        verbose_name=_("نوع انبار"),
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="managed_warehouses",
        null=True,
        blank=True,
        verbose_name=_("مسئول انبار"),
    )
    address = models.TextField(blank=True, verbose_name=_("آدرس"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("تاریخ ایجاد"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("آخرین ویرایش"),
    )

    class Meta:
        verbose_name = _("انبار")
        verbose_name_plural = _("انبارها")
        ordering = ["project", "name"]
        indexes = [
            models.Index(
                fields=["project", "code"],
                name="inv_wh_project_code_idx",
            ),
            models.Index(
                fields=["project", "is_active"],
                name="inv_wh_project_active_idx",
            ),
            models.Index(
                fields=["warehouse_type", "is_active"],
                name="inv_wh_type_active_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "code"],
                name="unique_warehouse_code_per_project",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        errors = {}

        if self.project_id and not self.project.is_active:
            errors["project"] = _(
                "امکان ثبت انبار برای پروژه غیرفعال وجود ندارد."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        self.name = self.name.strip()
        self.address = self.address.strip()
        self.description = self.description.strip()
        self.full_clean()
        super().save(*args, **kwargs)


class InventoryItem(models.Model):
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="inventory_items",
        verbose_name=_("پروژه"),
    )
    code = models.CharField(max_length=80, verbose_name=_("کد کالا"))
    name = models.CharField(max_length=255, verbose_name=_("نام کالا"))
    item_type = models.CharField(
        max_length=30,
        choices=ItemType.choices,
        default=ItemType.SPARE_PART,
        verbose_name=_("نوع کالا"),
    )
    category = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_("گروه کالا"),
    )
    unit_of_measure = models.CharField(
        max_length=20,
        choices=UnitOfMeasure.choices,
        default=UnitOfMeasure.EACH,
        verbose_name=_("واحد اندازه‌گیری"),
    )
    manufacturer = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_("سازنده"),
    )
    part_number = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_("شماره قطعه"),
    )
    manufacturer_part_number = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_("شماره قطعه سازنده"),
    )
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    minimum_stock = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=Decimal("0.000"),
        verbose_name=_("حداقل موجودی"),
    )
    maximum_stock = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=Decimal("0.000"),
        verbose_name=_("حداکثر موجودی"),
    )
    reorder_point = models.DecimalField(
        max_digits=16,
        decimal_places=3,
        default=Decimal("0.000"),
        verbose_name=_("نقطه سفارش"),
    )
    standard_unit_cost = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("بهای استاندارد واحد"),
    )
    is_critical = models.BooleanField(
        default=False,
        verbose_name=_("قطعه بحرانی"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("تاریخ ایجاد"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("آخرین ویرایش"),
    )

    class Meta:
        verbose_name = _("کالا")
        verbose_name_plural = _("کالاها")
        ordering = ["project", "name"]
        indexes = [
            models.Index(
                fields=["project", "code"],
                name="inv_item_project_code_idx",
            ),
            models.Index(
                fields=["project", "item_type"],
                name="inv_item_project_type_idx",
            ),
            models.Index(
                fields=["project", "is_active"],
                name="inv_item_project_active_idx",
            ),
            models.Index(
                fields=["manufacturer", "part_number"],
                name="inv_item_mfr_part_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "code"],
                name="unique_inventory_item_code_per_project",
            ),
            models.CheckConstraint(
                condition=Q(minimum_stock__gte=0),
                name="inv_item_min_stock_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(maximum_stock__gte=0),
                name="inv_item_max_stock_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(reorder_point__gte=0),
                name="inv_item_reorder_point_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(standard_unit_cost__gte=0),
                name="inv_item_unit_cost_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        errors = {}

        if self.project_id and not self.project.is_active:
            errors["project"] = _(
                "امکان ثبت کالا برای پروژه غیرفعال وجود ندارد."
            )

        if (
            self.maximum_stock > 0
            and self.minimum_stock > self.maximum_stock
        ):
            errors["minimum_stock"] = _(
                "حداقل موجودی نمی‌تواند بیشتر از حداکثر موجودی باشد."
            )

        if (
            self.maximum_stock > 0
            and self.reorder_point > self.maximum_stock
        ):
            errors["reorder_point"] = _(
                "نقطه سفارش نمی‌تواند بیشتر از حداکثر موجودی باشد."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        self.name = self.name.strip()
        self.category = self.category.strip()
        self.manufacturer = self.manufacturer.strip()
        self.part_number = self.part_number.strip().upper()
        self.manufacturer_part_number = (
            self.manufacturer_part_number.strip().upper()
        )
        self.description = self.description.strip()
        self.full_clean()
        super().save(*args, **kwargs)


class StockBalance(models.Model):
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="stock_balances",
        verbose_name=_("انبار"),
    )
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="stock_balances",
        verbose_name=_("کالا"),
    )
    quantity_on_hand = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=Decimal("0.000"),
        verbose_name=_("موجودی فیزیکی"),
    )
    reserved_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=Decimal("0.000"),
        verbose_name=_("موجودی رزروشده"),
    )
    average_unit_cost = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("میانگین بهای واحد"),
    )
    last_transaction_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("زمان آخرین تراکنش"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("تاریخ ایجاد"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("آخرین ویرایش"),
    )

    class Meta:
        verbose_name = _("موجودی انبار")
        verbose_name_plural = _("موجودی‌های انبار")
        ordering = ["warehouse", "item"]
        indexes = [
            models.Index(
                fields=["warehouse", "item"],
                name="inv_bal_wh_item_idx",
            ),
            models.Index(
                fields=["item", "quantity_on_hand"],
                name="inv_bal_item_qty_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse", "item"],
                name="unique_stock_balance_per_warehouse_item",
            ),
            models.CheckConstraint(
                condition=Q(quantity_on_hand__gte=0),
                name="inv_bal_on_hand_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(reserved_quantity__gte=0),
                name="inv_bal_reserved_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(reserved_quantity__lte=F("quantity_on_hand")),
                name="inv_bal_reserved_not_above_stock",
            ),
            models.CheckConstraint(
                condition=Q(average_unit_cost__gte=0),
                name="inv_bal_avg_cost_nonnegative",
            ),
        ]

    def __str__(self):
        return (
            f"{self.warehouse.code} - {self.item.code} - "
            f"{self.quantity_on_hand}"
        )

    @property
    def available_quantity(self):
        return self.quantity_on_hand - self.reserved_quantity

    @property
    def stock_value(self):
        return self.quantity_on_hand * self.average_unit_cost

    @property
    def is_below_reorder_point(self):
        return self.available_quantity <= self.item.reorder_point

    def clean(self):
        errors = {}

        if (
            self.warehouse_id
            and self.item_id
            and self.warehouse.project_id != self.item.project_id
        ):
            errors["item"] = _(
                "کالا و انبار باید متعلق به یک پروژه باشند."
            )

        if self.reserved_quantity > self.quantity_on_hand:
            errors["reserved_quantity"] = _(
                "موجودی رزروشده نمی‌تواند بیشتر از موجودی فیزیکی باشد."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class WorkOrderPart(models.Model):
    work_order = models.ForeignKey(
        "work_orders.WorkOrder",
        on_delete=models.CASCADE,
        related_name="required_parts",
        verbose_name=_("دستورکار"),
    )
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="work_order_parts",
        verbose_name=_("کالا"),
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="work_order_parts",
        null=True,
        blank=True,
        verbose_name=_("انبار تأمین‌کننده"),
    )
    requested_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=Decimal("0.000"),
        verbose_name=_("مقدار درخواستی"),
    )
    reserved_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=Decimal("0.000"),
        verbose_name=_("مقدار رزروشده"),
    )
    issued_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=Decimal("0.000"),
        verbose_name=_("مقدار تحویل‌شده"),
    )
    consumed_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=Decimal("0.000"),
        verbose_name=_("مقدار مصرف‌شده"),
    )
    returned_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=Decimal("0.000"),
        verbose_name=_("مقدار برگشتی"),
    )
    estimated_unit_cost = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("بهای برآوردی واحد"),
    )
    notes = models.TextField(blank=True, verbose_name=_("یادداشت"))
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("تاریخ ایجاد"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("آخرین ویرایش"),
    )

    class Meta:
        verbose_name = _("قطعه دستورکار")
        verbose_name_plural = _("قطعات دستورکار")
        ordering = ["work_order", "item"]
        indexes = [
            models.Index(
                fields=["work_order", "item"],
                name="inv_wop_order_item_idx",
            ),
            models.Index(
                fields=["warehouse", "item"],
                name="inv_wop_wh_item_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["work_order", "item", "warehouse"],
                name="unique_work_order_item_warehouse",
            ),
            models.CheckConstraint(
                condition=Q(requested_quantity__gt=0),
                name="inv_wop_requested_positive",
            ),
            models.CheckConstraint(
                condition=Q(reserved_quantity__gte=0),
                name="inv_wop_reserved_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(issued_quantity__gte=0),
                name="inv_wop_issued_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(consumed_quantity__gte=0),
                name="inv_wop_consumed_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(returned_quantity__gte=0),
                name="inv_wop_returned_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(estimated_unit_cost__gte=0),
                name="inv_wop_est_cost_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.work_order.work_order_number} - {self.item.code}"

    @property
    def remaining_requested_quantity(self):
        return max(
            self.requested_quantity - self.issued_quantity,
            Decimal("0.000"),
        )

    @property
    def remaining_required_quantity(self):
        """Quantity still available to reserve for this work-order part."""

        return max(
            self.requested_quantity
            - self.reserved_quantity
            - self.issued_quantity,
            Decimal("0.000"),
        )

    @property
    def issued_available_quantity(self):
        return self.issued_quantity - (
            self.consumed_quantity + self.returned_quantity
        )

    @property
    def estimated_total_cost(self):
        return self.requested_quantity * self.estimated_unit_cost

    @property
    def consumed_total_cost(self):
        return self.consumed_quantity * self.estimated_unit_cost

    def clean(self):
        errors = {}

        if (
            self.work_order_id
            and self.item_id
            and self.work_order.project_id != self.item.project_id
        ):
            errors["item"] = _(
                "کالا باید متعلق به پروژه دستورکار باشد."
            )

        if self.warehouse_id:
            if (
                self.work_order_id
                and self.warehouse.project_id
                != self.work_order.project_id
            ):
                errors["warehouse"] = _(
                    "انبار باید متعلق به پروژه دستورکار باشد."
                )

            if (
                self.item_id
                and self.warehouse.project_id != self.item.project_id
            ):
                errors["warehouse"] = _(
                    "انبار و کالا باید متعلق به یک پروژه باشند."
                )

            if not self.warehouse.is_active:
                errors["warehouse"] = _("انبار انتخاب‌شده غیرفعال است.")

        if self.item_id and not self.item.is_active:
            errors["item"] = _("کالای انتخاب‌شده غیرفعال است.")

        if self.requested_quantity <= 0:
            errors["requested_quantity"] = _(
                "مقدار درخواستی باید بیشتر از صفر باشد."
            )

        if self.reserved_quantity > self.requested_quantity:
            errors["reserved_quantity"] = _(
                "مقدار رزروشده نمی‌تواند بیشتر از مقدار درخواستی باشد."
            )

        if (
            self.reserved_quantity + self.issued_quantity
            > self.requested_quantity
        ):
            errors["reserved_quantity"] = _(
                "مجموع مقدار رزروشده و تحویل‌شده نمی‌تواند بیشتر از مقدار "
                "درخواستی باشد."
            )

        if self.issued_quantity > self.requested_quantity:
            errors["issued_quantity"] = _(
                "مقدار تحویل‌شده نمی‌تواند بیشتر از مقدار درخواستی باشد."
            )

        if (
            self.consumed_quantity + self.returned_quantity
            > self.issued_quantity
        ):
            errors["consumed_quantity"] = _(
                "مجموع مقدار مصرف‌شده و برگشتی نمی‌تواند بیشتر از "
                "مقدار تحویل‌شده باشد."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.notes = self.notes.strip()
        self.full_clean()
        super().save(*args, **kwargs)


class StockTransaction(models.Model):
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="stock_transactions",
        verbose_name=_("پروژه"),
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="stock_transactions",
        verbose_name=_("انبار"),
    )
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="stock_transactions",
        verbose_name=_("کالا"),
    )
    transaction_type = models.CharField(
        max_length=30,
        choices=StockTransactionType.choices,
        verbose_name=_("نوع تراکنش"),
    )
    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        verbose_name=_("مقدار"),
    )
    unit_cost = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("بهای واحد"),
    )
    balance_after = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_("موجودی پس از تراکنش"),
    )
    reserved_balance_after = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_("رزرو پس از تراکنش"),
    )
    work_order = models.ForeignKey(
        "work_orders.WorkOrder",
        on_delete=models.PROTECT,
        related_name="stock_transactions",
        null=True,
        blank=True,
        verbose_name=_("دستورکار"),
    )
    work_order_part = models.ForeignKey(
        WorkOrderPart,
        on_delete=models.PROTECT,
        related_name="stock_transactions",
        null=True,
        blank=True,
        verbose_name=_("قطعه دستورکار"),
    )
    counterpart_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="counterpart_stock_transactions",
        null=True,
        blank=True,
        verbose_name=_("انبار مقابل"),
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("شماره مرجع"),
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="performed_stock_transactions",
        verbose_name=_("ثبت‌کننده تراکنش"),
    )
    occurred_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("زمان تراکنش"),
    )
    notes = models.TextField(blank=True, verbose_name=_("یادداشت"))
    is_void = models.BooleanField(
        default=False,
        verbose_name=_("باطل‌شده"),
    )
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="voided_stock_transactions",
        null=True,
        blank=True,
        verbose_name=_("باطل‌کننده"),
    )
    voided_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("زمان ابطال"),
    )
    void_reason = models.TextField(
        blank=True,
        verbose_name=_("دلیل ابطال"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("تاریخ ایجاد"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("آخرین ویرایش"),
    )

    class Meta:
        verbose_name = _("تراکنش انبار")
        verbose_name_plural = _("تراکنش‌های انبار")
        ordering = ["-occurred_at", "-id"]
        indexes = [
            models.Index(
                fields=["project", "occurred_at"],
                name="inv_tx_project_time_idx",
            ),
            models.Index(
                fields=["warehouse", "item", "occurred_at"],
                name="inv_tx_wh_item_time_idx",
            ),
            models.Index(
                fields=["transaction_type", "occurred_at"],
                name="inv_tx_type_time_idx",
            ),
            models.Index(
                fields=["work_order", "occurred_at"],
                name="inv_tx_order_time_idx",
            ),
            models.Index(
                fields=["reference_number"],
                name="inv_tx_reference_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="inv_tx_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_cost__gte=0),
                name="inv_tx_unit_cost_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(balance_after__isnull=True)
                    | Q(balance_after__gte=0)
                ),
                name="inv_tx_balance_after_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(reserved_balance_after__isnull=True)
                    | Q(reserved_balance_after__gte=0)
                ),
                name="inv_tx_reserved_after_nonnegative",
            ),
        ]

    def __str__(self):
        return (
            f"{self.get_transaction_type_display()} - "
            f"{self.warehouse.code} - {self.item.code} - {self.quantity}"
        )

    @property
    def total_cost(self):
        return self.quantity * self.unit_cost

    def clean(self):
        errors = {}

        if self.quantity <= 0:
            errors["quantity"] = _("مقدار تراکنش باید بیشتر از صفر باشد.")

        if self.warehouse_id and self.project_id:
            if self.warehouse.project_id != self.project_id:
                errors["warehouse"] = _(
                    "انبار باید متعلق به پروژه تراکنش باشد."
                )

        if self.item_id and self.project_id:
            if self.item.project_id != self.project_id:
                errors["item"] = _(
                    "کالا باید متعلق به پروژه تراکنش باشد."
                )

        if self.warehouse_id and self.item_id:
            if self.warehouse.project_id != self.item.project_id:
                errors["item"] = _(
                    "کالا و انبار باید متعلق به یک پروژه باشند."
                )

        if self.work_order_id:
            if self.work_order.project_id != self.project_id:
                errors["work_order"] = _(
                    "دستورکار باید متعلق به پروژه تراکنش باشد."
                )

        if self.work_order_part_id:
            if (
                self.work_order_id
                and self.work_order_part.work_order_id
                != self.work_order_id
            ):
                errors["work_order_part"] = _(
                    "قطعه دستورکار باید متعلق به دستورکار انتخاب‌شده باشد."
                )

            if self.work_order_part.item_id != self.item_id:
                errors["work_order_part"] = _(
                    "کالای تراکنش باید با کالای قطعه دستورکار یکسان باشد."
                )

            if (
                self.work_order_part.warehouse_id
                and self.work_order_part.warehouse_id != self.warehouse_id
            ):
                errors["warehouse"] = _(
                    "انبار تراکنش باید با انبار قطعه دستورکار یکسان باشد."
                )

        transfer_types = {
            StockTransactionType.TRANSFER_IN,
            StockTransactionType.TRANSFER_OUT,
        }

        if self.transaction_type in transfer_types:
            if not self.counterpart_warehouse_id:
                errors["counterpart_warehouse"] = _(
                    "برای تراکنش انتقال، تعیین انبار مقابل الزامی است."
                )
            elif self.counterpart_warehouse_id == self.warehouse_id:
                errors["counterpart_warehouse"] = _(
                    "انبار مبدأ و مقصد انتقال نمی‌توانند یکسان باشند."
                )
            elif (
                self.project_id
                and self.counterpart_warehouse.project_id
                != self.project_id
            ):
                errors["counterpart_warehouse"] = _(
                    "انبار مقابل باید متعلق به پروژه تراکنش باشد."
                )
        elif self.counterpart_warehouse_id:
            errors["counterpart_warehouse"] = _(
                "انبار مقابل فقط برای تراکنش‌های انتقال قابل ثبت است."
            )

        work_order_types = {
            StockTransactionType.ISSUE,
            StockTransactionType.RETURN,
            StockTransactionType.RESERVATION,
            StockTransactionType.RESERVATION_RELEASE,
            StockTransactionType.CONSUMPTION,
        }

        if self.transaction_type in work_order_types:
            if not self.work_order_id:
                errors["work_order"] = _(
                    "برای این نوع تراکنش، تعیین دستورکار الزامی است."
                )
            if not self.work_order_part_id:
                errors["work_order_part"] = _(
                    "برای این نوع تراکنش، تعیین قطعه دستورکار الزامی است."
                )

        if self.is_void:
            if not self.voided_by_id:
                errors["voided_by"] = _(
                    "برای تراکنش باطل‌شده، تعیین باطل‌کننده الزامی است."
                )
            if not self.voided_at:
                errors["voided_at"] = _(
                    "برای تراکنش باطل‌شده، ثبت زمان ابطال الزامی است."
                )
            if not self.void_reason.strip():
                errors["void_reason"] = _(
                    "برای تراکنش باطل‌شده، ثبت دلیل ابطال الزامی است."
                )
        else:
            if self.voided_by_id or self.voided_at or self.void_reason.strip():
                errors["is_void"] = _(
                    "اطلاعات ابطال فقط برای تراکنش باطل‌شده قابل ثبت است."
                )

        if (
            self.voided_at
            and self.occurred_at
            and self.voided_at < self.occurred_at
        ):
            errors["voided_at"] = _(
                "زمان ابطال نمی‌تواند قبل از زمان تراکنش باشد."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.reference_number = self.reference_number.strip().upper()
        self.notes = self.notes.strip()
        self.void_reason = self.void_reason.strip()
        self.full_clean()
        super().save(*args, **kwargs)

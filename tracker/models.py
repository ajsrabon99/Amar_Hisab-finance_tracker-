from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class PaymentMethod(models.Model):
    """A user's money account/wallet. Balances are always exact: no hidden fees."""

    CASH = "cash"
    BKASH = "bkash"
    NAGAD = "nagad"
    BANK = "bank"
    OTHER = "other"
    METHOD_TYPES = [
        (CASH, "Cash"),
        (BKASH, "bKash"),
        (NAGAD, "Nagad"),
        (BANK, "Bank"),
        (OTHER, "Other"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="payment_methods",
        null=False,  # ✅ Changed from null=True
        blank=False  # ✅ Changed from blank=True
    )
    name = models.CharField(max_length=100)
    method_type = models.CharField(max_length=20, choices=METHOD_TYPES, default=OTHER)
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["method_type", "name"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "name"], name="unique_method_per_user")
        ]

    def __str__(self):
        return f"{self.name} ({self.get_method_type_display()})"

    def recalculate_balance(self):
        income = self.transactions.filter(txn_type=Transaction.INCOME).aggregate(
            s=Sum("amount"))["s"] or Decimal("0")
        expense = self.transactions.filter(txn_type=Transaction.EXPENSE).aggregate(
            s=Sum("amount"))["s"] or Decimal("0")
        transfer_in = Transfer.objects.filter(to_method=self).aggregate(
            s=Sum("amount"))["s"] or Decimal("0")
        transfer_out = Transfer.objects.filter(from_method=self).aggregate(
            s=Sum("amount"))["s"] or Decimal("0")
        self.current_balance = self.opening_balance + income - expense + transfer_in - transfer_out
        self.save(update_fields=["current_balance"])


class Category(models.Model):
    """Income sources and expense categories. owner=NULL means an admin/global category."""

    INCOME = "income"
    EXPENSE = "expense"
    CATEGORY_TYPES = [(INCOME, "Income"), (EXPENSE, "Expense")]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="categories", 
        null=True,  
        blank=True
    )
    name = models.CharField(max_length=100)
    name_bn = models.CharField(max_length=100, blank=True, default="")
    category_type = models.CharField(max_length=10, choices=CATEGORY_TYPES)
    icon = models.CharField(max_length=10, blank=True, default="📂")

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["category_type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name", "category_type"],
                name="unique_category_per_user_type",
            )
        ]

    def __str__(self):
        return f"{self.icon} {self.name}".strip()


class Transaction(models.Model):
    INCOME = "income"
    EXPENSE = "expense"
    TXN_TYPES = [(INCOME, "Income"), (EXPENSE, "Expense")]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="transactions",
        null=False,  # ✅ Changed from null=True
        blank=False  # ✅ Changed from blank=True
    )
    date = models.DateField(default=timezone.now)
    txn_type = models.CharField(max_length=10, choices=TXN_TYPES)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="transactions")
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.PROTECT, related_name="transactions"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    note = models.CharField(max_length=500, blank=True, default="")
    other_source = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        sign = "+" if self.txn_type == self.INCOME else "-"
        return f"{self.date} {sign}{self.amount} [{self.category}] via {self.payment_method}"

    def save(self, *args, **kwargs):
        old_method = None
        if self.pk:
            old = Transaction.objects.filter(pk=self.pk).first()
            if old and old.payment_method_id != self.payment_method_id:
                old_method = old.payment_method
        super().save(*args, **kwargs)
        if old_method:
            old_method.recalculate_balance()
        self.payment_method.recalculate_balance()

    def delete(self, *args, **kwargs):
        pm = self.payment_method
        super().delete(*args, **kwargs)
        pm.recalculate_balance()


class Transfer(models.Model):
    """Moves money between a user's own accounts. It is never counted as income/expense."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="transfers",
        null=True,  # ✅ Changed from null=True
        blank=True  # ✅ Changed from blank=True
    )
    date = models.DateField(default=timezone.now)
    from_method = models.ForeignKey(
        PaymentMethod, on_delete=models.PROTECT, related_name="transfers_out"
    )
    to_method = models.ForeignKey(
        PaymentMethod, on_delete=models.PROTECT, related_name="transfers_in"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    note = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.date}: {self.from_method} → {self.to_method} ৳{self.amount}"

    def save(self, *args, **kwargs):
        old_from = old_to = None
        if self.pk:
            old = Transfer.objects.filter(pk=self.pk).first()
            if old:
                old_from, old_to = old.from_method, old.to_method
        super().save(*args, **kwargs)
        if old_from and old_from.pk not in (self.from_method_id, self.to_method_id):
            old_from.recalculate_balance()
        if old_to and old_to.pk not in (self.from_method_id, self.to_method_id):
            old_to.recalculate_balance()
        self.from_method.recalculate_balance()
        self.to_method.recalculate_balance()

    def delete(self, *args, **kwargs):
        from_method, to_method = self.from_method, self.to_method
        super().delete(*args, **kwargs)
        from_method.recalculate_balance()
        to_method.recalculate_balance()
        

# ============================================================
# RECURRING TRANSACTIONS
# ============================================================

class RecurringTransaction(models.Model):
    """
    Automatically creates normal Transaction records on a schedule.
    """

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

    FREQUENCIES = [
        (DAILY, "Daily"),
        (WEEKLY, "Weekly"),
        (MONTHLY, "Monthly"),
        (YEARLY, "Yearly"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recurring_transactions",
    )

    name = models.CharField(
        max_length=150,
        help_text="Example: Internet Bill, House Rent, Salary"
    )

    txn_type = models.CharField(
        max_length=10,
        choices=Transaction.TXN_TYPES,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="recurring_transactions",
    )

    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name="recurring_transactions",
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCIES,
        default=MONTHLY,
    )

    start_date = models.DateField(
        default=timezone.now,
    )

    next_run_date = models.DateField()

    note = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["next_run_date", "name"]

    def __str__(self):
        return f"{self.name} - ৳{self.amount} ({self.get_frequency_display()})"


# ============================================================
# FINANCIAL GOALS
# ============================================================

class Goal(models.Model):
    """
    Personal savings goals such as Eid, Travel, Laptop etc.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="goals",
    )

    name = models.CharField(
        max_length=150,
    )

    description = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    target_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    saved_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    deadline = models.DateField(
        null=True,
        blank=True,
    )

    icon = models.CharField(
        max_length=10,
        default="🎯",
        blank=True,
    )

    is_completed = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["is_completed", "deadline", "-created_at"]

    def __str__(self):
        return f"{self.name} - ৳{self.saved_amount}/৳{self.target_amount}"

    @property
    def remaining_amount(self):
        remaining = self.target_amount - self.saved_amount
        return max(remaining, Decimal("0"))

    @property
    def progress_percentage(self):
        if self.target_amount <= 0:
            return Decimal("0")

        percentage = (
            self.saved_amount / self.target_amount
        ) * Decimal("100")

        return min(percentage, Decimal("100"))

    def update_completion(self):
        if self.saved_amount >= self.target_amount:
            self.saved_amount = self.target_amount
            self.is_completed = True
        else:
            self.is_completed = False

        self.save(
            update_fields=[
                "saved_amount",
                "is_completed",
                "updated_at",
            ]
        )


class GoalContribution(models.Model):
    """
    History of money added to or removed from a goal.
    """

    ADD = "add"
    WITHDRAW = "withdraw"

    TYPES = [
        (ADD, "Add Money"),
        (WITHDRAW, "Withdraw Money"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="goal_contributions",
    )

    goal = models.ForeignKey(
        Goal,
        on_delete=models.CASCADE,
        related_name="contributions",
    )

    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name="goal_contributions",
    )

    contribution_type = models.CharField(
        max_length=10,
        choices=TYPES,
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    date = models.DateField(
        default=timezone.now,
    )

    note = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        sign = "+" if self.contribution_type == self.ADD else "-"
        return f"{self.goal.name}: {sign}৳{self.amount}"


# ============================================================
# DEBT TRACKER
# ============================================================

class Debt(models.Model):
    """
    Tracks money borrowed or lent by the user.
    """

    BORROWED = "borrowed"
    LENT = "lent"

    DEBT_TYPES = [
        (BORROWED, "I Owe"),
        (LENT, "Owed to Me"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="debts",
    )

    person_name = models.CharField(
        max_length=150,
    )

    debt_type = models.CharField(
        max_length=20,
        choices=DEBT_TYPES,
    )

    description = models.CharField(
        max_length=300,
        blank=True,
        default="",
    )

    principal_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    interest_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    paid_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    start_date = models.DateField(
        default=timezone.now,
    )

    due_date = models.DateField(
        null=True,
        blank=True,
    )

    note = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    is_closed = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["is_closed", "due_date", "-created_at"]

    def __str__(self):
        return f"{self.person_name} - ৳{self.remaining_amount}"

    @property
    def total_amount(self):
        return self.principal_amount + self.interest_amount

    @property
    def remaining_amount(self):
        remaining = self.total_amount - self.paid_amount
        return max(remaining, Decimal("0"))

    @property
    def progress_percentage(self):
        if self.total_amount <= 0:
            return Decimal("0")

        percentage = (
            self.paid_amount / self.total_amount
        ) * Decimal("100")

        return min(percentage, Decimal("100"))

    @property
    def status(self):
        if self.is_closed or self.remaining_amount <= 0:
            return "paid"

        if self.due_date and self.due_date < timezone.localdate():
            return "overdue"

        if self.paid_amount > 0:
            return "partial"

        return "pending"


class DebtPayment(models.Model):
    """
    Individual debt repayment history.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="debt_payments",
    )

    debt = models.ForeignKey(
        Debt,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name="debt_payments",
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    date = models.DateField(
        default=timezone.now,
    )

    note = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.debt.person_name}: ৳{self.amount}"
    
# ============================================================
# USER PROFILE
# ============================================================

class Profile(models.Model):
    """
    Stores additional user profile information.
    Each user has exactly one profile.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    name = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    photo = models.ImageField(
        upload_to="profile_photos/",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.name or self.user.email
from django.contrib import admin
from .models import PaymentMethod, Category, Transaction, Transfer


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "method_type", "opening_balance", "current_balance", "is_active")
    list_filter = ("method_type", "is_active")
    readonly_fields = ("current_balance",)
    search_fields = ("name", "owner__username", "owner__email")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "name_bn", "category_type", "icon", "owner")
    list_filter = ("category_type",)
    search_fields = ("name", "owner__username", "owner__email")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "owner", "txn_type", "category", "payment_method", "amount", "other_source", "note")
    list_filter = ("txn_type", "category", "payment_method", "date")
    date_hierarchy = "date"
    search_fields = ("note", "owner__username", "owner__email")
    autocomplete_fields = ("category", "payment_method")


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ("date", "owner", "from_method", "to_method", "amount", "note")
    list_filter = ("date", "from_method", "to_method")
    date_hierarchy = "date"
    search_fields = ("note", "owner__username", "owner__email")

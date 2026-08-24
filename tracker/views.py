import calendar
import csv
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import Category, PaymentMethod, Transaction, Transfer


def _month_year_from_request(request):
    today = date.today()
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        if not 1 <= month <= 12:
            raise ValueError
    except (TypeError, ValueError):
        year, month = today.year, today.month
    return year, month


def _user_methods(user):
    return PaymentMethod.objects.filter(owner=user, is_active=True)


def _user_categories(user, category_type=None):
    qs = Category.objects.filter(owner__isnull=True) | Category.objects.filter(owner=user)
    qs = qs.distinct()
    if category_type:
        qs = qs.filter(category_type=category_type)
    return qs.order_by("name")


def _ensure_default_methods(user):
    defaults = [("Cash", PaymentMethod.CASH), ("bKash", PaymentMethod.BKASH),
                ("Nagad", PaymentMethod.NAGAD), ("Bank", PaymentMethod.BANK)]
    for name, method_type in defaults:
        PaymentMethod.objects.get_or_create(owner=user, name=name, defaults={"method_type": method_type})


@login_required
def dashboard(request):
    """Personal dashboard with exact balances and automatic summaries."""
    _ensure_default_methods(request.user)
    year, month = _month_year_from_request(request)
    payment_methods = list(_user_methods(request.user))
    total_balance = sum((pm.current_balance for pm in payment_methods), Decimal("0"))

    month_txns = Transaction.objects.filter(owner=request.user, date__year=year, date__month=month)
    total_income = month_txns.filter(txn_type=Transaction.INCOME).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    total_expense = month_txns.filter(txn_type=Transaction.EXPENSE).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    net = total_income - total_expense

    expense_by_category = month_txns.filter(txn_type=Transaction.EXPENSE).values(
        "category__name", "category__icon").annotate(total=Sum("amount")).order_by("-total")
    income_by_source = month_txns.filter(txn_type=Transaction.INCOME).values(
        "category__name", "category__icon").annotate(total=Sum("amount")).order_by("-total")
    expense_by_method = month_txns.filter(txn_type=Transaction.EXPENSE).values(
        "payment_method__name").annotate(total=Sum("amount")).order_by("-total")
    income_by_method = month_txns.filter(txn_type=Transaction.INCOME).values(
        "payment_method__name").annotate(total=Sum("amount")).order_by("-total")

    recent_transactions = month_txns.select_related("category", "payment_method")[:20]
    recent_transfers = Transfer.objects.filter(owner=request.user).select_related("from_method", "to_method")[:10]

    context = {
        "payment_methods": payment_methods, "total_balance": total_balance,
        "year": year, "month": month, "month_name": calendar.month_name[month],
        "total_income": total_income, "total_expense": total_expense, "net": net,
        "expense_by_category": expense_by_category, "income_by_source": income_by_source,
        "expense_by_method": expense_by_method, "income_by_method": income_by_method,
        "recent_transactions": recent_transactions, "recent_transfers": recent_transfers,
        "years_range": range(date.today().year - 5, date.today().year + 2),
        "months_range": [(i, calendar.month_name[i]) for i in range(1, 13)],
    }
    return render(request, "tracker/dashboard.html", context)


@login_required
def yearly_overview(request):
    today = date.today()
    try:
        year = int(request.GET.get("year", today.year))
    except ValueError:
        year = today.year

    monthly_data = []
    for m in range(1, 13):
        txns = Transaction.objects.filter(owner=request.user, date__year=year, date__month=m)
        income = txns.filter(txn_type=Transaction.INCOME).aggregate(s=Sum("amount"))["s"] or Decimal("0")
        expense = txns.filter(txn_type=Transaction.EXPENSE).aggregate(s=Sum("amount"))["s"] or Decimal("0")
        monthly_data.append({"month": calendar.month_abbr[m], "income": income, "expense": expense, "net": income-expense})

    year_txns = Transaction.objects.filter(owner=request.user, date__year=year)
    total_income = year_txns.filter(txn_type=Transaction.INCOME).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    total_expense = year_txns.filter(txn_type=Transaction.EXPENSE).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    expense_by_category = year_txns.filter(txn_type=Transaction.EXPENSE).values(
        "category__name", "category__icon").annotate(total=Sum("amount")).order_by("-total")

    return render(request, "tracker/yearly_overview.html", {
        "year": year, "monthly_data": monthly_data, "total_income": total_income,
        "total_expense": total_expense, "net": total_income-total_expense,
        "expense_by_category": expense_by_category,
        "years_range": range(today.year - 5, today.year + 2),
    })


@login_required
def add_transaction(request):
    _ensure_default_methods(request.user)
    if request.method == "POST":
        txn_type = request.POST.get("txn_type")
        category = get_object_or_404(_user_categories(request.user, txn_type), pk=request.POST.get("category"))
        method = get_object_or_404(_user_methods(request.user), pk=request.POST.get("payment_method"))
        try:
            amount = Decimal(request.POST.get("amount", "0"))
            if amount <= 0:
                raise InvalidOperation
        except InvalidOperation:
            messages.error(request, "Enter a valid amount greater than 0.")
        else:
            Transaction.objects.create(owner=request.user, date=request.POST["date"], txn_type=txn_type,
                category=category, payment_method=method, amount=amount, note=request.POST.get("note", "").strip(), other_source=request.POST.get("other_source", "").strip())
            messages.success(request, "Transaction saved. The exact amount you entered was added—no automatic fee was deducted.")
            return redirect("tracker:add_transaction")

    return render(request, "tracker/add_transaction.html", {
        "income_categories": _user_categories(request.user, Category.INCOME),
        "expense_categories": _user_categories(request.user, Category.EXPENSE),
        "payment_methods": _user_methods(request.user),
    })


@login_required
def transfer_money(request):
    _ensure_default_methods(request.user)
    methods = _user_methods(request.user)
    if request.method == "POST":
        from_method = get_object_or_404(methods, pk=request.POST.get("from_method"))
        to_method = get_object_or_404(methods, pk=request.POST.get("to_method"))
        try:
            amount = Decimal(request.POST.get("amount", "0"))
            if amount <= 0 or from_method.pk == to_method.pk or amount > from_method.current_balance:
                raise InvalidOperation
        except InvalidOperation:
            messages.error(request, "Check the accounts and enter an amount within the available balance.")
        else:
            Transfer.objects.create(owner=request.user, date=request.POST["date"], from_method=from_method,
                to_method=to_method, amount=amount, note=request.POST.get("note", "").strip())
            messages.success(request, "Transfer saved. It changes account balances but is not counted as income or expense.")
            return redirect("tracker:dashboard")
    return render(request, "tracker/transfer.html", {"payment_methods": methods})


@login_required
def transactions(request):
    qs = Transaction.objects.filter(owner=request.user).select_related("category", "payment_method")
    txn_type = request.GET.get("type")
    if txn_type in (Transaction.INCOME, Transaction.EXPENSE):
        qs = qs.filter(txn_type=txn_type)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(note__icontains=q) | qs.filter(category__name__icontains=q)
    return render(request, "tracker/transactions.html", {"transactions": qs[:100], "selected_type": txn_type, "q": q})


@login_required
def delete_transaction(request, pk):
    txn = get_object_or_404(Transaction, pk=pk, owner=request.user)
    if request.method == "POST":
        txn.delete()
        messages.success(request, "Transaction deleted and the account balance was recalculated.")
    return redirect("tracker:transactions")


@login_required
def export_csv(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="personal_finance_transactions.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["Date", "Type", "Category", "Account", "Amount", "Description"])
    for t in Transaction.objects.filter(owner=request.user).select_related("category", "payment_method"):
        writer.writerow([t.date, t.get_txn_type_display(), t.category.name, t.payment_method.name, t.amount, t.note])
    return response

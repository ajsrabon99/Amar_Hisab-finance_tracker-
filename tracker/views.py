import calendar
import csv
import random
import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import Category, PaymentMethod, Transaction, Transfer

# Logger setup
logger = logging.getLogger(__name__)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

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
    defaults = [
        ("Cash", PaymentMethod.CASH), 
        ("bKash", PaymentMethod.BKASH),
        ("Nagad", PaymentMethod.NAGAD), 
        ("Bank", PaymentMethod.BANK)
    ]
    for name, method_type in defaults:
        PaymentMethod.objects.get_or_create(
            owner=user, 
            name=name, 
            defaults={"method_type": method_type}
        )


# ============================================================
# DASHBOARD & OVERVIEW VIEWS
# ============================================================

@login_required
def dashboard(request):
    """Personal dashboard with exact balances and automatic summaries."""
    try:
        _ensure_default_methods(request.user)
    except Exception as e:
        print(f"Error ensuring default methods: {e}")
        # Continue even if default methods fail
    
    year, month = _month_year_from_request(request)
    
    # Safely get payment methods
    try:
        payment_methods = list(_user_methods(request.user))
        total_balance = sum((pm.current_balance for pm in payment_methods), Decimal("0"))
    except Exception as e:
        print(f"Error getting payment methods: {e}")
        payment_methods = []
        total_balance = Decimal("0")

    # Safely get transactions
    try:
        month_txns = Transaction.objects.filter(
            owner=request.user, 
            date__year=year, 
            date__month=month
        )
        total_income = month_txns.filter(txn_type=Transaction.INCOME).aggregate(s=Sum("amount"))["s"] or Decimal("0")
        total_expense = month_txns.filter(txn_type=Transaction.EXPENSE).aggregate(s=Sum("amount"))["s"] or Decimal("0")
        net = total_income - total_expense

        expense_by_category = month_txns.filter(txn_type=Transaction.EXPENSE).values(
            "category__name", "category__icon"
        ).annotate(total=Sum("amount")).order_by("-total")
        
        income_by_source = month_txns.filter(txn_type=Transaction.INCOME).values(
            "category__name", "category__icon"
        ).annotate(total=Sum("amount")).order_by("-total")
        
        expense_by_method = month_txns.filter(txn_type=Transaction.EXPENSE).values(
            "payment_method__name"
        ).annotate(total=Sum("amount")).order_by("-total")
        
        income_by_method = month_txns.filter(txn_type=Transaction.INCOME).values(
            "payment_method__name"
        ).annotate(total=Sum("amount")).order_by("-total")

        recent_transactions = month_txns.select_related("category", "payment_method")[:20]
        recent_transfers = Transfer.objects.filter(owner=request.user).select_related("from_method", "to_method")[:10]
    except Exception as e:
        print(f"Error getting transactions: {e}")
        total_income = Decimal("0")
        total_expense = Decimal("0")
        net = Decimal("0")
        expense_by_category = []
        income_by_source = []
        expense_by_method = []
        income_by_method = []
        recent_transactions = []
        recent_transfers = []

    context = {
        "payment_methods": payment_methods, 
        "total_balance": total_balance,
        "year": year, 
        "month": month, 
        "month_name": calendar.month_name[month],
        "total_income": total_income, 
        "total_expense": total_expense, 
        "net": net,
        "expense_by_category": expense_by_category, 
        "income_by_source": income_by_source,
        "expense_by_method": expense_by_method, 
        "income_by_method": income_by_method,
        "recent_transactions": recent_transactions, 
        "recent_transfers": recent_transfers,
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
        monthly_data.append({
            "month": calendar.month_abbr[m], 
            "income": income, 
            "expense": expense, 
            "net": income - expense
        })

    year_txns = Transaction.objects.filter(owner=request.user, date__year=year)
    total_income = year_txns.filter(txn_type=Transaction.INCOME).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    total_expense = year_txns.filter(txn_type=Transaction.EXPENSE).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    expense_by_category = year_txns.filter(txn_type=Transaction.EXPENSE).values(
        "category__name", "category__icon"
    ).annotate(total=Sum("amount")).order_by("-total")

    return render(request, "tracker/yearly_overview.html", {
        "year": year, 
        "monthly_data": monthly_data, 
        "total_income": total_income,
        "total_expense": total_expense, 
        "net": total_income - total_expense,
        "expense_by_category": expense_by_category,
        "years_range": range(today.year - 5, today.year + 2),
    })


# ============================================================
# TRANSACTION VIEWS
# ============================================================

@login_required
def add_transaction(request):
    _ensure_default_methods(request.user)
    if request.method == "POST":
        txn_type = request.POST.get("txn_type")
        category = get_object_or_404(
            _user_categories(request.user, txn_type), 
            pk=request.POST.get("category")
        )
        method = get_object_or_404(
            _user_methods(request.user), 
            pk=request.POST.get("payment_method")
        )
        try:
            amount = Decimal(request.POST.get("amount", "0"))
            if amount <= 0:
                raise InvalidOperation
        except InvalidOperation:
            messages.error(request, "Enter a valid amount greater than 0.")
        else:
            Transaction.objects.create(
                owner=request.user, 
                date=request.POST["date"], 
                txn_type=txn_type,
                category=category, 
                payment_method=method, 
                amount=amount, 
                note=request.POST.get("note", "").strip(), 
                other_source=request.POST.get("other_source", "").strip()
            )
            messages.success(request, "Transaction saved successfully.")
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
            Transfer.objects.create(
                owner=request.user, 
                date=request.POST["date"], 
                from_method=from_method,
                to_method=to_method, 
                amount=amount, 
                note=request.POST.get("note", "").strip()
            )
            messages.success(request, "Transfer saved successfully.")
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
    return render(request, "tracker/transactions.html", {
        "transactions": qs[:100], 
        "selected_type": txn_type, 
        "q": q
    })


@login_required
def delete_transaction(request, pk):
    txn = get_object_or_404(Transaction, pk=pk, owner=request.user)
    if request.method == "POST":
        txn.delete()
        messages.success(request, "Transaction deleted successfully.")
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


# ============================================================
# CUSTOM AUTHENTICATION VIEWS (Email + Code Verification)
# ============================================================

def custom_signup(request):
    """Custom signup with email verification code"""
    if request.method == 'POST':
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Validate passwords
        if password1 != password2:
            messages.error(request, 'Passwords do not match')
            return render(request, 'tracker/signup.html')
        
        # Check if user exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered')
            return render(request, 'tracker/signup.html')
        
        # Generate 5-digit verification code
        verification_code = str(random.randint(10000, 99999))
        
        # Store in session
        request.session['signup_data'] = {
            'email': email,
            'password': password1,
            'code': verification_code
        }
        request.session['signup_email'] = email
        
        # Send verification email
        try:
            subject = 'Verify your Amar Hishab account'
            message = f"""
Hello,

Thank you for signing up for Amar Hishab!

Your 5-digit verification code is: {verification_code}

Please enter this code on the verification page to complete your registration.

This code will expire in 10 minutes.

If you didn't request this, please ignore this email.

Best regards,
Amar Hishab Team
"""
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            
            logger.info(f"Verification code sent to {email}: {verification_code}")
            messages.success(request, f'Verification code sent to {email}')
            
            # Redirect to verification page
            return redirect('verify_email')
            
        except Exception as e:
            logger.error(f"Email sending failed: {str(e)}")
            messages.error(request, f'Could not send verification email. Error: {str(e)}')
            return render(request, 'tracker/signup.html')
    
    return render(request, 'tracker/signup.html')


def verify_email(request):
    """Verify email with 5-digit code"""
    # Check if we have signup data
    signup_data = request.session.get('signup_data')
    email = request.session.get('signup_email')
    
    if not signup_data or not email:
        messages.error(request, 'No signup data found. Please sign up again.')
        return redirect('custom_signup')
    
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        expected_code = signup_data.get('code')
        
        if code == expected_code:
            try:
                # Create user
                user = User.objects.create_user(
                    username=email,  # Using email as username
                    email=email,
                    password=signup_data.get('password')
                )
                user.save()
                
                # Log the user in
                user = authenticate(request, username=email, password=signup_data.get('password'))
                if user:
                    login(request, user)
                
                # Clear session data
                if 'signup_data' in request.session:
                    del request.session['signup_data']
                if 'signup_email' in request.session:
                    del request.session['signup_email']
                
                messages.success(request, 'Account created successfully! Welcome to Amar Hishab.')
                return redirect('tracker:dashboard')
                
            except Exception as e:
                logger.error(f"User creation failed: {str(e)}")
                messages.error(request, f'Account creation failed: {str(e)}')
                return render(request, 'tracker/verify_email.html', {'email': email})
        
        else:
            # Track failed attempts
            attempt_key = 'verification_attempts'
            request.session[attempt_key] = request.session.get(attempt_key, 0) + 1
            if request.session[attempt_key] >= 3:
                messages.error(request, 'Too many failed attempts. Please sign up again.')
                if 'signup_data' in request.session:
                    del request.session['signup_data']
                if 'signup_email' in request.session:
                    del request.session['signup_email']
                if attempt_key in request.session:
                    del request.session[attempt_key]
                return redirect('custom_signup')
            
            messages.error(request, f'Invalid verification code. Attempt {request.session[attempt_key]} of 3.')
            return render(request, 'tracker/verify_email.html', {'email': email})
    
    return render(request, 'tracker/verify_email.html', {'email': email})


def resend_code(request):
    """Resend verification code"""
    signup_data = request.session.get('signup_data')
    email = request.session.get('signup_email')
    
    if not signup_data or not email:
        messages.error(request, 'No signup data found. Please sign up again.')
        return redirect('custom_signup')
    
    # Generate new code
    new_code = str(random.randint(10000, 99999))
    signup_data['code'] = new_code
    request.session['signup_data'] = signup_data
    
    # Reset attempts
    if 'verification_attempts' in request.session:
        del request.session['verification_attempts']
    
    # Send new email
    try:
        send_mail(
            subject='Amar Hishab - New Verification Code',
            message=f'Your new verification code is: {new_code}\n\nThis code will expire in 10 minutes.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        messages.success(request, f'New verification code sent to {email}')
        logger.info(f"New verification code sent to {email}: {new_code}")
    except Exception as e:
        logger.error(f"Resend email failed: {str(e)}")
        messages.error(request, f'Could not send verification email: {str(e)}')
    
    return redirect('verify_email')
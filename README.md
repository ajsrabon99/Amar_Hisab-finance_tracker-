# Amar Hishab — Personal Finance Tracker

A Django personal finance tracker designed for one user per Google account.

## Main features

- Google account sign-in and per-user data isolation.
- EN / BN language switch in the navbar.
- Exact-amount accounting: the amount entered is recorded exactly. No automatic 0.03, service fee, rounding, or hidden deduction is applied.
- Income: source/category + received via (Cash, bKash, Nagad, Bank, Other) + amount + description + date.
- Expense: admin/user category + payment method + amount + description + date.
- Separate live balances for Cash, bKash, Nagad, Bank and other accounts.
- Money transfer between accounts. Transfers do not count as income or expense.
- Monthly and yearly summaries.
- Category-wise expense and account/method-wise expense.
- Income-source and received-via summaries.
- Transaction history, search, delete and CSV export.
- Django Admin for managing global categories and user data.

## Run locally

```bash
python -m venv venv
# Windows CMD
venv\\Scripts\\activate
# Windows PowerShell
# .\\venv\\Scripts\\Activate.ps1

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Google login setup

The project uses `django-allauth`. For Google sign-in, create a Google OAuth Web application and add the callback URL shown by allauth. Then open Django Admin → Sites and Social applications, create the Google provider app, select the site, and enter the Client ID and Secret.

For production, set a real `SECRET_KEY`, `DEBUG=False`, proper `ALLOWED_HOSTS`, HTTPS, and production database/storage settings.

## Accounting rules

1. Income increases the selected account balance.
2. Expense decreases the selected account balance.
3. Transfer decreases the source account and increases the destination account by the exact same amount.
4. A transfer is not income and not expense.
5. There is no automatic fee calculation. If a real bank/mobile-wallet fee exists, the user can record it as a separate expense only when it actually happened.

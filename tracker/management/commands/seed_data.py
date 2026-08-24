from django.core.management.base import BaseCommand
from tracker.models import Category, PaymentMethod


class Command(BaseCommand):
    help = "Creates default Bangladesh-context categories and payment methods."

    def handle(self, *args, **options):
        income_categories = [
            ("Salary", "বেতন", "💼"), ("From Home", "বাড়ি থেকে", "🏠"),
            ("Freelance", "ফ্রিল্যান্স", "💻"), ("Business", "ব্যবসা", "🏪"),
            ("Other Income", "অন্যান্য আয়", "➕"),
        ]
        expense_categories = [
            ("House Rent", "বাসা ভাড়া", "🏠"), ("Electricity Bill", "বিদ্যুৎ বিল", "💡"),
            ("Gas Bill", "গ্যাস বিল", "🔥"), ("WiFi/Internet Bill", "WiFi/ইন্টারনেট বিল", "📶"),
            ("Water Bill", "পানি বিল", "🚰"), ("Transport", "যাতায়াত", "🚌"),
            ("Food / Snacks", "খাবার / নাস্তা", "🍽️"), ("Education", "শিক্ষা", "📚"),
            ("Medicine", "ওষুধ", "💊"), ("Shopping", "কেনাকাটা", "🛍️"),
            ("Mobile Recharge", "মোবাইল রিচার্জ", "📱"), ("Entertainment", "বিনোদন", "🎬"),
            ("Other Expense", "অন্যান্য খরচ", "➖"),
        ]
        for name, name_bn, icon in income_categories:
            Category.objects.get_or_create(name=name, category_type=Category.INCOME, defaults={"name_bn": name_bn, "icon": icon})
        for name, name_bn, icon in expense_categories:
            Category.objects.get_or_create(name=name, category_type=Category.EXPENSE, defaults={"name_bn": name_bn, "icon": icon})

        self.stdout.write(self.style.SUCCESS("Default categories and payment methods created successfully."))

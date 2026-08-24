from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def assign_existing_data(apps, schema_editor):
    User = apps.get_model("auth", "User")
    user = User.objects.filter(is_superuser=True).order_by("id").first()
    if not user:
        return
    PaymentMethod = apps.get_model("tracker", "PaymentMethod")
    Transaction = apps.get_model("tracker", "Transaction")
    Transfer = apps.get_model("tracker", "Transfer")
    PaymentMethod.objects.filter(owner__isnull=True).update(owner=user)
    Transaction.objects.filter(owner__isnull=True).update(owner=user)
    Transfer.objects.filter(owner__isnull=True).update(owner=user)


def reverse_assign(apps, schema_editor):
    # Keep data intact on reverse; ownership can safely be reassigned later.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("tracker", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentmethod", name="owner",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="payment_methods", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="category", name="owner",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="categories", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="transaction", name="owner",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="transactions", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="category", name="name_bn",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="paymentmethod", name="name",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterUniqueTogether(
            name="category", unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="paymentmethod",
            constraint=models.UniqueConstraint(fields=("owner", "name"), name="unique_method_per_user"),
        ),
        migrations.AddConstraint(
            model_name="category",
            constraint=models.UniqueConstraint(fields=("owner", "name", "category_type"), name="unique_category_per_user_type"),
        ),
        migrations.CreateModel(
            name="Transfer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(default=django.utils.timezone.now)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("note", models.CharField(blank=True, default="", max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="transfers", to=settings.AUTH_USER_MODEL)),
                ("from_method", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transfers_out", to="tracker.paymentmethod")),
                ("to_method", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transfers_in", to="tracker.paymentmethod")),
            ],
            options={"ordering": ["-date", "-id"]},
        ),
        migrations.AddField(
            model_name="transaction", name="other_source",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="transaction", name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AddField(
            model_name="transaction", name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RunPython(assign_existing_data, reverse_assign),
    ]

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("tenants", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                ("id",          models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name",        models.CharField(max_length=200)),
                ("type",        models.CharField(choices=[("department", "Department"), ("branch", "Branch")], default="department", max_length=20)),
                ("description", models.TextField(blank=True)),
                ("created_at",  models.DateTimeField(auto_now_add=True)),
                ("company",     models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="departments", to="tenants.company")),
                ("head",        models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="headed_departments", to=settings.AUTH_USER_MODEL)),
                ("parent",      models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="children", to="organizations.department")),
            ],
            options={
                "verbose_name":        "Department",
                "verbose_name_plural": "Departments",
                "ordering":            ["name"],
            },
        ),
        migrations.AddConstraint(
            model_name="department",
            constraint=models.UniqueConstraint(
                fields=["company", "name", "parent"],
                name="unique_dept_name_per_parent",
            ),
        ),
    ]

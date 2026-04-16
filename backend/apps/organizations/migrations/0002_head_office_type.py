import django.db.models.functions
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="department",
            name="type",
            field=models.CharField(
                choices=[
                    ("head_office", "Head Office"),
                    ("department",  "Department"),
                    ("branch",      "Branch"),
                ],
                default="department",
                max_length=20,
            ),
        ),
        migrations.AddConstraint(
            model_name="department",
            constraint=models.UniqueConstraint(
                fields=["company"],
                condition=models.Q(type="head_office"),
                name="unique_head_office_per_company",
            ),
        ),
    ]

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("tenants", "0001_initial"),
        ("tasks", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Report",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("body", models.TextField()),
                ("report_type", models.CharField(
                    choices=[
                        ("daily",    "Daily Report"),
                        ("weekly",   "Weekly Report"),
                        ("issue",    "Issue / Problem"),
                        ("progress", "Progress Update"),
                        ("request",  "Request"),
                    ],
                    default="daily",
                    max_length=20,
                )),
                ("department", models.CharField(blank=True, max_length=100)),
                ("status", models.CharField(
                    choices=[
                        ("sent",         "Sent"),
                        ("read",         "Read"),
                        ("acknowledged", "Acknowledged"),
                    ],
                    default="sent",
                    max_length=20,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="reports",
                    to="tenants.company",
                )),
                ("sent_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="sent_reports",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("sent_to", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="received_reports",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("related_task", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="reports",
                    to="tasks.task",
                )),
            ],
            options={
                "verbose_name": "Report",
                "verbose_name_plural": "Reports",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ReportComment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("body", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("author", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
                ("report", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="comments",
                    to="reports.report",
                )),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["company", "sent_by"], name="reports_rep_company_sent_by_idx"),
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["company", "sent_to"], name="reports_rep_company_sent_to_idx"),
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["company", "status"], name="reports_rep_company_status_idx"),
        ),
    ]

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0002_head_office_type"),
        ("reports",       "0001_initial"),
        ("tasks",         "0001_initial"),
        ("tenants",       "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatRoom",
            fields=[
                ("id",          models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name",        models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("type",        models.CharField(
                    choices=[
                        ("company",    "Company-wide"),
                        ("branch",     "Branch / multiple branches"),
                        ("department", "Department / multiple departments"),
                        ("direct",     "Direct (specific employees)"),
                    ],
                    default="company",
                    max_length=20,
                )),
                ("created_at",  models.DateTimeField(auto_now_add=True)),
                ("updated_at",  models.DateTimeField(auto_now=True)),
                ("company",     models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chat_rooms", to="tenants.company")),
                ("created_by",  models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_chat_rooms", to=settings.AUTH_USER_MODEL)),
                ("members",     models.ManyToManyField(blank=True, related_name="chat_rooms", to=settings.AUTH_USER_MODEL)),
                ("org_units",   models.ManyToManyField(blank=True, related_name="chat_rooms", to="organizations.department")),
                ("related_report", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="chat_rooms", to="reports.report")),
                ("related_task",   models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="chat_rooms", to="tasks.task")),
            ],
            options={
                "verbose_name":        "Chat Room",
                "verbose_name_plural": "Chat Rooms",
                "ordering":            ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="ChatMessage",
            fields=[
                ("id",         models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("body",       models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("edited_at",  models.DateTimeField(blank=True, null=True)),
                ("author",     models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="chat_messages", to=settings.AUTH_USER_MODEL)),
                ("room",       models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="chat.chatroom")),
                ("related_task",   models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="tasks.task")),
                ("related_report", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="reports.report")),
            ],
            options={
                "verbose_name":        "Chat Message",
                "verbose_name_plural": "Chat Messages",
                "ordering":            ["created_at"],
            },
        ),
    ]

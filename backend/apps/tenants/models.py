"""
Tenants — Company (tenant) model.
Every piece of business data belongs to a Company.
This is the root of the entire multi-tenancy system.
"""
import uuid
from django.db import models
from django.utils.text import slugify


class Company(models.Model):
    """
    A company is the root tenant. All data is isolated by company.
    """

    class PlanTier(models.TextChoices):
        FREE = "free", "Free"
        STARTER = "starter", "Starter"
        GROWTH = "growth", "Growth"
        ENTERPRISE = "enterprise", "Enterprise"

    class Industry(models.TextChoices):
        IT_SOFTWARE = "it_software", "IT / Software"
        MARKETING_AGENCY = "marketing_agency", "Marketing Agency"
        ECOMMERCE = "ecommerce", "E-Commerce"
        CONSULTING = "consulting", "Consulting"
        SAAS = "saas", "SaaS"
        DIGITAL_SERVICES = "digital_services", "Digital Services"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    industry = models.CharField(
        max_length=50, choices=Industry.choices, default=Industry.OTHER
    )
    plan = models.CharField(
        max_length=20, choices=PlanTier.choices, default=PlanTier.FREE
    )
    logo = models.ImageField(upload_to="company_logos/", null=True, blank=True)
    website = models.URLField(blank=True)
    employee_count = models.PositiveIntegerField(default=1)
    timezone = models.CharField(max_length=64, default="UTC")

    # Agent configuration overrides at company level
    agent_autonomy_level = models.FloatField(
        default=0.3,
        help_text="0.0 = full human approval required, 1.0 = full autonomy",
    )
    daily_token_budget = models.PositiveIntegerField(
        default=100_000,
        help_text="Max OpenAI tokens per day across all agents",
    )
    tokens_used_today = models.PositiveIntegerField(default=0)
    tokens_reset_at = models.DateTimeField(null=True, blank=True)

    # Telegram integration
    telegram_chat_id = models.CharField(max_length=100, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure slug uniqueness
            original_slug = self.slug
            counter = 1
            while Company.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    @property
    def token_budget_remaining(self):
        return max(0, self.daily_token_budget - self.tokens_used_today)

    def consume_tokens(self, count: int) -> bool:
        """
        Deduct tokens from daily budget. Returns False if budget exhausted.
        """
        if self.tokens_used_today + count > self.daily_token_budget:
            return False
        Company.objects.filter(pk=self.pk).update(
            tokens_used_today=models.F("tokens_used_today") + count
        )
        return True


class TenantManager(models.Manager):
    """
    Custom manager that automatically filters by the current company context.
    All business-data models should use this manager.
    """

    def __init__(self, company_field="company"):
        super().__init__()
        self._company_field = company_field

    def for_company(self, company):
        return self.get_queryset().filter(**{self._company_field: company})

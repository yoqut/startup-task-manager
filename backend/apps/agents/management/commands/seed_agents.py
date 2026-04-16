"""
Management command: seed_agents
Creates AgentConfiguration records for every agent type for a given company
(or all companies), with default system prompts and parent relationships.

Usage:
    python manage.py seed_agents                  # seeds all companies
    python manage.py seed_agents --company <slug> # seeds one company
"""
from django.core.management.base import BaseCommand
from apps.agents.seeder import seed_agents_for_company


class Command(BaseCommand):
    help = "Seed AI agent configurations with default system prompts for all companies."

    def add_arguments(self, parser):
        parser.add_argument(
            "--company",
            type=str,
            default=None,
            help="Company slug to seed. Omit to seed all companies.",
        )

    def handle(self, *args, **options):
        from apps.tenants.models import Company

        slug = options.get("company")
        if slug:
            companies = Company.objects.filter(slug=slug, is_active=True)
            if not companies.exists():
                self.stderr.write(f'No active company with slug "{slug}" found.')
                return
        else:
            companies = Company.objects.filter(is_active=True)

        for company in companies:
            created, updated = seed_agents_for_company(company)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {company.name}: {created} created, {updated} updated"
                )
            )

        self.stdout.write(self.style.SUCCESS("Done."))

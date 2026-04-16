"""
Accounts serializers — registration, login, user profile.
"""
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.tenants.models import Company
from .models import Invitation

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name    = serializers.ReadOnlyField()
    company_name = serializers.CharField(source="company.name",    read_only=True)
    dept_name    = serializers.CharField(source="dept.name",       read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "avatar", "company", "company_name", "role", "department",
            "dept", "dept_name",
            "telegram_user_id", "telegram_username",
            "notify_via_telegram", "notify_via_email",
            "is_active", "created_at", "last_seen_at",
        ]
        read_only_fields = ["id", "email", "company", "role", "created_at", "last_seen_at"]


class RegisterSerializer(serializers.Serializer):
    # Company fields
    company_name = serializers.CharField(max_length=255)
    industry = serializers.ChoiceField(choices=Company.Industry.choices, default=Company.Industry.OTHER)

    # User fields
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def create(self, validated_data):
        # Create company first
        company = Company.objects.create(
            name=validated_data["company_name"],
            industry=validated_data["industry"],
        )
        # Seed all AI agents with default system prompts and hierarchy
        from apps.agents.seeder import seed_agents_for_company
        seed_agents_for_company(company)
        # Create owner user
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            company=company,
            role=User.Role.OWNER,
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Add user data to the token response."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=User.Role.choices, default=User.Role.MEMBER)

    def validate_email(self, value):
        return value.lower()

    def create(self, validated_data):
        company = self.context["request"].company
        inviter = self.context["request"].user
        invitation, _ = Invitation.objects.update_or_create(
            company=company,
            email=validated_data["email"],
            defaults={
                "role": validated_data["role"],
                "invited_by": inviter,
                "is_accepted": False,
                "expires_at": timezone.now() + timedelta(days=7),
            },
        )
        return invitation


class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    password = serializers.CharField(write_only=True, min_length=8)

from rest_framework import serializers
from .models import Department


class DepartmentChildSerializer(serializers.ModelSerializer):
    """Lightweight serializer used for nested children in DepartmentSerializer."""
    head_name   = serializers.CharField(source="head.full_name", read_only=True, default=None)
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model  = Department
        fields = ["id", "name", "type", "head_id", "head_name", "member_count"]


class DepartmentSerializer(serializers.ModelSerializer):
    parent_name  = serializers.CharField(source="parent.name",      read_only=True, default=None)
    head_name    = serializers.CharField(source="head.full_name",    read_only=True, default=None)
    member_count = serializers.IntegerField(read_only=True)
    children     = DepartmentChildSerializer(many=True, read_only=True)

    class Meta:
        model  = Department
        fields = [
            "id", "name", "type", "description",
            "parent", "parent_name",
            "head", "head_name",
            "member_count", "children",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

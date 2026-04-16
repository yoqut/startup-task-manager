from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Report, ReportComment

User = get_user_model()


class ReportCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)

    class Meta:
        model  = ReportComment
        fields = ["id", "body", "author_name", "created_at"]
        read_only_fields = ["id", "author_name", "created_at"]


class ReportListSerializer(serializers.ModelSerializer):
    sent_by_name   = serializers.CharField(source="sent_by.full_name", read_only=True)
    sent_to_name   = serializers.CharField(source="sent_to.full_name", read_only=True)
    comment_count  = serializers.IntegerField(source="comments.count", read_only=True)
    report_type_label = serializers.CharField(source="get_report_type_display", read_only=True)

    class Meta:
        model  = Report
        fields = [
            "id", "title", "report_type", "report_type_label",
            "department", "sent_by_name", "sent_to_name",
            "status", "comment_count", "created_at",
        ]


class ReportSerializer(serializers.ModelSerializer):
    sent_by_name      = serializers.CharField(source="sent_by.full_name", read_only=True)
    sent_to_name      = serializers.CharField(source="sent_to.full_name", read_only=True)
    report_type_label = serializers.CharField(source="get_report_type_display", read_only=True)
    comments          = ReportCommentSerializer(many=True, read_only=True)

    class Meta:
        model  = Report
        fields = [
            "id", "title", "body", "report_type", "report_type_label",
            "department", "sent_by", "sent_by_name", "sent_to", "sent_to_name",
            "status", "related_task", "comments", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "sent_by", "sent_by_name", "sent_to_name",
            "report_type_label", "created_at", "updated_at",
        ]

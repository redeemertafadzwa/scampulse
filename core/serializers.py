from django.conf import settings
from rest_framework import serializers

from .models import ModelVersion, ScamFamily


class ReportCreateSerializer(serializers.Serializer):
    redacted_text = serializers.CharField(max_length=settings.MAX_MESSAGE_CHARS)
    channel = serializers.CharField(max_length=30, required=False, allow_blank=True)
    claimed_category = serializers.CharField(max_length=40, required=False, allow_blank=True)


class FamilySerializer(serializers.ModelSerializer):
    reports_today = serializers.SerializerMethodField()

    class Meta:
        model = ScamFamily
        fields = ["id", "category", "representative_text", "report_count",
                  "reports_today", "status", "is_example", "first_seen", "last_seen"]

    def get_reports_today(self, obj):
        from django.utils import timezone
        start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return obj.reports.filter(created__gte=start).count()


class VoteSerializer(serializers.Serializer):
    family = serializers.IntegerField()
    kind = serializers.ChoiceField(choices=["scam", "fine"])


class ModelVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelVersion
        fields = ["version", "metrics", "created"]

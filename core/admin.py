from django.contrib import admin

from .models import ModelVersion, Report, ScamFamily, Vote


@admin.register(ScamFamily)
class ScamFamilyAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "short", "status", "report_count",
                    "is_example", "last_seen")
    list_filter = ("status", "category", "is_example", "last_seen")
    search_fields = ("representative_text", "representative_fingerprint", "category")
    actions = ["approve", "reject"]
    ordering = ("-report_count",)

    @admin.display(description="sample (redacted)")
    def short(self, obj):
        return obj.representative_text[:60]

    @admin.action(description="Approve: mark as Confirmed scam")
    def approve(self, request, queryset):
        n = queryset.update(status="confirmed")
        self.message_user(request, f"{n} family(ies) confirmed.")

    @admin.action(description="Reject: mark as Not a scam")
    def reject(self, request, queryset):
        n = queryset.update(status="rejected")
        self.message_user(request, f"{n} family(ies) rejected.")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "category_or_family", "channel", "short", "created")
    list_filter = ("channel", "claimed_category", "created")
    search_fields = ("redacted_text",)
    readonly_fields = ("redacted_text", "fingerprint", "device_hash", "created")

    @admin.display(description="text (redacted)")
    def short(self, obj):
        return obj.redacted_text[:60]

    @admin.display(description="family")
    def category_or_family(self, obj):
        return f"#{obj.family_id} {obj.claimed_category}" if obj.family_id else obj.claimed_category


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("id", "family", "kind", "created")
    list_filter = ("kind",)


@admin.register(ModelVersion)
class ModelVersionAdmin(admin.ModelAdmin):
    list_display = ("version", "published", "created")
    list_filter = ("published",)
    readonly_fields = ("metrics", "created")

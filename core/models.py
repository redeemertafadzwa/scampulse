from django.db import models


class ScamFamily(models.Model):
    STATUS = [("new", "New / unverified"), ("confirmed", "Confirmed"),
              ("rejected", "Rejected (not a scam)")]
    representative_fingerprint = models.TextField()
    representative_text = models.TextField(blank=True)  # redacted sample
    category = models.CharField(max_length=40)
    status = models.CharField(max_length=10, choices=STATUS, default="new")
    report_count = models.PositiveIntegerField(default=0)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    is_example = models.BooleanField(default=False, help_text="Seed example, clearly marked.")

    class Meta:
        ordering = ["-report_count", "-last_seen"]
        verbose_name_plural = "scam families"

    def __str__(self):
        return f"{self.category}: {self.representative_text[:40]} ({self.status})"


class Report(models.Model):
    redacted_text = models.TextField()
    fingerprint = models.TextField()
    channel = models.CharField(max_length=30, blank=True)
    claimed_category = models.CharField(max_length=40, blank=True)
    device_hash = models.CharField(max_length=64, db_index=True)
    family = models.ForeignKey(ScamFamily, null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="reports")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"Report {self.id}: {self.redacted_text[:40]}"


class Vote(models.Model):
    KIND = [("scam", "This is a scam"), ("fine", "This is fine")]
    device_hash = models.CharField(max_length=64, db_index=True)
    family = models.ForeignKey(ScamFamily, on_delete=models.CASCADE, related_name="votes")
    kind = models.CharField(max_length=4, choices=KIND)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["device_hash", "family"], name="one_vote_per_device_per_family")]


class ModelVersion(models.Model):
    version = models.CharField(max_length=20, unique=True)
    metrics = models.JSONField(default=dict)
    published = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"model {self.version} ({'published' if self.published else 'draft'})"

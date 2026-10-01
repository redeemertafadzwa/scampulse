"""Group reports into scam families and manage confirmation/votes."""
from django.conf import settings
from django.utils import timezone

from normalise import similarity

from .models import ScamFamily, Vote

MATCH_THRESHOLD = 0.6


def match_or_create_family(fingerprint, redacted_text, category):
    """Attach to the closest existing family, or start a new one."""
    best, best_sim = None, 0.0
    for fam in ScamFamily.objects.filter(status__in=["new", "confirmed"]):
        s = similarity(fingerprint, fam.representative_fingerprint)
        if s > best_sim:
            best, best_sim = fam, s
    if best and best_sim >= MATCH_THRESHOLD:
        best.report_count += 1
        best.last_seen = timezone.now()
        best.save(update_fields=["report_count", "last_seen"])
        return best
    return ScamFamily.objects.create(
        representative_fingerprint=fingerprint,
        representative_text=redacted_text[:280],
        category=category or "Unknown",
        report_count=1,
    )


def confirm_if_ready(family):
    """Confirm after N independent devices reported (admin can also confirm)."""
    if family.status != "new":
        return
    devices = family.reports.values("device_hash").distinct().count()
    if devices >= settings.CONFIRM_THRESHOLD:
        family.status = "confirmed"
        family.save(update_fields=["status"])


def record_vote(device_hash, family, kind):
    """One vote per device per family; 'fine' counter-votes send to review."""
    vote, created = Vote.objects.get_or_create(
        device_hash=device_hash, family=family, defaults={"kind": kind})
    if not created and vote.kind != kind:
        vote.kind = kind
        vote.save(update_fields=["kind"])
    # conflicting votes: if a confirmed family gets enough 'fine', flag for review
    fine = family.votes.filter(kind="fine").count()
    scam = family.votes.filter(kind="scam").count()
    if family.status == "confirmed" and fine > scam:
        family.status = "new"  # back to review queue
        family.save(update_fields=["status"])
    return vote

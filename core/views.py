import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from normalise import fingerprint as fp
from normalise import redact
from engine import rule_assess  # rule-only (no ML libs needed on the server)

from .models import ModelVersion, Report, ScamFamily
from .serializers import (FamilySerializer, ModelVersionSerializer,
                          ReportCreateSerializer, VoteSerializer)
from .services import confirm_if_ready, match_or_create_family, record_vote

STATIC = Path(settings.BASE_DIR) / "core" / "static"


def _device(request):
    return hashlib.sha256(
        request.headers.get("X-Device-Token", "anon").encode()).hexdigest()


def _etag_response(request, payload):
    body = json.dumps(payload, default=str, separators=(",", ":"))
    etag = '"' + hashlib.md5(body.encode()).hexdigest() + '"'
    if request.headers.get("If-None-Match") == etag:
        resp = HttpResponse(status=304)
    else:
        resp = HttpResponse(body, content_type="application/json")
    resp["ETag"] = etag
    resp["Cache-Control"] = "no-cache"
    return resp


# ---------------- pages ----------------
def app(request):
    return render(request, "index.html")


def privacy(request):
    return render(request, "privacy.html")


@staff_member_required
def moderate(request):
    """Simple, phone-friendly moderation dashboard (easier than /admin/)."""
    pending = ScamFamily.objects.filter(status="new").order_by("-report_count", "-last_seen")
    confirmed = ScamFamily.objects.filter(status="confirmed").order_by("-last_seen")[:25]
    stats = {
        "pending": pending.count(),
        "confirmed": ScamFamily.objects.filter(status="confirmed").count(),
        "reports": Report.objects.count(),
    }
    return render(request, "moderate.html",
                  {"pending": pending, "confirmed": confirmed, "stats": stats})


@staff_member_required
@require_POST
def moderate_action(request, family_id, action):
    fam = get_object_or_404(ScamFamily, id=family_id)
    if action == "verify":
        fam.status = "confirmed"
    elif action == "dismiss":
        fam.status = "rejected"
    fam.save(update_fields=["status"])
    return redirect("moderate")


def health(request):
    return JsonResponse({"status": "ok"})


def service_worker(request):
    sw = (STATIC / "js" / "sw.js").read_text(encoding="utf-8")
    resp = HttpResponse(sw, content_type="application/javascript")
    resp["Service-Worker-Allowed"] = "/"
    resp["Cache-Control"] = "no-cache"
    return resp


def manifest(request):
    data = (STATIC / "manifest.webmanifest").read_text(encoding="utf-8")
    return HttpResponse(data, content_type="application/manifest+json")


# ---------------- API ----------------
@api_view(["POST"])
def reports(request):
    ser = ReportCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    text = redact(ser.validated_data["redacted_text"])  # defensive re-redaction
    finger = fp(text)
    if not finger:
        return Response({"detail": "empty after redaction"}, status=400)
    # Auto-categorise by word-by-word scanning for scam indicators,
    # instead of trusting whatever the user claimed.
    _reasons, _score, rule_threat, _mw = rule_assess(text)
    category = rule_threat or ser.validated_data.get("claimed_category") or "Unknown"
    fam = match_or_create_family(finger, text, category)
    Report.objects.create(
        redacted_text=text, fingerprint=finger,
        channel=ser.validated_data.get("channel", ""),
        claimed_category=category, device_hash=_device(request), family=fam)
    confirm_if_ready(fam)
    return Response({"family": fam.id, "status": fam.status,
                     "message": "Reported. Shown as unverified until confirmed."},
                    status=status.HTTP_201_CREATED)


@api_view(["POST"])
def vote(request):
    ser = VoteSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    fam = get_object_or_404(ScamFamily, id=ser.validated_data["family"])
    record_vote(_device(request), fam, ser.validated_data["kind"])
    return Response({"ok": True, "status": fam.status})


def feed(request):
    qs = (ScamFamily.objects.filter(status="confirmed") |
          ScamFamily.objects.filter(is_example=True)).distinct()[:50]
    return _etag_response(request, FamilySerializer(qs, many=True).data)


def blocklist(request):
    qs = ScamFamily.objects.filter(status="confirmed").values_list(
        "representative_fingerprint", "category")
    data = [{"f": f, "c": c} for f, c in qs]
    return _etag_response(request, data)


def model_version(request):
    mv = ModelVersion.objects.filter(published=True).first()
    payload = ModelVersionSerializer(mv).data if mv else {"version": "1.0.0", "metrics": {}}
    return _etag_response(request, payload)

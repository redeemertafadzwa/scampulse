"""Seed the feed with verified, synthetic-but-realistic EXAMPLES, clearly
marked so nothing fake is passed off as a real community report."""
import sys

from django.conf import settings
from django.core.management.base import BaseCommand

sys.path.insert(0, str(settings.BASE_DIR))
from normalise import fingerprint  # noqa: E402

EXAMPLES = [
    ("Financial Scam", "Free [amount] data bundle! Reply with your PIN to activate.", "WhatsApp", 37),
    ("Financial Scam", "You received [amount] by mistake on mobile money, please reverse it now.", "SMS", 24),
    ("Phishing", "Your bank account is suspended, verify at [link] to avoid closure.", "SMS", 19),
    ("Identity Fraud", "Send a photo of your national ID and a selfie to verify your account.", "WhatsApp", 15),
    ("Malicious Link", "Claim your reward here [link] - offer ends tonight.", "SMS", 12),
    ("AI-Enabled Threat", "Voice note from your boss: urgently buy airtime and send the codes.", "WhatsApp", 9),
    ("Financial Scam", "Parcel held at customs, pay [amount] clearance fee immediately.", "SMS", 8),
]


class Command(BaseCommand):
    help = "Seed clearly-marked example scam families for the feed."

    def handle(self, *args, **opts):
        from core.models import ScamFamily
        made = 0
        for cat, text, channel, count in EXAMPLES:
            fp = fingerprint(text)
            obj, created = ScamFamily.objects.get_or_create(
                representative_fingerprint=fp,
                defaults={"representative_text": text, "category": cat,
                          "status": "confirmed", "report_count": count,
                          "is_example": True})
            made += int(created)
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {made} example families (total {ScamFamily.objects.count()})."))

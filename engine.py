"""
ScamPulse detection engine: explainable rule signals + a TF-IDF model that
vote. When they disagree, the engine takes the more cautious answer. Low
confidence becomes "Not sure, treat it as suspicious".
"""
import os
import re

try:
    from .normalise import normalise
except ImportError:  # run as a script / from /ml
    from normalise import normalise

# label -> (reason shown to user)
RULES = [
    ("asks for PIN/OTP", re.compile(r"\b(send|share|enter|reply with|provide)\b[^.]{0,25}\b(pin|otp|password|cvv|passcode)\b"), "Identity Fraud", 3),
    ("asks for ID/selfie", re.compile(r"\b(id|identity|national id|passport|kyc|selfie)\b[^.]{0,25}\b(photo|picture|send|upload|reply|number)\b"), "Identity Fraud", 3),
    ("asks for money", re.compile(r"\b(send|pay|deposit|transfer|reverse|activation|clearance|processing|registration)\b[^.]{0,25}\b(amounttoken|fee|money|cash|back)\b"), "Financial Scam", 3),
    ("unexpected prize", re.compile(r"(won|winner|congratulations|prize|reward|bonus|lottery|selected|free)\b"), "Financial Scam", 2),
    ("pressure / urgency", re.compile(r"(urgent|immediately|now|today only|expires?|within 24|before midnight|last chance|act now|hurry|quiet|secret)"), None, 1),
    ("suspicious link", re.compile(r"urltoken"), "Malicious Link", 2),
    ("voice/video claim", re.compile(r"(voice[\s-]?note|video|clip|recording)"), "AI-Enabled Threat", 2),
    ("authority impersonation", re.compile(r"(bank|ecocash|onemoney|cbz|zb bank|steward|telecash|nmb|econet|netone|telecel|ceo|boss|minister|government|customs|zesa|council|police)"), None, 1),
]

ACTIONS = {
    "Financial Scam": "Do not send money. Verify with the company using a number from their official website.",
    "Phishing": "Do not click the link or enter your details. Open the official app yourself instead.",
    "Identity Fraud": "Never send your ID, selfie, PIN or OTP. Real companies don't ask for these.",
    "Malicious Link": "Do not open the link. Type the official address yourself if you need the service.",
    "AI-Enabled Threat": "We can't check audio or video. Confirm it's really them another way.",
    "Benign": "No warning signs found, but stay alert if money or your PIN is involved.",
}
SCAM_CLASSES = {"Financial Scam", "Phishing", "Identity Fraud", "Malicious Link", "AI-Enabled Threat"}


def rule_assess(text: str):
    n = normalise(text)
    reasons, score, votes, max_weight = [], 0, {}, 0
    for item in RULES:
        label, rx, threat, weight = item
        if rx.search(n):
            reasons.append(label)
            score += weight
            max_weight = max(max_weight, weight)
            if threat:
                votes[threat] = votes.get(threat, 0) + weight
    rule_threat = max(votes, key=votes.get) if votes else None
    return reasons, score, rule_threat, max_weight


class Engine:
    def __init__(self, model=None):
        self.model = model  # sklearn pipeline with predict_proba, or None

    @classmethod
    def load(cls, path=None):
        import joblib
        path = path or os.path.join(os.path.dirname(__file__), "ml", "model.pkl")
        return cls(joblib.load(path))

    def assess(self, text: str) -> dict:
        reasons, score, rule_threat, max_weight = rule_assess(text)

        model_threat, model_conf = None, 0.0
        if self.model is not None:
            probs = self.model.predict_proba([normalise(text)])[0]
            classes = list(self.model.classes_)
            idx = int(probs.argmax())
            model_threat, model_conf = classes[idx], float(probs[idx])

        model_says_scam = model_threat in SCAM_CLASSES
        # a rule "scam" needs a strong signal (PIN/ID/money) or several mediums,
        # so legit messages that merely mention a bank or say "urgent" don't trip it
        rules_say_scam = max_weight >= 3 or score >= 4

        if model_says_scam or rules_say_scam:
            threat = rule_threat if (rules_say_scam and rule_threat) else model_threat
            if model_says_scam and max_weight < 3:
                threat = model_threat
            risk = "High" if (max_weight >= 3 or score >= 4 or model_conf >= 0.6 or
                              threat in {"Identity Fraud", "Phishing"}) else "Medium"
            return {
                "verdict": "Danger" if risk == "High" else "Be careful",
                "threat_type": threat, "risk": risk,
                "reasons": reasons or [f"matches known {threat} pattern"],
                "confidence": round(model_conf, 2),
                "action": ACTIONS.get(threat, ACTIONS["Financial Scam"]),
            }

        # both lean benign; only hedge when there's a real medium+ signal present
        if max_weight >= 2 and model_conf < 0.5:
            return {
                "verdict": "Be careful", "threat_type": "Uncertain", "risk": "Medium",
                "reasons": reasons or ["unclear message"], "confidence": round(model_conf, 2),
                "action": "Not sure — treat it as suspicious and verify before acting.",
            }
        return {
            "verdict": "No warning signs found", "threat_type": "Benign", "risk": "Low",
            "reasons": reasons, "confidence": round(model_conf, 2),
            "action": ACTIONS["Benign"],
        }

"""
ScamPulse shared text module: cleaning, redaction and fingerprinting.

Used by training, evaluation and the server. Re-implemented in JavaScript for
the phone; a parity test (Stage 2) feeds the same inputs through both and fails
on any difference. Keep every function pure and deterministic.
"""
import re

# --- leetspeak / look-alike character folding ---
_LEET = str.maketrans({
    "0": "o", "1": "l", "3": "e", "4": "a", "5": "s",
    "7": "t", "8": "b", "@": "a", "$": "s", "|": "l",
})

# --- patterns (order matters: redact URLs and amounts before bare numbers) ---
_URL = re.compile(
    r"(?:https?://|www\.)\S+"
    r"|\b[a-z0-9][a-z0-9\-.]*\.(?:com|net|org|co|co\.zw|zw|link|xyz|info|invalid|"
    r"click|top|live|app|ru|cn|tk|ml|ga|cf|gq|shop|online|site)\b(?:/\S*)?",
    re.IGNORECASE,
)
_PHONE = re.compile(
    r"(?:\+?263|0)(?:7[0-9]|86)\d(?:[\s\-]?\d){6,7}",
)
_AMOUNT = re.compile(
    r"(?:us\$|usd|zwl|rtgs|zar|r|\$|€|£)\s?\d[\d,]*(?:\.\d+)?"
    r"|\b\d[\d,]*(?:\.\d+)?\s?(?:usd|dollars?|rands?|bond|zwl|rtgs|pounds?)\b",
    re.IGNORECASE,
)
_ACCOUNT = re.compile(r"\b\d{6,}\b")
_NAME_AFTER_GREETING = re.compile(
    r"\b(dear|hi|hello|hey|mr|mrs|ms|miss|dr)\b[\s,]+([A-Z][a-z]+)",
)
_SPACE = re.compile(r"\s+")


def redact(text: str) -> str:
    """Mask identifying details before a report ever leaves the device."""
    if not text:
        return ""
    t = text
    t = _URL.sub("[link]", t)
    t = _PHONE.sub("[phone]", t)
    t = _AMOUNT.sub("[amount]", t)
    t = _NAME_AFTER_GREETING.sub(lambda m: f"{m.group(1)} [name]", t)
    t = _ACCOUNT.sub("[number]", t)
    return _SPACE.sub(" ", t).strip()


def normalise(text: str) -> str:
    """Clean text for the model: lowercase, placeholder tokens, tidy spacing.
    Keeps wording so char n-grams can still catch disguises like 'fr33 d@ta'."""
    if not text:
        return ""
    t = text.lower()
    t = _URL.sub(" urltoken ", t)
    t = _PHONE.sub(" phonetoken ", t)
    t = _AMOUNT.sub(" amounttoken ", t)
    t = _ACCOUNT.sub(" numtoken ", t)
    return _SPACE.sub(" ", t).strip()


def fingerprint(text: str) -> str:
    """Canonical form for duplicate/near-duplicate matching.
    Folds look-alike characters and strips placeholders so disguised repeats
    of the same scam collapse to one string."""
    t = normalise(text)
    t = t.translate(_LEET)
    t = re.sub(r"(urltoken|phonetoken|amounttoken|numtoken)", " ", t)
    t = re.sub(r"[^a-z\s]", " ", t)
    return _SPACE.sub(" ", t).strip()


def shingles(text: str, k: int = 3):
    """Word k-shingles for similarity (exact match for very short messages)."""
    words = fingerprint(text).split()
    if len(words) < 6:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}


def similarity(a: str, b: str) -> float:
    """Jaccard similarity of word shingles, 0..1."""
    sa, sb = shingles(a), shingles(b)
    if not sa or not sb:
        return 1.0 if fingerprint(a) == fingerprint(b) else 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0

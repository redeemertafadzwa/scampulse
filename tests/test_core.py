"""pytest: redaction never leaks, fingerprinting, and engine behaviour."""
import csv
import os
import re
import sys

import joblib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine import Engine                 # noqa: E402
from normalise import fingerprint, redact  # noqa: E402

MODEL = os.path.join(ROOT, "ml", "model.pkl")
PHONE = re.compile(r"(?:\+?263|0)(?:7[0-9]|86)\d(?:[\s\-]?\d){6,7}")
LINK = re.compile(r"https?://|www\.", re.I)


def _rows(name):
    with open(os.path.join(ROOT, "ml", "data", name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_redaction_masks_identifiers():
    t = redact("Send $50 to +263771234567 or visit http://x.example.invalid, Dear Tapiwa acc 123456789")
    assert "[phone]" in t and "[link]" in t and "[amount]" in t
    assert "263771234567" not in t and "123456789" not in t
    assert "http" not in t.lower()


def test_redaction_never_leaks_on_dataset():
    for name in ("test.csv", "disguised.csv"):
        for r in _rows(name):
            red = redact(r["text"])
            assert not PHONE.search(red), red
            assert not LINK.search(red), red


def test_fingerprint_folds_leetspeak():
    # @ -> a and 0 -> o fold so disguises collapse to the same fingerprint
    assert fingerprint("p@ssw0rd") == fingerprint("password") == "password"


def test_engine_flags_scams_and_clears_legit():
    eng = Engine(joblib.load(MODEL))
    scam = eng.assess("Send a photo of your national ID and your PIN to confirm your account")
    assert scam["verdict"] == "Danger"
    legit = eng.assess("Your one-time PIN is 4821. Do not share it with anyone. - CBZ")
    assert legit["verdict"] == "No warning signs found"

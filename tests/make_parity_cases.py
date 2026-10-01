"""Dump 200+ inputs with their Python redact/normalise/fingerprint outputs,
so the JS implementation can be checked against them."""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from normalise import fingerprint, normalise, redact  # noqa: E402

DATA = os.path.join(ROOT, "ml", "data")

EDGE = [
    "FREE d@ta bundle! reply with PIN 1234 now",
    "Send $5 to +263771234567 urgently",
    "Dear Tapiwa, your parcel awaits at http://parcel.example.invalid/pay",
    "Won US$1,000!!! claim at www.prize.example.invalid",
    "Your OTP is 4821, do not share it",
    "fr33 airt1me on 0712345678, visit examp1e.xyz",
    "Account 123456789 credited RTGS 2000", "hello world no scams here",
    "Hi Chipo pay 50 dollars to this number 0867654321",
    "Click bit.example.invalid/x NOW before midnight", "   spaced   out    text  ",
    "Mr Farai, verify at https://bank.example.invalid", "R50 bonus on Econet",
    "", "CALL 0772000111 or visit site.online for £20",
]


def collect():
    rows = list(EDGE)
    for name in ("training.csv", "test.csv", "disguised.csv", "legit.csv"):
        p = os.path.join(DATA, name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    rows.append(r["text"])
    # de-dup but keep order, cap for speed
    seen, out = set(), []
    for t in rows:
        if t not in seen:
            seen.add(t); out.append(t)
    return out[:400]


if __name__ == "__main__":
    cases = [{"in": t, "redact": redact(t), "normalise": normalise(t),
              "fingerprint": fingerprint(t)} for t in collect()]
    with open(os.path.join(os.path.dirname(__file__), "parity_cases.json"),
              "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False)
    print(f"wrote {len(cases)} parity cases")

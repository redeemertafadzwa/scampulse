"""
ScamPulse CLI (Stage 1): check a message from the terminal.

Usage:
  python check.py "paste the suspicious message here"
  python check.py            # runs a few demo messages
"""
import sys

import joblib

from engine import Engine

BAND = {"Danger": "!! DANGER", "Be careful": "~ BE CAREFUL",
        "No warning signs found": "ok NO WARNING SIGNS"}

DEMOS = [
    "Congratulations! You won US$500 in the Econet draw. Send $3 to 0771234567 to claim.",
    "Dear customer, verify your CBZ account at http://cbz-secure.example.invalid or it closes today.",
    "Send a photo of your national ID and your PIN to confirm your account.",
    "Voice note from your boss: urgently buy $50 airtime and send the codes, keep it quiet.",
    "Your one-time PIN is 4821. Do not share it with anyone. - CBZ",
    "Hi, are we still meeting at 3pm today?",
]


def show(eng, text):
    r = eng.assess(text)
    print("-" * 64)
    print(f"  {BAND.get(r['verdict'], r['verdict'])}   ({r['threat_type']}, risk: {r['risk']})")
    print(f"  message: {text[:70]}{'...' if len(text) > 70 else ''}")
    if r["reasons"]:
        print(f"  why:     {', '.join(r['reasons'])}")
    print(f"  action:  {r['action']}")
    print("  note:    ScamPulse can miss things. If money or your PIN is involved,")
    print("           check with the real company.")


def main():
    eng = Engine(joblib.load("ml/model.pkl"))
    msgs = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else DEMOS
    for m in msgs:
        show(eng, m)
    print("-" * 64)


if __name__ == "__main__":
    main()

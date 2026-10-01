"""
Evaluate the engine on the TEST, DISGUISED and LEGIT sets SEPARATELY.
Two headline numbers: scams wrongly cleared, and false alarms on legit.
Writes docs/evaluation-report.md. Never trains here.
"""
import os
import sys

import joblib
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine import Engine, SCAM_CLASSES  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DOCS = os.path.join(ROOT, "docs")


def load(name):
    return pd.read_csv(os.path.join(DATA, name))


def is_flagged(result):
    return result["verdict"] in ("Danger", "Be careful")


def main():
    eng = Engine(joblib.load(os.path.join(os.path.dirname(__file__), "model.pkl")))
    test, disg, legit = load("test.csv"), load("disguised.csv"), load("legit.csv")

    lines = ["# ScamPulse — Evaluation Report", "",
             "Measured on three held-out synthetic sets, each kept separate. "
             "The training CSV holds only 12 unique repeated messages, so accuracy "
             "on it is meaningless and is not reported here.", ""]

    # --- TEST: scam-vs-benign accuracy + per-threat-class quality ---
    y_true_bin, y_pred_bin, true_thr, pred_thr = [], [], [], []
    for _, r in test.iterrows():
        res = eng.assess(r["text"])
        scam_true = r["threat_type"] in SCAM_CLASSES
        y_true_bin.append(int(scam_true))
        y_pred_bin.append(int(is_flagged(res)))
        if scam_true:
            true_thr.append(r["threat_type"])
            pred_thr.append(res["threat_type"] if res["threat_type"] in SCAM_CLASSES else "Missed")
    acc = sum(int(a == b) for a, b in zip(y_true_bin, y_pred_bin)) / len(y_true_bin)
    lines += [f"## TEST set ({len(test)} messages)",
              f"- Scam-vs-benign accuracy: **{acc:.1%}**", "",
              "Per-threat-type (scam messages only):", "```",
              classification_report(true_thr, pred_thr, zero_division=0), "```",
              "Confusion matrix (threat types):", "```",
              str(confusion_matrix(true_thr, pred_thr,
                                   labels=sorted(set(true_thr + pred_thr)))),
              "labels: " + ", ".join(sorted(set(true_thr + pred_thr))), "```", ""]

    # --- Headline 1: scams wrongly cleared (TEST scams + DISGUISED) ---
    scam_rows = [r for _, r in test.iterrows() if r["threat_type"] in SCAM_CLASSES]
    scam_rows += [r for _, r in disg.iterrows()]
    missed = sum(1 for r in scam_rows if not is_flagged(eng.assess(r["text"])))
    cleared_rate = missed / len(scam_rows)

    # --- Headline 2: false alarms on LEGIT ---
    alarms = sum(1 for _, r in legit.iterrows() if is_flagged(eng.assess(r["text"])))
    alarm_rate = alarms / len(legit)

    # --- DISGUISED catch rate ---
    d_caught = sum(1 for _, r in disg.iterrows() if is_flagged(eng.assess(r["text"])))

    lines += ["## Headline numbers",
              f"- **Scams wrongly cleared:** {cleared_rate:.1%} "
              f"({missed}/{len(scam_rows)} scam messages missed)  — lower is better",
              f"- **False alarms on legit:** {alarm_rate:.1%} "
              f"({alarms}/{len(legit)} genuine messages flagged)  — lower is better", "",
              f"## DISGUISED set ({len(disg)} messages)",
              f"- Caught despite typos/leetspeak/mixed language: "
              f"**{d_caught/len(disg):.1%}** ({d_caught}/{len(disg)})", "",
              f"## LEGIT set ({len(legit)} messages)",
              f"- Correctly left alone: **{1-alarm_rate:.1%}**", "",
              "_See known-limitations.md for remaining failures._"]

    os.makedirs(DOCS, exist_ok=True)
    with open(os.path.join(DOCS, "evaluation-report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"TEST acc {acc:.1%} | scams wrongly cleared {cleared_rate:.1%} | "
          f"false alarms {alarm_rate:.1%} | disguised caught {d_caught/len(disg):.1%}")
    print("report -> docs/evaluation-report.md")


if __name__ == "__main__":
    main()

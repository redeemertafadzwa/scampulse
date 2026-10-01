"""
Retrain on the CSV + synthetic TRAINING set + Confirmed community items,
evaluate on the fixed regression sets, and publish ONLY if neither the
"scams wrongly cleared" rate nor the "false alarm" rate gets worse.
Never runs on a phone - this is a server command.
"""
import json
import os
import sys

import joblib
import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand

ROOT = str(settings.BASE_DIR)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "ml"))


def _rates(eng, test, legit):
    from engine import SCAM_CLASSES
    scams = [r for _, r in test.iterrows() if r["threat_type"] in SCAM_CLASSES]
    missed = sum(1 for r in scams
                 if eng.assess(r["text"])["verdict"] == "No warning signs found")
    alarms = sum(1 for _, r in legit.iterrows()
                 if eng.assess(r["text"])["verdict"] in ("Danger", "Be careful"))
    return missed / max(len(scams), 1), alarms / max(len(legit), 1)


class Command(BaseCommand):
    help = "Retrain the model and publish only if regression metrics don't worsen."

    def handle(self, *args, **opts):
        import train as mltrain
        from engine import Engine
        from core.models import ModelVersion, ScamFamily

        data = os.path.join(ROOT, "ml", "data")
        df = pd.read_csv(os.path.join(data, "training.csv"))
        test = pd.read_csv(os.path.join(data, "test.csv"))
        legit = pd.read_csv(os.path.join(data, "legit.csv"))

        # add confirmed community items as extra labelled scams
        extra = [(f.representative_text, f.category, "High")
                 for f in ScamFamily.objects.filter(status="confirmed")
                 if f.representative_text and f.category in set(df["threat_type"])]
        if extra:
            df = pd.concat([df, pd.DataFrame(extra, columns=df.columns)], ignore_index=True)
        self.stdout.write(f"training on {len(df)} rows (+{len(extra)} confirmed)")

        from normalise import normalise
        pipe = mltrain.build_pipeline()
        pipe.fit([normalise(t) for t in df["text"]], df["threat_type"])

        new_cleared, new_fa = _rates(Engine(pipe), test, legit)
        cur = ModelVersion.objects.filter(published=True).first()
        old = cur.metrics if cur else {"scams_cleared": 1.0, "false_alarms": 1.0}

        ok = (new_cleared <= old.get("scams_cleared", 1.0) + 1e-9 and
              new_fa <= old.get("false_alarms", 1.0) + 1e-9)
        self.stdout.write(
            f"new: cleared={new_cleared:.3f} fa={new_fa:.3f} | "
            f"old: cleared={old.get('scams_cleared')} fa={old.get('false_alarms')}")

        if not ok:
            self.stdout.write(self.style.WARNING(
                "Metrics would worsen - keeping the current model."))
            return

        # publish: write pickle + model.json (served to devices)
        joblib.dump(pipe, os.path.join(ROOT, "ml", "model.pkl"))
        mltrain.export_json(pipe, os.path.join(ROOT, "ml", "model.json"))
        mltrain.export_json(pipe, os.path.join(ROOT, "core", "static", "model.json"))

        parts = [int(x) for x in (cur.version if cur else "1.0.0").split(".")]
        parts[-1] += 1
        version = ".".join(map(str, parts))
        ModelVersion.objects.filter(published=True).update(published=False)
        ModelVersion.objects.create(
            version=version, published=True,
            metrics={"scams_cleared": round(new_cleared, 4),
                     "false_alarms": round(new_fa, 4)},
            notes=f"retrained on {len(df)} rows")
        self.stdout.write(self.style.SUCCESS(f"Published model {version}."))

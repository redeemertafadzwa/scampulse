"""
Train the TF-IDF + logistic-regression classifier on the TRAINING set only.
Saves model.pkl (server/eval) and exports model.json (on-device, Stage 2).
Shares normalise.py with the server.
"""
import json
import os
import sys

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from normalise import normalise  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
VERSION = "1.0.0"


def build_pipeline():
    word = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=1500,
                           sublinear_tf=True)
    char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2,
                           max_features=3000, sublinear_tf=True)
    feats = FeatureUnion([("w", word), ("c", char)])
    clf = LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced")
    return Pipeline([("feats", feats), ("clf", clf)])


def export_json(pipe, path):
    feats = pipe.named_steps["feats"]
    clf = pipe.named_steps["clf"]
    blocks = {}
    for name, vec in feats.transformer_list:
        vocab = {t: int(i) for t, i in vec.vocabulary_.items()}
        blocks[name] = {
            "analyzer": "char_wb" if name == "c" else "word",
            "ngram": list(vec.ngram_range),
            "vocab": vocab,
            "idf": [round(float(x), 4) for x in vec.idf_],
        }
    model = {
        "version": VERSION,
        "classes": list(clf.classes_),
        "blocks": blocks,
        "coef": [[round(float(x), 4) for x in row] for row in clf.coef_],
        "intercept": [round(float(x), 4) for x in clf.intercept_],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(model, f, separators=(",", ":"))
    return os.path.getsize(path)


def main():
    df = pd.read_csv(os.path.join(DATA, "training.csv"))
    X = [normalise(t) for t in df["text"]]
    y = df["threat_type"]
    pipe = build_pipeline()
    pipe.fit(X, y)
    acc = pipe.score(X, y)
    joblib.dump(pipe, os.path.join(HERE, "model.pkl"))
    size = export_json(pipe, os.path.join(HERE, "model.json"))
    print(f"trained on {len(df)} msgs | train acc {acc:.3f} | "
          f"model.json {size/1024:.0f} KB | version {VERSION}")


if __name__ == "__main__":
    main()

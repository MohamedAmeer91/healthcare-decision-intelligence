"""Builds the dashboard data from the committed outputs/ files.

Run `python web/build_data.py` to write web/static/data.json (used by the static
fallback). web/app.py imports build() so the Flask app serves the same data live.
Nothing here changes any file under outputs/.
"""
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

from common import (confusion, get_split, predict_at, predict_proba,  # noqa: E402
                    train_logistic)

OUT = os.path.join(ROOT, "outputs")


def _num(text):
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            pass
    return text


def read_results(name):
    out = {}
    with open(os.path.join(OUT, name)) as f:
        for line in f:
            if " = " in line:
                key, val = line.rstrip("\n").split(" = ", 1)
                out[key] = _num(val)
    return out


def read_csv(name):
    with open(os.path.join(OUT, name), newline="") as f:
        return [{k: _num(v) for k, v in row.items()} for row in csv.DictReader(f)]


def memo_paragraphs():
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"## Model-choice memo\s*(.*?)\s*## Limitations", text, re.S)
    return [p.strip() for p in m.group(1).split("\n\n") if p.strip()] if m else []


class Model:
    """The Task 2.2 logistic model, fitted once with the same code as part2.py."""

    def __init__(self):
        s = get_split()
        self.ytr, self.yte = s["ytr"], s["yte"]
        w, b, _ = train_logistic(s["Xtr_s"], self.ytr, 0.1, 1000)
        self.p_tr = predict_proba(s["Xtr_s"], w, b)
        self.p_te = predict_proba(s["Xte_s"], w, b)

    def at(self, k, den=100):
        """Confusion cells for tau = k/den on train and test rows."""
        res = {}
        for name, p, y in (("train", self.p_tr, self.ytr), ("test", self.p_te, self.yte)):
            tp, fp, tn, fn = confusion(y, predict_at(p, k, den))
            res[name] = dict(tp=tp, fp=fp, tn=tn, fn=fn)
        return res

    def sweep(self):
        rows = []
        for k in range(0, 101):
            c = self.at(k)
            rows.append(dict(tau=k / 100, train=c["train"], test=c["test"]))
        return rows


def build(model=None):
    model = model or Model()
    X, y, value = (get_split()[k] for k in ("X", "y", "value"))
    x4 = X[:, 3]
    return dict(
        p1=read_results("part1_results.txt"),
        p2=read_results("part2_results.txt"),
        p3=read_results("part3_results.txt"),
        p4=read_results("part4_results.txt"),
        thresholds=read_csv("part2_thresholds.csv"),
        knn_cv=read_csv("part2_knn_cv.csv"),
        segments=read_csv("part3_segments.csv"),
        hier=read_csv("part3_hierarchical.csv"),
        splits=read_csv("part4_splits.csv"),
        voting=read_csv("part4_voting.csv"),
        adaboost=read_csv("part4_adaboost.csv"),
        arch=read_csv("part4_architecture.csv"),
        sweep=model.sweep(),
        scatter=dict(x4=[round(float(v), 1) for v in x4],
                     value=[round(float(v), 2) for v in value]),
        memo=memo_paragraphs(),
    )


if __name__ == "__main__":
    static = os.path.join(ROOT, "web", "static")
    os.makedirs(static, exist_ok=True)
    payload = json.dumps(build(), separators=(",", ":"))
    # data.json for tools; data.js so index.html also opens straight from disk
    # (browsers block fetch() of local files).
    for name, text in (("data.json", payload), ("data.js", "window.__DATA__=" + payload + ";")):
        with open(os.path.join(static, name), "w") as f:
            f.write(text)
        print("wrote web/static/%s" % name, len(text), "bytes")

"""Shared helpers for part1.py .. part4.py. Importing this module runs nothing."""
import csv
import math
import os

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "outputs")


# ---------------------------------------------------------------- data / output
def load_data():
    """Return X (800x7), outcome (int array), value (float array) in file order."""
    with open(os.path.join(ROOT, "data", "records.csv"), newline="") as f:
        rows = list(csv.reader(f))[1:]
    X = np.array([[float(v) for v in r[1:8]] for r in rows])
    outcome = np.array([int(r[8]) for r in rows])
    value = np.array([float(r[9]) for r in rows])
    return X, outcome, value


def fmt(v):
    if isinstance(v, (bool, np.bool_)):
        return "yes" if v else "no"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        return "%.4f" % v
    return str(v)


def write_results(name, items):
    """items: list of (key, value) pairs; one 'key = value' line each."""
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", newline="\n") as f:
        for k, v in items:
            f.write("%s = %s\n" % (k, fmt(v)))


def write_csv(name, header, rows):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", newline="") as f:
        f.write(",".join(header) + "\n")
        for r in rows:
            f.write(",".join(fmt(v) for v in r) + "\n")


# ---------------------------------------------------------------- split / scale
def stratified_split(outcome):
    """Indices of train and test rows (file order kept inside each set)."""
    train, test = [], []
    for cls in (0, 1):
        idx = [i for i in range(len(outcome)) if outcome[i] == cls]
        k = (7 * len(idx)) // 10
        train += idx[:k]
        test += idx[k:]
    return np.array(sorted(train)), np.array(sorted(test))


def standardise(train, other=None):
    """Standardise with the mean and sample SD of `train`; apply to `other` too."""
    mean = train.mean(axis=0)
    sd = train.std(axis=0, ddof=1)
    if other is None:
        return (train - mean) / sd
    return (train - mean) / sd, (other - mean) / sd


def get_split():
    """Task 2.1 split. Returns dict with raw and standardised train/test data."""
    X, y, value = load_data()
    tr, te = stratified_split(y)
    Xtr_s, Xte_s = standardise(X[tr], X[te])
    return dict(X=X, y=y, value=value, tr=tr, te=te,
                Xtr=X[tr], Xte=X[te], ytr=y[tr], yte=y[te],
                Xtr_s=Xtr_s, Xte_s=Xte_s)


# ---------------------------------------------------------------- logistic regression
def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def bce(y, p):
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def predict_proba(X, w, b):
    return sigmoid(X @ w + b)


def train_logistic(X, y, eta, epochs, record=()):
    """Full-batch gradient descent from zeros. Returns w, b, {epoch: loss}."""
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    losses = {}
    if 0 in record:
        losses[0] = bce(y, predict_proba(X, w, b))
    for e in range(1, epochs + 1):
        err = predict_proba(X, w, b) - y
        w = w - eta * (X.T @ err) / n
        b = b - eta * err.mean()
        if e in record:
            losses[e] = bce(y, predict_proba(X, w, b))
    return w, b, losses


# ---------------------------------------------------------------- metrics
def confusion(y, pred):
    y = np.asarray(y)
    pred = np.asarray(pred).astype(bool)
    tp = int(np.sum(pred & (y == 1)))
    fp = int(np.sum(pred & (y == 0)))
    tn = int(np.sum(~pred & (y == 0)))
    fn = int(np.sum(~pred & (y == 1)))
    return tp, fp, tn, fn


def _div(a, b):
    return a / b if b else 0.0


def metrics(tp, fp, tn, fn):
    acc = _div(tp + tn, tp + fp + tn + fn)
    prec = _div(tp, tp + fp)
    rec = _div(tp, tp + fn)
    f1 = _div(2 * prec * rec, prec + rec)
    spec = _div(tn, tn + fp)
    return dict(accuracy=acc, precision=prec, recall=rec, f1=f1, specificity=spec,
                tpr=rec, fpr=_div(fp, fp + tn))


def predict_at(p, tau_num, tau_den):
    """p >= tau with tau = tau_num / tau_den, tolerant of float rounding."""
    return p >= (tau_num / tau_den) - 1e-12


# ---------------------------------------------------------------- k-nearest neighbours
def knn_pos_share(Xref, yref, Xq, K):
    """Share of positive neighbours among K for every query row.
    Neighbours ranked by (distance, reference position) via a stable sort."""
    shares = np.empty(len(Xq))
    for i, q in enumerate(Xq):
        d = np.sum((Xref - q) ** 2, axis=1)
        order = np.argsort(d, kind="stable")[:K]
        shares[i] = yref[order].sum() / K
    return shares


def knn_cv(Xtr, ytr, ks=tuple(range(1, 22, 2))):
    """5-fold CV (fold = training position mod 5) on already-standardised features.
    Returns [(K, mean F1 over folds)] and the best K (ties -> smaller K)."""
    fold = np.arange(len(ytr)) % 5
    f1s = {k: [] for k in ks}
    for f in range(5):
        ref, held = np.where(fold != f)[0], np.where(fold == f)[0]
        Xref, yref = Xtr[ref], ytr[ref]
        ranks = [np.argsort(np.sum((Xref - Xtr[i]) ** 2, axis=1), kind="stable") for i in held]
        for k in ks:
            pred = np.array([yref[o[:k]].sum() >= (k + 1) / 2 for o in ranks])
            f1s[k].append(metrics(*confusion(ytr[held], pred))["f1"])
    cv = [(k, float(np.mean(f1s[k]))) for k in ks]
    best = max(cv, key=lambda t: (t[1], -t[0]))[0]
    return cv, best


def knn_predict(Xref, yref, Xq, K):
    """Positive when at least (K+1)/2 of K neighbours are positive (K odd)."""
    pos = knn_pos_share(Xref, yref, Xq, K) * K
    return pos >= (K + 1) / 2 - 1e-9

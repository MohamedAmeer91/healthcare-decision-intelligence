"""Part 2 - classification and evaluation (70/30 stratified split)."""
import numpy as np

from common import (bce, confusion, get_split, knn_cv, knn_pos_share, metrics, predict_at,
                    predict_proba, train_logistic, write_csv, write_results)

S = get_split()
Xtr, Xte, ytr, yte = S["Xtr_s"], S["Xte_s"], S["ytr"], S["yte"]
R = []

# ---- 2.1 split and standardise
R += [("train_rows", len(ytr)), ("train_positives", int(ytr.sum())),
      ("test_rows", len(yte)), ("test_positives", int(yte.sum()))]

# ---- 2.2 logistic regression from scratch
w, b, L = train_logistic(Xtr, ytr, 0.1, 1000, record=(0, 1, 10, 100, 1000))
for e in (0, 1, 10, 100, 1000):
    R.append(("loss_epoch_%d" % e, L[e]))
for j in range(7):
    R.append(("weight_X%d" % (j + 1), float(w[j])))
R.append(("bias", float(b)))
p_tr = predict_proba(Xtr, w, b)
p_te = predict_proba(Xte, w, b)
R.append(("test_bce", bce(yte, p_te)))

# ---- 2.3 learning-rate effect
for eta in (0.01, 0.1, 1.0):
    _, _, l200 = train_logistic(Xtr, ytr, eta, 200, record=(200,))
    R.append(("loss_epoch_200_eta_%s" % eta, l200[200]))

# ---- 2.4 odds ratios
for j in range(7):
    R.append(("odds_ratio_X%d" % (j + 1), float(np.exp(w[j]))))

# ---- 2.5 two thresholds and blind accuracy
for name, num, den in (("0.5", 5, 10), ("0.3", 3, 10)):
    tp, fp, tn, fn = confusion(yte, predict_at(p_te, num, den))
    m = metrics(tp, fp, tn, fn)
    pre = "tau_%s_" % name
    R += [(pre + "tp", tp), (pre + "fp", fp), (pre + "tn", tn), (pre + "fn", fn)]
    R += [(pre + k, m[k]) for k in ("accuracy", "precision", "recall", "f1", "specificity")]
R.append(("blind_accuracy", float(np.mean(yte == 0))))

# ---- 2.6 threshold sweep
rows = []
for k in range(1, 10):
    tp, fp, tn, fn = confusion(yte, predict_at(p_te, k, 10))
    m = metrics(tp, fp, tn, fn)
    rows.append([k / 10, tp, fp, tn, fn, m["tpr"], m["fpr"]])
write_csv("part2_thresholds.csv", ["tau", "tp", "fp", "tn", "fn", "tpr", "fpr"], rows)

# ---- 2.7 KNN with 5-fold cross-validation on the training rows
cv, best_k = knn_cv(Xtr, ytr)
write_csv("part2_knn_cv.csv", ["K", "mean_cv_f1"], [[k, s] for k, s in cv])
R.append(("knn_best_k", best_k))
share_te = knn_pos_share(Xtr, ytr, Xte, best_k)
pred_knn = share_te * best_k >= (best_k + 1) / 2 - 1e-9
tp, fp, tn, fn = confusion(yte, pred_knn)
m = metrics(tp, fp, tn, fn)
R += [("knn_tp", tp), ("knn_fp", fp), ("knn_tn", tn), ("knn_fn", fn)]
R += [("knn_" + k, m[k]) for k in ("accuracy", "precision", "recall", "f1")]


# ---- 2.8 threshold chosen with money (on TRAINING rows)
def cost(y, pred):
    tp, fp, tn, fn = confusion(y, pred)
    return 50 * fp + 400 * fn


train_costs = [(k, cost(ytr, predict_at(p_tr, k, 20))) for k in range(1, 20)]
best_cost = min(c for _, c in train_costs)
best_k20 = min(k for k, c in train_costs if c == best_cost)  # ties -> smaller tau
cost_tau = best_k20 / 20
R += [("cost_tau", cost_tau), ("cost_train_at_tau", best_cost),
      ("cost_test_at_tau", cost(yte, predict_at(p_te, best_k20, 20))),
      ("cost_test_at_0.5", cost(yte, predict_at(p_te, 5, 10))),
      ("cost_test_flag_nobody", cost(yte, np.zeros(len(yte), dtype=bool)))]

write_results("part2_results.txt", R)
for k, v in R:
    print(k, "=", v)

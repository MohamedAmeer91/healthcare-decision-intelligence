"""Part 4 - model choice and architecture sizing. Reuses the Part 2 models via common.py."""
import math

import numpy as np

from common import (confusion, get_split, knn_cv, knn_pos_share, metrics, predict_proba,
                    train_logistic, write_csv, write_results)

S = get_split()
Xtr_raw, ytr, yte = S["Xtr"], S["ytr"], S["yte"]
Xte_raw = S["Xte"]
R = []


# ---- 4.1 which split is purest (training rows, original units)
def entropy(pos, n):
    if n == 0:
        return 0.0
    e = 0.0
    for c in (pos, n - pos):
        if c:
            q = c / n
            e -= q * math.log2(q)
    return e


def gini(pos, n):
    if n == 0:
        return 0.0
    q = pos / n
    return 1 - q * q - (1 - q) ** 2


n_tr, pos_tr = len(ytr), int(ytr.sum())
root_e, root_g = entropy(pos_tr, n_tr), gini(pos_tr, n_tr)
R += [("root_entropy", root_e), ("root_gini", root_g)]

splits = {"S1": lambda X: X[:, 5] == 1, "S2": lambda X: X[:, 6] == 1,
          "S3": lambda X: X[:, 2] > 0.5, "S4": lambda X: X[:, 0] <= 24}
split_rows, gains = [], {}
for name, cond in splits.items():
    yes = cond(Xtr_raw)
    ny, py = int(yes.sum()), int(ytr[yes].sum())
    nn, pn = n_tr - ny, pos_tr - py
    ig = root_e - (ny / n_tr * entropy(py, ny) + nn / n_tr * entropy(pn, nn))
    gg = root_g - (ny / n_tr * gini(py, ny) + nn / n_tr * gini(pn, nn))
    gains[name] = (ig, gg)
    split_rows.append([name, ny, py, nn, pn, ig, gg])
write_csv("part4_splits.csv", ["split", "n_yes", "positives_yes", "n_no", "positives_no",
                               "info_gain", "gini_gain"], split_rows)
best_ig = max(gains, key=lambda s: gains[s][0])
best_gg = max(gains, key=lambda s: gains[s][1])
R += [("best_split_by_info_gain", best_ig), ("best_split_by_gini_gain", best_gg)]

# ---- 4.2 stump, hard vote, soft vote (test rows)
cond = splits[best_ig]
yes_tr = cond(Xtr_raw)
rate_yes = float(ytr[yes_tr].mean())
rate_no = float(ytr[~yes_tr].mean())
R += [("stump_rate_yes", rate_yes), ("stump_rate_no", rate_no)]
p_stump = np.where(cond(Xte_raw), rate_yes, rate_no)

w, b, _ = train_logistic(S["Xtr_s"], ytr, 0.1, 1000)
p_log = predict_proba(S["Xte_s"], w, b)
_, K = knn_cv(S["Xtr_s"], ytr)
p_knn = knn_pos_share(S["Xtr_s"], ytr, S["Xte_s"], K)

TOL = 1e-12
pred_log = p_log >= 0.3 - TOL
pred_knn = p_knn * K >= (K + 1) / 2 - 1e-9
pred_stump = p_stump >= 0.3 - TOL
pred_hard = (pred_log.astype(int) + pred_knn.astype(int) + pred_stump.astype(int)) >= 2
pred_soft = (p_log + p_knn + p_stump) / 3 >= 0.3 - TOL

vote_rows = []
for name, pred in (("logistic", pred_log), ("knn", pred_knn), ("stump", pred_stump),
                   ("hard_vote", pred_hard), ("soft_vote", pred_soft)):
    tp, fp, tn, fn = confusion(yte, pred)
    m = metrics(tp, fp, tn, fn)
    vote_rows.append([name, tp, fp, tn, fn, m["precision"], m["recall"], m["f1"]])
write_csv("part4_voting.csv", ["model", "tp", "fp", "tn", "fn", "precision", "recall", "f1"],
          vote_rows)

# ---- 4.3 two rounds of AdaBoost by hand
y = np.array([1, 1, 1, -1, -1, -1, 1, -1], dtype=float)
h1 = np.array([1, 1, -1, -1, -1, -1, -1, -1], dtype=float)
h2 = np.array([-1, 1, 1, -1, 1, -1, 1, -1], dtype=float)
wts = np.full(8, 1 / 8)
alphas, ada_rows, errs = [], [], []
for rnd, h in ((1, h1), (2, h2)):
    eps = float(wts[h != y].sum())
    alpha = 0.5 * math.log((1 - eps) / eps)
    unnorm = wts * np.exp(-alpha * y * h)
    after = unnorm / unnorm.sum()
    for i in range(8):
        ada_rows.append([rnd, i + 1, float(wts[i]), float(unnorm[i]), float(after[i])])
    if rnd == 1:
        mis_weight_r1 = float(after[h != y].sum())
    errs.append(eps)
    alphas.append(alpha)
    wts = after
write_csv("part4_adaboost.csv", ["round", "point", "weight_before", "weight_unnormalised",
                                 "weight_after"], ada_rows)
ens = np.sign(alphas[0] * h1 + alphas[1] * h2)
R += [("round1_error", errs[0]), ("round1_alpha", alphas[0]),
      ("round2_error", errs[1]), ("round2_alpha", alphas[1]),
      ("ensemble_accuracy", float(np.mean(ens == y))),
      ("round1_misclassified_weight_after", mis_weight_r1)]

# ---- 4.4 out-of-bag share
R.append(("oob_fraction", (1 - 1 / 560) ** 560))


# ---- 4.5 architecture sizing (counted from shapes)
def dense(n_in, n_out):
    return n_in * n_out + n_out


def conv(k, c_in, c_out):
    return k * k * c_in * c_out + c_out


def out_side(inp, f, pad, stride):
    return (inp - f + 2 * pad) // stride + 1


mlp = [("mlp_hidden1", dense(784, 16)), ("mlp_hidden2", dense(16, 16)), ("mlp_output", dense(16, 10))]
s1 = out_side(28, 5, 2, 1)          # conv1 -> 28
p1 = out_side(s1, 2, 0, 2)          # pool  -> 14
s2 = out_side(p1, 5, 0, 1)          # conv2 -> 10
p2 = out_side(s2, 2, 0, 2)          # pool  -> 5
flat = p2 * p2 * 16                 # 400
cnn = [("cnn_conv1", conv(5, 1, 6)), ("cnn_conv2", conv(5, 6, 16)),
       ("cnn_dense1", dense(flat, 32)), ("cnn_dense2", dense(32, 10))]
write_csv("part4_architecture.csv", ["layer", "parameters"], [[k, v] for k, v in mlp + cnn])
R += [("mlp_total", sum(v for _, v in mlp)), ("cnn_total", sum(v for _, v in cnn)),
      ("fc_layer_params", dense(128 * 128 * 3, 1024)), ("conv_layer_params", conv(3, 3, 64)),
      ("rnn_total", 128 * 64 + 128 * 128 + 16 * 128 + 128 + 16)]

write_results("part4_results.txt", R)
print("CNN shapes: conv1 %dx%dx6, pool1 %dx%dx6, conv2 %dx%dx16, pool2 %dx%dx16, flatten %d, K=%d"
      % (s1, s1, p1, p1, s2, s2, p2, p2, flat, K))

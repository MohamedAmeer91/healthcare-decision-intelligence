"""Part 3 - segmentation and dimensionality reduction (all 800 rows, X1..X5)."""
import numpy as np

from common import load_data, write_csv, write_results

X, outcome, value = load_data()
X5 = X[:, :5]
n = len(X5)
Z = (X5 - X5.mean(axis=0)) / X5.std(axis=0, ddof=1)
R = []


# ---- 3.1 K-means from scratch with pinned starting rows
def kmeans(Z, K):
    step = len(Z) // K
    cent = Z[[i * step for i in range(K)]].copy()
    labels = None
    passes = 0
    while True:
        passes += 1
        d = ((Z[:, None, :] - cent[None, :, :]) ** 2).sum(axis=2)
        new = np.argmin(d, axis=1)  # ties -> lower-numbered centroid
        if labels is not None and np.array_equal(new, labels):
            break
        labels = new
        for k in range(K):
            members = Z[labels == k]
            if len(members):
                cent[k] = members.mean(axis=0)
    wcss = float(((Z - cent[labels]) ** 2).sum())
    return labels, cent, wcss, passes


fits = {K: kmeans(Z, K) for K in range(2, 7)}
wcss = {K: fits[K][2] for K in fits}
for K in range(2, 7):
    R.append(("wcss_k%d" % K, wcss[K]))
    print("K=%d passes=%d" % (K, fits[K][3]))

# ---- 3.2 elbow rule
elbow_k = next((K for K in (3, 4, 5)
                if wcss[K] - wcss[K + 1] < 0.5 * (wcss[K - 1] - wcss[K])), None)
R.append(("elbow_k", elbow_k if elbow_k is not None else "none"))

# ---- 3.3 profile K = 3 segments (A, B, C by ascending mean X3)
labels3 = fits[3][0]
order = sorted(range(3), key=lambda k: X[labels3 == k, 2].mean())
seg_of = np.empty(n, dtype=int)
rows = []
for name, k in zip("ABC", order):
    mask = labels3 == k
    seg_of[mask] = "ABC".index(name)
    R.append(("size_segment_%s" % name, int(mask.sum())))
    rows.append([name, int(mask.sum())] + [float(X[mask, j].mean()) for j in range(5)]
                + [float(outcome[mask].mean()), float(value[mask].mean())])
write_csv("part3_segments.csv",
          ["segment", "size", "mean_X1", "mean_X2", "mean_X3", "mean_X4", "mean_X5",
           "outcome_rate", "mean_value"], rows)

# ---- 3.4 hierarchical clustering on the supplied table
D = np.array([[0.0, 7.9, 7.4, 2.9, 2.9, 6.1],
              [7.9, 0.0, 1.4, 5.9, 5.3, 2.0],
              [7.4, 1.4, 0.0, 5.8, 4.6, 1.3],
              [2.9, 5.9, 5.8, 0.0, 2.8, 4.5],
              [2.9, 5.3, 4.6, 2.8, 0.0, 3.4],
              [6.1, 2.0, 1.3, 4.5, 3.4, 0.0]])


def linkage_dist(a, b, rule):
    ds = [D[i, j] for i in a for j in b]
    return min(ds) if rule == "single" else (max(ds) if rule == "complete" else sum(ds) / len(ds))


def label(c):
    return "+".join("E%d" % (i + 1) for i in sorted(c))


hier_rows = []
for rule in ("single", "complete", "average"):
    clusters = [[i] for i in range(6)]
    heights = []
    for step in range(1, 6):
        best = None
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                h = linkage_dist(clusters[i], clusters[j], rule)
                if best is None or h < best[0]:
                    best = (h, i, j)
        h, i, j = best
        a, b = clusters[i], clusters[j]
        if min(b) < min(a):
            a, b = b, a
        hier_rows.append([rule, step, label(a), label(b), h])
        heights.append(h)
        clusters = [c for k, c in enumerate(clusters) if k not in (i, j)] + [a + b]
    gaps = [heights[k + 1] - heights[k] for k in range(4)]
    g = int(np.argmax(gaps))  # the cut lies in gap g: merges 1..g+1 are below it
    R.append(("%s_clusters_at_cut" % rule, 6 - (g + 1)))
write_csv("part3_hierarchical.csv", ["linkage", "merge_no", "cluster_a", "cluster_b", "height"],
          hier_rows)

# ---- 3.5 PCA in seven steps
mean_vec = Z.mean(axis=0)                 # (1) all zeros after standardising
Xc = Z - mean_vec                         # (2) centre
S = (Xc.T @ Xc) / (n - 1)                 # (3) covariance matrix
vals, vecs = np.linalg.eigh(S)            # (4) eigen-decomposition
idx = np.argsort(-vals)                   # (5) largest first
vals, vecs = vals[idx], vecs[:, idx]
for j in range(vecs.shape[1]):            # sign convention
    if vecs[np.argmax(np.abs(vecs[:, j])), j] < 0:
        vecs[:, j] = -vecs[:, j]
W = vecs[:, :2]                           # (6) top two eigenvectors
P = Xc @ W                                # (7) project

total = float(vals.sum())
ratio = vals / total
cum = np.cumsum(ratio)
R.append(("eigenvalue_sum", total))
R += [("eigenvalue_%d" % (i + 1), float(vals[i])) for i in range(5)]
R += [("explained_ratio_%d" % (i + 1), float(ratio[i])) for i in range(5)]
R += [("cumulative_ratio_%d" % (i + 1), float(cum[i])) for i in range(5)]
R.append(("components_for_80pct", int(np.argmax(cum >= 0.8 - 1e-12)) + 1))
R += [("pc1_loading_X%d" % (j + 1), float(vecs[j, 0])) for j in range(5)]
R += [("pc2_loading_X%d" % (j + 1), float(vecs[j, 1])) for j in range(5)]
for r in range(3):
    R += [("row%d_pc1" % (r + 1), float(P[r, 0])), ("row%d_pc2" % (r + 1), float(P[r, 1]))]
for s, name in enumerate("ABC"):
    R.append(("mean_pc1_segment_%s" % name, float(P[seg_of == s, 0].mean())))

write_results("part3_results.txt", R)
print("mean vector:", np.round(mean_vec, 12))

"""Part 1 - estimation, inference and regression baseline (all 800 rows)."""
import math

import numpy as np

from common import load_data, write_results

X, outcome, value = load_data()
n = len(value)
x4 = X[:, 3]
R = []  # ordered (key, value) results


def sd(a):
    return math.sqrt(float(np.sum((a - a.mean()) ** 2)) / (len(a) - 1))


def simple_ols(x, y):
    """Closed form: slope = cov/var (both n-1), intercept = ybar - slope*xbar."""
    xm, ym = x.mean(), y.mean()
    cov = float(np.sum((x - xm) * (y - ym))) / (len(x) - 1)
    var = float(np.sum((x - xm) ** 2)) / (len(x) - 1)
    slope = cov / var
    return slope, ym - slope * xm


def halves_sd(resid, fitted):
    order = np.argsort(fitted, kind="stable")
    half = len(order) // 2
    return sd(resid[order[:half]]), sd(resid[order[half:]])


# ---- 1.1 estimate with an interval
mean_value = float(value.mean())
sd_value = sd(value)
se_value = sd_value / math.sqrt(n)
R += [("n", n), ("mean_value", mean_value), ("sd_value", sd_value), ("se_value", se_value),
      ("ci95_low", mean_value - 1.96 * se_value), ("ci95_high", mean_value + 1.96 * se_value)]

# ---- 1.2 test H0: mu = 8.0
z_stat = (mean_value - 8.0) / se_value
R += [("z_stat", z_stat), ("reject_h0", abs(z_stat) > 1.96)]

# ---- 1.3 required sample size for E = 0.5
n_required = math.ceil((1.96 * sd_value / 0.5) ** 2)
R += [("n_required", n_required)]

# ---- 1.4 simple regression, closed form
slope, intercept = simple_ols(x4, value)
fitted = intercept + slope * x4
ym = value.mean()
tss = float(np.sum((value - ym) ** 2))
ess = float(np.sum((fitted - ym) ** 2))
resid = value - fitted
rss = float(np.sum(resid ** 2))
R += [("reg_slope", slope), ("reg_intercept", intercept), ("tss", tss), ("ess", ess), ("rss", rss),
      ("tss_equals_ess_plus_rss", abs(tss - ess - rss) < 1e-6 * tss),
      ("r2", 1 - rss / tss), ("rmse", math.sqrt(rss / n)), ("mae", float(np.mean(np.abs(resid))))]

# ---- 1.5 gradient descent on standardised X4
x4_mean, x4_sd = float(x4.mean()), sd(x4)
z = (x4 - x4_mean) / x4_sd
m, c = 0.0, 0.0
eta = 0.1
J = {}


def cost(m, c):
    e = value - (m * z + c)
    return float(np.sum(e ** 2)) / n


J[0] = cost(m, c)
for step in range(1, 501):
    e = value - (m * z + c)
    gm = -(2.0 / n) * float(np.sum(z * e))
    gc = -(2.0 / n) * float(np.sum(e))
    m -= eta * gm
    c -= eta * gc
    if step in (1, 10, 100, 500):
        J[step] = cost(m, c)
gd_slope = m / x4_sd
gd_intercept = c - m * x4_mean / x4_sd
R += [("gd_J0", J[0]), ("gd_J1", J[1]), ("gd_J10", J[10]), ("gd_J100", J[100]), ("gd_J500", J[500]),
      ("gd_slope", gd_slope), ("gd_intercept", gd_intercept), ("gd_slope_gap", abs(gd_slope - slope))]

# ---- 1.6 funnel check and log-log remedy
lo, hi = halves_sd(resid, fitted)
R += [("resid_sd_lower_raw", lo), ("resid_sd_upper_raw", hi), ("resid_sd_ratio_raw", hi / lo)]

ly, lx = np.log(value), np.log(x4)
ll_slope, ll_int = simple_ols(lx, ly)
ll_fit = ll_int + ll_slope * lx
ll_res = ly - ll_fit
ll_rss = float(np.sum(ll_res ** 2))
ll_tss = float(np.sum((ly - ly.mean()) ** 2))
ll_r2 = 1 - ll_rss / ll_tss
lo2, hi2 = halves_sd(ll_res, ll_fit)
R += [("loglog_intercept", ll_int), ("loglog_slope", ll_slope), ("loglog_r2", ll_r2),
      ("loglog_rmse", math.sqrt(ll_rss / n)),
      ("resid_sd_lower_log", lo2), ("resid_sd_upper_log", hi2), ("resid_sd_ratio_log", hi2 / lo2)]

# ---- 1.7 multiple regression by the normal equation
A = np.column_stack([np.ones(n), lx, X[:, 0], X[:, 1], X[:, 2], X[:, 4], X[:, 5], X[:, 6]])
beta = np.linalg.solve(A.T @ A, A.T @ ly)
mr_res = ly - A @ beta
mr_r2 = 1 - float(np.sum(mr_res ** 2)) / ll_tss
p = 7
mr_adj = 1 - (1 - mr_r2) * (n - 1) / (n - p - 1)
ll_adj = 1 - (1 - ll_r2) * (n - 1) / (n - 1 - 1)
R += [("mr_beta_%d" % i, float(beta[i])) for i in range(8)]
R += [("mr_r2", mr_r2), ("mr_adj_r2", mr_adj), ("loglog_adj_r2", ll_adj)]

write_results("part1_results.txt", R)
for k, v in R:
    print(k, "=", v)

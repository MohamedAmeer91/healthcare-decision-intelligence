(function () {
"use strict";
var D, LIVE = false;
var $ = function (s, r) { return (r || document).querySelector(s); };
var f4 = function (v) { return Number(v).toFixed(4); };
var f2 = function (v) { return Number(v).toFixed(2); };
var inr = function (v) { return "INR " + Math.round(v).toLocaleString("en-IN"); };
var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
var SEGC = ["var(--c1)", "var(--c2)", "var(--c3)"];
var PRED = ["Tenure (months)", "Missed visits (12m)", "Co-pay ratio", "Avg bill (INR k)", "Adherence score"];

/* ---------- chart helpers (inline SVG) ---------- */
function niceTicks(lo, hi, n) {
  n = n || 5;
  var span = hi - lo, s0 = span / n, mag = Math.pow(10, Math.floor(Math.log10(s0))), nm = s0 / mag;
  var step = (nm < 1.5 ? 1 : nm < 3 ? 2 : nm < 7 ? 5 : 10) * mag, out = [];
  for (var v = Math.ceil(lo / step - 1e-9) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(10));
  return out;
}
function frame(o) {
  var W = 640, H = o.h || 300, m = { l: o.ml || 56, r: 16, t: 12, b: 44 };
  var iw = W - m.l - m.r, ih = H - m.t - m.b, xd = o.xd, yd = o.yd;
  var X = o.xband ? null : function (v) { return m.l + (v - xd[0]) / (xd[1] - xd[0]) * iw; };
  var Y = function (v) { return m.t + ih - (v - yd[0]) / (yd[1] - yd[0]) * ih; };
  var s = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' + esc(o.label) + '">';
  niceTicks(yd[0], yd[1], 5).forEach(function (t) {
    s += '<line class="grid" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + Y(t) + '" y2="' + Y(t) + '"/>' +
      '<text x="' + (m.l - 8) + '" y="' + (Y(t) + 4) + '" text-anchor="end">' + (o.yfmt ? o.yfmt(t) : t) + "</text>";
  });
  if (X) niceTicks(xd[0], xd[1], 6).forEach(function (t) {
    s += '<text x="' + X(t) + '" y="' + (H - m.b + 16) + '" text-anchor="middle">' + (o.xfmt ? o.xfmt(t) : t) + "</text>";
  });
  s += '<line class="axis" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + (m.t + ih) + '" y2="' + (m.t + ih) + '"/>';
  if (o.xlabel) s += '<text class="ttl" x="' + (m.l + iw / 2) + '" y="' + (H - 6) + '" text-anchor="middle">' + esc(o.xlabel) + "</text>";
  if (o.ylabel) s += '<text class="ttl" transform="translate(12 ' + (m.t + ih / 2) + ') rotate(-90)" text-anchor="middle">' + esc(o.ylabel) + "</text>";
  return { s: s, X: X, Y: Y, m: m, iw: iw, ih: ih, W: W, H: H };
}
function legend(series) {
  if (series.length < 2) return "";
  return '<div class="legend">' + series.map(function (x) {
    return '<span><i style="background:' + x.color + '"></i>' + esc(x.name) + "</span>";
  }).join("") + "</div>";
}
function lineChart(o) {
  var F = frame(o), s = F.s;
  o.series.forEach(function (se) {
    s += '<polyline fill="none" stroke="' + se.color + '" stroke-width="2"' + (se.dash ? ' stroke-dasharray="5 4"' : "") +
      ' stroke-linejoin="round" points="' + se.pts.map(function (p) { return F.X(p[0]).toFixed(1) + "," + F.Y(p[1]).toFixed(1); }).join(" ") + '"/>';
  });
  o.series.forEach(function (se) {
    if (se.noHover) return;
    se.pts.forEach(function (p) {
      s += '<circle cx="' + F.X(p[0]).toFixed(1) + '" cy="' + F.Y(p[1]).toFixed(1) + '" r="6" fill="transparent" data-tip="' +
        esc(se.name + " · " + (o.tip ? o.tip(p, se) : p[0] + ", " + p[1])) + '"/>';
    });
  });
  (o.markers || []).forEach(function (mk) {
    s += '<circle cx="' + F.X(mk.x) + '" cy="' + F.Y(mk.y) + '" r="5" fill="' + mk.color + '" stroke="var(--surface)" stroke-width="2" data-tip="' + esc(mk.tip) + '"/>';
    if (mk.label) s += '<text x="' + (F.X(mk.x) + 8) + '" y="' + (F.Y(mk.y) - 8) + '">' + esc(mk.label) + "</text>";
  });
  return s + "</svg>" + legend(o.series);
}
function rounded(x, y, w, h, r, up) {
  r = Math.min(r, w / 2, Math.abs(h));
  if (h === 0) return "";
  return up
    ? "M" + x + " " + (y + h) + "V" + (y + r) + "Q" + x + " " + y + " " + (x + r) + " " + y + "H" + (x + w - r) + "Q" + (x + w) + " " + y + " " + (x + w) + " " + (y + r) + "V" + (y + h) + "Z"
    : "M" + x + " " + y + "V" + (y + h - r) + "Q" + x + " " + (y + h) + " " + (x + r) + " " + (y + h) + "H" + (x + w - r) + "Q" + (x + w) + " " + (y + h) + " " + (x + w) + " " + (y + h - r) + "V" + y + "Z";
}
function barChart(o) {
  var F = frame({ xband: true, yd: o.yd, yfmt: o.yfmt, ylabel: o.ylabel, label: o.label, h: o.h, xd: [0, 1] }), s = F.s;
  var n = o.cats.length, band = F.iw / n, k = o.series.length, bw = Math.min(46, band * 0.7 / k - 2);
  var y0 = F.Y(0), gx = band - k * (bw + 2);
  if (o.ref !== undefined) s += '<line x1="' + F.m.l + '" x2="' + (F.W - F.m.r) + '" y1="' + F.Y(o.ref) + '" y2="' + F.Y(o.ref) + '" stroke="var(--ink2)" stroke-dasharray="4 4"/>' +
    '<text x="' + (F.W - F.m.r) + '" y="' + (F.Y(o.ref) - 5) + '" text-anchor="end">' + esc(o.refLabel || "") + "</text>";
  o.cats.forEach(function (c, i) {
    var cx = F.m.l + band * i;
    s += '<text x="' + (cx + band / 2) + '" y="' + (F.H - F.m.b + 16) + '" text-anchor="middle">' + esc(c) + "</text>";
    o.series.forEach(function (se, j) {
      var v = se.vals[i], x = cx + gx / 2 + j * (bw + 2), y = F.Y(v), h = y0 - y;
      var col = Array.isArray(se.color) ? se.color[i] : se.color;
      var tip = (o.cats[i] + (k > 1 ? " · " + se.name : "") + ": " + (o.tipfmt ? o.tipfmt(v) : v));
      s += '<path d="' + (v >= 0 ? rounded(x, y, bw, h, 4, true) : rounded(x, y0, bw, -h, 4, false)) + '" fill="' + col + '" tabindex="0" data-tip="' + esc(tip) + '"/>';
    });
  });
  s += '<line class="axis" x1="' + F.m.l + '" x2="' + (F.W - F.m.r) + '" y1="' + y0 + '" y2="' + y0 + '"/>';
  return s + "</svg>" + legend(o.series);
}
function table(head, rows) {
  return '<div class="scroll"><table><thead><tr>' + head.map(function (h) { return "<th>" + esc(h) + "</th>"; }).join("") +
    "</tr></thead><tbody>" + rows.map(function (r) { return "<tr>" + r.map(function (c) { return "<td>" + esc(c) + "</td>"; }).join("") + "</tr>"; }).join("") + "</tbody></table></div>";
}
function card(title, note, chart, tbl, id) {
  return '<div class="card"' + (id ? ' id="' + id + '"' : "") + "><h3>" + esc(title) + "</h3>" + (note ? '<p class="note">' + note + "</p>" : "") +
    '<div class="chart">' + chart + "</div>" + (tbl ? "<details><summary>Table view</summary>" + tbl + "</details>" : "") + "</div>";
}

/* ---------- data helpers ---------- */
function cells(k) { return D.sweep[k]; }
function cost(c, fa, ms) { return fa * c.fp + ms * c.fn; }
function metr(c) {
  var P = c.tp + c.fn, pr = c.tp + c.fp;
  return { recall: P ? c.tp / P : 0, precision: pr ? c.tp / pr : 0 };
}

/* ---------- sections ---------- */
function overview() {
  var p1 = D.p1, p2 = D.p2, p3 = D.p3;
  var k = [
    [f2(p1.mean_value) + "k", "mean care-plan cost (INR thousands), above the INR 8k plan; z = " + f2(p1.z_stat)],
    [p1.n_required + " vs 800", "records needed for a ±INR 500 margin vs. records available"],
    [f2(p2["tau_0.3_recall"] * 100) + "%", "no-shows caught at τ = 0.3 (test); blind accuracy is " + f2(p2.blind_accuracy * 100) + "%"],
    [inr(p2.cost_test_at_tau), "test cost at τ = " + f2(p2.cost_tau) + " vs " + inr(p2["cost_test_at_0.5"]) + " at 0.5"],
    ["3 segments", "highest no-show rate " + f2(D.segments[2].outcome_rate * 100) + "% (segment C)"]
  ];
  return '<section id="overview"><h2>Overview</h2><div class="kpis">' + k.map(function (x) {
    return '<div class="kpi"><div class="v">' + esc(x[0]) + '</div><div class="l">' + esc(x[1]) + "</div></div>";
  }).join("") + "</div></section>";
}
function part1() {
  var p = D.p1;
  var keyTbl = table(["Quantity", "Value"], [
    ["Mean cost (INR k)", f4(p.mean_value)], ["Std. deviation", f4(p.sd_value)], ["95% interval", f4(p.ci95_low) + " to " + f4(p.ci95_high)],
    ["z for H0: mean = 8.0", f4(p.z_stat)], ["Reject H0?", p.reject_h0], ["Records needed (±INR 500)", p.n_required],
    ["Simple regression R²", f4(p.r2)], ["Log-log R²", f4(p.loglog_r2)], ["Multiple regression adj. R²", f4(p.mr_adj_r2)]
  ]);
  var names = ["Constant", "ln(avg bill)", "Tenure", "Missed visits", "Co-pay ratio", "Adherence", "Chronic flag", "Insured flag"];
  var betaRows = names.map(function (n, i) { return [n, f4(p["mr_beta_" + i]), Math.abs(p["mr_beta_" + i]) > 0.05 && i > 0 ? "above 0.05" : ""]; });
  var ratio = barChart({
    cats: ["Raw model", "Log-log model"], yd: [0, 4], yfmt: function (v) { return v; }, ylabel: "Residual SD, upper ÷ lower half", ref: 1, refLabel: "1 = no funnel",
    series: [{ name: "Ratio", color: ["var(--c2)", "var(--c1)"], vals: [p.resid_sd_ratio_raw, p.resid_sd_ratio_log] }], label: "Funnel ratio for raw and log models", tipfmt: f4
  });
  return '<section id="part1"><h2>1 · Care-plan cost and regression</h2><div class="grid">' +
    '<div class="card"><h3>Is the INR 8,000 planning assumption still right?</h3><p class="note">Rejected: the average is ' + inr(p.mean_value * 1000) +
    " (z = " + f2(p.z_stat) + " vs 1.96). To pin it down to ±INR 500 the team needs " + p.n_required + " records; 800 are available.</p>" + keyTbl + "</div>" +
    '<div class="card" id="scatterCard"><h3>Average bill vs care-plan cost</h3><p class="note">Raw scale fans out like a funnel; the log scale tames it.</p>' +
    '<div class="tabs" role="group" aria-label="Scale"><button aria-pressed="true" data-scale="raw">Raw</button><button aria-pressed="false" data-scale="log">Log-log</button></div><div id="scatter"></div></div>' +
    card("Does the log remedy remove the funnel?", "Ratio of residual spread, upper half over lower half of fitted values.", ratio,
      table(["Model", "Ratio"], [["Raw", f4(p.resid_sd_ratio_raw)], ["Log-log", f4(p.resid_sd_ratio_log)]])) +
    '<div class="card"><h3>Multiple regression on ln(cost)</h3><p class="note">Coefficients are in different units; the 0.05 flag is a mechanical rule, not a ranking.</p>' + table(["Predictor", "Coefficient", ""], betaRows) + "</div></div></section>";
}
function drawScatter(mode) {
  var p = D.p1, xs = D.scatter.x4, ys = D.scatter.value, log = mode === "log";
  var X = log ? xs.map(Math.log) : xs, Y = log ? ys.map(Math.log) : ys;
  var xd = [Math.floor(Math.min.apply(null, X)), Math.ceil(Math.max.apply(null, X))], yd = [Math.floor(Math.min.apply(null, Y)), Math.ceil(Math.max.apply(null, Y))];
  var icp = log ? p.loglog_intercept : p.reg_intercept, sl = log ? p.loglog_slope : p.reg_slope;
  var F = frame({ xd: xd, yd: yd, label: "Scatter of bill against cost", xlabel: log ? "ln(avg bill, INR k)" : "Average bill (INR thousands)", ylabel: log ? "ln(cost)" : "Care-plan cost (INR k)", h: 320 }), s = F.s;
  X.forEach(function (x, i) {
    s += '<circle cx="' + F.X(x).toFixed(1) + '" cy="' + F.Y(Y[i]).toFixed(1) + '" r="2.8" fill="var(--c1)" fill-opacity=".4" data-tip="' + esc("Bill INR " + xs[i] + "k · cost INR " + ys[i] + "k") + '"/>';
  });
  var y1 = Math.max(yd[0], icp + sl * xd[0]), y2 = Math.min(yd[1], icp + sl * xd[1]);
  var xa = Math.max(xd[0], (y1 - icp) / sl), xb = Math.min(xd[1], (y2 - icp) / sl);
  s += '<line x1="' + F.X(xa) + '" y1="' + F.Y(icp + sl * xa) + '" x2="' + F.X(xb) + '" y2="' + F.Y(icp + sl * xb) + '" stroke="var(--c2)" stroke-width="2.5"/></svg>';
  $("#scatter").innerHTML = s + '<div class="legend"><span><i style="background:var(--c1)"></i>800 patients</span><span><i style="background:var(--c2)"></i>fitted line (slope ' + f4(sl) + ")</span></div>";
}

function part2() {
  var p = D.p2;
  var roc = lineChart({
    xd: [0, 1], yd: [0, 1], xfmt: f2, yfmt: f2, xlabel: "False-positive rate", ylabel: "True-positive rate (recall)", label: "ROC curve on test rows",
    series: [
      { name: "Chance", color: "var(--neutral)", dash: true, noHover: true, pts: [[0, 0], [1, 1]] },
      { name: "Logistic model", color: "var(--c1)", pts: D.sweep.map(function (r) { var m = r.test, P = m.tp + m.fn, N = m.fp + m.tn; return [m.fp / N, m.tp / P, r.tau]; }) }
    ],
    tip: function (pt) { return "τ " + f2(pt[2]) + ": FPR " + f2(pt[0]) + ", TPR " + f2(pt[1]); }, h: 300
  });
  var lr = barChart({
    cats: ["η = 0.01", "η = 0.1", "η = 1.0"], yd: [0, 0.6], yfmt: f2, ylabel: "Training loss after 200 updates", label: "Learning rate effect",
    series: [{ name: "Loss", color: "var(--c1)", vals: [p["loss_epoch_200_eta_0.01"], p["loss_epoch_200_eta_0.1"], p["loss_epoch_200_eta_1.0"]] }], tipfmt: f4
  });
  var orv = [1, 2, 3, 4, 5, 6, 7].map(function (i) { return p["odds_ratio_X" + i]; });
  var odds = barChart({
    cats: ["X1", "X2", "X3", "X4", "X5", "X6", "X7"], yd: [0, 3], yfmt: f2, ylabel: "Odds ratio per +1 SD", ref: 1, refLabel: "1 = no effect", label: "Odds ratios",
    series: [{ name: "Odds ratio", color: "var(--c1)", vals: orv }], tipfmt: f4
  });
  var oddsNames = ["X1 months registered", "X2 missed visits", "X3 co-pay ratio", "X4 avg bill", "X5 adherence", "X6 chronic flag", "X7 insured flag"];
  var cmp = table(["Model (test rows)", "F1", "Recall", "Precision"], [
    ["Logistic, τ = 0.3", f4(p["tau_0.3_f1"]), f4(p["tau_0.3_recall"]), f4(p["tau_0.3_precision"])],
    ["Logistic, τ = 0.5", f4(p["tau_0.5_f1"]), f4(p["tau_0.5_recall"]), f4(p["tau_0.5_precision"])],
    ["KNN, K = " + p.knn_best_k, f4(p.knn_f1), f4(p.knn_recall), f4(p.knn_precision)]
  ]);
  var explorer = '<div class="card" style="margin-bottom:16px"><h3>Alert threshold and money</h3><p class="note">Slide the threshold: a lower τ flags more patients. Cost = false-alarm cost × false alarms + missed-no-show cost × misses. The capstone choice, τ = ' +
    f2(p.cost_tau) + ", was picked on the training rows with INR 50 and INR 400.</p>" +
    '<div class="controls"><div><label for="tau">Threshold τ: <b id="tauv">' + f2(p.cost_tau) + '</b></label><input id="tau" type="range" min="0" max="100" step="1" value="' + Math.round(p.cost_tau * 100) + '"></div>' +
    '<div><label for="fa">False-alarm call (INR)</label><input id="fa" type="number" min="0" max="100000" value="50"></div>' +
    '<div><label for="ms">Missed no-show (INR)</label><input id="ms" type="number" min="0" max="100000" value="400"></div></div>' +
    '<div class="readout" id="readout"></div><div id="costchart"></div></div>';
  return '<section id="part2"><h2>2 · Which patients will miss an appointment?</h2>' + explorer + '<div class="grid">' +
    card("ROC curve (test rows)", "Each point is one threshold τ; hover for its true- and false-positive rate.", roc,
      table(["τ", "TP", "FP", "TN", "FN", "TPR", "FPR"], D.thresholds.map(function (r) { return [f2(r.tau), r.tp, r.fp, r.tn, r.fn, f4(r.tpr), f4(r.fpr)]; }))) +
    card("Learning-rate effect", "A rate that is too small has barely learned after 200 updates.", lr, table(["η", "Loss"], [["0.01", f4(p["loss_epoch_200_eta_0.01"])], ["0.1", f4(p["loss_epoch_200_eta_0.1"])], ["1.0", f4(p["loss_epoch_200_eta_1.0"])]])) +
    card("Odds ratios", "Co-pay ratio (X3) is the strongest driver of no-shows.", odds, table(["Predictor", "Odds ratio"], oddsNames.map(function (n, i) { return [n, f4(orv[i])]; }))) +
    '<div class="card"><h3>Logistic vs nearest neighbours</h3><p class="note">Blind accuracy (never flag anyone) is ' + f4(p.blind_accuracy) + " vs " + f4(p["tau_0.5_accuracy"]) + " for the model at 0.5, so accuracy alone is a weak score.</p>" + cmp + "</div></div></section>";
}
function readout(c, fa, ms, tau, P) {
  var m = metr(c), tot = cost(c, fa, ms), nobody = ms * P;
  var items = [[inr(tot), "test cost at τ " + f2(tau)], [inr(nobody), "cost of flagging nobody"], [c.tp + c.fp + " flagged", c.tp + " real no-shows"], [f2(m.recall * 100) + "%", "recall (caught)"], [f2(m.precision * 100) + "%", "precision"], [c.fp + " / " + c.fn, "false alarms / misses"]];
  $("#readout").innerHTML = items.map(function (x) { return "<div><b>" + esc(x[0]) + "</b><span>" + esc(x[1]) + "</span></div>"; }).join("");
}
function drawExplorer() {
  var fa = Math.max(0, +$("#fa").value || 0), ms = Math.max(0, +$("#ms").value || 0), k = +$("#tau").value, tau = k / 100;
  $("#tauv").textContent = f2(tau);
  var te = D.sweep.map(function (r) { return [r.tau, cost(r.test, fa, ms)]; }), tr = D.sweep.map(function (r) { return [r.tau, cost(r.train, fa, ms)]; });
  var ymax = Math.max.apply(null, te.concat(tr).map(function (p) { return p[1]; })) * 1.05 || 1;
  var P = D.p2.test_positives, best = tr.reduce(function (a, b) { return b[1] < a[1] ? b : a; });
  var bk = Math.round(D.p2.cost_tau * 100);
  $("#costchart").innerHTML = lineChart({
    xd: [0, 1], yd: [0, ymax], xfmt: f2, yfmt: function (v) { return Math.round(v / 1000) + "k"; }, xlabel: "Threshold τ", ylabel: "Cost (INR)", label: "Cost against threshold", h: 280,
    series: [{ name: "Test rows", color: "var(--c1)", pts: te }, { name: "Training rows", color: "var(--c3)", pts: tr }],
    tip: function (pt) { return "τ " + f2(pt[0]) + ": " + inr(pt[1]); },
    markers: [{ x: tau, y: te[k][1], color: "var(--ink)", tip: "Selected τ " + f2(tau) + ": " + inr(te[k][1]) + " on test rows", label: "selected" },
      { x: D.sweep[bk].tau, y: te[bk][1], color: "var(--c2)", tip: "Capstone choice τ " + f2(D.p2.cost_tau) + " (picked on training rows)", label: "capstone τ" }]
  }) + '<p class="note">Cheapest τ on the training rows with these costs (0.01 steps): ' + f2(best[0]) + ".</p>";
  readout(cells(k).test, fa, ms, tau, P);
  if (LIVE) {
    fetch("api/threshold?tau=" + tau + "&false_alarm=" + fa + "&missed=" + ms).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      if (j && +$("#tau").value === k) readout(j.test, fa, ms, tau, P);
    }).catch(function () {});
  }
}

function part3() {
  var p = D.p3, S = D.segments, names = ["A · Steady regulars", "B · High-friction, high-bill", "C · New, high co-pay, low adherence"];
  var cardsHtml = S.map(function (s, i) {
    return '<div class="card seg" style="border-left-color:' + SEGC[i] + '"><h3>' + esc(names[i]) + '</h3><p class="note">' + s.size + " patients</p>" +
      table(["Metric", "Value"], [["No-show rate", f2(s.outcome_rate * 100) + "%"], ["Mean cost (INR k)", f2(s.mean_value)], ["Tenure (months)", f2(s.mean_X1)], ["Missed visits", f2(s.mean_X2)], ["Co-pay ratio", f2(s.mean_X3)], ["Adherence", f2(s.mean_X5)]]) + "</div>";
  }).join("");
  var rate = barChart({ cats: ["A", "B", "C"], yd: [0, 0.6], yfmt: function (v) { return Math.round(v * 100) + "%"; }, ylabel: "No-show rate", label: "No-show rate by segment", tipfmt: function (v) { return f2(v * 100) + "%"; },
    series: [{ name: "Rate", color: SEGC, vals: S.map(function (s) { return s.outcome_rate; }) }] });
  var wc = [2, 3, 4, 5, 6].map(function (k) { return [k, p["wcss_k" + k]]; });
  var elbow = lineChart({ xd: [2, 6], yd: [1000, 2400], xfmt: function (v) { return v; }, yfmt: function (v) { return v; }, xlabel: "Number of clusters K", ylabel: "Within-cluster sum of squares", label: "Elbow plot", h: 260,
    series: [{ name: "WCSS", color: "var(--c1)", pts: wc }], tip: function (pt) { return "K " + pt[0] + ": WCSS " + f2(pt[1]); },
    markers: [{ x: 3, y: p.wcss_k3, color: "var(--c2)", tip: "K = 3 used for segments (elbow rule picks " + p.elbow_k + ")", label: "K = 3" }] });
  var ev = [1, 2, 3, 4, 5].map(function (i) { return p["explained_ratio_" + i]; });
  var scree = barChart({ cats: ["PC1", "PC2", "PC3", "PC4", "PC5"], yd: [0, 0.6], yfmt: function (v) { return Math.round(v * 100) + "%"; }, ylabel: "Variance explained", label: "Scree plot", tipfmt: function (v) { return f2(v * 100) + "%"; },
    series: [{ name: "Explained", color: "var(--c1)", vals: ev }] });
  var ld = [1, 2, 3, 4, 5].map(function (i) { return p["pc1_loading_X" + i]; });
  var load = barChart({ cats: ["Tenure", "Missed", "Co-pay", "Bill", "Adhere"], yd: [-0.6, 0.6], yfmt: f2, ylabel: "PC1 loading", label: "PC1 loadings", tipfmt: f4,
    series: [{ name: "Loading", color: "var(--c1)", vals: ld }] });
  var linkages = ["single", "complete", "average"];
  var hier = table(["Linkage", "Merge", "Joined", "Height"], D.hier.map(function (r) { return [r.linkage, r.merge_no, r.cluster_a + " + " + r.cluster_b, f2(r.height)]; }));
  return '<section id="part3"><h2>3 · Patient segments and PCA</h2><div class="grid">' + cardsHtml + "</div>" +
    '<div class="grid" style="margin-top:16px">' +
    card("No-show rate by segment", "Segments are named by how patients use the service.", rate, table(["Segment", "Rate"], S.map(function (s) { return [s.segment, f4(s.outcome_rate)]; }))) +
    card("Elbow plot (K-means)", "Drops after K = 3 are small, so three segments are used.", elbow, table(["K", "WCSS"], wc.map(function (r) { return [r[0], f4(r[1])]; }))) +
    card("Variance explained by component", "Three components keep " + f2(p.cumulative_ratio_3 * 100) + "% of the variance.", scree, table(["Component", "Share", "Cumulative"], ev.map(function (v, i) { return ["PC" + (i + 1), f4(v), f4(p["cumulative_ratio_" + (i + 1)])]; }))) +
    card("What drives PC1", "A settled, adherent, low-friction axis.", load, table(["Predictor", "PC1 loading"], PRED.map(function (n, i) { return [n, f4(ld[i])]; }))) +
    '<div class="card"><h3>Cohort dendrogram (supplied table)</h3><p class="note">Clusters at the cut: single ' + p.single_clusters_at_cut + ", complete " + p.complete_clusters_at_cut + ", average " + p.average_clusters_at_cut + ".</p>" + hier + "</div></div></section>";
}

function part4() {
  var p = D.p4, V = D.voting;
  var gains = barChart({ cats: D.splits.map(function (r) { return r.split; }), yd: [0, 0.15], yfmt: f2, ylabel: "Information gain", label: "Information gain by split", tipfmt: f4,
    series: [{ name: "Gain", color: D.splits.map(function (r) { return r.split === p.best_split_by_info_gain ? "var(--c2)" : "var(--c1)"; }), vals: D.splits.map(function (r) { return r.info_gain; }) }] });
  var vote = barChart({ cats: V.map(function (r) { return r.model.replace("_", " "); }), yd: [0, 1], yfmt: f2, label: "Voting model scores", tipfmt: f4,
    series: [{ name: "Precision", color: "var(--c1)", vals: V.map(function (r) { return r.precision; }) }, { name: "Recall", color: "var(--c2)", vals: V.map(function (r) { return r.recall; }) }, { name: "F1", color: "var(--c3)", vals: V.map(function (r) { return r.f1; }) }] });
  var ada = table(["Round", "Point", "Weight before", "Unnormalised", "Weight after"], D.adaboost.map(function (r) { return [r.round, r.point, f4(r.weight_before), f4(r.weight_unnormalised), f4(r.weight_after)]; }));
  var arch = table(["Layer", "Parameters"], D.arch.map(function (r) { return [r.layer, r.parameters.toLocaleString("en-IN")]; }).concat([
    ["MLP total", p.mlp_total.toLocaleString("en-IN")], ["CNN total", p.cnn_total.toLocaleString("en-IN")], ["RNN total", p.rnn_total.toLocaleString("en-IN")],
    ["Dense 128×128×3 → 1024", p.fc_layer_params.toLocaleString("en-IN")], ["Conv 3×3×3, 64 filters", p.conv_layer_params.toLocaleString("en-IN")]]));
  return '<section id="part4"><h2>4 · Model choice and architecture sizing</h2><div class="grid">' +
    card("Best first question for the tree", "Months registered ≤ 24 (S4) separates no-shows best (gain " + f4(D.splits[3].info_gain) + ").", gains,
      table(["Split", "Yes: n", "Yes: positives", "No: n", "No: positives", "Info gain", "Gini gain"], D.splits.map(function (r) { return [r.split, r.n_yes, r.positives_yes, r.n_no, r.positives_no, f4(r.info_gain), f4(r.gini_gain)]; }))) +
    card("Single models vs voting (test rows)", "Combining models did not beat logistic regression.", vote,
      table(["Model", "TP", "FP", "TN", "FN", "Precision", "Recall", "F1"], V.map(function (r) { return [r.model, r.tp, r.fp, r.tn, r.fn, f4(r.precision), f4(r.recall), f4(r.f1)]; }))) +
    '<div class="card"><h3>AdaBoost by hand</h3><p class="note">Round 1 error ' + f4(p.round1_error) + ", alpha " + f4(p.round1_alpha) + "; round 2 error " + f4(p.round2_error) + ", alpha " + f4(p.round2_alpha) + ". Ensemble accuracy " + f4(p.ensemble_accuracy) + ".</p>" + ada + "</div>" +
    '<div class="card"><h3>Sizing later neural networks (nothing trained)</h3><p class="note">Parameter counts for scan routing (MLP or CNN) and referral-note sorting (RNN).</p>' + arch + "</div></div></section>";
}
function memo() {
  var html = D.memo.map(function (t) { return "<p>" + esc(t).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>") + "</p>"; }).join("");
  return '<section id="memo"><h2>Model-choice memo</h2><div class="card memo">' + html + "</div></section>";
}

/* ---------- boot ---------- */
function render() {
  $("#app").innerHTML = overview() + part1() + part2() + part3() + part4() + memo();
  drawScatter("raw");
  document.querySelectorAll("[data-scale]").forEach(function (b) {
    b.addEventListener("click", function () {
      document.querySelectorAll("[data-scale]").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
      drawScatter(b.dataset.scale);
    });
  });
  ["tau", "fa", "ms"].forEach(function (id) { $("#" + id).addEventListener("input", drawExplorer); });
  drawExplorer();
}
var tip = $("#tip");
function showTip(e) {
  var t = e.target.closest ? e.target.closest("[data-tip]") : null;
  if (!t) { tip.style.opacity = 0; return; }
  tip.textContent = t.getAttribute("data-tip");
  var x = e.clientX ? e.clientX + 14 : t.getBoundingClientRect().left, y = e.clientY ? e.clientY + 14 : t.getBoundingClientRect().top;
  tip.style.left = Math.min(x, window.innerWidth - 270) + "px"; tip.style.top = y + "px"; tip.style.opacity = 1;
}
document.addEventListener("mousemove", showTip);
document.addEventListener("focusin", showTip);
document.addEventListener("focusout", function () { tip.style.opacity = 0; });

function start(data, live) {
  D = data; LIVE = live;
  var b = $("#mode"); b.textContent = live ? "Live: served by Flask, threshold calculated on the server" : "Static: reading bundled data, no server"; b.className = "badge" + (live ? " live" : "");
  render();
}
fetch("api/health").then(function (r) { if (!r.ok) throw 0; return r.json(); })
  .then(function () { return fetch("api/data").then(function (r) { return r.json(); }); })
  .then(function (d) { start(d, true); })
  .catch(function () { start(window.__DATA__, false); });
})();

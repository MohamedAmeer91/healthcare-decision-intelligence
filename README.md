Domain: Healthcare

# PharmEasy Healthcare Decision Intelligence (capstone)

All data is synthetic, produced by `generate_data.py`. Nothing here is clinical advice. Only Python and NumPy are used; every graded number comes from code in this repository (`common.py` holds the shared helpers, `part1.py` to `part4.py` the Parts).

## How to run

From a clean clone, in this order:

```
pip install -r requirements.txt
python generate_data.py
python part1.py
python part2.py
python part3.py
python part4.py
```

`generate_data.py` prints `800 10 170 e26b46e82f1a1af44dcabc133050802e`. Each part script regenerates its files in `outputs/`.

## Part 1 findings

- **R1.1** H0 (mean care-plan cost = 8.0) is **rejected**: `z_stat` = 2.8930, which is beyond the critical value 1.96 (95% interval for the mean: 8.3026 to 9.5738). A Type I error here would mean concluding that the average care-plan cost differs from INR 8,000 when it truly equals INR 8,000. The gap `mean_value` - 8.0 = 0.9382 column units (about INR 938 per patient, `mean_value` = 8.9382). It is statistically clear; whether it matters depends on the budget, but about 12% above plan on every patient is likely material for a large base.
- **R1.2** `n_required` = 1293 records are needed to estimate the average within INR 500 at 95% confidence, against the 800 rows available. The current data are not enough for that precision: the present margin is about 1.96 x 0.3243 = INR 636, so the team needs roughly 500 more records (the cost column is very spread out, `sd_value` = 9.1723).
- **R1.3** `gd_slope_gap` = 0.0000. The cost function for a straight line is a single bowl-shaped (convex) surface, so with a small enough step size gradient descent walks to the same minimum the closed form computes directly.
- **R1.4** `resid_sd_ratio_raw` = 3.7525, `resid_sd_ratio_log` = 1.0396. The raw model shows a clear funnel: residual spread in the upper half of fitted values is almost four times that of the lower half. The log-log model removes it (ratio close to 1).
- **R1.5** Predictors in Task 1.7 with |coefficient| > 0.05: ln(X4) (1.1576), X2 `missed_visit_count_12m` (0.0940), X3 `copay_burden_ratio` (0.1067) and X6 `chronic_condition_flag` (0.1518). This is a mechanical rule on coefficients in different units, not a ranking of importance. `mr_adj_r2` = 0.7403 versus `loglog_adj_r2` = 0.6561, so the extra predictors do earn their place (about eight points more variance explained after the adjustment for the number of predictors).

## Part 2 findings

- **R2.1** After 200 updates the losses are 0.3703 (eta = 1.0) < 0.3776 (eta = 0.1) < 0.5091 (eta = 0.01). A rate that is too small has barely moved after 200 steps, while a large rate converges fastest here (it did not diverge on this standardised problem).
- **R2.2** The largest absolute weights are X3 `copay_burden_ratio` (0.9013), X1 `months_registered` (-0.5554) and X2 `missed_visit_count_12m` (0.5505). The largest odds ratio is X3 at 2.4629: each one-SD rise in the share of the bill a patient pays out of pocket multiplies the odds of a no-show by about 2.5, other things fixed.
- **R2.3** `blind_accuracy` = 0.7875 versus 0.8042 at tau = 0.5, so a model that never flags anyone is almost as accurate, which is why accuracy alone is weak when only about one in five records is a no-show. Lowering tau from 0.5 to 0.3 raised recall from 0.4706 to 0.7451 (tp 24 to 38) and lowered precision from 0.5455 to 0.4634 (fp 20 to 44).
- **R2.4** At tau = 0.3 logistic regression has `f1` = 0.5714 and recall 0.7451; KNN (K = 5) has `f1` = 0.3696 and recall 0.3333. Logistic regression is clearly better on both.
- **R2.5** I would deploy logistic regression at tau = 0.15 (`cost_tau`). On the test rows it costs INR 6,050 (`cost_test_at_tau`), against INR 11,800 at tau = 0.5 (`cost_test_at_0.5`) and INR 20,400 for flagging nobody (`cost_test_flag_nobody`). The threshold was chosen on training rows so that the test rows stay an honest, untouched check of the choice.

## Part 3 findings

- **R3.1** WCSS drops: WCSS(2) - WCSS(3) = 659.8282, WCSS(3) - WCSS(4) = 108.0739, WCSS(4) - WCSS(5) = 171.0575, WCSS(5) - WCSS(6) = 45.5466. The elbow rule gives `elbow_k` = 3: the drop after K = 3 (108.07) is below half the drop into K = 3 (659.83 x 0.5 = 329.91). The drops do not shrink steadily (171.06 after 108.07), because the pinned starting rows give one reproducible solution, not necessarily the global optimum.
- **R3.2** Segments (named by service usage):
  - **A, "Steady regulars"** (322 patients; tenure 47.5 months, 1.95 missed visits, copay 0.225, `outcome_rate` 0.0186, mean cost 3.60 thousand): keep a light touch, with ordinary automated reminders and no calls.
  - **B, "High-friction, high-bill"** (255; 28.6 months, 6.07 missed visits, average bill 28.7 thousand, `outcome_rate` 0.2353, mean cost 17.12 thousand): offer a rebooking or care-plan review conversation, since they miss many visits and carry the highest costs.
  - **C, "New, high co-pay, low adherence"** (223; 14.4 months, copay 0.712, adherence 38.5, `outcome_rate` 0.4664, mean cost 7.29 thousand): this is the segment with the highest `outcome_rate` (0.4664); call or message them before every slot and explain co-pay options.
- **R3.3** Single linkage cuts at 4 clusters: {E1}, {E4}, {E5}, {E2, E3, E6}. Complete linkage cuts at 2 clusters: {E1, E4, E5} and {E2, E3, E6}. Single linkage merges two clusters as soon as any one pair is close, so it chains E2 onto E3+E6 at 1.4 and its heights stay compressed (1.3 to 3.4), putting the largest gap early. Complete linkage needs every pair to be close, so the two tight groups stay apart until the final merge at 7.9 and the largest gap is the last one.
- **R3.4** The mean vector after standardising is all zeros (to rounding). PC1 is driven by months registered (+0.5317) and adherence (+0.4418) pulling one way against copay ratio (-0.5187), missed visits (-0.4100) and average bill (-0.2916): a "settled, adherent, low-friction" axis. `components_for_80pct` = 3 (two components keep 0.7593, three keep 0.8616). `mean_pc1_segment_A/B/C` = 1.7773 / -0.7831 / -1.6709, so PC1 orders the segments cleanly from A to C and matches their no-show rates.

## Part 4 findings

- **R4.1** S4 (months registered <= 24) is the best split by both information gain (0.1252) and Gini gain (0.0606): it separates 188 rows with 45.7% no-shows from 372 rows with 8.9%, a bigger drop in impurity than the other three. A tree grown until every leaf is pure would memorise noise in the 560 training rows and generalise poorly. A maximum depth, or a minimum number of records per leaf, stops it growing too deep.
- **R4.2** I would ship logistic regression (`f1` 0.5714, recall 0.7451 at tau = 0.3). Combining did not help: hard vote has `f1` 0.5344 and recall 0.6863, soft vote 0.5507 and 0.7451, the stump 0.5532 and 0.7647, and KNN 0.3696 and 0.3333. The weak KNN drags the ensembles below the best single model.
- **R4.3** After round 1 normalisation the two misclassified points (3 and 7) carry a total weight of 0.5000 (0.25 each). Round 2 trusts h2 more because its weighted error is lower (0.1667 against 0.2500), which gives it the larger alpha (0.8047 against 0.5493).
- **R4.4** Model A option 2 (total `cnn_total` = 15734 parameters; the fully connected option has `mlp_total` = 13002):

  | Layer | Output shape (H x W x D) | Parameters |
  |---|---|---|
  | conv 5x5, 6 filters, pad 2 | 28 x 28 x 6 | 156 |
  | ReLU + max-pool 2x2 | 14 x 14 x 6 | 0 |
  | conv 5x5, 16 filters | 10 x 10 x 16 | 2416 |
  | ReLU + max-pool 2x2 | 5 x 5 x 16 | 0 |
  | flatten | 400 | 0 |
  | dense 32 + ReLU | 32 | 12832 |
  | dense 10 (output) | 10 | 330 |

  Model B: W_xh is 128 x 64, W_hh is 128 x 128 and W_hy is 16 x 128, giving `rnn_total` = 26768; it does not grow with longer sequences because the same weights are reused at every time step. For 10 classes I would use ReLU in the hidden layers and softmax at the output with categorical cross-entropy loss. In a very deep plain network, backpropagation multiplies many derivatives smaller than 1, so the gradient reaching the early layers shrinks towards zero and they stop learning. A skip connection adds the input straight to the layer's output, giving the gradient a direct path back that is not shrunk by those multiplications.

## Model-choice memo

To: Head of Scheduling Operations

**Recommendation: deploy the logistic-regression model with an alert threshold of 0.15.**

On 240 held-out records, logistic regression at 0.3 reaches F1 0.5714 and recall 0.7451 (`part4_voting.csv`), against F1 0.3696 and recall 0.3333 for nearest neighbours. Hard and soft voting (F1 0.5344 and 0.5507) did not beat it, so combining models adds complexity without gain.

The threshold was chosen on training data with the cost rule INR 50 per unnecessary reminder call and INR 400 per missed no-show. At 0.15 the cost on the test records is INR 6,050 (`part2_results.txt`). The default 0.5 would cost INR 11,800, and flagging nobody would cost INR 20,400. This is the logistic model's cost; I did not cost the other models.

The strongest signal is the share of the bill the patient pays: each one-SD rise multiplies no-show odds by about 2.5.

**Risk:** the test set holds only 51 no-shows from one split, and the data is synthetic, so the cost saving may not carry over to real operations; recheck on live data first.

Neither Model A (scan routing) nor Model B (referral-note sorting) is worth building before the structured model is in production.

## Limitations

- The data is synthetic and generated from known formulas, so the findings say nothing about real PharmEasy patients or costs.
- A single 70/30 split is used; the test set has only 51 positive records, so metrics such as recall move by about two points per record and the chosen threshold and K are valid for this split only.
- The cost figures use two assumed unit costs (INR 50 and INR 400) and ignore other effects, such as patient annoyance or overbooking; the chosen threshold is sensitive to their ratio.
- K-means uses pinned starting rows and may not reach the global optimum, and the 6-cohort dendrogram is built from a supplied table, not from the patient data.
- Models A and B are only sized as parameter counts; nothing was trained, so their accuracy is unknown.

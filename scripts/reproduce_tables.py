"""Reproduce the main results of the ErgoSight paper from the released questions and replies.

Usage:  python scripts/reproduce_tables.py
Writes one CSV per result to results/ and prints the headline numbers.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ergosight import load_questions, load_answers, accuracy, bootstrap_ci, signal_detection, swap_consistency, MODELS, CRITERIA, LEVELS, DISPLAYS
from ergosight.io import own_question_set

OUT = ROOT / 'results'
OUT.mkdir(exist_ok=True)
NAMES = pd.read_csv(ROOT / 'data' / 'models.csv').set_index('tag').name.to_dict()
q = load_questions()
a = load_answers(questions=q)
a = a.merge(q.drop(columns=['answer', 'n_options']), on='qid', how='left')
s0 = a[a.setting == 'S0']
core = s0[s0.core_subset]


def save(df, name):
    df.to_csv(OUT / f'{name}.csv', float_format='%.1f')
    print(f'\n== {name}\n{df.round(1).to_string()}')


# 1 overall accuracy of every model on the 891 core questions in S0, with the 95% bootstrap interval
rows = {}
rng = np.random.default_rng(0)
for m in MODELS:
    v = core[core.model == m].correct.values
    lo, hi = bootstrap_ci(v, rng=rng)
    rows[NAMES[m]] = {'accuracy': accuracy(v), 'ci_low': lo, 'ci_high': hi, 'questions': len(v)}
chance = (100 / q[q.core_subset].n_options).mean()
save(pd.DataFrame(rows).T.assign(chance=chance), 'overall_core_s0')

# 2 accuracy per criterion on the generated questions of the core subset in S0 (Table 8 of the paper)
gen = core[core.source_type == 'generated']
t = pd.DataFrame({NAMES[m]: [accuracy(gen[(gen.model == m) & (gen.criterion == c)].correct) for c in CRITERIA] + [accuracy(gen[gen.model == m].correct)] for m in MODELS},
                 index=CRITERIA + ['All']).T
qs = q[q.core_subset & (q.source_type == 'generated')]
t.loc['Chance'] = [(100 / qs[qs.criterion == c].n_options).mean() for c in CRITERIA] + [(100 / qs.n_options).mean()]
save(t, 'table8_accuracy_by_criterion')

# 3 accuracy per display condition and task level on the generated core questions (Table S4 of the supplement)
t = pd.DataFrame({NAMES[m]: [accuracy(gen[(gen.model == m) & (gen.display == d)].correct) for d in DISPLAYS] + [accuracy(gen[(gen.model == m) & (gen.level == l)].correct) for l in LEVELS] for m in MODELS},
                 index=DISPLAYS + LEVELS).T
save(t, 'display_and_level')

# 4 real against generated pages, each model on its evaluation set in S0
rows = {}
for m in MODELS:
    x = own_question_set(s0[s0.model == m], m)
    rows[NAMES[m]] = {'generated': accuracy(x[x.source_type == 'generated'].correct), 'real': accuracy(x[x.source_type == 'real'].correct),
                      'real_questions': int((x.source_type == 'real').sum())}
save(pd.DataFrame(rows).T, 'real_vs_generated')

# 5 S0, S1 and S2 on the core subset for the four models evaluated with the PMO values, and the S1 gain on each own set
rows = {}
for m in MODELS:
    r = {}
    for s in ('S0', 'S1', 'S2'):
        x = a[(a.model == m) & (a.setting == s) & a.core_subset]
        r[f'{s}_core'] = accuracy(x.correct) if len(x) else np.nan
    r['S1_gain'] = r['S1_core'] - r['S0_core']
    r['S2_gain'] = r['S2_core'] - r['S0_core']
    rows[NAMES[m]] = r
save(pd.DataFrame(rows).T, 'settings_s0_s1_s2')

# 6 ablation of the PVL views for the three small models on the extended subset (Table 12 of the paper)
small = ['qwen35_9b', 'qwen3vl8b', 'internvl35']
t = {}
for s in ('S0', 'S1', 'S1-noSim', 'S1-noRuler', 'S1-noLoupe'):
    x = a[(a.setting == s) & a.extended_subset & a.model.isin(small)]
    t[s] = [accuracy(x[x.model == m].correct) for m in small] + [accuracy(x.correct)]
save(pd.DataFrame(t, index=[NAMES[m] for m in small] + ['Three small models']), 'pvl_view_ablation')

# 7 direction of the errors on generated interfaces in S0 (Table 13 of the paper): detection by signal detection theory on L1,
#   estimation by the signed error in range steps on L4, each model on its evaluation set
rows = {}
for m in MODELS:
    x = own_question_set(s0[(s0.model == m) & (s0.source_type == 'generated')], m)
    l1 = x[x.level == 'L1']
    h, f, dp, c = signal_detection(l1.answer == 'B', l1.pred == 'B')
    l4 = x[(x.level == 'L4') & x.pred.isin(list('ABC'))]
    err = l4.pred.map({'A': 0, 'B': 1, 'C': 2}) - l4.answer.map({'A': 0, 'B': 1, 'C': 2})
    rows[NAMES[m]] = {'L1_questions': len(l1), 'hit_rate': h, 'false_alarm_rate': f, 'd_prime': dp, 'criterion_c': c,
                      'L4_questions': len(l4), 'signed_error': err.mean(), 'over': (err > 0).mean() * 100, 'under': (err < 0).mean() * 100}
t = pd.DataFrame(rows).T
t.to_csv(OUT / 'error_direction.csv', float_format='%.2f'); print(f'\n== error_direction\n{t.round(2).to_string()}')

# 8 consistency on the position-swapped L3 pairs and the share of L3 answers that pick option B
pairs = [(r.qid, r.twin_of) for r in q.itertuples() if r.twin_of]
rows = {}
for m in MODELS:
    x = s0[s0.model == m]
    l3 = x[x.level == 'L3']
    rows[NAMES[m]] = {'swap_consistency': swap_consistency(dict(zip(x.qid, x.correct)), pairs), 'L3_share_of_B': accuracy(l3.pred == 'B')}
save(pd.DataFrame(rows).T, 'robustness')
print('\nAll results written to', OUT)

"""Reproduce the additional analyses of the revised ErgoSight paper from the released questions and replies.

Usage:  python scripts/reproduce_revision.py
Writes one CSV per analysis to results/ (prefix revision_) and prints the numbers quoted in the paper.
"""
import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ergosight import load_questions, load_answers, accuracy, bootstrap_ci, cluster_bootstrap_ci, holm, mcnemar_exact, MODELS
from ergosight.io import own_question_set

OUT = ROOT / 'results'
OUT.mkdir(exist_ok=True)
NAMES = pd.read_csv(ROOT / 'data' / 'models.csv').set_index('tag').name.to_dict()
PROPRIETARY = ['sonnet55', 'gemini38', 'gpt54mini', 'haiku55']
S2_MODELS = ['haiku55', 'qwen35_9b', 'qwen3vl8b', 'internvl35']
q = load_questions()
a = load_answers(questions=q)
a = a.merge(q.drop(columns=['answer', 'n_options']), on='qid', how='left')
views = {r.qid: tuple(sorted(set(r.inputs.get('S1', [])) - {'s0'})) for r in q.itertuples()}
a['views'] = a.qid.map(views)
P = {s: a[a.setting == s].pivot_table(index='qid', columns='model', values='correct') for s in ('S0', 'S1', 'S2')}
core_ids = q[q.core_subset].qid


def save(df, name):
    df.to_csv(OUT / f'revision_{name}.csv', float_format='%.3f')
    print(f'\n== {name}\n{df.round(3).to_string()}')


# 1 errors fixed and broken by the measured values (S2 against S0) on the core subset, the four models evaluated in S2
p0, p2 = P['S0'].loc[core_ids, S2_MODELS], P['S2'].loc[core_ids, S2_MODELS]
err, fixed, broken = int((p0 == 0).sum().sum()), int(((p0 == 0) & (p2 == 1)).sum().sum()), int(((p0 == 1) & (p2 == 0)).sum().sum())
save(pd.DataFrame({'S0 errors': [err], 'fixed': [fixed], 'broken': [broken], 'fix rate %': [fixed / err * 100], 'net reduction %': [(fixed - broken) / err * 100],
                   'S0 accuracy %': [p0.mean().mean() * 100], 'S1 accuracy %': [P['S1'].loc[core_ids, S2_MODELS].mean().mean() * 100], 'S2 accuracy %': [p2.mean().mean() * 100]}), 's2_fixed_and_net')

# 2 question-level and page-level (cluster) bootstrap intervals on the core subset in S0
c = a[(a.setting == 'S0') & a.qid.isin(core_ids)]
rows = {}
rng_q, rng_p = np.random.default_rng(0), np.random.default_rng(0)
for m in MODELS:
    x = c[c.model == m]                     # same rows and generator as Table 15 of the paper (scripts/reproduce_tables.py)
    rows[NAMES[m]] = dict(zip(['question low', 'question high'], bootstrap_ci(x.correct.values, rng=rng_q)))
    rows[NAMES[m]].update(zip(['page low', 'page high'], cluster_bootstrap_ci(x.correct.values, x.page_id.values, rng=rng_p)))
ci = pd.DataFrame(rows).T
save(ci, 'bootstrap_question_vs_page')
print('largest change of an interval end: %.1f points' % (ci[['question low', 'question high']].values - ci[['page low', 'page high']].values).__abs__().max())
print('proprietary lower bounds above every open-source upper bound (page level):',
      ci.loc[[NAMES[m] for m in PROPRIETARY], 'page low'].min() > ci.loc[[NAMES[m] for m in MODELS if m not in PROPRIETARY], 'page high'].max())

# 3 exact McNemar tests of all 28 pairs of models on the core subset in S0, with Holm's correction
pairs, ps = [], []
for i, m1 in enumerate(MODELS):
    for m2 in MODELS[i + 1:]:
        pairs.append((NAMES[m1], NAMES[m2], (m1 in PROPRIETARY) != (m2 in PROPRIETARY))); ps.append(mcnemar_exact(P['S0'].loc[core_ids, m1], P['S0'].loc[core_ids, m2]))
t = pd.DataFrame(pairs, columns=['model 1', 'model 2', 'proprietary vs open']).assign(p=ps, p_holm=holm(ps))
save(t, 'pairwise_holm')
print('significant after Holm: %d of %d, proprietary vs open-source: %d of %d' % ((t.p_holm < 0.05).sum(), len(t), (t[t['proprietary vs open']].p_holm < 0.05).sum(), t['proprietary vs open'].sum()))

# 4 real against generated pages on the core subset that all eight models answer
rows = {NAMES[m]: {'generated': accuracy(c[(c.model == m) & (c.source_type == 'generated')].correct), 'real': accuracy(c[(c.model == m) & (c.source_type == 'real')].correct)} for m in MODELS}
rv = pd.DataFrame(rows).T
save(rv, 'real_vs_generated_core')
print('real questions in the core subset: %d, rank correlation %.3f' % (q[q.core_subset & (q.source_type == 'real')].shape[0], rv.generated.rank().corr(rv.real.rank())))

# 5 answers changed by S1 on questions with and without a view (each model on its own S1 question set)
rows = {}
for m in MODELS:
    x0 = own_question_set(a[(a.model == m) & (a.setting == 'S0')], m).set_index('qid'); x1 = a[(a.model == m) & (a.setting == 'S1')].set_index('qid')
    ids = x0.index.intersection(x1.index); nv = [i for i in ids if views[i] == ()]; wv = [i for i in ids if views[i] != ()]
    rows[NAMES[m]] = {'changed with a view %': (x0.loc[wv, 'pred'] != x1.loc[wv, 'pred']).mean() * 100,
                      'changed without a view %': (x0.loc[nv, 'pred'] != x1.loc[nv, 'pred']).mean() * 100, 'questions without a view': len(nv)}
save(pd.DataFrame(rows).T, 'view_vs_noview_changes')

# 6 gain of S1 by type of view on the core subset
rows = {}
kinds = {'crop only': lambda v: v == ('loupe',), 'with a viewer simulation': lambda v: 'sim' in v, 'scale reference only': lambda v: v == ('ruler',)}
for k, f in kinds.items():
    ids = [i for i in core_ids if f(views[i])]
    rows[k] = {NAMES[m]: (P['S1'].loc[ids, m].mean() - P['S0'].loc[ids, m].mean()) * 100 for m in MODELS} | {'questions': len(ids)}
g = pd.DataFrame(rows).T
save(g, 'gain_by_view_type')
print('crop only, mean over the eight models: %.1f points' % g.loc['crop only', [NAMES[m] for m in MODELS]].mean())

# 7 sensitivity of the visual angle labels to the cap-height ratio: kappa 0.70 -> 0.72, with the threshold that applies to each question
k = 0.72 / 0.70; certain = ambiguous = n = 0
for r in q[(q.criterion == 'VA') & (q.level == 'L1')].itertuples():
    if r.measured_value is None or pd.isna(r.measured_value):
        continue
    v = float(r.measured_value); meets = r.options['ABCD'.index(r.answer)].lower().startswith('yes'); n += 1
    if 16 <= v < 20 and not meets and v * k >= 20: certain += 1          # threshold 20 arcmin follows from the label
    if 16 / k <= v < 16 and not meets: ambiguous += 1                     # changes only if the text is not critical (threshold 16)
save(pd.DataFrame({'questions': [n], 'certain changes': [certain], 'possible changes': [ambiguous], 'lower bound %': [certain / n * 100], 'upper bound %': [(certain + ambiguous) / n * 100]}), 'kappa_sensitivity')

# 8 misses and false alarms on the detection questions of the generated interfaces in S0 (each model on its own question set)
rows = {}
for m in MODELS:
    x = own_question_set(a[(a.model == m) & (a.setting == 'S0') & (a.level == 'L1') & (a.source_type == 'generated')], m)
    txt = lambda r, letter: r.options['ABCD'.index(letter)].lower() if isinstance(letter, str) and letter in 'ABCD' and 'ABCD'.index(letter) < len(r.options) else ''
    truth_meets = np.array([txt(r, r.answer).startswith('yes') for r in x.itertuples()]); said_meets = np.array([txt(r, r.pred).startswith('yes') for r in x.itertuples()])
    answered = x.pred.isin(list('ABCD')).values
    rows[NAMES[m]] = {'misses': int((~truth_meets & said_meets).sum()), 'false alarms': int((truth_meets & ~said_meets & answered).sum())}
t = pd.DataFrame(rows).T
save(t, 'misses_false_alarms')
print('models with more misses than false alarms: %d of 8' % (t.misses > t['false alarms']).sum())

# 9 output length of Qwen3.5-397B-A17B in S0 and S1, with and without a view
x = a[a.model == 'qwen35']; x0 = x[x.setting == 'S0'].set_index('qid'); x1 = x[x.setting == 'S1'].set_index('qid')
wv = [i for i in x1.index if views[i] != ()]; nv = [i for i in x1.index if views[i] == ()]
save(pd.DataFrame({'median output tokens S0': [x0.tokens_out.median()], 'median output tokens S1 with a view': [x1.loc[wv].tokens_out.median()],
                   'median output tokens S1 without a view': [x1.loc[nv].tokens_out.median()], 'S1 replies with an explanation %': [(x1.loc[wv].reply.astype(str).str.len() > 40).mean() * 100],
                   'questions without a view': [len(nv)], 'identical answers without a view': [int((x1.loc[nv].pred == x0.loc[nv].pred).sum())]}), 'qwen35_output_length')

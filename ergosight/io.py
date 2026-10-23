"""Loading ErgoSight-Bench questions and the recorded MLLM replies."""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODELS = ['sonnet55', 'gemini38', 'gpt54mini', 'haiku55', 'qwen35', 'qwen35_9b', 'qwen3vl8b', 'internvl35']
CRITERIA = ['TC', 'NC', 'VA', 'TS', 'RF', 'TI', 'CV', 'AC']
LEVELS = ['L1', 'L2', 'L3', 'L4']
DISPLAYS = ['D1', 'D2', 'D3', 'D4', 'D5', 'D6']
# question set of each model in the paper: core = 891 questions, extended = 1,781 questions, full = 4,275 questions
QUESTION_SET = {'sonnet55': 'core', 'gemini38': 'extended', 'gpt54mini': 'extended', 'qwen35': 'extended',
                'haiku55': 'full', 'qwen35_9b': 'full', 'qwen3vl8b': 'full', 'internvl35': 'full'}


def load_questions(path=None) -> pd.DataFrame:
    """One row per question with its criterion, level, display condition, options, label, measured value and subsets."""
    path = Path(path) if path else ROOT / 'data' / 'questions.jsonl'
    rows = [json.loads(line) for line in path.open(encoding='utf-8')]
    q = pd.DataFrame(rows)
    q['n_options'] = q.options.map(len)
    return q


def load_answers(path=None, questions=None) -> pd.DataFrame:
    """One row per request (model, setting, question) with the raw reply, the parsed answer and its correctness."""
    from .parse import parse_reply
    path = Path(path) if path else ROOT / 'data' / 'answers.csv.gz'
    a = pd.read_csv(path)
    q = questions if questions is not None else load_questions()
    a = a.merge(q[['qid', 'answer', 'n_options']], on='qid', how='left')
    a['pred'] = [parse_reply(r, n) for r, n in zip(a.reply, a.n_options)]
    a['correct'] = (a.pred == a.answer).astype(int)
    return a


def own_question_set(df: pd.DataFrame, model: str) -> pd.DataFrame:
    """Rows of df restricted to the question set on which the paper evaluates the model."""
    s = QUESTION_SET[model]
    if s == 'core':
        return df[df.core_subset]
    if s == 'extended':
        return df[df.extended_subset]
    return df


def image_paths(qid: str, setting: str = 'S0', questions: pd.DataFrame = None, root=None) -> list:
    """Paths of the images that a question shows in a setting, after ErgoSight-Bench.zip is unpacked into data/.

    S0 and S2 show the screenshot (s0.jpg); S1 adds the views of the Physical View Lens (loupe.jpg, ruler.jpg, sim.jpg).
    """
    q = questions if questions is not None else load_questions()
    inputs = q.set_index('qid').loc[qid, 'inputs'][setting]
    root = Path(root) if root else ROOT / 'data' / 'images'
    return [root / qid / f'{name}.jpg' for name in inputs]


def page_path(page_id: str, root=None) -> Path:
    """Path of the HTML file of an interface, after ErgoSight-Bench.zip is unpacked into data/."""
    root = Path(root) if root else ROOT / 'data' / 'pages'
    return root / f'{page_id}.html'

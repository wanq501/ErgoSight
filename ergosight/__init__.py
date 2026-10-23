"""ErgoSight evaluation toolkit: loading ErgoSight-Bench, reading MLLM answers, and computing the metrics of the paper."""
from .io import load_questions, load_answers, image_paths, page_path, MODELS, CRITERIA, LEVELS, DISPLAYS
from .parse import parse_reply
from .metrics import accuracy, bootstrap_ci, cluster_bootstrap_ci, holm, mcnemar_exact, signal_detection, swap_consistency

__all__ = ['load_questions', 'load_answers', 'image_paths', 'page_path', 'parse_reply', 'accuracy', 'bootstrap_ci', 'cluster_bootstrap_ci', 'holm', 'mcnemar_exact', 'signal_detection', 'swap_consistency',
           'MODELS', 'CRITERIA', 'LEVELS', 'DISPLAYS']

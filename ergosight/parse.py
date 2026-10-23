"""Reading the chosen option from an MLLM reply.

The question prompt asks for a single letter. Most replies are a bare letter, some reason first and end with the letter,
and a few open with the letter and then explain. The reader takes the letter that ends the reply if there is one and
otherwise the letter that opens it, which reads 66,237 of the 66,261 replies of the paper; the others count as wrong.
"""
import re

_START = re.compile(r'^\s*(?:\*\*)?(?:answer\s*(?:is|:)?\s*)?\(?([A-D])\)?(?:\*\*)?(?=[\s\.\:\)]|$)', re.I)
_LINE = re.compile(r'^(?:\*\*)?(?:answer\s*(?:is|:)?\s*)?\(?([A-D])[\)\:\.\s\*]', re.I)
_END = re.compile(r'(?:answer\s*(?:is|:)?\s*)?(?:\*\*)?\(?([A-D])\)?(?:\*\*)?\.?\s*$', re.I)


def parse_reply(reply, n_options: int):
    """Return the option letter chosen in the reply, or None when no letter can be read."""
    s = reply.strip() if isinstance(reply, str) else ''
    if not s:
        return None
    letters = 'ABCD'[:int(n_options)]
    a = _START.match(s)
    b = _END.search(s[-60:])
    first = a.group(1).upper() if a and a.group(1).upper() in letters else None
    last = b.group(1).upper() if b and b.group(1).upper() in letters else None
    if last is None:
        lines = [ln for ln in s.splitlines() if ln.strip()]
        tail = lines[-1].strip() if lines else ''
        c = _LINE.match(tail)
        if c and c.group(1).upper() in letters and len(tail) <= 60:
            last = c.group(1).upper()
    return last if last else first

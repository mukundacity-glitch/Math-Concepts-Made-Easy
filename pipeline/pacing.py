"""Pacing and construction helpers — the engine behind "always building".

Cell 4 draws the pictures; this module decides *what* can be built and
*when* something has to happen. It is deliberately free of any Manim
import so the whole thing is unit-testable without a renderer.

Everything here derives from the lesson's own data (its board lines, its
formula, its narration). Nothing knows which lesson is playing — a
fraction found in Day 3's board drives the long-division animation the
same way a power found in Day 4's board drives the expansion animation.

Four groups of helpers:

  timing      fill_times()          — when an idle screen needs a beat
  construction split_latex_parts()  — how to build a formula piece by piece
  arithmetic  long_division(), prime_factorization(), factor_tree(),
              expand_power(), is_terminating()
  selection   find_fractions(), find_powers(), contrast_fractions(),
              emphasis_words(), lesson_vocabulary()
"""

import math
import re

# ── timing ───────────────────────────────────────────────────────────


def fill_times(t0, t1, max_gap):
    """Evenly spaced moments where an ambient beat must fire.

    A scene that narrates from t0 to t1 with nothing scheduled in between
    would leave the screen still. Returns the timestamps at which
    something — a camera drift, a highlight, a progress tick — has to
    happen so no still stretch is ever longer than `max_gap`.

    >>> fill_times(0.0, 10.0, 4.0)
    [3.333, 6.667]
    >>> fill_times(0.0, 3.0, 4.0)
    []
    """
    span = float(t1) - float(t0)
    if span <= max_gap or max_gap <= 0:
        return []
    count = math.ceil(span / max_gap) - 1
    step = span / (count + 1)
    return [round(t0 + step * (i + 1), 3) for i in range(count)]


# ── construction: splitting a formula into buildable pieces ──────────

_OPENERS = "{(["
_CLOSERS = "})]"

# Longest first — "\\Rightarrow" must win over "\\r..." style prefixes.
_SEPARATORS = [
    r"\Longrightarrow", r"\Rightarrow", r"\rightarrow", r"\implies",
    r"\iff", r"\quad", r"\qquad", r"\cdot", r"\times", r"\div",
    r"\neq", r"\leq", r"\geq", r"\le", r"\ge", r"\pm",
    "=", "+", ",", ";",
]


def split_latex_parts(latex, min_parts=2):
    """Split a LaTeX expression at its top-level joins.

    The pieces concatenate back to the original, so `MathTex(*parts)`
    lays the formula out exactly as `MathTex(whole)` would — but each
    piece is its own submobject and can be written on its own beat.
    That is what turns "the formula appears" into "the formula is built".

    >>> split_latex_parts(r"a^m \\cdot a^n = a^{m+n}")
    ['a^m ', '\\\\cdot', ' a^n ', '=', ' a^{m+n}']

    Splits never happen inside braces or brackets, so `a^{m+n}` and
    `\\frac{p}{q}` survive intact. Returns `[latex]` unchanged when the
    expression has fewer than `min_parts` natural joins.
    """
    text = str(latex or "")
    if not text.strip():
        return [text]

    parts, buf, depth, i, n = [], [], 0, 0, len(text)
    while i < n:
        ch = text[i]
        if ch in _OPENERS:
            depth += 1
            buf.append(ch)
            i += 1
            continue
        if ch in _CLOSERS:
            depth = max(0, depth - 1)
            buf.append(ch)
            i += 1
            continue
        if ch == "\\" and i + 1 < n and not text[i + 1].isalpha():
            # escaped punctuation such as "\," or "\ " — never a split
            buf.append(text[i:i + 2])
            i += 2
            continue

        sep = _match_separator(text, i) if depth == 0 else None
        if sep and not _is_unary_sign(text, i):
            parts.append("".join(buf))
            parts.append(sep)
            buf = []
            i += len(sep)
            continue

        buf.append(ch)
        i += 1
    parts.append("".join(buf))

    parts = _merge_stray_parts(parts)
    if len(parts) < min_parts:
        return [text]
    return parts


def _match_separator(text, i):
    for sep in _SEPARATORS:
        if not text.startswith(sep, i):
            continue
        # A control word must not be a prefix of a longer one (\le vs \leq)
        if sep[0] == "\\" and sep[-1].isalpha():
            nxt = i + len(sep)
            if nxt < len(text) and text[nxt].isalpha():
                continue
        return sep
    return None


def _is_unary_sign(text, i):
    """True for a leading '+'/'-' that is a sign, not a join."""
    if text[i] not in "+-":
        return False
    before = text[:i].strip()
    return not before or before[-1] in "=+-(,"


def _merge_stray_parts(parts):
    """Drop empty pieces and glue orphan spacing onto its neighbour."""
    cleaned = []
    for part in parts:
        if not part:
            continue
        if not part.strip() or part.strip() in ("\\", "\\ "):
            if cleaned:
                cleaned[-1] = cleaned[-1] + part
            elif len(parts) > 1:
                continue
            else:
                cleaned.append(part)
            continue
        cleaned.append(part)
    return cleaned


# ── arithmetic the animations are built from ─────────────────────────


def long_division(p, q, max_digits=10):
    """Divide p by q the way it is done on a board, digit by digit.

    Returns the running strings a student would write ("0.", "0.1",
    "0.12", "0.125") so the decimal can appear one digit at a time
    instead of landing fully formed, plus whether the expansion
    terminates and where it starts repeating if it does not.

    >>> r = long_division(1, 8)
    >>> r["steps"]
    ['0.', '0.1', '0.12', '0.125']
    >>> r["terminating"], r["repeat_start"]
    (True, None)
    >>> long_division(1, 3)["repeat_start"]
    0
    """
    try:
        p, q = int(p), int(q)
    except (TypeError, ValueError):
        return None
    if q == 0:
        return None

    sign = "-" if (p < 0) ^ (q < 0) and p != 0 else ""
    p, q = abs(p), abs(q)
    whole, rem = divmod(p, q)

    digits, seen, repeat_start = [], {}, None
    while rem and len(digits) < max_digits:
        if rem in seen:
            repeat_start = seen[rem]
            break
        seen[rem] = len(digits)
        rem *= 10
        digits.append(str(rem // q))
        rem %= q

    terminating = rem == 0 and repeat_start is None
    truncated = repeat_start is None and rem != 0

    head = f"{sign}{whole}."
    steps = [head]
    for d in digits:
        steps.append(steps[-1] + d)

    if repeat_start is not None:
        head_digits = "".join(digits[:repeat_start])
        cycle = "".join(digits[repeat_start:])
        display = f"{sign}{whole}.{head_digits}{cycle}{cycle}…"
    elif truncated:
        display = f"{sign}{whole}." + "".join(digits) + "…"
    else:
        display = f"{sign}{whole}." + "".join(digits) if digits else f"{sign}{whole}"

    return {
        "whole": whole,
        "digits": digits,
        "steps": steps,
        "display": display,
        "terminating": terminating,
        "repeat_start": repeat_start,
        "verdict": "Stops" if terminating else "Never stops",
    }


def divides_visibly(p, q):
    """Is there actually a division worth watching here?

    8/2 is 4 — the decimal point never even gets used, so animating it
    digit by digit shows a student nothing. Only fractions that produce
    decimal digits earn the long-division treatment.

    >>> divides_visibly(1, 8), divides_visibly(8, 2), divides_visibly(1, 3)
    (True, False, True)
    """
    if q in (0, 1, -1):
        return False
    result = long_division(p, q, max_digits=4)
    return bool(result and result["digits"])


def is_terminating(p, q):
    """Does p/q have a terminating decimal expansion?

    True exactly when the reduced denominator's only primes are 2 and 5.

    >>> is_terminating(1, 8), is_terminating(1, 3), is_terminating(3, 6)
    (True, False, True)
    """
    try:
        p, q = int(p), int(q)
    except (TypeError, ValueError):
        return False
    if q == 0:
        return False
    q = abs(q) // math.gcd(abs(p), abs(q))
    for prime in (2, 5):
        while q % prime == 0:
            q //= prime
    return q == 1


def prime_factorization(n):
    """[(prime, power), …] for n ≥ 2, empty for anything smaller.

    >>> prime_factorization(200)
    [(2, 3), (5, 2)]
    """
    try:
        n = abs(int(n))
    except (TypeError, ValueError):
        return []
    if n < 2:
        return []
    factors, d = [], 2
    while d * d <= n:
        power = 0
        while n % d == 0:
            n //= d
            power += 1
        if power:
            factors.append((d, power))
        d += 1 if d == 2 else 2
    if n > 1:
        factors.append((n, 1))
    return factors


def factor_tree(n, max_depth=4):
    """Nested {value, children} splitting off the smallest prime each time.

    The shape a factor tree is drawn in: every node either is prime (no
    children) or splits into its smallest prime factor and the rest.

    >>> factor_tree(12)["children"][0]["value"]
    2
    """
    try:
        n = abs(int(n))
    except (TypeError, ValueError):
        return None
    if n < 2:
        return None

    def build(value, depth):
        node = {"value": value, "children": [], "prime": True}
        if depth >= max_depth:
            return node
        for d in range(2, int(math.isqrt(value)) + 1):
            if value % d == 0:
                node["prime"] = False
                node["children"] = [build(d, depth + 1),
                                    build(value // d, depth + 1)]
                break
        return node

    return build(n, 0)


def best_expandable_power(lines, max_terms=6):
    """The power in these lines that makes the clearest expansion picture.

    The biggest exponent that still fits on a line teaches the most —
    x⁵ as five x's says more than x² as two — so the largest usable one
    wins rather than simply the first one written.

    >>> best_expandable_power([r"x^2 \\cdot x^3 = x^5"])
    ('x', 5)
    >>> best_expandable_power([r"a^m \\cdot a^n"]) is None
    True
    """
    candidates = [(base, exp) for base, exp in find_powers(lines, limit=12)
                  if 2 <= exp <= max_terms]
    if not candidates:
        return None
    return max(candidates, key=lambda pair: pair[1])


def expand_power(base, exponent, max_terms=8):
    """"3^4" as the multiplication it stands for: ['3','3','3','3'].

    Empty when the exponent is not a small positive integer — there is
    nothing honest to draw for a^n or 2^100.

    >>> expand_power("x", 3)
    ['x', 'x', 'x']
    """
    try:
        exponent = int(exponent)
    except (TypeError, ValueError):
        return []
    if exponent < 1 or exponent > max_terms:
        return []
    return [str(base)] * exponent


# ── selection: what this lesson's own content offers ─────────────────

_FRACTION_RE = re.compile(r"(?<![\d.])(-?\d{1,4})\s*/\s*(\d{1,4})(?![\d.])")
_POWER_RE = re.compile(r"(?<![\\A-Za-z0-9])([A-Za-z]|\d{1,3})\s*\^\s*\{?\s*(-?\d{1,2})\s*\}?")
_INT_RE = re.compile(r"(?<![\d.^])(\d{2,5})(?![\d.])")

_SUPERSCRIPT = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
                "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9"}
_SUPERSCRIPT_RUN = re.compile("[" + "".join(_SUPERSCRIPT) + "]+")


def desuperscript(text):
    """Turn display superscripts back into power notation.

    On-screen lines have already been through latex_to_plain, which
    renders `x^2` as `x²`. Powers still need to be findable there.

    >>> desuperscript("x² · x³")
    'x^2 · x^3'
    """
    return _SUPERSCRIPT_RUN.sub(
        lambda m: "^" + "".join(_SUPERSCRIPT[c] for c in m.group(0)),
        str(text))


def find_fractions(lines, limit=6):
    """Every p/q written in these plain-text lines, in order, deduped.

    >>> find_fractions(["Ex 1: 1/8 = 0.125", "and 1/3 never stops"])
    [(1, 8), (1, 3)]
    """
    found, seen = [], set()
    for line in _as_lines(lines):
        for match in _FRACTION_RE.finditer(line):
            p, q = int(match.group(1)), int(match.group(2))
            if q == 0 or (p, q) in seen:
                continue
            seen.add((p, q))
            found.append((p, q))
            if len(found) >= limit:
                return found
    return found


def find_powers(lines, limit=6):
    """Every base^exponent written in these lines, in order, deduped.

    Reads both the LaTeX form and the on-screen form, so a power is
    found whether the line says `x^2` or `x²`.

    >>> find_powers([r"x^2 \\cdot x^3 = x^5"])
    [('x', 2), ('x', 3), ('x', 5)]
    >>> find_powers(["x² · x³"])
    [('x', 2), ('x', 3)]
    """
    found, seen = [], set()
    for line in _as_lines(lines):
        line = desuperscript(line)
        for match in _POWER_RE.finditer(line):
            base, exp = match.group(1), int(match.group(2))
            if (base, exp) in seen:
                continue
            seen.add((base, exp))
            found.append((base, exp))
            if len(found) >= limit:
                return found
    return found


def find_composites(lines, limit=4, minimum=4):
    """Standalone integers worth drawing a factor tree for."""
    found, seen = [], set()
    for line in _as_lines(lines):
        for match in _INT_RE.finditer(line):
            value = int(match.group(1))
            if value < minimum or value in seen:
                continue
            if len(prime_factorization(value)) < 1:
                continue
            if factor_tree(value) and factor_tree(value)["prime"]:
                continue
            seen.add(value)
            found.append(value)
            if len(found) >= limit:
                return found
    return found


def contrast_fractions(lines):
    """A terminating fraction paired against a non-terminating one.

    This is what makes a side-by-side comparison possible without anyone
    writing the comparison into the curriculum: if the lesson's own board
    happens to contain both kinds, the pair is drawn; if it does not,
    None comes back and the caller draws something else.

    >>> spec = contrast_fractions(["1/8 and 1/3"])
    >>> spec["left"]["decimal"], spec["right"]["verdict"]
    ('0.125', 'Never stops')
    """
    stops, runs = [], []
    for p, q in find_fractions(lines, limit=12):
        if not divides_visibly(p, q):
            continue          # 8/2 is not a case worth contrasting
        (stops if is_terminating(p, q) else runs).append((p, q))
    if not stops or not runs:
        return None

    def panel(pair, title):
        p, q = pair
        division = long_division(p, q, max_digits=8)
        return {
            "title": title,
            "fraction": (p, q),
            "decimal": division["display"] if division else "",
            "steps": division["steps"] if division else [],
            "verdict": division["verdict"] if division else "",
            "terminating": bool(division and division["terminating"]),
        }

    return {"left": panel(stops[0], "Terminating"),
            "right": panel(runs[0], "Recurring")}


# ── which construction a lesson earns ────────────────────────────────

#: In teaching order — a genuine contrast says more than a single
#: calculation, and a calculation says more than a list of steps.
CONSTRUCTION_KINDS = ("compare", "division", "expansion", "factor_tree",
                      "flowchart")


def choose_construction(plain_lines, raw_lines=()):
    """Pick the richest construction this lesson's own board supports.

    Returns `(kind, payload)` where kind is one of CONSTRUCTION_KINDS, or
    None when the lesson offers nothing to build. Cell 4 maps the kind to
    a drawing class — the *decision* lives here so it can be checked
    against the whole curriculum without a renderer.

    Both forms of the board are read, because the two survive different
    translations: fractions read cleanly from the on-screen text
    ("1/8"), powers from the LaTeX (`x^2` — the on-screen text has
    already turned that into `x²`).

    >>> choose_construction(["Ex 1: 1/8 stops but 1/3 does not"])[0]
    'compare'
    >>> choose_construction(["Ex 1: 3/8 of a pizza"])[0]
    'division'
    >>> choose_construction(["counting"], [r"x^2 \\cdot x^3 = x^5"])
    ('expansion', ('x', 5))
    """
    plain = [l for l in _as_lines(plain_lines) if l]
    raw   = [l for l in _as_lines(raw_lines) if l]
    pool  = plain + raw

    contrast = contrast_fractions(pool)
    if contrast:
        return "compare", contrast

    for p, q in find_fractions(plain):
        if divides_visibly(p, q):
            return "division", (p, q)

    power = best_expandable_power(pool)
    if power:
        return "expansion", power

    composites = find_composites(plain)
    if composites:
        return "factor_tree", composites[0]

    if len(plain) >= 2:
        return "flowchart", plain[:4]

    return None


_STRUCTURAL_TERMS = {
    "numerator", "denominator", "fraction", "decimal", "prime", "factor",
    "factors", "power", "powers", "base", "exponent", "index", "root",
    "square", "cube", "terminating", "recurring", "repeating", "rational",
    "irrational", "integer", "remainder", "quotient", "product", "sum",
    "difference", "equation", "formula", "rule", "law", "proof", "graph",
    "angle", "triangle", "degree", "coefficient", "variable", "constant",
    "positive", "negative", "zero", "infinite", "identity", "inverse",
}


def lesson_vocabulary(*sources):
    """The words this lesson is actually about, drawn from its own data.

    Feed it the title, subtopic, formula and board lines; it returns the
    set of content words worth glowing when the narration says them.
    """
    vocab = set()
    for source in sources:
        for line in _as_lines(source):
            for word in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", line):
                lowered = word.lower()
                if lowered in _STOPWORDS:
                    continue
                vocab.add(lowered)
    return vocab


_STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can",
    "her", "was", "one", "our", "out", "day", "get", "has", "him", "his",
    "how", "man", "new", "now", "old", "see", "two", "way", "who", "boy",
    "did", "its", "let", "put", "say", "she", "too", "use", "that", "this",
    "with", "have", "from", "they", "will", "your", "what", "when", "make",
    "like", "time", "just", "know", "take", "into", "than", "them", "then",
    "look", "only", "come", "over", "also", "back", "after", "work", "first",
    "well", "even", "want", "because", "there", "here", "every", "which",
}


def emphasis_words(sentence, vocabulary=(), limit=3):
    """Words in this sentence worth highlighting as the voice says them.

    Numbers and symbols always count — they are what a student's eye is
    hunting for. Beyond those, a word counts if it belongs to the lesson's
    own vocabulary or is standard mathematical structure language.

    >>> emphasis_words("Notice the denominator is 8", limit=2)
    ['denominator', '8']
    """
    vocab = set(vocabulary) | _STRUCTURAL_TERMS
    picked, seen = [], set()
    for token in re.findall(r"[A-Za-z][A-Za-z\-]*|\d+(?:\.\d+)?(?:/\d+)?", str(sentence)):
        key = token.lower()
        if key in seen:
            continue
        if token[0].isdigit() or key in vocab:
            seen.add(key)
            picked.append(token)
        if len(picked) >= limit:
            break
    return picked


def _as_lines(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        out = []
        for item in value:
            out.extend(_as_lines(item))
        return out
    return [str(value)]

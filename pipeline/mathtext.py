"""Shared LaTeX translation used across the pipeline.

Curriculum content is written in LaTeX (`\\tfrac{3}{4}`, `\\text{...}`,
`\\neq` ...). Three consumers need it in different shapes:

  * latex_to_plain()  → clean unicode for on-screen Text when MathTex is
                        unavailable or the string is mostly prose
                        ("Ex 1: Is 3/4 rational?", "q ≠ 0 → Yes")
  * latex_to_speech() → natural spoken English for the TTS voice
                        ("Example one. Is three over 4 rational?")
  * split_sentences() → sentence beats used for narration↔visual sync

Never render a raw LaTeX string on screen and never feed one to the
voice — always pass it through here first.
"""

import re

# ── shared fragment handling ─────────────────────────────────────────

_FRAC_RE = re.compile(r"\\[dt]?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}")
_TEXT_RE = re.compile(r"\\text(?:bf|it|rm)?\s*\{([^{}]*)\}")
_SQRT_RE = re.compile(r"\\sqrt\s*\{([^{}]*)\}")
_MATHBB_RE = re.compile(r"\\mathbb\s*\{([A-Za-z])\}")
_SPACING_RE = re.compile(r"\\[,;:!]|\\quad|\\qquad|\\ ")
_LEFTRIGHT_RE = re.compile(r"\\left|\\right")

# Blackboard-bold number-set letters (\mathbb{Q} etc.) — screen unicode
# and spoken phrase, since these are common in irrational/set-theory
# proofs and are not simple one-token symbols like the _SYMBOLS list.
_MATHBB_UNICODE = {"Q": "ℚ", "R": "ℝ", "Z": "ℤ", "N": "ℕ", "C": "ℂ"}
_MATHBB_SPOKEN = {
    "Q": "the rational numbers", "R": "the real numbers",
    "Z": "the integers", "N": "the natural numbers",
    "C": "the complex numbers",
}

# LaTeX command → (screen unicode, spoken English)
_SYMBOLS = [
    (r"\Longrightarrow", "⟹", " which means "),
    (r"\Rightarrow", "→", " which means "),
    (r"\rightarrow", "→", " goes to "),
    (r"\Leftarrow", "←", " follows from "),
    (r"\iff", "⇔", " if and only if "),
    (r"\implies", "⟹", " which means "),
    (r"\checkmark", "Yes", " yes "),
    (r"\neq", "≠", " is not equal to "),
    (r"\ne", "≠", " is not equal to "),
    (r"\leq", "≤", " is less than or equal to "),
    (r"\le", "≤", " is less than or equal to "),
    (r"\geq", "≥", " is greater than or equal to "),
    (r"\ge", "≥", " is greater than or equal to "),
    (r"\approx", "≈", " is approximately "),
    (r"\equiv", "≡", " is equivalent to "),
    (r"\pm", "±", " plus or minus "),
    (r"\cdot", "·", " times "),
    (r"\times", "×", " times "),
    (r"\div", "÷", " divided by "),
    (r"\infty", "∞", " infinity "),
    (r"\degree", "°", " degrees "),
    (r"\circ", "°", " degrees "),
    (r"\perp", "⊥", " is perpendicular to "),
    (r"\parallel", "∥", " is parallel to "),
    (r"\cong", "≅", " is congruent to "),
    (r"\sim", "~", " is similar to "),
    (r"\triangle", "△", " triangle "),
    (r"\angle", "∠", " angle "),
    (r"\pi", "π", " pi "),
    (r"\theta", "θ", " theta "),
    (r"\alpha", "α", " alpha "),
    (r"\beta", "β", " beta "),
    (r"\gamma", "γ", " gamma "),
    (r"\Delta", "Δ", " delta "),
    (r"\delta", "δ", " delta "),
    (r"\lambda", "λ", " lambda "),
    (r"\mu", "μ", " mu "),
    (r"\sigma", "σ", " sigma "),
    (r"\Sigma", "Σ", " the sum of "),
    (r"\sum", "Σ", " the sum of "),
    (r"\int", "∫", " the integral of "),
    (r"\lim", "lim", " the limit "),
    (r"\sin", "sin", " sine "),
    (r"\cos", "cos", " cosine "),
    (r"\tan", "tan", " tangent "),
    (r"\log", "log", " log "),
    (r"\ln", "ln", " natural log "),
    (r"\notin", "∉", " is not in "),
    (r"\in", "∈", " belongs to "),
    (r"\subset", "⊂", " is a subset of "),
    (r"\cup", "∪", " union "),
    (r"\cap", "∩", " intersection "),
    (r"\emptyset", "∅", " the empty set "),
    (r"\forall", "∀", " for all "),
    (r"\exists", "∃", " there exists "),
    (r"\dots", "…", " and so on "),
    (r"\ldots", "…", " and so on "),
    (r"\cdots", "…", " and so on "),
]

_SMALL_NUMBERS = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
    "10": "ten", "11": "eleven", "12": "twelve",
}


def _strip_residue(text: str) -> str:
    """Remove leftover LaTeX punctuation after all translation passes."""
    text = _SPACING_RE.sub(" ", text)
    text = _LEFTRIGHT_RE.sub("", text)
    # Any surviving \command becomes its bare name (better than backslashes)
    text = re.sub(r"\\([A-Za-z]+)", r"\1", text)
    text = text.replace("$", "").replace("{", "").replace("}", "")
    text = text.replace("\\", "")
    return " ".join(text.split())


def latex_to_plain(latex) -> str:
    """LaTeX → clean unicode string for on-screen display.

    '\\text{Ex 1: Is } \\tfrac{3}{4} \\text{ rational?}'
        → 'Ex 1: Is 3/4 rational?'
    'p=3,\\ q=4,\\ q \\neq 0 \\;\\Rightarrow\\; \\checkmark \\text{ Yes}'
        → 'p = 3, q = 4, q ≠ 0 → Yes'
    """
    if latex is None:
        return ""
    text = str(latex)

    # Nested-safe: unwrap \text{} and fractions repeatedly
    for _ in range(4):
        new = _TEXT_RE.sub(r"\1", text)
        new = _FRAC_RE.sub(r"\1/\2", new)
        new = _SQRT_RE.sub(r"√(\1)", new)
        new = _MATHBB_RE.sub(lambda m: _MATHBB_UNICODE.get(m.group(1), m.group(1)), new)
        if new == text:
            break
        text = new

    for cmd, screen, _spoken in _SYMBOLS:
        text = text.replace(cmd, f" {screen} ")

    text = text.replace("^2", "²").replace("^3", "³")
    text = re.sub(r"\^\{([^{}]*)\}", r"^\1", text)
    text = re.sub(r"_\{([^{}]*)\}", r"\1", text)
    text = _strip_residue(text)

    # Pad '=' for readability, collapse duplicated verdicts ("Yes Yes")
    text = re.sub(r"\s*=\s*", " = ", text)
    text = re.sub(r"\b(Yes|No)(\s+\1)+\b", r"\1", text, flags=re.IGNORECASE)
    # A '×' used as a cross-mark verdict before a word reads better as ✗
    text = re.sub(r"×\s+(?=[A-Z])", "✗ ", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    return " ".join(text.split())


def latex_to_speech(latex) -> str:
    """LaTeX (string or list of strings) → natural spoken English."""
    if not latex:
        return ""
    if isinstance(latex, (list, tuple)):
        return " ".join(latex_to_speech(item) for item in latex)
    text = str(latex)

    for _ in range(4):
        new = _TEXT_RE.sub(r"\1", text)
        new = _FRAC_RE.sub(lambda m: f" {_speak_num(m.group(1))} over {_speak_num(m.group(2))} ", new)
        new = _SQRT_RE.sub(r" the square root of \1 ", new)
        new = _MATHBB_RE.sub(lambda m: f" {_MATHBB_SPOKEN.get(m.group(1), m.group(1))} ", new)
        if new == text:
            break
        text = new

    for cmd, _screen, spoken in _SYMBOLS:
        text = text.replace(cmd, spoken)

    text = text.replace("^2", " squared").replace("^3", " cubed")
    text = re.sub(r"\^\{([^{}]*)\}", r" to the power of \1 ", text)
    text = re.sub(r"_\{([^{}]*)\}", r" \1 ", text)
    text = _strip_residue(text)

    # Spoken operators — only where they are clearly math, so hyphenated
    # words and prose punctuation are never mangled.
    text = re.sub(r"\s*=\s*", " equals ", text)
    text = re.sub(r"(?<=[\d\)a-z])\s*\+\s*(?=[\d\(a-z])", " plus ", text)
    text = re.sub(r"(?<=[\d\)])\s*-\s*(?=[\d\(])", " minus ", text)
    text = re.sub(r"(?<=\s)-(?=\d)", "negative ", text)
    text = re.sub(r"(?<=[\d\)])\s*/\s*(?=[\d\(])", " over ", text)
    text = text.replace("×", " times ").replace("÷", " divided by ")
    text = text.replace("≠", " is not equal to ").replace("→", " which means ")
    text = text.replace("≈", " is approximately ").replace("±", " plus or minus ")
    text = text.replace("Ex 1", "Example one").replace("Ex 2", "Example two")
    text = text.replace("Ex 3", "Example three").replace("Ex 4", "Example four")
    text = text.replace("Ex 5", "Example five")

    # Cross-mark verdicts: "times Undefined" is a ✗ before a word, not a product
    text = re.sub(r"\btimes\s+undefined\b", "so it is undefined", text,
                  flags=re.IGNORECASE)
    text = re.sub(r"\b(yes)([,.!]?\s+yes)+\b", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(no)([,.!]?\s+no)+\b", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = " ".join(text.split())
    # Ensure a sentence break at the end so beats stay clean
    if text and text[-1] not in ".?!":
        text += "."
    return text


def _speak_num(s: str) -> str:
    s = s.strip()
    if s.startswith("-"):
        rest = s[1:].strip()
        return "negative " + _SMALL_NUMBERS.get(rest, rest)
    return _SMALL_NUMBERS.get(s, s)


def spoken_lines(latex_lines) -> list:
    """List of LaTeX lines → list of spoken sentences (one per line).

    Cell 2 stores these next to the on-screen lines so Cell 4 can find
    the exact moment each line is spoken inside the scene narration.
    """
    if not latex_lines:
        return []
    return [latex_to_speech(line) for line in latex_lines]


_SENT_RE = re.compile(r"(?<=[.?!])\s+")


def split_sentences(text: str) -> list:
    """Split prose into trimmed sentences (empty ones dropped)."""
    if not text:
        return []
    return [s.strip() for s in _SENT_RE.split(str(text).strip()) if s.strip()]


def normalize_word(w: str) -> str:
    """Same normalization Cell 3 applies to TTS word boundaries."""
    import unicodedata
    w = unicodedata.normalize("NFKD", str(w)).encode("ASCII", "ignore").decode()
    return re.sub(r"[^\w]", "", w).lower()

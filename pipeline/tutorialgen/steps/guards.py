"""Deterministic guardrails applied after LLM calls.

The prompts already forbid inventing quantities, durations, temperatures or settings. This is the
belt to that suspender: any number in generated step text that does not occur in the evidence
(narration, uploader answers, the previous version of the step) is replaced by ``[?]`` and turned
into a blocking missing-info item, so it becomes a question instead of an assertion.
"""

from __future__ import annotations

import re

UNITS = (r"%|°\s?[CF]?|degrees?(?:\s+[CF])?|seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|"
         r"ml|mL|millilit(?:er|re)s?|lit(?:er|re)s?|l|L|kg|mg|g|grams?|oz|ounces?|lbs?|pounds?|"
         r"mm|cm|m|meters?|metres?|inch(?:es)?|in|ft|feet|psi|bar|rpm|volts?|V|watts?|W|amps?|A|times|x")
# Not preceded or followed by a letter, so "3D", "M3" and "G28" are names rather than quantities ("20s" still counts).
NUMBER = re.compile(rf"(?<![\w.])(\d+(?:[.,]\d+)?)(\s*(?:{UNITS})\b)?(?![^\W\ds])")
WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000,
    "half": 0.5, "once": 1, "twice": 2,
}
# Fraction denominators: narration says "one-eighth" where a step writes "1/8".
ORDINALS = {"half": 2, "third": 3, "quarter": 4, "fourth": 4, "fifth": 5, "sixth": 6, "eighth": 8, "tenth": 10,
            "twelfth": 12, "sixteenth": 16, "thirtysecond": 32, "sixtyfourth": 64}


def numbers_in(text: str) -> set[float]:
    found = {float(m.group(1).replace(",", ".")) for m in NUMBER.finditer(text)}
    words = re.findall(r"[a-z]+", text.lower())
    found |= {float(WORDS[w]) for w in words if w in WORDS}
    found |= {float(ORDINALS[w.removesuffix("s")]) for w in words if w.removesuffix("s") in ORDINALS}
    for a, b in zip(words, words[1:]):  # "twenty five" -> 25
        if a in WORDS and b in WORDS and WORDS[a] >= 20 and WORDS[a] % 10 == 0 and WORDS[b] < 10:
            found.add(float(WORDS[a] + WORDS[b]))
    return found


def ungrounded(texts: list[str], evidence: str) -> list[str]:
    """Number tokens (with unit) in ``texts`` whose value does not occur in ``evidence``."""
    allowed = numbers_in(evidence)
    bad: list[str] = []
    for text in texts:
        for m in NUMBER.finditer(text):
            if float(m.group(1).replace(",", ".")) not in allowed and m.group(0).strip() not in bad:
                bad.append(m.group(0).strip())
    return bad


def redact(text: str, tokens: list[str]) -> str:
    for tok in sorted(tokens, key=len, reverse=True):
        text = re.sub(rf"(?<![\w.]){re.escape(tok)}(?![\w])", "[?]", text)
    return text

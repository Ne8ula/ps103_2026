"""Edit decision list: turn each step's full time range into kept, sped-up and cut units.

The protocol is the same for every video:

1. Units. A step's range is split into spoken lines (Whisper word timestamps, so cuts land between
   words) and the gaps between them.
2. Evidence. Each unit gets deterministic features: share of hand samples with a hand, and pixel
   motion in the frame (independent of hand detection, so hidden hands still count as work).
3. Labels. Gaps are labelled by rule (idle when nothing moves and no hand is seen, else task).
   Spoken lines are labelled by the LLM from a fixed set (task, result, explain, aside), citing
   only offered unit ids; anything it does not label is kept.
4. Actions, by fixed rules: cut long idle and asides; speed up an aside spoken while the hands keep
   working, and long silent task stretches; keep everything else.
5. Guards. A number stated in the step text keeps a unit where it was said; a spoken line with a
   number is never cut or muted; every step keeps a minimum length.
"""

from .rules import EditConfig, apply_rules, step_output_seconds
from .units import build_units, pixel_motion, subtitle_lines

__all__ = ["EditConfig", "apply_rules", "build_units", "pixel_motion", "step_output_seconds", "subtitle_lines"]

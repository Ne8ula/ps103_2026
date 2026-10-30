"""Versioned prompt templates. ``load_prompt("segment_steps")`` -> Prompt(system, user_template, version).

File format (prompts/<name>.md):

    # system
    ...system text...
    # user
    ...user template with {placeholders}...
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

PROMPT_DIR = Path(__file__).parent


@dataclass(frozen=True)
class Prompt:
    name: str
    system: str
    user_template: str
    version: str

    def render(self, **values) -> str:
        return self.user_template.format(**values)


def load_prompt(name: str) -> Prompt:
    text = (PROMPT_DIR / f"{name}.md").read_text()
    parts = text.split("# user", 1)
    if len(parts) != 2 or "# system" not in parts[0]:
        raise ValueError(f"prompt {name} must have '# system' and '# user' sections")
    system = parts[0].split("# system", 1)[1].strip()
    user = parts[1].strip()
    version = hashlib.sha256(text.encode()).hexdigest()[:10]
    return Prompt(name, system, user, version)

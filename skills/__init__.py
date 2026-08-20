"""
MAX 2.0 — Skills Package
Each skill registers with the SkillRouter via the @skill decorator.
"""
from skills.router import SkillRouter, skill

__all__ = ["SkillRouter", "skill"]

"""
MAX 2.0 — Skill Router
Central dispatcher — maps skill names (from brain intent) to handler functions.
"""
from core.logger import log
from typing import Callable, Optional


class SkillRouter:
    """Registry that maps skill name → handler callable."""

    def __init__(self):
        self._registry: dict[str, Callable] = {}

    def register(self, name: str, handler: Callable) -> None:
        self._registry[name] = handler
        log.debug(f"Skill registered: {name}")

    def dispatch(self, intent: dict, gui_callback=None) -> Optional[str]:
        """
        Dispatch an intent dict to the matching skill.
        intent = {"skill": str, "args": dict, "speak": str}
        Returns the spoken response string or None.
        """
        skill_name = intent.get("skill", "general_chat")
        args = intent.get("args", {})
        spoken = intent.get("speak", "")

        handler = self._registry.get(skill_name)

        if handler:
            log.info(f"Dispatching to skill: {skill_name}")
            try:
                result = handler(args, spoken)
                return result
            except Exception as e:
                log.error(f"Skill '{skill_name}' raised: {e}")
                return f"I hit a snag running that skill. {e}"
        else:
            # Unknown skill — just speak the LLM response
            log.debug(f"No handler for skill '{skill_name}', speaking LLM text")
            return spoken


# Decorator for inline skill registration
_router = SkillRouter()


def skill(name: str):
    """Decorator to register a function as a skill handler."""
    def decorator(fn: Callable) -> Callable:
        _router.register(name, fn)
        return fn
    return decorator


def get_router() -> SkillRouter:
    return _router

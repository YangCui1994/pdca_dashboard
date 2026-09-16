"""Re-export shell:正式实现在 workbench/services/prompt_library.py。

原型包只引用不维护,防止双份实现漂移(合并计划 §3)。
"""

from workbench.services.prompt_library import (  # noqa: F401
    PROMPTS_ROOT,
    PromptLibrary,
    PromptSpec,
)

__all__ = ["PROMPTS_ROOT", "PromptLibrary", "PromptSpec"]

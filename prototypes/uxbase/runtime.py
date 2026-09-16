"""Re-export shell:正式实现在 workbench/runtime/text_runtime.py。

原型包只引用不维护,防止双份实现漂移(合并计划 §3)。
"""

from workbench.runtime.text_runtime import (  # noqa: F401
    FakePromptRuntime,
    OpenAITextRuntime,
    TextEvent,
    collect_text,
)

__all__ = ["FakePromptRuntime", "OpenAITextRuntime", "TextEvent", "collect_text"]

"""Re-export shell:正式实现在 workbench/services/file_watcher.py。

原型包只引用不维护,防止双份实现漂移(合并计划 §3)。
"""

from workbench.services.file_watcher import FileWatcher  # noqa: F401

__all__ = ["FileWatcher"]

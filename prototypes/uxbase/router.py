"""Re-export shell:正式实现在 workbench/services/file_routing.py。

原型包只引用不维护,防止双份实现漂移(合并计划 §3)。
"""

from workbench.services.file_routing import (  # noqa: F401
    RouteDecision,
    parse_route_decision,
    route_file,
)

__all__ = ["RouteDecision", "parse_route_decision", "route_file"]

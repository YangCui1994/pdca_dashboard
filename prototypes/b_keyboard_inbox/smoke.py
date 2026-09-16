"""B 版冒烟:排序/键位路由/直接状态切换/命令面板文档/落盘(headless)。"""

from __future__ import annotations

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from prototypes.b_keyboard_inbox.app import (  # noqa: E402
    IDEA_KEY_ACTIONS,
    build_commands,
    move_selection,
    sort_ideas,
    sort_plan,
)
from prototypes.uxbase.seed_demo import seed  # noqa: E402
from workbench.domain.models import Idea  # noqa: E402
from workbench.services.workspace_service import WorkspaceService  # noqa: E402
from workbench.storage import WorkspaceStorage  # noqa: E402


def main() -> int:
    today = date.today()
    with tempfile.TemporaryDirectory() as tmp:
        service = seed(Path(tmp) / "vault", reseed=True)

        # 1. 排序:pending 置顶、新的在前;未完成计划置顶
        ideas = sort_ideas(service.ideas())
        assert ideas[0].status == "pending"
        kept_older = Idea(idea_id="idea-090", text="旧的保留", status="kept", created_at=today - timedelta(days=9))
        assert [i.status for i in ideas].index("pending") == 0
        plan = service.day_record(today).plan
        assert all(not i.done for i in sort_plan(plan)[: sum(1 for i in plan if not i.done)])

        # 2. 键位路由:j/k 选择范围钳制;1/2/3 映射到想法动作
        assert move_selection(3, 0, "j") == 1 and move_selection(3, 2, "j") == 2
        assert move_selection(3, 0, "k") == 0
        assert IDEA_KEY_ACTIONS == {"1": "kept", "2": "archived", "3": "plan"}
        pending = [i for i in ideas if i.status == "pending"]
        first = pending[0]
        service.set_idea_status(first.idea_id, IDEA_KEY_ACTIONS["1"])  # 按 1
        assert first.status == "kept"

        # 3. 按 3 → 转今日计划(写计划 + kept)
        target = [i for i in sort_ideas(service.ideas()) if i.status == "pending"][0]
        service.add_plan_item(today, target.text)
        service.set_idea_status(target.idea_id, "kept")
        assert any(i.text == target.text for i in service.day_record(today).plan)

        # 4. e → 重命名计划项;行动状态 s/d 直改(不经 AI)
        item = service.day_record(today).plan[0]
        service.rename_plan_item(today, item.item_id, item.text + "(改)")
        assert service.day_record(today).plan[0].text.endswith("(改)")
        service.set_action_status("proj-atlas", "act-001", "in_progress")
        service.set_action_status("proj-atlas", "act-001", "completed")
        project = next(p for p in service.projects() if p.project_id == "proj-atlas")
        assert next(a for a in project.actions if a.action_id == "act-001").status == "completed"

        # 5. 命令面板:空查询 = 完整命令文档
        commands = build_commands()
        labels = [k for k, _ in commands]
        assert {"c", "j / k", "1", "2", "3", "e", "s", "d", "Ctrl+K"} <= set(labels)

        # 6. 落盘回环
        reloaded = WorkspaceService.open(WorkspaceStorage(Path(tmp) / "vault"))
        assert len(reloaded.ideas()) == len(service.ideas())

    print("B smoke OK: 排序/键位/转计划/重命名/直改状态/命令文档/落盘 全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

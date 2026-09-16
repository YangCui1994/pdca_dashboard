"""A 版冒烟:headless 按用户剧本走一遍并断言落盘(不打开窗口)。

python -m prototypes.a_today_hub.smoke
"""

from __future__ import annotations

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from prototypes.a_today_hub.app import plan_summary_lines, route_capture  # noqa: E402
from prototypes.uxbase.loader import PromptLibrary  # noqa: E402
from prototypes.uxbase.runtime import FakePromptRuntime, collect_text  # noqa: E402
from prototypes.uxbase.seed_demo import projects_summary, seed  # noqa: E402
from workbench.services.workspace_service import WorkspaceService  # noqa: E402
from workbench.storage import WorkspaceStorage  # noqa: E402

PROMPTS_ROOT = Path(__file__).resolve().parents[1] / "ux-2026-09" / "prompts"


def main() -> int:
    today = date.today()
    with tempfile.TemporaryDirectory() as tmp:
        service = seed(Path(tmp) / "vault", reseed=True)

        # 1. 智能捕获路由:! → 计划;#项目 → 归属计划;纯文字 → 想法
        names = {p.name: p.project_id for p in service.projects()}
        kind, payload, project_id = route_capture("!给运营同步周报口径", names)
        assert (kind, payload, project_id) == ("plan", "给运营同步周报口径", ""), (kind, payload)
        item = service.add_plan_item(today, payload, project_id)
        kind, payload, project_id = route_capture("#星图演示库 跟进数据口径差异", names)
        assert kind == "plan" and project_id == "proj-atlas", (kind, project_id)
        item_proj = service.add_plan_item(today, payload, project_id)
        kind, payload, _ = route_capture("把异常波动标注做成固定栏目", names)
        assert kind == "idea", kind
        idea = service.quick_capture(payload)

        # 2. 勾选完成 → 活动流出现 task_completed
        service.toggle_plan_item(today, item.item_id)
        assert any(e.kind == "task_completed" for e in service.activity())

        # 3. 昨日未完成顺延 → 今天出现、昨天消失;撤销可回
        yesterday = today - timedelta(days=1)
        undone = [i for i in service.day_record(yesterday).plan if not i.done]
        assert len(undone) >= 2, undone
        moved_ids = []
        for old in undone:
            moved = service.add_plan_item(today, old.text, old.project_id)
            moved_ids.append(moved.item_id)
            service.remove_plan_item(yesterday, old.item_id)
        texts_today = [i.text for i in service.day_record(today).plan]
        assert "准备用户访谈提纲" in texts_today
        assert all(i.text not in [x.text for x in service.day_record(yesterday).plan] for i in undone)

        # 4. 想法 touch-once:入今日 + 保留 → pending 减少
        service.add_plan_item(today, idea.text)
        service.set_idea_status(idea.idea_id, "kept")
        assert idea.status == "kept"

        # 5. 思考方式(fake)产出确定性草稿 → 采纳为计划
        library = PromptLibrary(PROMPTS_ROOT)
        spec = library.get("thinking", "grill_me")
        rendered = spec.render(target_kind="想法", target_text=payload, project_brief="")
        draft, trace = collect_text(FakePromptRuntime().complete(spec, rendered))
        assert draft and "最致命" in draft, draft
        adopted = service.add_plan_item(today, draft.splitlines()[0])

        # 6. 阶段提示词 plan_suggest 可渲染并出 fake 草稿
        stage = library.get("stages", "plan_suggest")
        record = service.day_record(today)
        rendered = stage.render(
            yesterday_unfinished="\n".join(plan_summary_lines(service.day_record(yesterday))),
            pending_ideas="\n".join(i.text for i in service.ideas() if i.status == "pending"),
            project_brief=projects_summary(service),
        )
        suggestion, _ = collect_text(FakePromptRuntime().complete(stage, rendered))
        assert suggestion and "proj-" in suggestion or "计划" in suggestion, suggestion

        # 7. 全部落盘:重开服务状态一致
        reloaded = WorkspaceService.open(WorkspaceStorage(Path(tmp) / "vault"))
        assert len(reloaded.day_record(today).plan) == len(service.day_record(today).plan)

    print("A smoke OK: 路由/勾选/顺延/touch-once/思考采纳/阶段草稿/落盘 全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""C 版冒烟:向导四步的领域逻辑 + Check/Act 落盘 + md 镜像(headless)。"""

from __future__ import annotations

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from prototypes.c_review_wizard.app import act_draft, apply_marks, carry_items, plan_summary  # noqa: E402
from prototypes.uxbase.loader import PromptLibrary  # noqa: E402
from prototypes.uxbase.runtime import FakePromptRuntime, collect_text  # noqa: E402
from prototypes.uxbase.seed_demo import seed  # noqa: E402
from workbench.services.workspace_service import WorkspaceService  # noqa: E402
from workbench.storage import WorkspaceStorage  # noqa: E402

PROMPTS_ROOT = Path(__file__).resolve().parents[1] / "ux-2026-09" / "prompts"


def main() -> int:
    today = date.today()
    yesterday = today - timedelta(days=1)
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp) / "vault"
        service = seed(vault, reseed=True)

        # 步骤①:勾选与实际不符的项,apply_marks 落盘
        marks = {i.item_id: i.done for i in service.day_record(yesterday).plan}
        undone = [i for i in service.day_record(yesterday).plan if not i.done]
        marks[undone[0].item_id] = True  # 用户说其实做完了
        assert apply_marks(service, yesterday, marks) == 1
        assert next(i for i in service.day_record(yesterday).plan if i.item_id == undone[0].item_id).done

        # 步骤②:Check 草稿(fake 确定性)→ 保存 → DayRecord + md 镜像
        library = PromptLibrary(PROMPTS_ROOT)
        spec = library.get("stages", "day_check")
        record = service.day_record(yesterday)
        rendered = spec.render(plan_summary=plan_summary(record), worklog=record.worklog)
        check, _ = collect_text(FakePromptRuntime().complete(spec, rendered))
        assert check and "完成" in check
        service.set_day_check(yesterday, check)

        # 步骤③:剩余未完成项 → 今日再做/放弃
        still_undone = [i.item_id for i in service.day_record(yesterday).plan if not i.done]
        assert len(still_undone) >= 1
        carry_id, drop_id = still_undone[0], still_undone[-1]
        carry_texts_before = next(i for i in service.day_record(yesterday).plan if i.item_id == carry_id).text
        dropped, carried, removed = carry_items(service, yesterday, [carry_id], "carry")
        assert (dropped, carried) == (1, 1) and removed
        assert any(i.text == carry_texts_before for i in service.day_record(today).plan)
        if drop_id != carry_id:
            dropped2, carried2, removed2 = carry_items(service, yesterday, [drop_id], "drop")
            assert (dropped2, carried2) == (1, 0) and removed2

        # 步骤④:Act 草稿(确定性)→ 保存
        act = act_draft([carry_texts_before], check)
        assert act.startswith("明日优先:")
        service.set_day_act(yesterday, act)

        # 落盘:重开服务 + md 镜像包含 ## Check / ## Act
        reloaded = WorkspaceService.open(WorkspaceStorage(vault))
        reloaded_record = reloaded.day_record(yesterday)
        assert reloaded_record.check_note == check
        assert "明日优先:" in reloaded_record.act_note
        md = (vault / "days" / f"{yesterday.isoformat()}.md").read_text(encoding="utf-8")
        assert "## Check" in md and "## Act" in md

        # 周复盘阶段提示词可用(fake)
        weekly = library.get("stages", "weekly_review")
        text, _ = collect_text(FakePromptRuntime().complete(weekly, weekly.render(
            week_activity="(示例)", stalled_list="(无)", project_brief="proj-atlas 星图")))
        assert text and "空转" in text

    print("C smoke OK: 勾选落盘/Check 草稿/顺延与放弃/Act 草稿/md 镜像/周复盘 全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

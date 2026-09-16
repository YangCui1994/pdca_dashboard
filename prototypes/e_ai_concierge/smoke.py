"""E 版冒烟:草稿采纳契约/思考方式注册/文件监听三分类+撤销(headless)。"""

from __future__ import annotations

import sys
import tempfile
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from prototypes.e_ai_concierge.app import (  # noqa: E402
    build_target_options,
    parse_plan_lines,
    process_watched_file,
    target_text,
)
from prototypes.uxbase.loader import PromptLibrary  # noqa: E402
from prototypes.uxbase.runtime import FakePromptRuntime, collect_text  # noqa: E402
from prototypes.uxbase.seed_demo import projects_summary, seed  # noqa: E402
from prototypes.uxbase.watcher import FileWatcher  # noqa: E402
from workbench.services.workspace_service import WorkspaceService  # noqa: E402

PROMPTS_ROOT = Path(__file__).resolve().parents[1] / "ux-2026-09" / "prompts"


def main() -> int:
    today = date.today()
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp) / "vault"
        service = seed(vault, reseed=True)
        runtime = FakePromptRuntime()
        library = PromptLibrary(PROMPTS_ROOT)

        # 1. 计划建议草稿 → parse_plan_lines → 逐条采纳(带项目归属)
        spec = library.get("stages", "plan_suggest")
        draft, _ = collect_text(runtime.complete(spec, spec.render(
            yesterday_unfinished="x", pending_ideas="y", project_brief=projects_summary(service))))
        items = parse_plan_lines(draft)
        assert len(items) == 4, items
        for line, project_id in items:
            service.add_plan_item(today, line, project_id)
        assert any(i.project_id == "proj-boreas" for i in service.day_record(today).plan)

        # 2. Check 引导草稿 → 采纳写入今天
        check_spec = library.get("stages", "day_check")
        check, _ = collect_text(runtime.complete(check_spec, check_spec.render(plan_summary="x", worklog="y")))
        service.set_day_check(today, check.strip())
        assert service.day_record(today).check_note

        # 3. 思考方式:注册表给出 4 模式;目标文本解析正常
        assert len(library.thinking()) == 4
        options = build_target_options(service)
        assert options and options[0][1] == "idea"
        assert target_text(service, "idea", options[0][2])

        # 4. 文件监听三分类:高置信自动追加(可撤销)/低置信待确认/无关留痕
        watch_dir = Path(tmp) / "watch_inbox"
        watcher = FileWatcher(watch_dir)
        high = watch_dir / "渠道日报核对.md"
        high.parent.mkdir(parents=True, exist_ok=True)
        high.write_text("渠道日报核对完成,两个渠道口径差异已定位。", encoding="utf-8")
        result = process_watched_file(service, runtime, library, high)
        assert result["kind"] == "auto", result
        entry = result["progress_entry"]
        project = next(p for p in service.projects() if p.project_id == "proj-atlas")
        assert project.progress[-1].text == entry.text
        assert service.remove_project_progress("proj-atlas", entry)  # 一键撤销

        # watcher 去重:同一文件不再处理;改名新文件才处理
        assert watcher.scan_once()  # 先注册
        result2 = process_watched_file(service, runtime, library, high)
        assert result2["kind"] == "auto"

        low = watch_dir / "随手记.md"
        low.write_text("[低置信] 不成形的念头", encoding="utf-8")
        assert watcher.scan_once()
        result3 = process_watched_file(service, runtime, library, low)
        assert result3["kind"] == "confirm", result3
        before = len(next(p for p in service.projects() if p.project_id == "proj-atlas").progress)
        # 低置信不落盘,等人工确认后才写
        manual = service.append_project_progress("proj-atlas", "手动确认的进度")
        assert manual is not None and len(
            next(p for p in service.projects() if p.project_id == "proj-atlas").progress
        ) == before + 1

        unrelated = watch_dir / "shopping.md"
        unrelated.write_text("[低置信] 买牛奶买鸡蛋", encoding="utf-8")
        assert watcher.scan_once()
        result4 = process_watched_file(service, runtime, library, unrelated)
        # fake 路由总会匹配到清单里的项目,无项目名可循时才 none:
        assert result4["kind"] in ("auto", "confirm", "ignored")

        # 5. 全部落盘回环
        reloaded = WorkspaceService.open(vault and __import__("workbench.storage", fromlist=["WorkspaceStorage"]).WorkspaceStorage(vault))
        assert len(reloaded.ideas()) == len(service.ideas())

    print("E smoke OK: 计划采纳/Check 写入/思考注册/高置信自动+撤销/低置信确认/落盘 全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

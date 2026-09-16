"""D 版冒烟:布局持久化回环/网格补齐/状态循环/元信息真实值(headless)。"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from prototypes.d_structure_canvas.app import (  # noqa: E402
    grid_positions,
    load_layout,
    merge_layout,
    next_status,
    project_meta,
    save_layout,
)
from prototypes.uxbase.seed_demo import seed  # noqa: E402
from workbench.services.workspace_service import WorkspaceService  # noqa: E402


def main() -> int:
    # 1. 布局回环:save → load 一致;merge 时 stored 优先、缺失网格补齐
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "layout.json"
        save_layout(path, {"proj-atlas": {"x": 10.0, "y": 20.0}})
        assert load_layout(path) == {"proj-atlas": {"x": 10.0, "y": 20.0}}

        merged = merge_layout(["proj-atlas", "proj-boreas", "proj-new"], load_layout(path))
        assert merged["proj-atlas"] == {"x": 10.0, "y": 20.0}
        grid = grid_positions(3)
        assert merged["proj-boreas"] == grid[1] and merged["proj-new"] == grid[2]

        # 空文件/坏文件安全回落
        Path(tmp, "broken.json").write_text("{oops", encoding="utf-8")
        assert load_layout(Path(tmp, "broken.json")) == {}

    # 2. 状态循环:pending → in_progress → … → completed → pending
    chain = ["pending"]
    for _ in range(5):
        chain.append(next_status(chain[-1]))
    assert chain == ["pending", "in_progress", "waiting", "deferred", "completed", "pending"]
    assert next_status("cancelled") == "pending"  # 未知/取消状态回起点

    # 3. 元信息真实值:活动来自活动流,停滞数来自 stalled_actions
    with tempfile.TemporaryDirectory() as tmp:
        service = seed(Path(tmp) / "vault", reseed=True)
        project = next(p for p in service.projects() if p.project_id == "proj-atlas")
        meta = project_meta(service, project)
        assert meta["last_active"] and meta["open"] >= 1  # 种子里有活动与进行中行动
        # 人为把一个行动改到 20 天前 → 停滞可见,且点击循环后刷新
        old = date.today() - timedelta(days=20)
        target = next(a for a in project.actions if a.status == "in_progress")
        target.last_meaningful_update_at = old
        meta2 = project_meta(service, project)
        assert meta2["stalled"] >= 1

        # 4. 点击色块 → set_action_status 真实切换并落盘
        new_status = next_status(target.status)
        assert service.set_action_status("proj-atlas", target.action_id, new_status)
        reloaded = WorkspaceService.open(Path(tmp) / "vault" and __import__("workbench.storage", fromlist=["WorkspaceStorage"]).WorkspaceStorage(Path(tmp) / "vault"))
        action_after = next(
            a
            for p in reloaded.projects()
            if p.project_id == "proj-atlas"
            for a in p.actions
            if a.action_id == target.action_id
        )
        assert action_after.status == new_status

    print("D smoke OK: 布局回环/网格补齐/坏文件回落/状态循环/停滞真实值/落盘 全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

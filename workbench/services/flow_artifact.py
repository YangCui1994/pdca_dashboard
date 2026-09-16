"""项目流图 Artifact 生成器:真实 workspace 数据 → 离线自包含 HTML。

不引入任何运行时依赖:CSS/JS 手写内联,Mermaid 只输出源文本块
(按样片约定不加载外部渲染库)。所有用户数据经 html.escape 注入。
"""

from __future__ import annotations

import html
from datetime import date

from workbench.services.workspace_service import WorkspaceService

# 节点 kind → 流程栏分组(E1 约定:项目 → 决策 → 资源 → 下一行动)。
_GROUP_ORDER = ("decision", "resource", "test", "next")
_GROUP_LABEL = {
    "decision": "决策",
    "resource": "资源",
    "test": "资源",
    "next": "下一行动",
}

_STATUS_LABEL = {
    "pending": "待办",
    "in_progress": "进行中",
    "waiting": "等待",
    "deferred": "延后",
    "completed": "已完成",
    "cancelled": "已取消",
}


def _mermaid_source(project, nodes_by_group, open_actions) -> str:
    lines = ["graph TD"]
    lines.append(f'  P["{project.name}"]')
    for group in _GROUP_ORDER:
        for node in nodes_by_group.get(group, ()):
            key = f"N{node.node_id.replace('-', '_')}"
            lines.append(f'  P --> {key}["{_GROUP_LABEL[group]}:{node.title}"]')
    for action in open_actions:
        key = f"A{action.action_id.replace('-', '_')}"
        lines.append(
            f'  P --> {key}["行动:{action.title}({_STATUS_LABEL.get(action.status, action.status)})"]'
        )
    return "\n".join(lines)


def render_flow_html(service: WorkspaceService, project_id: str) -> str:
    """Render the interactive project-flow artifact for one project."""

    project = service.project(project_id)
    if project is None:
        return "<!DOCTYPE html><html><body><p>项目不存在。</p></body></html>"
    esc = html.escape

    nodes_by_group: dict[str, list] = {group: [] for group in _GROUP_ORDER}
    context_nodes = []
    for node in project.outline:
        if node.kind in nodes_by_group:
            nodes_by_group[node.kind].append(node)
        else:
            context_nodes.append(node)

    open_actions = [
        a for a in project.actions if a.status in ("in_progress", "pending", "waiting")
    ]
    stalled = {
        a.action_id
        for a in service.stalled_actions(project_id=project_id)
    }

    flow_items = []
    detail_blocks = []

    def _detail(block_id: str, title: str, kind_label: str, body_lines: list[str]):
        detail_blocks.append(
            f'<section id="{esc(block_id)}" class="d" hidden>'
            f"<h3>{esc(title)}</h3><p class=\"kind\">{esc(kind_label)}</p>"
            + "".join(f"<p>{line}</p>" for line in body_lines)
            + "</section>"
        )

    _detail(
        "d-project",
        project.name,
        "项目",
        [
            f"目标:{project.goal}",
            f"阶段:{project.phase} · 当前焦点:{project.current_focus}",
            f"里程碑:{project.next_milestone}",
            f"负责人:{project.owner}",
        ],
    )
    flow_items.append(
        '<div class="node" data-d="d-project"><h2>📁 项目</h2>'
        f"<p>{esc(project.name)} · {esc(project.phase)}</p></div>"
    )

    for group in _GROUP_ORDER:
        for node in nodes_by_group[group]:
            block_id = f"d-{node.node_id}"
            body = [esc(node.note)] if node.note else []
            for resource in node.resources:
                body.append(
                    f"📎 {esc(resource.name)}"
                    + (f' <span class="tag resource">{esc(" ".join(resource.tags))}</span>' if resource.tags else "")
                    + (f"<br>{esc(resource.source)}" if resource.source else "")
                )
            _detail(block_id, node.title, _GROUP_LABEL[group], body or ["(暂无内容,双击工作台节点可补)"])
            flow_items.append(
                f'<div class="node" data-d="{esc(block_id)}">'
                f'<h2>{esc(node.title)} <span class="tag {esc(group)}">{esc(_GROUP_LABEL[group])}</span></h2>'
                f"<p>{esc(node.note[:60]) or '(暂无备注)'}</p></div>"
            )

    for action in open_actions:
        block_id = f"d-{action.action_id}"
        idle = (date.today() - action.last_meaningful_update_at).days
        warn = f" · ⚠️ 停滞 {idle} 天" if action.action_id in stalled else ""
        _detail(
            block_id,
            action.title,
            "行动",
            [f"状态:{_STATUS_LABEL.get(action.status, action.status)}{warn}",
             f"最后实质更新:{action.last_meaningful_update_at.isoformat()}"],
        )
        flow_items.append(
            f'<div class="node" data-d="{esc(block_id)}">'
            f'<h2>{esc(action.title)} <span class="tag action">{esc(_STATUS_LABEL.get(action.status, action.status))}</span></h2>'
            f"<p>{esc(warn.lstrip(' · ') or '行动')}</p></div>"
        )

    context_html = "".join(
        f"<li>{esc(node.title)}:{esc(node.note) or '(待补)'}</li>"
        for node in context_nodes
    )

    mermaid = _mermaid_source(project, nodes_by_group, open_actions)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>项目流图 · {esc(project.name)}</title>
<style>
  :root {{ --canvas:#F7F8FA; --card:#FFF; --border:#E9E9F2; --purple:#6C5CE7;
    --purple-deep:#5B4BC4; --purple-soft:#EFEBFF; --orange:#E8890C; --orange-soft:#FDF3E3;
    --text:#1F2333; --sub:#6B7280; --faint:#9CA3AF; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--canvas); color:var(--text);
    font:14px/1.6 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif; padding:28px; }}
  h1 {{ font-size:18px; }} .meta {{ color:var(--faint); font-size:12px; margin-top:4px; margin-bottom:16px; }}
  .wrap {{ display:flex; gap:16px; align-items:flex-start; }}
  .flow {{ display:flex; flex-direction:column; width:360px; }}
  .node {{ background:var(--card); border:1px solid var(--border); border-radius:12px;
    padding:12px 14px; cursor:pointer; transition:border-color .15s; }}
  .node:hover {{ border-color:var(--purple); }}
  .node.active {{ border-color:var(--purple); background:var(--purple-soft); }}
  .node h2 {{ font-size:14px; display:flex; align-items:center; gap:6px; flex-wrap:wrap; }}
  .node p {{ font-size:12px; color:var(--sub); margin-top:3px; }}
  .tag {{ font-size:11px; border-radius:99px; padding:1px 8px; }}
  .tag.decision {{ background:var(--orange-soft); color:var(--orange); }}
  .tag.resource, .tag.test {{ background:var(--purple-soft); color:var(--purple-deep); }}
  .tag.action {{ background:#E6F5EC; color:#2E9E5B; }}
  .arrow {{ width:2px; height:16px; background:var(--border); margin-left:28px; }}
  .detail {{ flex:1; background:var(--card); border:1px solid var(--border);
    border-radius:12px; padding:16px 18px; min-height:320px; }}
  .detail h3 {{ font-size:15px; margin-bottom:6px; }}
  .detail .kind {{ font-size:12px; color:var(--purple-deep); margin-bottom:10px; }}
  .detail p {{ font-size:13px; color:var(--sub); margin-top:6px; }}
  .detail ul {{ margin:8px 0 0 18px; color:var(--sub); font-size:13px; }}
  .note {{ margin-top:18px; background:var(--card); border:1px dashed var(--border);
    border-radius:12px; padding:12px 16px; font-size:12px; color:var(--sub); }}
  .note code {{ display:block; white-space:pre-wrap; margin-top:8px;
    font-size:12px; color:var(--text); }}
</style></head>
<body>
<header><h1>项目流图 · {esc(project.name)}</h1>
<p class="meta">来源 {esc(project_id)} · 生成于 {date.today().isoformat()} · 离线自包含,点击左侧节点查看详情</p></header>
<div class="wrap">
  <div class="flow">{'<div class="arrow"></div>'.join(flow_items)}</div>
  <div class="detail" id="detail">{''.join(detail_blocks)}
    <p id="placeholder">← 点击左侧任意节点</p></div>
</div>
<div class="note"><b>背景节点</b><ul>{context_html or '<li>(无)</li>'}</ul>
<p style="margin-top:10px">下面这段 Mermaid 源文本可直接粘贴到任何 Mermaid 渲染器;本页不加载任何外部运行时。</p>
<code>```mermaid
{esc(mermaid)}
```</code></div>
<script>
document.querySelectorAll('.node').forEach(function (n) {{
  n.addEventListener('click', function () {{
    document.querySelectorAll('.node').forEach(function (m) {{ m.classList.remove('active'); }});
    n.classList.add('active');
    document.querySelectorAll('.d').forEach(function (d) {{ d.hidden = true; }});
    var t = document.getElementById(n.getAttribute('data-d'));
    if (t) {{ t.hidden = false; }}
    var ph = document.getElementById('placeholder'); if (ph) ph.remove();
  }});
}});
</script>
</body></html>"""

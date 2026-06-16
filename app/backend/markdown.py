from __future__ import annotations

from app.backend.models import Capture, Project, Task


def _frontmatter_list(values: list[str]) -> str:
    if not values:
        return "[]"
    return "\n".join(f"  - {value}" for value in values)


def render_capture_markdown(capture: Capture, created: str) -> str:
    tags = _frontmatter_list(capture.tags)
    return f"""---
type: {capture.kind}
status: {capture.status}
created: {created}
tags:
{tags if capture.tags else "  []"}
---

# {capture.title}

## 原始输入

{capture.raw_text}

## AI 整理结果

{capture.ai_output or "尚未生成 AI 整理结果。"}

## 人工确认

- 是否进入 todo：
- 所属项目：
- 下一步动作：
- 预期产出物：
"""


def render_task_line(task: Task) -> str:
    return (
        f"- [{task.status}] {task.title} | "
        f"下一步：{task.next_action or '未填写'} | "
        f"产出物：{task.expected_artifact or '未填写'}"
    )


def render_project_home(project: Project) -> str:
    tags = _frontmatter_list(project.tags)
    return f"""---
type: project
status: {project.status}
created: {project.created}
phase: {project.phase}
project_type: {project.project_type}
business_object: {project.business_object}
tags:
{tags if project.tags else "  []"}
---

# {project.title}

## 任务看板

### idea

### todo

### doing

### waiting

### done

## 下一步行动项讨论

- 当前最小启动动作：
- 外部推进建议：
- 自己开发注意点：

## 最近日志

- {project.created} 创建项目。

## 当前阻塞/等待反馈

- 暂无。

## 项目背景

请补充这个项目为什么存在、解决什么问题、涉及哪些业务对象。

## 当前结论

请补充已经被人工确认的结论。
"""

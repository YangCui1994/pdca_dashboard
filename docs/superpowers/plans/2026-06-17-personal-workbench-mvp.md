# Personal Workbench MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an extensible local web workbench that turns scattered work ideas, project tasks, AI critiques, daily plans, and follow-up notes into structured Markdown files.

**Architecture:** Use a dependency-light local app: Python standard-library HTTP backend, static HTML/CSS/JS frontend, Markdown vault storage, and a pluggable AI provider interface. The first AI provider calls Hermes through `hermes -z`, while the rest of the system talks only to a local `AIProvider` abstraction so Hermes proxy, aigate, or OpenCode can replace it later. AI actions also pass through a lightweight agent execution mode layer so simple document work can use one agent, while important decisions can later use Round Table debate or layered approval without rewriting the app workflow.

**Tech Stack:** Python 3 standard library, `unittest`, static HTML/CSS/JavaScript, local Markdown files, Hermes Agent CLI.

---

## MVP Design Baseline

This plan consolidates the prior brainstorming and grill-me discussion into one buildable baseline.

The first version is not a generic note app. It is a personal work-progress system for a user with many ideas, frequent interruptions, data-analysis tasks, platform follow-ups, and a need to turn scattered inputs into durable project memory.

The MVP supports one core loop:

```text
Capture input -> classify as idea/task/project note -> ask AI for critique or structure -> edit result -> save Markdown -> use daily workbench to pick today's work
```

Key product decisions already made:

- Projects are folders, not single giant Markdown files.
- Each project folder contains `project.md`, `tasks.md`, `log.md`, `ai-notes.md`, and `assets/`.
- Top-level vault folders are status-oriented: `inbox`, `active`, `waiting`, `done`, `archive`.
- Project metadata stores type, business object, tags, priority, and phase.
- Task states are `idea`, `todo`, `doing`, `waiting`, and `done`.
- `idea` is not a commitment. It enters execution only after AI or the user fills in project, value, next action, expected artifact, risk, and minimum MVP.
- AI must not only polish ideas; it must also point out execution-cost and communication-push risks.
- Daily planning uses a candidate pool. The user manually selects today's work.
- Unfinished items require a reason before being moved. Personal blockers and external blockers route differently.
- First implementation keeps AI suggestions at the project level. Task-level suggestions can be added after the project-level flow works.
- Agent execution must be selectable by mode. MVP implements the interface and keeps actual execution on `single` mode; `round-table` and `approval-chain` are represented as validated orchestration plans so later work can add multi-agent debate or staged review without changing capture, storage, or prompt APIs.
- Use `single` mode for information completion, document cleanup, summaries, and routine AI formatting.
- Use `round-table` mode for important decisions where different perspectives should argue before a recommendation is saved, such as product direction, prioritization, architecture choices, or high-risk communication strategy.
- Use `approval-chain` mode when output should pass through sequential checks, such as draft -> risk review -> final decision, or agent proposal -> human-ready recommendation.

## File Structure

Create this structure:

```text
app/
  __init__.py
  backend/
    __init__.py
    ai.py
    agent_modes.py
    app_state.py
    markdown.py
    models.py
    prompts.py
    server.py
    storage.py
  frontend/
    index.html
    styles.css
    app.js
  prompts/
    idea_critique.md
    structure_capture.md
    daily_review.md
data-issue-vault/
  inbox/
  active/
  waiting/
  done/
  archive/
tests/
  test_agent_modes.py
  test_ai.py
  test_markdown.py
  test_models.py
  test_storage.py
```

Responsibilities:

- `models.py`: domain dataclasses and allowed status values.
- `markdown.py`: deterministic Markdown rendering from domain objects.
- `storage.py`: safe file and folder creation inside the local vault.
- `prompts.py`: load prompt templates and render prompts with capture text.
- `ai.py`: provider interface, fake provider, Hermes CLI provider.
- `agent_modes.py`: validated orchestration plans for `single`, `round-table`, and `approval-chain` execution modes.
- `app_state.py`: high-level workflows used by HTTP routes.
- `server.py`: local JSON API and static file serving.
- `frontend/*`: three-column workbench UI.
- `app/prompts/*`: editable AI action templates.

## Task 1: Create App Skeleton And Vault Layout

**Files:**
- Create: `app/__init__.py`
- Create: `app/backend/__init__.py`
- Create: `app/prompts/idea_critique.md`
- Create: `app/prompts/structure_capture.md`
- Create: `app/prompts/daily_review.md`
- Create: `data-issue-vault/inbox/.gitkeep`
- Create: `data-issue-vault/active/.gitkeep`
- Create: `data-issue-vault/waiting/.gitkeep`
- Create: `data-issue-vault/done/.gitkeep`
- Create: `data-issue-vault/archive/.gitkeep`

- [x] **Step 1: Create package marker files**

Create `app/__init__.py`:

```python
"""Local personal workbench application."""
```

Create `app/backend/__init__.py`:

```python
"""Backend modules for the local personal workbench."""
```

- [x] **Step 2: Create prompt template for idea critique**

Create `app/prompts/idea_critique.md`:

```markdown
你是一个犀利但务实的工作推进教练。请审查下面这个 idea。

输出必须包含：

## 价值判断
- 这个 idea 解决什么真实问题：
- 是否值得进入 todo：

## 执行成本风险
- 最大依赖：
- 是否过度设计：
- 最小启动动作：

## 沟通推进风险
- 需要谁配合：
- 哪句话容易引起误解：
- 低摩擦推进方式：

## 最小 MVP
- 预期产出物：
- 30 分钟内能开始的第一步：

原始输入：
{{input}}
```

- [x] **Step 3: Create prompt template for structured capture**

Create `app/prompts/structure_capture.md`:

```markdown
请把下面的碎片输入整理成结构化工作卡片。

输出必须包含：

## 标题

## 类型
从 idea / task / project-note / data-issue / communication-draft 中选择一个。

## 所属项目

## 为什么值得做

## 下一步动作

## 预期产出物

## 主要风险

## 建议状态
从 idea / todo / doing / waiting / done 中选择一个。

原始输入：
{{input}}
```

- [x] **Step 4: Create prompt template for daily review**

Create `app/prompts/daily_review.md`:

```markdown
请把今天的工作记录整理成轻量复盘。

输出必须包含：

## 今天原计划

## 实际完成

## 计划调整原因

## 个人卡点
从启动慢 / 细节困住 / 任务定太满 / 注意力切换 / 精力不足中选择相关项。

## 外部卡点
从临时插单 / 等待反馈 / 需求变化 / 数据或权限缺失 / 他人依赖中选择相关项。

## 明天保留事项

## 明天第一启动动作

原始输入：
{{input}}
```

- [x] **Step 5: Create vault marker files**

Create empty `.gitkeep` files in each vault folder listed above. If using a shell:

```bash
mkdir -p data-issue-vault/inbox data-issue-vault/active data-issue-vault/waiting data-issue-vault/done data-issue-vault/archive
touch data-issue-vault/inbox/.gitkeep data-issue-vault/active/.gitkeep data-issue-vault/waiting/.gitkeep data-issue-vault/done/.gitkeep data-issue-vault/archive/.gitkeep
```

- [x] **Step 6: Verify skeleton**

Run:

```bash
find app data-issue-vault -maxdepth 3 -type f | sort
```

Expected output includes:

```text
app/__init__.py
app/backend/__init__.py
app/prompts/daily_review.md
app/prompts/idea_critique.md
app/prompts/structure_capture.md
data-issue-vault/active/.gitkeep
data-issue-vault/archive/.gitkeep
data-issue-vault/done/.gitkeep
data-issue-vault/inbox/.gitkeep
data-issue-vault/waiting/.gitkeep
```

## Task 2: Define Domain Models

**Files:**
- Create: `app/backend/models.py`
- Create: `tests/test_models.py`

- [x] **Step 1: Write failing model tests**

Create `tests/test_models.py`:

```python
import unittest

from app.backend.models import Capture, Project, Task, normalize_slug


class ModelTests(unittest.TestCase):
    def test_normalize_slug_keeps_chinese_and_ascii_words(self):
        self.assertEqual(normalize_slug("数据异常 Follow Up!"), "数据异常-follow-up")

    def test_task_requires_allowed_status(self):
        with self.assertRaises(ValueError):
            Task(title="Bad status", status="blocked")

    def test_capture_defaults_to_inbox(self):
        capture = Capture(raw_text="温度数据昨天突然跳变")
        self.assertEqual(capture.status, "inbox")
        self.assertEqual(capture.kind, "idea")

    def test_project_folder_name_uses_date_and_slug(self):
        project = Project(title="炉温异常排查", created="2026-06-17")
        self.assertEqual(project.folder_name(), "2026-06-17-炉温异常排查")


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m unittest tests/test_models.py
```

Expected: FAIL with `ModuleNotFoundError` or import error because `models.py` does not exist yet.

- [x] **Step 3: Implement domain models**

Create `app/backend/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Literal


TaskStatus = Literal["idea", "todo", "doing", "waiting", "done"]
CaptureKind = Literal["idea", "task", "project-note", "data-issue", "communication-draft"]
VaultStatus = Literal["inbox", "active", "waiting", "done", "archive"]

TASK_STATUSES = {"idea", "todo", "doing", "waiting", "done"}
CAPTURE_KINDS = {"idea", "task", "project-note", "data-issue", "communication-draft"}
VAULT_STATUSES = {"inbox", "active", "waiting", "done", "archive"}


def normalize_slug(value: str) -> str:
    lowered = value.strip().lower()
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", "-", lowered)
    collapsed = re.sub(r"-+", "-", cleaned).strip("-")
    return collapsed or "untitled"


@dataclass
class Task:
    title: str
    status: TaskStatus = "idea"
    project: str = ""
    value: str = ""
    next_action: str = ""
    expected_artifact: str = ""
    main_risk: str = ""
    minimum_mvp: str = ""

    def __post_init__(self) -> None:
        if self.status not in TASK_STATUSES:
            raise ValueError(f"Unsupported task status: {self.status}")


@dataclass
class Capture:
    raw_text: str
    title: str = "未命名输入"
    kind: CaptureKind = "idea"
    status: VaultStatus = "inbox"
    ai_output: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.kind not in CAPTURE_KINDS:
            raise ValueError(f"Unsupported capture kind: {self.kind}")
        if self.status not in VAULT_STATUSES:
            raise ValueError(f"Unsupported vault status: {self.status}")


@dataclass
class Project:
    title: str
    created: str
    status: VaultStatus = "active"
    project_type: str = ""
    business_object: str = ""
    phase: str = "探索"
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status not in VAULT_STATUSES:
            raise ValueError(f"Unsupported project status: {self.status}")

    def folder_name(self) -> str:
        return f"{self.created}-{normalize_slug(self.title)}"
```

- [x] **Step 4: Run model tests**

Run:

```bash
python3 -m unittest tests/test_models.py
```

Expected: PASS.

## Task 3: Render Markdown Deterministically

**Files:**
- Create: `app/backend/markdown.py`
- Create: `tests/test_markdown.py`

- [x] **Step 1: Write failing Markdown tests**

Create `tests/test_markdown.py`:

```python
import unittest

from app.backend.markdown import render_capture_markdown, render_project_home
from app.backend.models import Capture, Project


class MarkdownTests(unittest.TestCase):
    def test_render_capture_markdown_contains_frontmatter_and_raw_text(self):
        capture = Capture(
            title="炉温跳变",
            kind="data-issue",
            raw_text="昨晚炉温数据突然跳变",
            ai_output="建议先问平台是否有清洗逻辑变更",
            tags=["炉温", "平台核实"],
        )
        markdown = render_capture_markdown(capture, created="2026-06-17")
        self.assertIn("type: data-issue", markdown)
        self.assertIn("status: inbox", markdown)
        self.assertIn("- 炉温", markdown)
        self.assertIn("## 原始输入", markdown)
        self.assertIn("昨晚炉温数据突然跳变", markdown)
        self.assertIn("## AI 整理结果", markdown)

    def test_render_project_home_prioritizes_progress_context(self):
        project = Project(title="炉温异常排查", created="2026-06-17", tags=["炉温"])
        markdown = render_project_home(project)
        self.assertTrue(markdown.startswith("---"))
        self.assertIn("# 炉温异常排查", markdown)
        self.assertLess(markdown.index("## 任务看板"), markdown.index("## 项目背景"))
        self.assertIn("## 下一步行动项讨论", markdown)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m unittest tests/test_markdown.py
```

Expected: FAIL because `markdown.py` does not exist.

- [x] **Step 3: Implement Markdown rendering**

Create `app/backend/markdown.py`:

```python
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
```

- [x] **Step 4: Run Markdown tests**

Run:

```bash
python3 -m unittest tests/test_markdown.py
```

Expected: PASS.

## Task 4: Implement Vault Storage

**Files:**
- Create: `app/backend/storage.py`
- Create: `tests/test_storage.py`

- [x] **Step 1: Write failing storage tests**

Create `tests/test_storage.py`:

```python
import tempfile
import unittest
from pathlib import Path

from app.backend.models import Capture, Project
from app.backend.storage import VaultStorage


class StorageTests(unittest.TestCase):
    def test_save_capture_writes_to_inbox(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            path = storage.save_capture(Capture(title="炉温跳变", raw_text="数据跳变"), created="2026-06-17")
            self.assertEqual(path.parent.name, "inbox")
            self.assertTrue(path.name.endswith("炉温跳变.md"))
            self.assertIn("数据跳变", path.read_text(encoding="utf-8"))

    def test_create_project_writes_project_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = VaultStorage(Path(temp_dir))
            folder = storage.create_project(Project(title="炉温异常排查", created="2026-06-17"))
            self.assertTrue((folder / "project.md").exists())
            self.assertTrue((folder / "tasks.md").exists())
            self.assertTrue((folder / "log.md").exists())
            self.assertTrue((folder / "ai-notes.md").exists())
            self.assertTrue((folder / "assets").is_dir())


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m unittest tests/test_storage.py
```

Expected: FAIL because `storage.py` does not exist.

- [x] **Step 3: Implement vault storage**

Create `app/backend/storage.py`:

```python
from __future__ import annotations

from pathlib import Path

from app.backend.markdown import render_capture_markdown, render_project_home
from app.backend.models import Capture, Project, normalize_slug


class VaultStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.ensure_layout()

    def ensure_layout(self) -> None:
        for folder in ("inbox", "active", "waiting", "done", "archive"):
            (self.root / folder).mkdir(parents=True, exist_ok=True)

    def save_capture(self, capture: Capture, created: str) -> Path:
        folder = self.root / capture.status
        folder.mkdir(parents=True, exist_ok=True)
        filename = f"{created}-{normalize_slug(capture.title)}.md"
        path = folder / filename
        path.write_text(render_capture_markdown(capture, created), encoding="utf-8")
        return path

    def create_project(self, project: Project) -> Path:
        folder = self.root / project.status / project.folder_name()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "assets").mkdir(exist_ok=True)
        (folder / "project.md").write_text(render_project_home(project), encoding="utf-8")
        (folder / "tasks.md").write_text("# Tasks\n\n", encoding="utf-8")
        (folder / "log.md").write_text("# Log\n\n", encoding="utf-8")
        (folder / "ai-notes.md").write_text("# AI Notes\n\n", encoding="utf-8")
        return folder

    def list_markdown_files(self) -> list[Path]:
        return sorted(self.root.glob("**/*.md"))
```

- [x] **Step 4: Run storage tests**

Run:

```bash
python3 -m unittest tests/test_storage.py
```

Expected: PASS.

## Task 5: Implement Prompt Loading And AI Provider Interface

**Files:**
- Create: `app/backend/prompts.py`
- Create: `app/backend/ai.py`
- Create: `tests/test_ai.py`

- [x] **Step 1: Write failing AI tests**

Create `tests/test_ai.py`:

```python
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from app.backend.ai import FakeAIProvider, HermesCLIProvider
from app.backend.prompts import render_prompt


class AITests(unittest.TestCase):
    def test_render_prompt_replaces_input_marker(self):
        prompt = render_prompt(Path("app/prompts/structure_capture.md"), "原始想法")
        self.assertIn("原始想法", prompt)
        self.assertNotIn("{{input}}", prompt)

    def test_fake_provider_returns_predictable_text(self):
        provider = FakeAIProvider()
        self.assertEqual(provider.complete("hello"), "[fake-ai]\nhello")

    def test_hermes_provider_calls_oneshot_mode(self):
        completed = subprocess.CompletedProcess(args=["hermes"], returncode=0, stdout="整理完成\n", stderr="")
        with patch("subprocess.run", return_value=completed) as run:
            provider = HermesCLIProvider(binary="/Users/yang/.local/bin/hermes")
            result = provider.complete("请整理")
        self.assertEqual(result, "整理完成")
        run.assert_called_once()
        args = run.call_args.args[0]
        self.assertEqual(args[0], "/Users/yang/.local/bin/hermes")
        self.assertIn("-z", args)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m unittest tests/test_ai.py
```

Expected: FAIL because `ai.py` and `prompts.py` do not exist.

- [x] **Step 3: Implement prompt rendering**

Create `app/backend/prompts.py`:

```python
from __future__ import annotations

from pathlib import Path


def render_prompt(template_path: Path, user_input: str) -> str:
    template = template_path.read_text(encoding="utf-8")
    return template.replace("{{input}}", user_input)
```

- [x] **Step 4: Implement AI providers**

Create `app/backend/ai.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import subprocess
from typing import Protocol


class AIProvider(Protocol):
    def complete(self, prompt: str) -> str:
        raise NotImplementedError


@dataclass
class FakeAIProvider:
    def complete(self, prompt: str) -> str:
        return f"[fake-ai]\n{prompt}"


@dataclass
class HermesCLIProvider:
    binary: str = "/Users/yang/.local/bin/hermes"
    timeout_seconds: int = 120

    def complete(self, prompt: str) -> str:
        completed = subprocess.run(
            [self.binary, "-z", prompt],
            check=False,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            message = stderr or f"Hermes exited with code {completed.returncode}"
            raise RuntimeError(message)
        return completed.stdout.strip()
```

- [x] **Step 5: Run AI tests**

Run:

```bash
python3 -m unittest tests/test_ai.py
```

Expected: PASS.

## Task 5A: Define Agent Execution Modes

**Files:**
- Create: `app/backend/agent_modes.py`
- Create: `tests/test_agent_modes.py`

This task adds the interface for selecting how an AI action should be executed. MVP execution still uses one provider call, but the workflow can now carry a validated orchestration plan for future modes.

- `single`: one agent completes the task. Use for information completion, document cleanup, summarization, and routine formatting.
- `round-table`: multiple named roles debate a high-stakes decision before producing a recommendation. Use for product direction, prioritization, architecture choices, or sensitive communication strategy.
- `approval-chain`: output passes through ordered reviewers before being accepted. Use for proposal review, risk review, or human-ready finalization.

- [x] **Step 1: Write failing agent mode tests**

Create `tests/test_agent_modes.py`:

```python
import unittest

from app.backend.agent_modes import (
    AgentRole,
    create_approval_chain_plan,
    create_round_table_plan,
    create_single_agent_plan,
)


class AgentModeTests(unittest.TestCase):
    def test_single_agent_plan_has_one_executor_role(self):
        plan = create_single_agent_plan(action="structure_capture", prompt="整理这段输入")
        self.assertEqual(plan.mode, "single")
        self.assertEqual([role.name for role in plan.roles], ["executor"])
        self.assertEqual(plan.approval_steps, [])

    def test_round_table_requires_at_least_two_roles(self):
        with self.assertRaises(ValueError):
            create_round_table_plan(
                prompt="是否推进这个项目",
                roles=[AgentRole(name="product", responsibility="判断用户价值")],
            )

    def test_round_table_keeps_role_responsibilities(self):
        plan = create_round_table_plan(
            prompt="是否推进这个项目",
            roles=[
                AgentRole(name="product", responsibility="判断用户价值"),
                AgentRole(name="engineering", responsibility="判断实现成本"),
                AgentRole(name="risk", responsibility="指出推进风险"),
            ],
        )
        self.assertEqual(plan.mode, "round-table")
        self.assertEqual(plan.roles[1].responsibility, "判断实现成本")

    def test_approval_chain_preserves_ordered_review_steps(self):
        plan = create_approval_chain_plan(
            prompt="生成领导反馈草稿",
            reviewers=["risk-review", "final-editor"],
        )
        self.assertEqual(plan.mode, "approval-chain")
        self.assertEqual(plan.approval_steps, ["risk-review", "final-editor"])


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m unittest tests/test_agent_modes.py
```

Expected: FAIL because `agent_modes.py` does not exist.

- [x] **Step 3: Implement agent mode data structures**

Create `app/backend/agent_modes.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


AgentExecutionMode = Literal["single", "round-table", "approval-chain"]

AGENT_EXECUTION_MODES = {"single", "round-table", "approval-chain"}


@dataclass(frozen=True)
class AgentRole:
    name: str
    responsibility: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Agent role name is required")
        if not self.responsibility.strip():
            raise ValueError("Agent role responsibility is required")


@dataclass(frozen=True)
class AgentExecutionPlan:
    mode: AgentExecutionMode
    prompt: str
    roles: list[AgentRole] = field(default_factory=list)
    approval_steps: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.mode not in AGENT_EXECUTION_MODES:
            raise ValueError(f"Unsupported agent execution mode: {self.mode}")
        if not self.prompt.strip():
            raise ValueError("Agent execution prompt is required")
        if self.mode == "single" and len(self.roles) != 1:
            raise ValueError("Single agent mode requires exactly one role")
        if self.mode == "round-table" and len(self.roles) < 2:
            raise ValueError("Round table mode requires at least two roles")
        if self.mode == "approval-chain" and not self.approval_steps:
            raise ValueError("Approval chain mode requires at least one approval step")


def create_single_agent_plan(action: str, prompt: str) -> AgentExecutionPlan:
    return AgentExecutionPlan(
        mode="single",
        prompt=prompt,
        roles=[AgentRole(name="executor", responsibility=f"Complete AI action: {action}")],
    )


def create_round_table_plan(prompt: str, roles: list[AgentRole]) -> AgentExecutionPlan:
    return AgentExecutionPlan(mode="round-table", prompt=prompt, roles=roles)


def create_approval_chain_plan(prompt: str, reviewers: list[str]) -> AgentExecutionPlan:
    clean_reviewers = [reviewer.strip() for reviewer in reviewers if reviewer.strip()]
    return AgentExecutionPlan(
        mode="approval-chain",
        prompt=prompt,
        roles=[AgentRole(name="executor", responsibility="Create the first draft")],
        approval_steps=clean_reviewers,
    )
```

- [x] **Step 4: Run agent mode tests**

Run:

```bash
python3 -m unittest tests/test_agent_modes.py
```

Expected: PASS.

- [x] **Step 5: Run all tests**

Run:

```bash
python3 -m unittest discover tests
```

Expected: PASS.

## Task 6: Implement Application Workflows

**Files:**
- Create: `app/backend/app_state.py`
- Modify: `tests/test_storage.py`

- [x] **Step 1: Add workflow test**

Append this test class to `tests/test_storage.py` before the `if __name__ == "__main__"` block:

```python
from app.backend.ai import FakeAIProvider
from app.backend.app_state import WorkbenchApp


class WorkbenchAppTests(unittest.TestCase):
    def test_capture_with_ai_saves_markdown_and_ai_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app = WorkbenchApp(vault_root=Path(temp_dir), ai_provider=FakeAIProvider())
            result = app.capture_with_ai(
                raw_text="这个炉温跳变可能是平台清洗问题",
                action="structure_capture",
                title="炉温跳变",
                kind="data-issue",
            )
            saved_path = Path(result["path"])
            self.assertTrue(saved_path.exists())
            content = saved_path.read_text(encoding="utf-8")
            self.assertIn("[fake-ai]", content)
            self.assertIn("炉温跳变", content)
```

- [x] **Step 2: Run workflow test to verify failure**

Run:

```bash
python3 -m unittest tests/test_storage.py
```

Expected: FAIL because `app_state.py` does not exist.

- [x] **Step 3: Implement workflow layer**

Create `app/backend/app_state.py`:

```python
from __future__ import annotations

from datetime import date
from pathlib import Path

from app.backend.ai import AIProvider, FakeAIProvider
from app.backend.models import Capture, CaptureKind
from app.backend.prompts import render_prompt
from app.backend.storage import VaultStorage


PROMPT_MAP = {
    "idea_critique": Path("app/prompts/idea_critique.md"),
    "structure_capture": Path("app/prompts/structure_capture.md"),
    "daily_review": Path("app/prompts/daily_review.md"),
}


class WorkbenchApp:
    def __init__(self, vault_root: Path, ai_provider: AIProvider | None = None) -> None:
        self.storage = VaultStorage(vault_root)
        self.ai_provider = ai_provider or FakeAIProvider()

    def capture_with_ai(
        self,
        raw_text: str,
        action: str,
        title: str = "未命名输入",
        kind: CaptureKind = "idea",
    ) -> dict[str, str]:
        if action not in PROMPT_MAP:
            raise ValueError(f"Unsupported AI action: {action}")
        prompt = render_prompt(PROMPT_MAP[action], raw_text)
        ai_output = self.ai_provider.complete(prompt)
        capture = Capture(title=title, kind=kind, raw_text=raw_text, ai_output=ai_output)
        path = self.storage.save_capture(capture, created=date.today().isoformat())
        return {"path": str(path), "ai_output": ai_output}

    def list_files(self) -> list[str]:
        return [str(path) for path in self.storage.list_markdown_files()]
```

- [x] **Step 4: Run workflow tests**

Run:

```bash
python3 -m unittest tests/test_storage.py
```

Expected: PASS.

## Task 7: Implement Local HTTP Server

**Files:**
- Create: `app/backend/server.py`

- [x] **Step 1: Create server with JSON routes and static serving**

Create `app/backend/server.py`:

```python
from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from app.backend.ai import FakeAIProvider, HermesCLIProvider
from app.backend.app_state import WorkbenchApp


def build_ai_provider(name: str):
    if name == "hermes":
        return HermesCLIProvider()
    if name == "fake":
        return FakeAIProvider()
    raise ValueError(f"Unsupported provider: {name}")


class WorkbenchHandler(SimpleHTTPRequestHandler):
    app_state: WorkbenchApp
    static_root: Path

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/files":
            self._send_json({"files": self.app_state.list_files()})
            return
        if parsed.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/capture":
            payload = self._read_json()
            result = self.app_state.capture_with_ai(
                raw_text=payload.get("raw_text", ""),
                action=payload.get("action", "structure_capture"),
                title=payload.get("title", "未命名输入"),
                kind=payload.get("kind", "idea"),
            )
            self._send_json(result)
            return
        self.send_error(404, "Route not found")

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        relative = parsed.path.lstrip("/") or "index.html"
        return str(self.static_root / relative)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        if not raw:
            return {}
        return json.loads(raw)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--provider", choices=["fake", "hermes"], default="fake")
    parser.add_argument("--vault", default="data-issue-vault")
    args = parser.parse_args()

    WorkbenchHandler.static_root = Path("app/frontend").resolve()
    WorkbenchHandler.app_state = WorkbenchApp(
        vault_root=Path(args.vault),
        ai_provider=build_ai_provider(args.provider),
    )

    server = ThreadingHTTPServer((args.host, args.port), WorkbenchHandler)
    print(f"Workbench running at http://{args.host}:{args.port}")
    print(f"AI provider: {args.provider}")
    server.serve_forever()


if __name__ == "__main__":
    main()
```

- [x] **Step 2: Run import check**

Run:

```bash
python3 -m app.backend.server --help
```

Expected output contains:

```text
--provider {fake,hermes}
--vault VAULT
```

## Task 8: Build Static Frontend

**Files:**
- Create: `app/frontend/index.html`
- Create: `app/frontend/styles.css`
- Create: `app/frontend/app.js`

- [ ] **Step 1: Create HTML shell**

Create `app/frontend/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Personal Workbench</title>
    <link rel="stylesheet" href="/styles.css">
  </head>
  <body>
    <main class="workspace">
      <aside class="panel inbox-panel">
        <div class="panel-header">
          <h1>Workbench</h1>
          <button id="refreshFiles" title="刷新文件列表">↻</button>
        </div>
        <ul id="fileList" class="file-list"></ul>
      </aside>

      <section class="panel capture-panel">
        <label>
          标题
          <input id="titleInput" type="text" value="未命名输入">
        </label>
        <label>
          类型
          <select id="kindInput">
            <option value="idea">idea</option>
            <option value="task">task</option>
            <option value="project-note">project-note</option>
            <option value="data-issue">data-issue</option>
            <option value="communication-draft">communication-draft</option>
          </select>
        </label>
        <label>
          原始输入
          <textarea id="rawInput" rows="16" placeholder="写下异常、想法、领导需求、沟通草稿或字段口径疑问"></textarea>
        </label>
      </section>

      <section class="panel ai-panel">
        <div class="actions">
          <button data-action="structure_capture">整理成卡片</button>
          <button data-action="idea_critique">犀利审查 idea</button>
          <button data-action="daily_review">生成日复盘</button>
        </div>
        <div id="statusText" class="status-text">等待输入。</div>
        <label>
          AI 输出
          <textarea id="aiOutput" rows="20"></textarea>
        </label>
        <div class="saved-path" id="savedPath"></div>
      </section>
    </main>
    <script src="/app.js"></script>
  </body>
</html>
```

- [ ] **Step 2: Create CSS**

Create `app/frontend/styles.css`:

```css
:root {
  color-scheme: light;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #f6f7f2;
  color: #1f2933;
}

body {
  margin: 0;
}

.workspace {
  display: grid;
  grid-template-columns: 280px minmax(360px, 1fr) minmax(360px, 1fr);
  gap: 1px;
  min-height: 100vh;
  background: #c8d0d8;
}

.panel {
  background: #ffffff;
  padding: 18px;
  overflow: auto;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

h1 {
  font-size: 20px;
  margin: 0;
}

label {
  display: grid;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  font-weight: 650;
}

input,
select,
textarea {
  box-sizing: border-box;
  width: 100%;
  border: 1px solid #c8d0d8;
  border-radius: 6px;
  padding: 10px;
  font: inherit;
}

textarea {
  resize: vertical;
  line-height: 1.5;
}

button {
  border: 1px solid #9aa6b2;
  border-radius: 6px;
  background: #1f2933;
  color: #ffffff;
  padding: 9px 12px;
  font: inherit;
  cursor: pointer;
}

button:hover {
  background: #334155;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

.status-text,
.saved-path {
  min-height: 22px;
  margin-bottom: 12px;
  color: #52606d;
  font-size: 13px;
}

.file-list {
  list-style: none;
  padding: 0;
  margin: 16px 0 0;
}

.file-list li {
  border-bottom: 1px solid #e4e7eb;
  padding: 8px 0;
  font-size: 13px;
  overflow-wrap: anywhere;
}

@media (max-width: 960px) {
  .workspace {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 3: Create frontend behavior**

Create `app/frontend/app.js`:

```javascript
const titleInput = document.querySelector("#titleInput");
const kindInput = document.querySelector("#kindInput");
const rawInput = document.querySelector("#rawInput");
const aiOutput = document.querySelector("#aiOutput");
const statusText = document.querySelector("#statusText");
const savedPath = document.querySelector("#savedPath");
const fileList = document.querySelector("#fileList");
const refreshFiles = document.querySelector("#refreshFiles");

async function refreshFileList() {
  const response = await fetch("/api/files");
  const payload = await response.json();
  fileList.innerHTML = "";
  for (const file of payload.files) {
    const item = document.createElement("li");
    item.textContent = file;
    fileList.appendChild(item);
  }
}

async function runAction(action) {
  const rawText = rawInput.value.trim();
  if (!rawText) {
    statusText.textContent = "请先输入内容。";
    return;
  }
  statusText.textContent = "AI 正在处理。";
  savedPath.textContent = "";
  const response = await fetch("/api/capture", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      title: titleInput.value.trim() || "未命名输入",
      kind: kindInput.value,
      raw_text: rawText,
      action
    })
  });
  if (!response.ok) {
    statusText.textContent = `请求失败：${response.status}`;
    return;
  }
  const payload = await response.json();
  aiOutput.value = payload.ai_output;
  savedPath.textContent = `已保存：${payload.path}`;
  statusText.textContent = "完成。";
  await refreshFileList();
}

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => runAction(button.dataset.action));
});

refreshFiles.addEventListener("click", refreshFileList);
refreshFileList();
```

- [ ] **Step 4: Run frontend smoke check**

Run:

```bash
python3 -m app.backend.server --provider fake --port 8765
```

Expected terminal output:

```text
Workbench running at http://127.0.0.1:8765
AI provider: fake
```

Open `http://127.0.0.1:8765`, enter text, click `整理成卡片`, and confirm a Markdown file appears in `data-issue-vault/inbox/`.

## Task 9: Verify Hermes Provider Manually

**Files:**
- No file changes.

- [ ] **Step 1: Test Hermes directly**

Run:

```bash
/Users/yang/.local/bin/hermes -z "请只回复：Hermes OK"
```

Expected: final response contains `Hermes OK` or a close Chinese equivalent confirming the request.

- [ ] **Step 2: Run server with Hermes provider**

Run:

```bash
python3 -m app.backend.server --provider hermes --port 8765
```

Expected terminal output:

```text
Workbench running at http://127.0.0.1:8765
AI provider: hermes
```

- [ ] **Step 3: Test one AI action through the browser**

Open `http://127.0.0.1:8765`, enter:

```text
我怀疑昨晚炉温数据跳变不是业务真实变化，而是平台清洗逻辑变化，需要问平台同事。
```

Click `犀利审查 idea`.

Expected result:

- `AI 输出` contains sections for value judgment, execution-cost risk, communication-push risk, and minimum MVP.
- `data-issue-vault/inbox/` contains a new Markdown file with the same AI output.

## Task 10: Run Full Verification

**Files:**
- No file changes.

- [ ] **Step 1: Run all automated tests**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Verify no placeholders in created source files**

Run:

```bash
rg -n "T[B]D|TO[D]O|implement [l]ater|fill in [d]etails" app tests docs/superpowers/plans
```

Expected: no matches in `app/` or `tests/`. The plan file may contain the phrase list in the skill-derived self-review section only if copied there; this plan avoids those markers in implementation steps.

- [ ] **Step 3: Verify vault output**

Run:

```bash
find data-issue-vault -maxdepth 3 -type f | sort
```

Expected: marker files are present, and after browser testing at least one `.md` file exists under `data-issue-vault/inbox/`.

- [ ] **Step 4: Check Git availability**

Run:

```bash
git status --short
```

Expected in the current workspace: this may print `fatal: not a git repository`. If so, skip commit steps and tell the user the workspace is not under Git. If a repository has been initialized before execution, commit after each completed task group.

## Self-Review

Spec coverage:

- Project-folder structure is covered by Task 4.
- Status-oriented vault layout is covered by Task 1 and Task 4.
- `idea / todo / doing / waiting / done` task states are covered by Task 2.
- AI critique and structured capture are covered by Task 1, Task 5, and Task 6.
- Hermes `-z` provider is covered by Task 5 and Task 9.
- Local web UI is covered by Task 7 and Task 8.
- Markdown persistence is covered by Task 3, Task 4, and Task 6.
- Daily review prompt is covered by Task 1 and Task 8.

Placeholder scan:

- Implementation steps define concrete paths, commands, and expected outputs.
- Code snippets use concrete function names and file names.
- No step asks the implementer to invent missing behavior.

Type consistency:

- `Capture.kind` values match frontend `<select>` values.
- `action` values in frontend buttons match `PROMPT_MAP`.
- `VaultStorage.save_capture()` accepts `Capture` and a date string as used by `WorkbenchApp`.
- `HermesCLIProvider.complete()` returns text consumed by `WorkbenchApp.capture_with_ai()`.

Execution handoff:

- Recommended execution mode: subagent-driven per task once this plan is reviewed.
- Inline execution is also feasible because this MVP has no external package installation step.

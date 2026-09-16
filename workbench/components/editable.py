"""可编辑文本组件:双击进入编辑(无铅笔等常驻图标)。

提交语义:单行 Enter/失焦提交,内容不变则什么都不发生;多行编辑器
配「保存/取消」按钮。Flet 0.86 的 TextField 没有 Esc 事件,取消只能
靠按钮或把内容改回去——这是平台限制,不是遗漏。
"""

from __future__ import annotations

import flet as ft

from workbench.components import FONT_BODY, THEME


def _safe_update(control) -> None:
    """Repaint when attached to a page; stay silent in off-page tests."""

    try:
        control.update()
    except Exception:
        pass


def _field_style(size: int, multiline: bool) -> dict:
    return dict(
        text_size=size,
        multiline=multiline,
        border_color=THEME["border"],
        focused_border_color=THEME["purple"],
        content_padding=ft.Padding(left=8, top=6, right=8, bottom=6)
        if not multiline
        else ft.Padding(left=10, top=8, right=10, bottom=8),
        color=THEME["text"],
        cursor_color=THEME["purple"],
    )


def build_editable_label(
    value: str,
    on_commit,
    *,
    size: int = FONT_BODY,
    weight=None,
    color=None,
    placeholder: str = "双击填写",
    expand: bool = True,
    on_refresh=None,
) -> ft.Container:
    """单行可编辑标签:双击文字进入编辑,悬停 tooltip 提示。"""

    state = {"editing": False}

    def display(shown: str) -> ft.Control:
        text = ft.Text(
            shown or placeholder,
            size=size,
            weight=weight,
            color=color or (THEME["text"] if shown else THEME["text_faint"]),
        )
        return ft.GestureDetector(
            content=text,
            on_double_tap=lambda _e: enter_edit(),
        )

    def restore(shown: str):
        state["editing"] = False
        box.content = display(shown)
        _safe_update(box)

    def commit(_e=None):
        if not state["editing"]:
            return
        new = (field.value or "").strip()
        restore(new or value)
        if new and new != value:
            on_commit(new)
            if on_refresh is not None:
                on_refresh()

    def enter_edit(_e=None):
        if state["editing"]:
            return
        state["editing"] = True
        # STRETCH 列让输入框占满标签区域的宽度,不缩成窄方块。
        box.content = ft.Column(
            [field], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
        field.value = value
        _safe_update(box)

    field = ft.TextField(
        hint_text=placeholder,
        autofocus=True,
        on_submit=commit,
        on_blur=commit,
        **_field_style(size, multiline=False),
    )
    box = ft.Container(
        content=display(value), expand=expand, tooltip="双击编辑"
    )
    return box


def build_editable_markdown(
    value: str,
    on_commit,
    *,
    on_refresh=None,
    min_lines: int = 10,
    empty_hint: str = "双击此处开始记录",
) -> ft.Container:
    """多行 Markdown 编辑:双击正文进入编辑,保存/取消按钮提交。"""

    state = {"editing": False}

    def preview(shown: str) -> ft.Control:
        body = (
            ft.Markdown(shown, selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_WEB)
            if shown
            else ft.Text(empty_hint, color=THEME["text_faint"])
        )
        return ft.GestureDetector(
            content=body,
            on_double_tap=lambda _e: enter_edit(),
        )

    def restore(shown: str):
        state["editing"] = False
        box.content = preview(shown)
        _safe_update(box)

    def save(_e=None):
        if not state["editing"]:
            return
        new = field.value or ""
        restore(new)
        if new != value:
            on_commit(new)
            if on_refresh is not None:
                on_refresh()

    def enter_edit():
        if state["editing"]:
            return
        state["editing"] = True
        # STRETCH 让输入框占满卡片宽度;min_lines 按现有内容行数抬高,
        # 多行 TextField 未设 max_lines,内容增多时框随内容向下生长。
        box.content = ft.Column(
            [
                field,
                ft.Row(
                    [
                        ft.FilledButton("保存", icon=ft.Icons.CHECK, on_click=save),
                        ft.OutlinedButton("取消", on_click=lambda _e: restore(value)),
                    ],
                    spacing=8,
                ),
            ],
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        field.value = value
        field.min_lines = max(min_lines, value.count("\n") + 1)
        _safe_update(box)

    field = ft.TextField(
        **_field_style(FONT_BODY, multiline=True), min_lines=min_lines
    )
    box = ft.Container(content=preview(value))
    return box


def build_add_row(hint: str, on_add, *, on_refresh=None, label="添加计划项") -> ft.Container:
    """列表底部的「＋ 添加」行:点击变输入框,回车提交,失焦取消。"""

    state = {"editing": False}

    def idle() -> ft.Control:
        return ft.TextButton(
            label,  # 加号由 icon 提供,文字里不再重复
            icon=ft.Icons.ADD,
            style=ft.ButtonStyle(
                color=THEME["text_sub"],
                padding=ft.Padding(left=0, top=2, right=8, bottom=2),
            ),
            on_click=lambda _e: enter(),
        )

    def restore():
        state["editing"] = False
        box.content = idle()
        _safe_update(box)

    def commit(_e=None):
        if not state["editing"]:
            return
        new = (field.value or "").strip()
        restore()
        if new:
            on_add(new)
            if on_refresh is not None:
                on_refresh()

    def enter():
        if state["editing"]:
            return
        state["editing"] = True
        box.content = ft.Column(
            [field], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
        field.value = ""
        _safe_update(box)

    field = ft.TextField(
        hint_text=hint,
        autofocus=True,
        on_submit=commit,
        on_blur=commit,
        **_field_style(FONT_BODY, multiline=False),
    )
    box = ft.Container(content=idle())
    return box

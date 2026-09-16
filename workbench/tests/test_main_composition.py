"""构建自检门(发布三道门之一):FakePage 组合渲染全部路由,只构建不启动。

实测能抓到「Row 参数名写错 / detail_panel 顺序 / 构建期 AttributeError」
这类树遍历契约抓不到的组装错误。
"""

import unittest

from workbench import main as main_module
from workbench.domain.fixtures import load_demo_workspace
from workbench.runtime.text_runtime import FakePromptRuntime
from workbench.services.prompt_library import PromptLibrary
from workbench.services.workspace_service import WorkspaceService

_ROUTES = (
    "/today",
    "/ideas",
    "/projects",
    "/projects/proj-atlas",
    "/projects/proj-atlas/node/node-tests",
    "/activity",
    "/archive",
)


class _FakePage:
    """只实现 WorkbenchApp.render() 用到的页面表面。"""

    def __init__(self):
        self.route = "/today"
        self.controls = []
        self.on_route_change = None
        self.title = ""
        self.padding = 0
        self.bgcolor = None
        self.fonts = {}
        self.theme = None
        self.window = None

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self):
        pass

    def go(self, route):
        self.route = route
        if self.on_route_change is not None:
            self.on_route_change(None)


class BuildSelfCheckTests(unittest.TestCase):
    def test_every_route_composes_without_error(self):
        projects, activity = load_demo_workspace()
        service = WorkspaceService(projects, activity)
        page = _FakePage()
        app = main_module.WorkbenchApp(page, service, FakeRuntimeStub())
        main_module._LIBRARY = PromptLibrary()
        main_module._TEXT_RUNTIME = FakePromptRuntime()
        try:
            for route in _ROUTES:
                page.route = route
                app.render()
                self.assertEqual(len(page.controls), 1, f"路由 {route} 应产出一棵页面树")
                page.controls.clear()
            # AI 面板开启态(草稿卡主控台)也要能组装
            app.ai_open = True
            page.route = "/projects/proj-atlas"
            app.render()
            self.assertEqual(len(page.controls), 1, "AI 面板开启态应产出一棵页面树")
            page.controls.clear()
        finally:
            main_module._LIBRARY = None
            main_module._TEXT_RUNTIME = None


class FakeRuntimeStub:
    """review runtime 桩:render() 不消费事件流,events 永不被调用。"""

    def events(self, request):
        return iter(())


if __name__ == "__main__":
    unittest.main()

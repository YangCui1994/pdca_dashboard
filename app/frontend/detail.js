const detailTitle = document.querySelector("#detailTitle");
const detailPath = document.querySelector("#detailPath");
const detailStatus = document.querySelector("#detailStatus");
const taskEditor = document.querySelector("#taskEditor");
const contextEditor = document.querySelector("#contextEditor");
const aiNotesEditor = document.querySelector("#aiNotesEditor");
const agentContextOutput = document.querySelector("#agentContextOutput");
const assetList = document.querySelector("#assetList");
const saveButton = document.querySelector("#saveButton");
const agentContextButton = document.querySelector("#agentContextButton");

const params = new URLSearchParams(window.location.search);
const workItemPath = params.get("path") || "";

function setDetailStatus(message) {
  detailStatus.textContent = message;
}

async function loadWorkItem() {
  if (!workItemPath) {
    setDetailStatus("缺少任务路径。");
    return;
  }
  const response = await fetch(`/api/work-item?path=${encodeURIComponent(workItemPath)}`);
  if (!response.ok) {
    setDetailStatus(`加载失败：${response.status}`);
    return;
  }
  const item = await response.json();
  detailTitle.textContent = item.title;
  detailPath.textContent = item.path;
  taskEditor.value = item.task;
  contextEditor.value = item.context;
  aiNotesEditor.value = item.ai_notes;
  renderAssets(item.assets);
  setDetailStatus(`状态：${item.status}`);
}

function renderAssets(assets) {
  assetList.innerHTML = "";
  if (!assets.length) {
    const empty = document.createElement("li");
    empty.textContent = "暂无";
    assetList.appendChild(empty);
    return;
  }
  for (const asset of assets) {
    const item = document.createElement("li");
    item.textContent = asset;
    assetList.appendChild(item);
  }
}

async function saveWorkItem() {
  setDetailStatus("保存中。");
  const response = await fetch("/api/work-item", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      path: workItemPath,
      task: taskEditor.value,
      context: contextEditor.value,
      ai_notes: aiNotesEditor.value
    })
  });
  if (!response.ok) {
    setDetailStatus(`保存失败：${response.status}`);
    return;
  }
  setDetailStatus("已保存。");
}

async function loadAgentContext() {
  setDetailStatus("读取上下文中。");
  const response = await fetch(`/api/agent-context?path=${encodeURIComponent(workItemPath)}`);
  if (!response.ok) {
    setDetailStatus(`读取失败：${response.status}`);
    return;
  }
  const payload = await response.json();
  agentContextOutput.value = payload.context;
  setDetailStatus("上下文已读取。");
}

saveButton.addEventListener("click", saveWorkItem);
agentContextButton.addEventListener("click", loadAgentContext);
loadWorkItem();

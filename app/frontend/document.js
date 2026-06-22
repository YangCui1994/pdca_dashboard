const documentTitle = document.querySelector("#documentTitle");
const documentPath = document.querySelector("#documentPath");
const documentStatus = document.querySelector("#documentStatus");
const documentEditor = document.querySelector("#documentEditor");
const saveDocumentButton = document.querySelector("#saveDocumentButton");
const documentNav = document.querySelector("#documentNav");

const params = new URLSearchParams(window.location.search);
const workItemPath = params.get("path") || "";
const documentKind = document.body.dataset.documentKind;

const documentMap = {
  task: {label: "task.md", field: "task", page: "task.html"},
  context: {label: "context.md", field: "context", page: "context.html"},
  events: {label: "events.md", field: "events", page: "events.html"},
  "ai-notes": {label: "ai-notes.md", field: "ai_notes", page: "ai-notes.html"}
};

let currentItem = null;

function setDocumentStatus(message) {
  documentStatus.textContent = message;
}

function documentUrl(kind) {
  return `/${documentMap[kind].page}?path=${encodeURIComponent(workItemPath)}`;
}

function renderDocumentNav() {
  documentNav.innerHTML = "";
  for (const [kind, doc] of Object.entries(documentMap)) {
    const link = document.createElement("a");
    link.className = `nav-item${kind === documentKind ? " active" : ""}`;
    link.href = documentUrl(kind);
    link.textContent = doc.label;
    documentNav.appendChild(link);
  }
}

async function loadDocument() {
  if (!workItemPath) {
    setDocumentStatus("缺少任务路径。");
    return;
  }
  const documentConfig = documentMap[documentKind];
  if (!documentConfig) {
    setDocumentStatus("未知文档类型。");
    return;
  }
  const response = await fetch(`/api/work-item?path=${encodeURIComponent(workItemPath)}`);
  if (!response.ok) {
    setDocumentStatus(`加载失败：${response.status}`);
    return;
  }
  currentItem = await response.json();
  documentTitle.textContent = `${currentItem.title} · ${documentConfig.label}`;
  documentPath.textContent = `${currentItem.path}/${documentConfig.label}`;
  documentEditor.value = currentItem[documentConfig.field] || "";
  renderDocumentNav();
  setDocumentStatus(`状态：${currentItem.status}`);
}

async function saveDocument() {
  if (!currentItem) {
    setDocumentStatus("尚未加载文档。");
    return;
  }
  const documentConfig = documentMap[documentKind];
  const payload = {
    path: workItemPath,
    task: currentItem.task || "",
    context: currentItem.context || "",
    ai_notes: currentItem.ai_notes || "",
    events: currentItem.events || ""
  };
  payload[documentConfig.field] = documentEditor.value;
  setDocumentStatus("保存中。");
  const response = await fetch("/api/work-item", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    setDocumentStatus(`保存失败：${response.status}`);
    return;
  }
  currentItem[documentConfig.field] = documentEditor.value;
  setDocumentStatus("已保存。");
}

saveDocumentButton.addEventListener("click", saveDocument);
renderDocumentNav();
loadDocument();

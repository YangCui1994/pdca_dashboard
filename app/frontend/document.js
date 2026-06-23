const documentTitle = document.querySelector("#documentTitle");
const documentPath = document.querySelector("#documentPath");
const documentStatus = document.querySelector("#documentStatus");
const documentEditor = document.querySelector("#documentEditor");
const documentPreview = document.querySelector("#documentPreview");
const saveDocumentButton = document.querySelector("#saveDocumentButton");
const documentNav = document.querySelector("#documentNav");
const copyContextButton = document.querySelector("#copyContextButton");
const downloadContextButton = document.querySelector("#downloadContextButton");
const contextReadiness = document.querySelector("#contextReadiness");
const helperInput = document.querySelector("#helperInput");
const helperSkills = document.querySelector("#helperSkills");
const aiHelperButton = document.querySelector("#aiHelperButton");
const helperDraft = document.querySelector("#helperDraft");
const applyDraftButton = document.querySelector("#applyDraftButton");

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
let latestDraft = "";

function setDocumentStatus(message) {
  documentStatus.textContent = message;
}

function documentUrl(kind) {
  return `/${documentMap[kind].page}?path=${encodeURIComponent(workItemPath)}`;
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function stripFrontmatter(markdown) {
  if (!markdown.startsWith("---\n")) {
    return markdown;
  }
  const end = markdown.indexOf("\n---", 4);
  if (end === -1) {
    return markdown;
  }
  return markdown.slice(end + 4).trimStart();
}

function renderMarkdownPreview(markdown) {
  const lines = stripFrontmatter(markdown).split("\n");
  const html = [];
  let listOpen = false;
  let codeOpen = false;
  let paragraph = [];

  function flushParagraph() {
    if (!paragraph.length) {
      return;
    }
    html.push(`<p>${paragraph.join("<br>")}</p>`);
    paragraph = [];
  }

  function closeList() {
    if (!listOpen) {
      return;
    }
    html.push("</ul>");
    listOpen = false;
  }

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const trimmed = line.trim();
    if (trimmed.startsWith("```")) {
      flushParagraph();
      closeList();
      html.push(codeOpen ? "</code></pre>" : "<pre><code>");
      codeOpen = !codeOpen;
      continue;
    }
    if (codeOpen) {
      html.push(escapeHtml(rawLine));
      continue;
    }
    if (!trimmed) {
      flushParagraph();
      closeList();
      continue;
    }
    const heading = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      closeList();
      const level = heading[1].length;
      html.push(`<h${level}>${escapeHtml(heading[2])}</h${level}>`);
      continue;
    }
    const listItem = trimmed.match(/^[-*]\s+(.+)$/);
    if (listItem) {
      flushParagraph();
      if (!listOpen) {
        html.push("<ul>");
        listOpen = true;
      }
      html.push(`<li>${escapeHtml(listItem[1])}</li>`);
      continue;
    }
    paragraph.push(escapeHtml(trimmed));
  }
  flushParagraph();
  closeList();
  if (codeOpen) {
    html.push("</code></pre>");
  }
  return html.join("\n") || "<p>暂无内容。</p>";
}

function updateDocumentPreview() {
  if (!documentPreview) {
    return;
  }
  documentPreview.innerHTML = renderMarkdownPreview(documentEditor.value);
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
  updateDocumentPreview();
  renderDocumentNav();
  await loadContextReadiness();
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
  updateDocumentPreview();
  setDocumentStatus("已保存。");
  await loadContextReadiness();
}

async function runDocumentHelper() {
  if (!currentItem) {
    setDocumentStatus("尚未加载文档。");
    return;
  }
  const instruction = helperInput.value.trim();
  if (!instruction) {
    setDocumentStatus("请先输入要补充或修改的内容。");
    return;
  }
  setDocumentStatus("AI Helper 正在整理草稿。");
  const response = await fetch("/api/document-helper", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      path: workItemPath,
      document: documentKind,
      instruction,
      skills: helperSkills.value.trim()
    })
  });
  if (!response.ok) {
    setDocumentStatus(`AI Helper 失败：${response.status}`);
    return;
  }
  const payload = await response.json();
  latestDraft = payload.draft || "";
  helperDraft.value = latestDraft;
  documentPreview.innerHTML = renderMarkdownPreview(latestDraft);
  setDocumentStatus("草稿已生成。确认后可采用，再保存 Markdown。");
}

function applyHelperDraft() {
  const draft = latestDraft || helperDraft.value.trim();
  if (!draft) {
    setDocumentStatus("没有可采用的草稿。");
    return;
  }
  documentEditor.value = draft;
  updateDocumentPreview();
  setDocumentStatus("草稿已采用到 Markdown 编辑器；保存后才会写入文件。");
}

async function fetchAgentContext() {
  const response = await fetch(`/api/agent-context?path=${encodeURIComponent(workItemPath)}`);
  if (!response.ok) {
    throw new Error(`Agent Context 加载失败：${response.status}`);
  }
  const payload = await response.json();
  return payload.context || "";
}

async function loadContextReadiness() {
  if (!contextReadiness || !workItemPath) {
    return;
  }
  const response = await fetch(`/api/context-readiness?path=${encodeURIComponent(workItemPath)}`);
  if (!response.ok) {
    contextReadiness.textContent = `Context readiness 加载失败：${response.status}`;
    return;
  }
  const payload = await response.json();
  const missing = payload.missing && payload.missing.length ? payload.missing.join("；") : "无缺口";
  contextReadiness.textContent = `Agent Context ready: ${payload.ready ? "yes" : "no"} · ${missing}`;
}

async function copyAgentContext() {
  try {
    const context = await fetchAgentContext();
    await navigator.clipboard.writeText(context);
    setDocumentStatus("Agent Context 已复制。");
  } catch (error) {
    setDocumentStatus(error.message);
  }
}

async function downloadAgentContext() {
  try {
    const context = await fetchAgentContext();
    const blob = new Blob([context], {type: "text/markdown;charset=utf-8"});
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${currentItem.title || "agent-context"}-context.md`;
    link.click();
    URL.revokeObjectURL(link.href);
    setDocumentStatus("Agent Context 已准备下载。");
  } catch (error) {
    setDocumentStatus(error.message);
  }
}

saveDocumentButton.addEventListener("click", saveDocument);
documentEditor.addEventListener("input", updateDocumentPreview);
if (aiHelperButton) {
  aiHelperButton.addEventListener("click", runDocumentHelper);
}
if (applyDraftButton) {
  applyDraftButton.addEventListener("click", applyHelperDraft);
}
if (copyContextButton) {
  copyContextButton.addEventListener("click", copyAgentContext);
}
if (downloadContextButton) {
  downloadContextButton.addEventListener("click", downloadAgentContext);
}
renderDocumentNav();
loadDocument();

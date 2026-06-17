const titleInput = document.querySelector("#titleInput");
const kindInput = document.querySelector("#kindInput");
const rawInput = document.querySelector("#rawInput");
const aiOutput = document.querySelector("#aiOutput");
const statusText = document.querySelector("#statusText");
const savedPath = document.querySelector("#savedPath");
const fileList = document.querySelector("#fileList");
const refreshFiles = document.querySelector("#refreshFiles");
const boardPanel = document.querySelector("#boardPanel");
const boardGrid = document.querySelector("#boardGrid");
const viewButtons = document.querySelectorAll("[data-view]");

const boardStatuses = ["inbox", "active", "waiting", "done", "archive"];
let currentFiles = [];

function titleFromPath(file) {
  const filename = file.split("/").pop() || file;
  return filename.replace(/^\d{4}-\d{2}-\d{2}-/, "").replace(/\.md$/, "");
}

function statusFromPath(file) {
  const parts = file.split("/");
  return parts.find((part) => boardStatuses.includes(part)) || "inbox";
}

function detailUrl(file) {
  return `/detail.html?path=${encodeURIComponent(file)}`;
}

async function refreshFileList() {
  const response = await fetch("/api/files");
  const payload = await response.json();
  currentFiles = payload.files;
  renderFileList(currentFiles);
  renderBoard(currentFiles);
}

function renderFileList(files) {
  fileList.innerHTML = "";
  for (const file of files) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = detailUrl(file);
    link.textContent = file;
    item.appendChild(link);
    fileList.appendChild(item);
  }
}

function renderBoard(files) {
  const grouped = Object.fromEntries(boardStatuses.map((status) => [status, []]));
  for (const file of files) {
    grouped[statusFromPath(file)].push(file);
  }

  boardGrid.innerHTML = "";
  for (const status of boardStatuses) {
    const column = document.createElement("section");
    column.className = "board-column";

    const heading = document.createElement("div");
    heading.className = "board-column-header";
    heading.innerHTML = `<span>${status}</span><strong>${grouped[status].length}</strong>`;
    column.appendChild(heading);

    const cards = document.createElement("div");
    cards.className = "board-cards";
    for (const file of grouped[status]) {
      const card = document.createElement("a");
      card.className = "board-card";
      card.href = detailUrl(file);

      const title = document.createElement("h2");
      title.textContent = titleFromPath(file);

      const path = document.createElement("p");
      path.textContent = file;

      card.append(title, path);
      cards.appendChild(card);
    }
    column.appendChild(cards);
    boardGrid.appendChild(column);
  }
}

function setView(view) {
  const boardMode = view === "board";
  document.querySelector(".workspace").classList.toggle("board-mode", boardMode);
  boardPanel.hidden = !boardMode;
  fileList.hidden = boardMode;
  for (const button of viewButtons) {
    button.classList.toggle("is-active", button.dataset.view === view);
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

viewButtons.forEach((button) => {
  button.addEventListener("click", () => setView(button.dataset.view));
});

refreshFiles.addEventListener("click", refreshFileList);
refreshFileList();

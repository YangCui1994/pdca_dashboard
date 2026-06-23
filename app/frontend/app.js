const boardGrid = document.querySelector("#boardGrid");
const showNewTaskButton = document.querySelector("#showNewTaskButton");
const refreshItems = document.querySelector("#refreshItems");
const statusOverview = document.querySelector("#statusOverview");
const vaultOverview = document.querySelector("#vaultOverview");
const boardCallouts = document.querySelector("#boardCallouts");
const totalCount = document.querySelector("#totalCount");
const progressFill = document.querySelector("#progressFill");
const statusFilter = document.querySelector("#statusFilter");
const dateFilter = document.querySelector("#dateFilter");
const tagFilter = document.querySelector("#tagFilter");
const blockerFilter = document.querySelector("#blockerFilter");
const newTaskForm = document.querySelector("#newTaskForm");
const newTaskTitle = document.querySelector("#newTaskTitle");
const newTaskInput = document.querySelector("#newTaskInput");
const newTaskUseAi = document.querySelector("#newTaskUseAi");
const newTaskStatus = document.querySelector("#newTaskStatus");
const createTaskButton = document.querySelector("#createTaskButton");

const boardStatuses = ["inbox", "active", "waiting", "done", "archive"];
const statusLabels = {
  inbox: "收件箱",
  active: "推进中",
  waiting: "等待",
  done: "完成",
  archive: "归档"
};

let allItems = [];

function detailUrl(path) {
  return `/task.html?path=${encodeURIComponent(path)}`;
}

function emptyText(value, fallback) {
  return value && value.trim() ? value : fallback;
}

async function refreshBoard() {
  const response = await fetch("/api/work-items");
  const payload = await response.json();
  allItems = payload.items || [];
  applyFilters();
}

function applyFilters() {
  const items = allItems.filter((item) => {
    const statusMatch = statusFilter.value === "all" || item.status === statusFilter.value;
    const dateMatch = matchesDateFilter(item.created, dateFilter.value);
    const tagQuery = tagFilter.value.trim().toLowerCase();
    const tags = item.tags || [];
    const tagMatch = !tagQuery || tags.some((tag) => tag.toLowerCase().includes(tagQuery));
    const blockerMatch =
      blockerFilter.value === "all" ||
      (blockerFilter.value === "blocked" && Boolean(item.blocker)) ||
      (blockerFilter.value === "ready" && Boolean(item.basis) && !item.blocker);
    return statusMatch && dateMatch && tagMatch && blockerMatch;
  });
  renderOverview(items);
  renderBoard(items);
}

function matchesDateFilter(dateText, filterValue) {
  if (filterValue === "all") {
    return true;
  }
  if (!dateText) {
    return filterValue === "undated";
  }
  if (filterValue === "today") {
    return dateText === new Date().toISOString().slice(0, 10);
  }
  if (filterValue === "week") {
    return isThisWeek(dateText);
  }
  return true;
}

function isThisWeek(dateText) {
  const itemDate = new Date(`${dateText}T00:00:00`);
  const now = new Date();
  const start = new Date(now);
  start.setDate(now.getDate() - now.getDay() + 1);
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(start.getDate() + 7);
  return itemDate >= start && itemDate < end;
}

function groupItems(items) {
  const grouped = Object.fromEntries(boardStatuses.map((status) => [status, []]));
  for (const item of items) {
    const status = boardStatuses.includes(item.status) ? item.status : "inbox";
    grouped[status].push(item);
  }
  return grouped;
}

function renderOverview(items) {
  const grouped = groupItems(items);
  const total = items.length;
  const ready = items.filter((item) => item.basis && !item.blocker).length;
  const needsContext = items.filter((item) => !item.basis || item.blocker).length;
  const activeRatio = total ? Math.round(((grouped.active.length + grouped.done.length) / total) * 100) : 0;

  totalCount.textContent = `${total} items`;
  progressFill.style.width = `${Math.max(activeRatio, total ? 8 : 0)}%`;

  statusOverview.innerHTML = "";
  for (const status of boardStatuses) {
    const item = document.createElement("a");
    item.className = `nav-item${status === "inbox" ? " active" : ""}`;
    item.href = `#${status}`;
    item.textContent = `${statusLabels[status]} · ${grouped[status].length}`;
    statusOverview.appendChild(item);
  }

  vaultOverview.innerHTML = "";
  for (const status of boardStatuses.slice(0, 4)) {
    const badge = document.createElement("div");
    badge.className = "badge-button";
    badge.innerHTML = `${statusLabels[status]} <span class="dot">${grouped[status].length}</span>`;
    vaultOverview.appendChild(badge);
  }

  boardCallouts.innerHTML = "";
  boardCallouts.append(
    buildCallout("soft-green", "✓", `${ready} 个任务已有基础上下文。`, "进入详情"),
    buildCallout("soft-amber", "◉", `${needsContext} 个任务仍需补齐卡点或基础。`, "补上下文")
  );
}

function buildCallout(tone, icon, text, action) {
  const callout = document.createElement("div");
  callout.className = `callout ${tone}`;
  callout.innerHTML = `<span>${icon}</span><span>${text}</span><button type="button">${action}</button>`;
  return callout;
}

function renderBoard(items) {
  const grouped = groupItems(items);

  boardGrid.innerHTML = "";
  for (const status of boardStatuses) {
    const column = document.createElement("section");
    column.className = "board-column";
    column.id = status;

    const heading = document.createElement("div");
    heading.className = "board-column-header";
    heading.innerHTML = `<span>${statusLabels[status]}</span><strong>${grouped[status].length}</strong>`;
    column.appendChild(heading);

    const cards = document.createElement("div");
    cards.className = "board-cards";
    for (const item of grouped[status]) {
      const card = document.createElement("article");
      card.className = "board-card";

      const link = document.createElement("a");
      link.href = detailUrl(item.path);
      link.className = "board-card-title";
      const title = document.createElement("h2");
      title.textContent = item.title;
      link.appendChild(title);

      const blocker = document.createElement("p");
      blocker.className = "board-card-blocker";
      blocker.textContent = `卡点：${emptyText(item.blocker, "未填写")}`;

      const summary = document.createElement("p");
      summary.className = "board-card-summary";
      summary.textContent = `摘要：${emptyText(item.summary, item.basis || "未填写")}`;

      const event = document.createElement("p");
      event.textContent = `最近：${emptyText(item.last_event, "暂无事件")}`;

      const meta = document.createElement("p");
      meta.textContent = `日期：${emptyText(item.created, "无日期")} · 标签：${(item.tags || []).join(", ") || "无"}`;

      const statusActions = document.createElement("div");
      statusActions.className = "card-status-actions";
      for (const targetStatus of boardStatuses.filter((candidate) => candidate !== item.status)) {
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.path = item.path;
        button.dataset.status = targetStatus;
        button.textContent = statusLabels[targetStatus];
        statusActions.appendChild(button);
      }

      card.append(link, summary, blocker, event, meta, statusActions);
      cards.appendChild(card);
    }
    if (!grouped[status].length) {
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = "这一列暂无事项。";
      cards.appendChild(empty);
    }
    column.appendChild(cards);
    boardGrid.appendChild(column);
  }
}

async function moveWorkItemStatus(path, status) {
  await fetch("/api/work-item-status", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({path, status})
  });
  await refreshBoard();
}

async function createTask(event) {
  event.preventDefault();
  const title = newTaskTitle.value.trim() || "未命名任务";
  const rawText = newTaskInput.value.trim();
  if (!rawText) {
    newTaskStatus.textContent = "请先输入内容";
    return;
  }
  newTaskStatus.textContent = newTaskUseAi.checked ? "AI 整理中" : "保存中";
  createTaskButton.disabled = true;
  const response = await fetch("/api/capture", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      title,
      raw_text: rawText,
      action: "structure_capture",
      kind: "task",
      use_ai: newTaskUseAi.checked
    })
  });
  createTaskButton.disabled = false;
  if (!response.ok) {
    newTaskStatus.textContent = `创建失败：${response.status}`;
    return;
  }
  const payload = await response.json();
  newTaskStatus.textContent = "已创建";
  window.location.href = detailUrl(payload.path);
}

function focusNewTaskForm() {
  newTaskForm.scrollIntoView({behavior: "smooth", block: "start"});
  newTaskTitle.focus();
}

for (const control of [statusFilter, dateFilter, tagFilter, blockerFilter]) {
  control.addEventListener("input", applyFilters);
}

boardGrid.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-path][data-status]");
  if (!button) {
    return;
  }
  moveWorkItemStatus(button.dataset.path, button.dataset.status);
});

newTaskForm.addEventListener("submit", createTask);
showNewTaskButton.addEventListener("click", focusNewTaskForm);
refreshItems.addEventListener("click", refreshBoard);
refreshBoard();

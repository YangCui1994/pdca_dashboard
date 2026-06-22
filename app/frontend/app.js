const boardGrid = document.querySelector("#boardGrid");
const refreshItems = document.querySelector("#refreshItems");
const statusOverview = document.querySelector("#statusOverview");
const vaultOverview = document.querySelector("#vaultOverview");
const boardCallouts = document.querySelector("#boardCallouts");
const totalCount = document.querySelector("#totalCount");
const progressFill = document.querySelector("#progressFill");

const boardStatuses = ["inbox", "active", "waiting", "done", "archive"];
const statusLabels = {
  inbox: "收件箱",
  active: "推进中",
  waiting: "等待",
  done: "完成",
  archive: "归档"
};

function detailUrl(path) {
  return `/task.html?path=${encodeURIComponent(path)}`;
}

function emptyText(value, fallback) {
  return value && value.trim() ? value : fallback;
}

async function refreshBoard() {
  const response = await fetch("/api/work-items");
  const payload = await response.json();
  const items = payload.items || [];
  renderOverview(items);
  renderBoard(items);
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
      const card = document.createElement("a");
      card.className = "board-card";
      card.href = detailUrl(item.path);

      const title = document.createElement("h2");
      title.textContent = item.title;

      const blocker = document.createElement("p");
      blocker.className = "board-card-blocker";
      blocker.textContent = `卡点：${emptyText(item.blocker, "未填写")}`;

      const basis = document.createElement("p");
      basis.textContent = `基础：${emptyText(item.basis, "未填写")}`;

      const event = document.createElement("p");
      event.textContent = `最近：${emptyText(item.last_event, "暂无事件")}`;

      card.append(title, blocker, basis, event);
      cards.appendChild(card);
    }
    column.appendChild(cards);
    boardGrid.appendChild(column);
  }
}

refreshItems.addEventListener("click", refreshBoard);
refreshBoard();

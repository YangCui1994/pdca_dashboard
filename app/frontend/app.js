const boardGrid = document.querySelector("#boardGrid");
const refreshItems = document.querySelector("#refreshItems");

const boardStatuses = ["inbox", "active", "waiting", "done", "archive"];
const statusLabels = {
  inbox: "收件箱",
  active: "推进中",
  waiting: "等待",
  done: "完成",
  archive: "归档"
};

function detailUrl(path) {
  return `/detail.html?path=${encodeURIComponent(path)}`;
}

function emptyText(value, fallback) {
  return value && value.trim() ? value : fallback;
}

async function refreshBoard() {
  const response = await fetch("/api/work-items");
  const payload = await response.json();
  renderBoard(payload.items || []);
}

function renderBoard(items) {
  const grouped = Object.fromEntries(boardStatuses.map((status) => [status, []]));
  for (const item of items) {
    const status = boardStatuses.includes(item.status) ? item.status : "inbox";
    grouped[status].push(item);
  }

  boardGrid.innerHTML = "";
  for (const status of boardStatuses) {
    const column = document.createElement("section");
    column.className = "board-column";

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

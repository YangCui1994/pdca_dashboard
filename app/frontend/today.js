const titleInput = document.querySelector("#titleInput");
const rawInput = document.querySelector("#rawInput");
const aiOutput = document.querySelector("#aiOutput");
const statusText = document.querySelector("#statusText");
const savedPath = document.querySelector("#savedPath");
const todayList = document.querySelector("#todayList");
const refreshToday = document.querySelector("#refreshToday");
const todayCount = document.querySelector("#todayCount");
const todayProgress = document.querySelector("#todayProgress");

function detailUrl(path) {
  return `/detail.html?path=${encodeURIComponent(path)}`;
}

function isThisWeek(dateText) {
  if (!dateText) {
    return false;
  }
  const itemDate = new Date(`${dateText}T00:00:00`);
  const now = new Date();
  const start = new Date(now);
  start.setDate(now.getDate() - now.getDay() + 1);
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(start.getDate() + 7);
  return itemDate >= start && itemDate < end;
}

async function refreshTodayList() {
  const response = await fetch("/api/work-items");
  const payload = await response.json();
  const items = (payload.items || []).filter((item) => item.status !== "archive" && isThisWeek(item.created));
  renderTodayOverview(items);
  renderTodayList(items);
}

function renderTodayOverview(items) {
  const doneCount = items.filter((item) => item.status === "done").length;
  const ratio = items.length ? Math.round((doneCount / items.length) * 100) : 0;
  todayCount.textContent = `${items.length} items`;
  todayProgress.style.width = `${Math.max(ratio, items.length ? 8 : 0)}%`;
}

function renderTodayList(items) {
  todayList.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "本周还没有事项。";
    todayList.appendChild(empty);
    return;
  }
  for (const item of items) {
    const link = document.createElement("a");
    link.className = "today-item";
    link.href = detailUrl(item.path);
    link.innerHTML = `<strong>${item.title}</strong><span>${item.status} · ${item.created || "无日期"}</span>`;
    todayList.appendChild(link);
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
      title: titleInput.value.trim() || "今日 PDCA 输入",
      kind: "task",
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
  await refreshTodayList();
}

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => runAction(button.dataset.action));
});

refreshToday.addEventListener("click", refreshTodayList);
refreshTodayList();

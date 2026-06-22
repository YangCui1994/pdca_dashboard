const titleInput = document.querySelector("#titleInput");
const planInput = document.querySelector("#planInput");
const doInput = document.querySelector("#doInput");
const checkInput = document.querySelector("#checkInput");
const actInput = document.querySelector("#actInput");
const aiOutput = document.querySelector("#aiOutput");
const reviewOutput = document.querySelector("#reviewOutput");
const statusText = document.querySelector("#statusText");
const savedPath = document.querySelector("#savedPath");
const reviewPath = document.querySelector("#reviewPath");
const todayList = document.querySelector("#todayList");
const todayItems = document.querySelector("#todayItems");
const weekItems = document.querySelector("#weekItems");
const refreshToday = document.querySelector("#refreshToday");
const todayCount = document.querySelector("#todayCount");
const todayProgress = document.querySelector("#todayProgress");
const analyzePdcaButton = document.querySelector("#analyzePdcaButton");
const reviewPdcaButton = document.querySelector("#reviewPdcaButton");
const acceptPdcaButton = document.querySelector("#acceptPdcaButton");
const targetTaskSelect = document.querySelector("#targetTaskSelect");
const todayStatusFilter = document.querySelector("#todayStatusFilter");
const todayDateFilter = document.querySelector("#todayDateFilter");
const planResult = document.querySelector("#planResult");
const trueDoResult = document.querySelector("#trueDoResult");
const candidateDoResult = document.querySelector("#candidateDoResult");
const notDoResult = document.querySelector("#notDoResult");
const checkResult = document.querySelector("#checkResult");
const actResult = document.querySelector("#actResult");

let workItems = [];
let latestPdcaAnalysis = "";

function detailUrl(path) {
  return `/task.html?path=${encodeURIComponent(path)}`;
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
  workItems = (payload.items || []).filter((item) => item.status !== "archive");
  const items = filterTodayItems(workItems);
  renderTodayOverview(items);
  renderTodayList(items);
  renderTaskOptions(workItems);
}

function filterTodayItems(items) {
  return items.filter((item) => {
    const statusMatch = todayStatusFilter.value === "all" || item.status === todayStatusFilter.value;
    const dateValue = todayDateFilter.value;
    const dateMatch = dateValue ? item.created === dateValue : isThisWeek(item.created);
    return statusMatch && dateMatch;
  });
}

function renderTodayOverview(items) {
  const doneCount = items.filter((item) => item.status === "done").length;
  const ratio = items.length ? Math.round((doneCount / items.length) * 100) : 0;
  todayCount.textContent = `${items.length} items`;
  todayProgress.style.width = `${Math.max(ratio, items.length ? 8 : 0)}%`;
}

function renderTodayList(items) {
  todayList.innerHTML = "";
  todayItems.innerHTML = "";
  weekItems.innerHTML = "";
  const today = items.filter((item) => isToday(item.created));
  const week = items.filter((item) => !isToday(item.created));
  renderItemGroup(todayItems, today, "今天没有匹配事项。");
  renderItemGroup(weekItems, week, "本周其他日期没有匹配事项。");
}

function renderItemGroup(container, items, emptyMessage) {
  container.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = emptyMessage;
    container.appendChild(empty);
    return;
  }
  for (const item of items) {
    const link = document.createElement("a");
    link.className = "today-item";
    link.href = detailUrl(item.path);
    link.innerHTML = `<strong>${item.title}</strong><span>${item.status} · ${item.created || "无日期"}</span>`;
    container.appendChild(link);
  }
}

function renderTaskOptions(items) {
  targetTaskSelect.innerHTML = "";
  for (const item of items) {
    const option = document.createElement("option");
    option.value = item.path;
    option.textContent = `${item.title} · ${item.status}`;
    targetTaskSelect.appendChild(option);
  }
  if (!items.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "没有可保存的任务";
    targetTaskSelect.appendChild(option);
  }
}

function hasPdcaInput() {
  return [planInput, doInput, checkInput, actInput].some((input) => input.value.trim());
}

async function analyzePdcaEntry() {
  if (!hasPdcaInput()) {
    statusText.textContent = "请先填写至少一个 PDCA 输入框。";
    return;
  }
  statusText.textContent = "AI 正在分析并记录初始想法。";
  savedPath.textContent = "";
  const response = await fetch("/api/pdca-entry", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      title: titleInput.value.trim() || "今日 PDCA 输入",
      plan: planInput.value,
      do: doInput.value,
      check: checkInput.value,
      act: actInput.value
    })
  });
  if (!response.ok) {
    statusText.textContent = `请求失败：${response.status}`;
    return;
  }
  const payload = await response.json();
  latestPdcaAnalysis = payload.ai_output;
  aiOutput.value = payload.ai_output;
  renderPdcaResultSections(payload.ai_output);
  savedPath.textContent = `已记录：${payload.log_path}`;
  statusText.textContent = "完成。";
  await refreshTodayList();
}

function renderPdcaResultSections(aiText) {
  planResult.textContent = planInput.value.trim() || extractSection(aiText, "Plan") || "未填写 Plan。";
  trueDoResult.textContent = extractLabel(aiText, "true_do") || "等待 AI 明确 true_do。";
  candidateDoResult.textContent = extractLabel(aiText, "candidate_do") || "等待 AI 明确 candidate_do。";
  notDoResult.textContent = extractLabel(aiText, "not_do") || extractLabel(aiText, "bias_or_judgment") || "等待 AI 明确 not_do / judgment。";
  checkResult.textContent = checkInput.value.trim() || extractSection(aiText, "Check") || "未填写 Check。";
  actResult.textContent = actInput.value.trim() || extractSection(aiText, "Act") || "未填写 Act。";
}

function extractLabel(text, label) {
  const line = text.split("\n").find((candidate) => candidate.includes(label));
  return line ? line.trim() : "";
}

function extractSection(text, heading) {
  const pattern = new RegExp(`(?:^|\\n)#+\\\\s*${heading}\\\\s*\\n([\\\\s\\\\S]*?)(?=\\n#+\\\\s|$)`, "i");
  const match = text.match(pattern);
  return match ? match[1].trim() : "";
}

async function acceptPdcaAnalysis() {
  const path = targetTaskSelect.value;
  if (!path) {
    statusText.textContent = "请选择一个目标任务。";
    return;
  }
  const eventText = latestPdcaAnalysis || aiOutput.value.trim();
  if (!eventText) {
    statusText.textContent = "请先生成单次 AI 分析。";
    return;
  }
  statusText.textContent = "正在保存到 events.md。";
  const response = await fetch("/api/work-item-event", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({path, event: `PDCA Review\n\n${eventText}`})
  });
  if (!response.ok) {
    statusText.textContent = `保存失败：${response.status}`;
    return;
  }
  statusText.textContent = "已保存到任务 events.md。";
  await refreshTodayList();
}

async function reviewPdcaHistory() {
  statusText.textContent = "AI 正在生成周期 Review。";
  reviewPath.textContent = "";
  const response = await fetch("/api/pdca-review", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({limit: 20})
  });
  if (!response.ok) {
    statusText.textContent = `请求失败：${response.status}`;
    return;
  }
  const payload = await response.json();
  reviewOutput.value = payload.ai_output;
  reviewPath.textContent = `已保存：${payload.review_path}`;
  statusText.textContent = "周期 Review 已生成。";
}

function isToday(dateText) {
  return Boolean(dateText) && dateText === new Date().toISOString().slice(0, 10);
}

analyzePdcaButton.addEventListener("click", analyzePdcaEntry);
reviewPdcaButton.addEventListener("click", reviewPdcaHistory);
acceptPdcaButton.addEventListener("click", acceptPdcaAnalysis);
todayStatusFilter.addEventListener("input", refreshTodayList);
todayDateFilter.addEventListener("input", refreshTodayList);
refreshToday.addEventListener("click", refreshTodayList);
refreshTodayList();

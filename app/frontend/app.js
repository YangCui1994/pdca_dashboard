const titleInput = document.querySelector("#titleInput");
const kindInput = document.querySelector("#kindInput");
const rawInput = document.querySelector("#rawInput");
const aiOutput = document.querySelector("#aiOutput");
const statusText = document.querySelector("#statusText");
const savedPath = document.querySelector("#savedPath");
const fileList = document.querySelector("#fileList");
const refreshFiles = document.querySelector("#refreshFiles");

async function refreshFileList() {
  const response = await fetch("/api/files");
  const payload = await response.json();
  fileList.innerHTML = "";
  for (const file of payload.files) {
    const item = document.createElement("li");
    item.textContent = file;
    fileList.appendChild(item);
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

refreshFiles.addEventListener("click", refreshFileList);
refreshFileList();

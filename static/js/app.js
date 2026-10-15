// TaskFlow front-end. All user text is written with textContent (never innerHTML),
// so a task titled "<script>..." is shown as plain text and never runs.
const $ = (s) => document.querySelector(s);
const STATUS_LABEL = { todo: "To do", in_progress: "In progress", completed: "Completed" };
const ORDER = ["todo", "in_progress", "completed"];
const TITLES = { all: "Project board", today: "Due this week", high: "High priority",
                 overdue: "Overdue", completed: "Completed" };
let view = "all", editingId = null, deleteId = null, dragId = null, tasks = [];

async function api(url, options = {}) {
  try {
    const res = await fetch(url, { headers: { "Content-Type": "application/json" }, ...options });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Something went wrong.");
    return data;
  } catch (err) {
    if (err instanceof TypeError) throw new Error("Cannot reach the server. Is it running?");
    throw err;
  }
}

function toast(msg, isError = false) {
  const t = document.createElement("div");
  t.className = "toast" + (isError ? " error" : "");
  t.textContent = msg;
  $("#toasts").append(t);
  setTimeout(() => t.remove(), 3200);
}

const todayStr = () => new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD
const isLate = (t) => t.due_date && t.status !== "completed" && t.due_date < todayStr();

function fmtDate(d) {
  return new Date(d + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function buildCard(t) {
  const card = el("article", `card p-${t.priority}`);
  card.draggable = true;
  card.dataset.id = t.id;
  card.append(el("h3", "", t.title));
  if (t.description) card.append(el("p", "", t.description));
  const meta = el("div", "meta");
  meta.append(el("span", `tag ${t.priority}`, t.priority));
  if (t.due_date) meta.append(el("span", "due" + (isLate(t) ? " late" : ""), (isLate(t) ? "Overdue · " : "Due ") + fmtDate(t.due_date)));
  const tools = el("div", "tools");
  const idx = ORDER.indexOf(t.status);
  const btn = (label, title, fn, show = true) => {
    if (!show) return;
    const b = el("button", "", label); b.title = title; b.setAttribute("aria-label", title);
    b.onclick = fn; tools.append(b);
  };
  btn("←", "Move left", () => move(t.id, ORDER[idx - 1]), idx > 0);
  btn("→", "Move right", () => move(t.id, ORDER[idx + 1]), idx < 2);
  btn("Edit", "Edit task", () => openForm(t));
  btn("Delete", "Delete task", () => askDelete(t));
  meta.append(tools);
  card.append(meta);
  card.addEventListener("dragstart", () => { dragId = t.id; card.classList.add("dragging"); });
  card.addEventListener("dragend", () => card.classList.remove("dragging"));
  return card;
}

function render() {
  document.querySelectorAll(".column").forEach((col) => {
    const list = tasks.filter((t) => t.status === col.dataset.status);
    col.querySelector(".count").textContent = list.length;
    const box = col.querySelector(".cards");
    box.replaceChildren(...list.map(buildCard));
    if (!list.length) {
      const filtered = $("#search").value || $("#priorityFilter").value || view !== "all";
      box.append(el("div", "empty", filtered ? "No matching tasks here." : "Nothing here yet. Drop a task or add a new one."));
    }
  });
}

async function load() {
  const p = new URLSearchParams();
  if ($("#search").value.trim()) p.set("search", $("#search").value.trim());
  let prio = $("#priorityFilter").value;
  if (view === "high") prio = "high";
  if (prio) p.set("priority", prio);
  if (view === "completed") p.set("status", "completed");
  try {
    tasks = await api("/api/tasks?" + p);
    const limit = new Date(); limit.setDate(limit.getDate() + 7);
    const lim = limit.toLocaleDateString("en-CA");
    if (view === "today") tasks = tasks.filter((t) => t.status !== "completed" && t.due_date && t.due_date <= lim);
    if (view === "overdue") tasks = tasks.filter(isLate);
    render();
    const s = await api("/api/stats");
    $("#stTotal").textContent = s.total; $("#stTodo").textContent = s.todo;
    $("#stProg").textContent = s.in_progress; $("#stDone").textContent = s.completed;
    $("#stOver").textContent = s.overdue;
  } catch (e) { toast(e.message, true); }
}

async function move(id, status) {
  try { await api(`/api/tasks/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
        toast("Moved to " + STATUS_LABEL[status]); load(); }
  catch (e) { toast(e.message, true); }
}

// ----- add / edit form -----
function openForm(t = null) {
  editingId = t ? t.id : null;
  $("#dialogTitle").textContent = t ? "Edit task" : "New task";
  $("#fTitle").value = t ? t.title : ""; $("#fDesc").value = t ? t.description : "";
  $("#fStatus").value = t ? t.status : "todo"; $("#fPriority").value = t ? t.priority : "medium";
  $("#fDue").value = t && t.due_date ? t.due_date : ""; $("#formError").textContent = "";
  $("#taskDialog").showModal(); $("#fTitle").focus();
}

$("#taskForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = { title: $("#fTitle").value, description: $("#fDesc").value, status: $("#fStatus").value,
                 priority: $("#fPriority").value, due_date: $("#fDue").value || null };
  try {
    await api(editingId ? `/api/tasks/${editingId}` : "/api/tasks",
              { method: editingId ? "PUT" : "POST", body: JSON.stringify(body) });
    $("#taskDialog").close(); toast(editingId ? "Task updated." : "Task created."); load();
  } catch (err) { $("#formError").textContent = err.message; }
});

// ----- delete -----
function askDelete(t) { deleteId = t.id; $("#confirmText").textContent = `"${t.title}" will be removed permanently.`; $("#confirmDialog").showModal(); }
$("#yesBtn").onclick = async () => {
  try { await api(`/api/tasks/${deleteId}`, { method: "DELETE" }); toast("Task deleted."); }
  catch (e) { toast(e.message, true); }
  $("#confirmDialog").close(); load();
};
$("#noBtn").onclick = () => $("#confirmDialog").close();

// ----- drag & drop -----
document.querySelectorAll(".column").forEach((col) => {
  col.addEventListener("dragover", (e) => { e.preventDefault(); col.classList.add("over"); });
  col.addEventListener("dragleave", () => col.classList.remove("over"));
  col.addEventListener("drop", (e) => {
    e.preventDefault(); col.classList.remove("over");
    const t = tasks.find((x) => x.id === dragId);
    if (t && t.status !== col.dataset.status) move(dragId, col.dataset.status);
  });
});

// ----- toolbar, nav, misc -----
let timer;
$("#search").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(load, 250); });
$("#priorityFilter").addEventListener("change", load);
$("#clearBtn").onclick = () => { $("#search").value = ""; $("#priorityFilter").value = ""; setView("all"); };
$("#addBtn").onclick = () => openForm();
$("#cancelBtn").onclick = () => $("#taskDialog").close();
$("#menuBtn").onclick = () => $("#sidebar").classList.toggle("open");

function setView(v) {
  view = v; $("#viewTitle").textContent = TITLES[v];
  document.querySelectorAll(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.view === v));
  $("#sidebar").classList.remove("open"); load();
}
document.querySelectorAll(".nav-item").forEach((b) => (b.onclick = () => setView(b.dataset.view)));

$("#today").textContent = new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });
api("/health").then((h) => ($("#health").textContent = `Server ${h.status} · ${h.task_count} tasks`))
              .catch(() => ($("#health").textContent = "Server unreachable"));
load();

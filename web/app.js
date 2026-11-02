// Empório da Música — web chat client (no framework, no build step).

const SUGGESTIONS = [
  ["Catálogo", "Quais violões disponíveis custam até R$ 1000?"],
  ["Preço e parcelas", "Quanto custa o Takamine GD20? Dá pra parcelar?"],
  ["Meu pedido", "Quero saber o status do meu pedido"],
  ["Trocas", "Me arrependi da compra, posso devolver?"],
];

const $ = (sel) => document.querySelector(sel);
const thread = $("#thread");
const scroller = $("#scroll");
const input = $("#input");
const sendBtn = $("#send");
const welcome = $("#welcome");

const state = {
  session: new URLSearchParams(location.search).get("s"),
  busy: false,
  turn: 0,
  assistant: "Lia",
};

// ------------------------------------------------------------------ utils
const escapeHtml = (s) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// Minimal, safe Markdown: escape first, then bold / lists / paragraphs.
function renderMarkdown(text) {
  const inline = (s) => escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  const out = [];
  let list = null;
  const close = () => { if (list) { out.push(`</${list}>`); list = null; } };
  let para = [];
  const flush = () => { if (para.length) { out.push(`<p>${para.join("<br>")}</p>`); para = []; } };

  for (const raw of text.split("\n")) {
    const line = raw.trimEnd();
    const ul = line.match(/^\s*[-•*]\s+(.*)$/);
    const ol = line.match(/^\s*\d+[.)]\s+(.*)$/);
    if (ul || ol) {
      flush();
      const kind = ul ? "ul" : "ol";
      if (list !== kind) { close(); out.push(`<${kind}>`); list = kind; }
      out.push(`<li>${inline((ul || ol)[1])}</li>`);
    } else if (!line.trim()) {
      flush(); close();
    } else {
      close(); para.push(inline(line));
    }
  }
  flush(); close();
  return out.join("");
}

const scrollDown = () => requestAnimationFrame(() => { scroller.scrollTop = scroller.scrollHeight; });

function setSession(id) {
  state.session = id;
  const url = new URL(location.href);
  if (id) url.searchParams.set("s", id); else url.searchParams.delete("s");
  history.replaceState(null, "", url);
  renderMeta();
}

function renderMeta() {
  $("#meta").innerHTML = `Modelo ${escapeHtml(state.model || "")}<br>Sessão ${escapeHtml(state.session || "nova")}`;
}

// ------------------------------------------------------------------ render
function addUser(text) {
  welcome.hidden = true;
  const el = document.createElement("div");
  el.className = "msg msg-user";
  el.innerHTML = `<div class="bubble-user"></div>`;
  el.firstChild.textContent = text;
  thread.appendChild(el);
  scrollDown();
}

function addBot() {
  welcome.hidden = true;
  const el = document.createElement("div");
  el.className = "msg msg-bot";
  el.innerHTML = `
    <span class="avatar">${escapeHtml(state.assistant[0])}</span>
    <div class="bot">
      <div class="answer-frame">
        <div class="tools" hidden></div>
        <div class="answer"><span class="typing"><span></span><span></span><span></span></span></div>
      </div>
    </div>`;
  thread.appendChild(el);
  scrollDown();
  return el;
}

function addChip(botEl, tool, done = false) {
  const box = botEl.querySelector(".tools");
  box.hidden = false;
  box.querySelectorAll(".chip.running").forEach((c) => c.classList.replace("running", "done"));
  const chip = document.createElement("span");
  chip.className = `chip ${done ? "done" : "running"}`;
  chip.innerHTML = `<span class="ic"></span><span></span>`;
  chip.lastChild.textContent = tool.label;
  box.appendChild(chip);
  const args = document.createElement("code");
  args.className = "chip-args";
  args.textContent = `${tool.name}(${JSON.stringify(tool.arguments)})`;
  box.appendChild(args);
  scrollDown();
}

function finishChips(botEl) {
  botEl.querySelectorAll(".chip.running").forEach((c) => c.classList.replace("running", "done"));
}

async function typeAnswer(botEl, text, animate = true) {
  const box = botEl.querySelector(".answer");
  if (!animate) { box.innerHTML = renderMarkdown(text); return; }
  const words = text.split(/(\s+)/);
  const step = Math.max(1, Math.round(words.length / 90)); // ~1.2s whatever the length
  for (let i = 0; i <= words.length; i += step) {
    box.innerHTML = renderMarkdown(words.slice(0, i).join("")) + '<span class="caret"></span>';
    if (i % (step * 6) === 0) scrollDown();
    await new Promise((r) => setTimeout(r, 14));
  }
  box.innerHTML = renderMarkdown(text);
  scrollDown();
}

function addActions(botEl, turn, score) {
  const bar = document.createElement("div");
  bar.className = "actions";
  bar.innerHTML = `
    <button class="act" data-score="1" title="Resposta útil">▲ Útil</button>
    <button class="act" data-score="0" title="Não ajudou">▼ Não ajudou</button>
    <button class="act" data-copy title="Copiar resposta">Copiar</button>`;
  const mark = (s) => {
    bar.querySelectorAll("[data-score]").forEach((b) => b.classList.toggle("on", b.dataset.score === String(s)));
    bar.classList.toggle("voted", s !== undefined && s !== null);
  };
  mark(score);
  bar.addEventListener("click", async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    if (btn.hasAttribute("data-copy")) {
      await navigator.clipboard?.writeText(botEl.querySelector(".answer").innerText);
      btn.textContent = "Copiado"; setTimeout(() => (btn.textContent = "Copiar"), 1400);
      return;
    }
    const s = Number(btn.dataset.score);
    mark(s);
    fetch("/feedback", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.session, turn, score: s }),
    });
  });
  botEl.querySelector(".bot").appendChild(bar);
}

// ------------------------------------------------------------------ network
async function send(text) {
  text = text.trim();
  if (!text || state.busy) return;
  state.busy = true; sendBtn.disabled = true;
  input.value = ""; autosize();
  addUser(text);
  const bot = addBot();

  try {
    const res = await fetch("/chat/stream", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: state.session }),
    });
    if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finished = false;
    while (!finished) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf("\n\n")) >= 0) {
        const raw = buffer.slice(0, idx); buffer = buffer.slice(idx + 2);
        const kind = raw.match(/^event: (.*)$/m)?.[1];
        const data = JSON.parse(raw.match(/^data: (.*)$/m)?.[1] || "{}");
        if (kind === "tool") addChip(bot, data);
        if (kind === "error") throw new Error(data.message);
        if (kind === "done") {
          finished = true;
          setSession(data.session_id);
          finishChips(bot);
          await typeAnswer(bot, data.reply);
          state.turn += 1;
          addActions(bot, state.turn);
        }
      }
    }
    if (!finished) throw new Error("conexão encerrada");
  } catch (err) {
    finishChips(bot);
    bot.querySelector(".answer").outerHTML =
      `<div class="error">Não consegui responder agora (${escapeHtml(String(err.message || err))}). Tente de novo em instantes.</div>`;
  } finally {
    state.busy = false; sendBtn.disabled = !input.value.trim();
    input.focus();
  }
}

async function loadHistory() {
  if (!state.session) return;
  const res = await fetch(`/sessions/${encodeURIComponent(state.session)}/turns`);
  if (!res.ok) return;
  const { turns, feedback } = await res.json();
  for (const t of turns) {
    addUser(t.user);
    if (!t.answer) continue;
    const bot = addBot();
    t.tools.forEach((tool) => addChip(bot, tool, true));
    await typeAnswer(bot, t.answer, false);
    state.turn += 1;
    addActions(bot, state.turn, feedback[state.turn]);
  }
  scrollDown();
}

async function loadStore() {
  try {
    const info = await (await fetch("/store")).json();
    state.assistant = info.assistant;
    for (const id of ["agentName", "heroName"]) $("#" + id).textContent = info.assistant;
    $("#agentInitial").textContent = info.assistant[0];
    input.placeholder = `Escreva para a ${info.assistant}…`;
    const st = $("#storeStatus");
    st.classList.add(info.is_open ? "open" : "closed");
    st.lastElementChild.textContent = info.is_open ? "Aberta agora" : "Fechada agora";
    $("#storeStatusSub").textContent = info.is_open
      ? info.status.match(/\((.*)\)/)?.[1] ?? ""
      : info.status.split(". ").slice(1).join(". ");
    const d = new Date(info.now);
    const fmt = d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
    $("#simDate").textContent = `Data simulada · ${fmt}`;
    state.model = info.model;
    renderMeta();
  } catch { /* UI still works without store info */ }
}

// ------------------------------------------------------------------ wiring
function autosize() {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 160) + "px";
  sendBtn.disabled = state.busy || !input.value.trim();
}

function renderSuggestions() {
  const box = $("#suggestions");
  SUGGESTIONS.forEach(([kicker, q], i) => {
    const b = document.createElement("button");
    b.className = "suggestion";
    b.style.animationDelay = `${120 + i * 70}ms`;
    b.innerHTML = `<span class="suggestion-text"><span class="suggestion-kicker"></span><span class="suggestion-q"></span></span><span class="pill-dot" aria-hidden="true"></span>`;
    b.querySelector(".suggestion-kicker").textContent = kicker;
    b.querySelector(".suggestion-q").textContent = q;
    b.addEventListener("click", () => send(q));
    box.appendChild(b);
  });
}

$("#composer").addEventListener("submit", (e) => { e.preventDefault(); send(input.value); });
input.addEventListener("input", autosize);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(input.value); }
});

$("#newChat").addEventListener("click", () => {
  setSession(null);
  thread.querySelectorAll(".msg").forEach((m) => m.remove());
  welcome.hidden = false; state.turn = 0;
  document.body.classList.remove("panel-open");
  loadStore(); input.focus();
});

const tech = $("#techMode");
try { tech.checked = localStorage.getItem("tech") === "1"; } catch {}
document.body.classList.toggle("tech", tech.checked);
tech.addEventListener("change", () => {
  document.body.classList.toggle("tech", tech.checked);
  try { localStorage.setItem("tech", tech.checked ? "1" : "0"); } catch {}
});

$("#panelOpen").addEventListener("click", () => document.body.classList.add("panel-open"));
$("#panelClose").addEventListener("click", () => document.body.classList.remove("panel-open"));
$("#scrim").addEventListener("click", () => document.body.classList.remove("panel-open"));

renderSuggestions();
autosize();
loadStore();
loadHistory();
input.focus();

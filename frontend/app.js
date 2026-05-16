// ─── CONFIG ───────────────────────────────────────────────────────────────────
const API = ""; // same origin — backend serves frontend at root

// ─── RULER DATA ───────────────────────────────────────────────────────────────
const QUADRANTS = {
  rojo:     { label: "🔴 Rojo",    words: ["furioso","enojado","frustrado","irritado","ansioso","tenso","preocupado","abrumado"] },
  amarillo: { label: "🟡 Amarillo", words: ["emocionado","eufórico","feliz","optimista","motivado","inspirado","orgulloso","alegre"] },
  azul:     { label: "🔵 Azul",    words: ["triste","decepcionado","desanimado","solo","agotado","vacío","melancólico","derrotado"] },
  verde:    { label: "🟢 Verde",   words: ["calmado","sereno","agradecido","satisfecho","tranquilo","relajado","contento","en paz"] },
};

// ─── STATE ────────────────────────────────────────────────────────────────────
let state = {
  currentScreen: "mood",
  selectedQuadrant: null,
  selectedEmotion: null,
  audioBlob: null,
  rulerResult: null,
};

// ─── NAVIGATION ───────────────────────────────────────────────────────────────
function showScreen(name) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  document.getElementById(`screen-${name}`)?.classList.add("active");
  document.querySelectorAll(".tab-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.screen === name);
  });
  state.currentScreen = name;
  if (name === "history") loadHistory();
  if (name === "patterns") loadPatterns();
}

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const target = btn.dataset.screen;
    if (target === "mood") { showScreen("mood"); return; }
    showScreen(target);
  });
});

// ─── MOOD METER ───────────────────────────────────────────────────────────────
document.querySelectorAll(".quadrant").forEach(q => {
  q.addEventListener("click", () => {
    state.selectedQuadrant = q.dataset.q;
    showWordScreen(q.dataset.q);
  });
});

function showWordScreen(quadrant) {
  const data = QUADRANTS[quadrant];
  document.getElementById("words-title").textContent = `${data.label} — ¿cuál te describe mejor?`;
  const grid = document.getElementById("words-grid");
  grid.innerHTML = "";
  data.words.forEach(word => {
    const chip = document.createElement("button");
    chip.className = "emotion-chip";
    chip.textContent = word;
    chip.addEventListener("click", () => {
      document.querySelectorAll(".emotion-chip").forEach(c => c.classList.remove("selected"));
      chip.classList.add("selected");
      state.selectedEmotion = word;
      setTimeout(() => showScreen("record"), 300);
      document.getElementById("selected-emotion-badge").textContent = word;
    });
    grid.appendChild(chip);
  });
  showScreen("words");
}

document.getElementById("btn-back-words").addEventListener("click", () => showScreen("mood"));
document.getElementById("btn-back-record").addEventListener("click", () => showScreen("words"));

// ─── AUDIO RECORDING ──────────────────────────────────────────────────────────
let mediaRecorder = null;
let audioChunks = [];
let animFrame = null;
let analyser = null;

const recordBtn = document.getElementById("record-btn");
const recordStatus = document.getElementById("record-status");
const waveCanvas = document.getElementById("waveform");
const waveCtx = waveCanvas.getContext("2d");

recordBtn.addEventListener("pointerdown", startRecording);
recordBtn.addEventListener("pointerup", stopRecording);
recordBtn.addEventListener("pointerleave", stopRecording);

async function startRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const ctx = new AudioContext();
  const source = ctx.createMediaStreamSource(stream);
  analyser = ctx.createAnalyser();
  analyser.fftSize = 256;
  source.connect(analyser);

  audioChunks = [];
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
  mediaRecorder.start();

  recordBtn.classList.add("recording");
  recordStatus.textContent = "Grabando...";
  drawWaveform();
}

function stopRecording() {
  if (!mediaRecorder || mediaRecorder.state === "inactive") return;
  mediaRecorder.stop();
  mediaRecorder.onstop = () => {
    state.audioBlob = new Blob(audioChunks, { type: "audio/webm" });
    recordStatus.textContent = "Audio listo ✓";
    document.getElementById("transcription-box").classList.remove("hidden");
    document.getElementById("transcription-box").textContent = "Transcribiendo...";
    document.getElementById("btn-analyze").classList.remove("hidden");
  };
  recordBtn.classList.remove("recording");
  cancelAnimationFrame(animFrame);
}

function drawWaveform() {
  animFrame = requestAnimationFrame(drawWaveform);
  if (!analyser) return;
  const data = new Uint8Array(analyser.frequencyBinCount);
  analyser.getByteTimeDomainData(data);
  waveCtx.clearRect(0, 0, waveCanvas.width, waveCanvas.height);
  waveCtx.strokeStyle = "#6366f1";
  waveCtx.lineWidth = 2;
  waveCtx.beginPath();
  data.forEach((v, i) => {
    const x = (i / data.length) * waveCanvas.width;
    const y = (v / 128) * (waveCanvas.height / 2);
    i === 0 ? waveCtx.moveTo(x, y) : waveCtx.lineTo(x, y);
  });
  waveCtx.stroke();
}

// ─── TRANSCRIBE + ANALYZE ─────────────────────────────────────────────────────
document.getElementById("btn-analyze").addEventListener("click", async () => {
  if (!state.audioBlob) return;
  recordStatus.textContent = "Procesando...";
  document.getElementById("btn-analyze").disabled = true;

  const form = new FormData();
  form.append("audio", state.audioBlob, "recording.webm");
  form.append("emocion_seleccionada", state.selectedEmotion);

  try {
    const res = await fetch(`${API}/api/entry`, { method: "POST", body: form });
    const data = await res.json();
    state.rulerResult = data;

    if (data.crisis_flag) showCrisisModal();

    document.getElementById("transcription-box").textContent = data.transcripcion || "";
    renderRulerDisplay(data);
    showScreen("confirm");
  } catch (err) {
    recordStatus.textContent = "Error al procesar. Intenta de nuevo.";
    console.error(err);
  } finally {
    document.getElementById("btn-analyze").disabled = false;
  }
});

// ─── RULER DISPLAY ────────────────────────────────────────────────────────────
function renderRulerDisplay(ruler) {
  const container = document.getElementById("ruler-display");
  const colorMap = { rojo: "text-red-300", amarillo: "text-yellow-300", azul: "text-blue-300", verde: "text-green-300" };
  container.innerHTML = `
    <div class="bg-white/5 rounded-xl p-4">
      <p class="text-xs text-slate-400 mb-1">Emoción principal</p>
      <p class="text-lg font-bold ${colorMap[ruler.cuadrante] || ''}">${ruler.emocion_primaria || ""}</p>
      ${ruler.emociones_secundarias?.length ? `<p class="text-xs text-slate-400 mt-1">${ruler.emociones_secundarias.join(", ")}</p>` : ""}
    </div>
    <div class="bg-white/5 rounded-xl p-4">
      <p class="text-xs text-slate-400 mb-1">Disparador</p>
      <p class="text-sm text-white">${ruler.disparador || "—"}</p>
    </div>
    <div class="bg-white/5 rounded-xl p-4">
      <p class="text-xs text-slate-400 mb-1">Intensidad</p>
      <div class="flex gap-1 mt-1">
        ${Array.from({length:10},(_,i)=>`<div class="h-2 flex-1 rounded-full ${i < (ruler.intensidad||0) ? "bg-indigo-500" : "bg-white/10"}"></div>`).join("")}
      </div>
    </div>
    <div class="bg-white/5 rounded-xl p-4">
      <p class="text-xs text-slate-400 mb-1">Resumen</p>
      <p class="text-sm text-slate-300 italic">${ruler.resumen || "—"}</p>
    </div>
    ${ruler.pensamientos?.length ? `<div class="bg-white/5 rounded-xl p-4"><p class="text-xs text-slate-400 mb-2">Pensamientos</p>${ruler.pensamientos.map(t=>`<p class="text-sm text-slate-300">• ${t}</p>`).join("")}</div>` : ""}
  `;
}

// ─── SAVE / DISCARD ───────────────────────────────────────────────────────────
document.getElementById("btn-save").addEventListener("click", async () => {
  if (!state.rulerResult) return;
  // Entry already saved via /api/entry — just navigate home
  resetRecordState();
  showScreen("mood");
});

document.getElementById("btn-discard").addEventListener("click", () => {
  resetRecordState();
  showScreen("mood");
});

function resetRecordState() {
  state.audioBlob = null;
  state.rulerResult = null;
  document.getElementById("transcription-box").classList.add("hidden");
  document.getElementById("btn-analyze").classList.add("hidden");
  document.getElementById("btn-analyze").disabled = false;
  recordStatus.textContent = "Listo";
}

// ─── HISTORY ──────────────────────────────────────────────────────────────────
async function loadHistory() {
  const container = document.getElementById("history-list");
  container.innerHTML = `<div class="spinner mx-auto mt-8"></div>`;
  try {
    const res = await fetch(`${API}/api/history?limit=30`);
    const data = await res.json();
    if (!data.entries?.length) {
      container.innerHTML = `<p class="text-slate-500 text-center mt-8">Sin registros aún.</p>`;
      return;
    }
    container.innerHTML = data.entries.map(e => `
      <div class="entry-card ${e.cuadrante || 'azul'}">
        <div class="flex justify-between items-start">
          <div>
            <span class="font-medium text-white">${e.emocion_primaria || "—"}</span>
            ${e.emociones_secundarias ? `<span class="text-xs text-slate-400 ml-2">${Array.isArray(e.emociones_secundarias) ? e.emociones_secundarias.join(", ") : e.emociones_secundarias}</span>` : ""}
          </div>
          <span class="text-xs text-slate-500">${formatDate(e.saved_at)}</span>
        </div>
        <p class="text-sm text-slate-400 mt-1">${e.resumen || ""}</p>
        ${e.disparador ? `<p class="text-xs text-slate-500 mt-1">↳ ${e.disparador}</p>` : ""}
      </div>
    `).join("");
  } catch (err) {
    container.innerHTML = `<p class="text-red-400 text-center mt-8">Error cargando historial</p>`;
  }
}

function formatDate(iso) {
  if (!iso) return "";
  try { return new Date(iso).toLocaleDateString("es-MX", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); }
  catch { return iso; }
}

// ─── PATTERNS ─────────────────────────────────────────────────────────────────
async function loadPatterns() {
  const container = document.getElementById("patterns-container");
  container.innerHTML = `<div class="spinner mx-auto mt-8"></div>`;
  try {
    const res = await fetch(`${API}/api/patterns`);
    const data = await res.json();

    const moodColors = { rojo: "#ef4444", amarillo: "#eab308", azul: "#3b82f6", verde: "#22c55e" };
    const moodEntries = Object.entries(data.mini_mood_meter || {});
    const total = moodEntries.reduce((s, [,v]) => s + v, 0);

    container.innerHTML = `
      <!-- Mini mood meter -->
      <div class="bg-white/5 rounded-xl p-4">
        <h3 class="text-sm font-medium text-slate-300 mb-3">Distribución emocional</h3>
        ${moodEntries.length ? moodEntries.map(([q, count]) => `
          <div class="flex items-center gap-2 mb-2">
            <span class="text-xs w-16 text-slate-400 capitalize">${q}</span>
            <div class="flex-1 bg-white/5 rounded-full h-2">
              <div class="h-2 rounded-full" style="width:${Math.round(count/total*100)}%;background:${moodColors[q]||'#6366f1'}"></div>
            </div>
            <span class="text-xs text-slate-500">${count}</span>
          </div>`).join("") : `<p class="text-slate-500 text-sm">Sin datos aún</p>`}
      </div>

      <!-- Top words -->
      <div class="bg-white/5 rounded-xl p-4">
        <h3 class="text-sm font-medium text-slate-300 mb-3">Emociones más frecuentes</h3>
        <div class="flex flex-wrap gap-2">
          ${(data.palabras_frecuentes || []).map(w => `<span class="emotion-chip text-xs">${w}</span>`).join("") || `<p class="text-slate-500 text-sm">Sin datos aún</p>`}
        </div>
      </div>

      <!-- Pattern -->
      <div class="bg-white/5 rounded-xl p-4">
        <h3 class="text-sm font-medium text-slate-300 mb-2">Patrón detectado</h3>
        <p class="text-sm text-slate-400">${data.patron_detectado || "—"}</p>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<p class="text-red-400 text-center mt-8">Error cargando patrones</p>`;
  }
}

// ─── CHAT ─────────────────────────────────────────────────────────────────────
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");

document.getElementById("btn-send-chat").addEventListener("click", sendChat);
chatInput.addEventListener("keydown", e => { if (e.key === "Enter") sendChat(); });

async function sendChat() {
  const q = chatInput.value.trim();
  if (!q) return;
  chatInput.value = "";
  appendBubble(q, "user");
  const thinking = appendBubble("...", "ai");

  try {
    const res = await fetch(`${API}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q }),
    });
    const data = await res.json();
    thinking.textContent = data.answer || "No pude responder.";
  } catch {
    thinking.textContent = "Error de conexión.";
  }
}

function appendBubble(text, role) {
  const div = document.createElement("div");
  div.className = `p-3 max-w-xs text-sm ${role === "user" ? "bubble-user self-end ml-auto" : "bubble-ai self-start"} text-white`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

// ─── CRISIS MODAL ─────────────────────────────────────────────────────────────
function showCrisisModal() {
  document.getElementById("crisis-modal").classList.remove("hidden");
}

document.getElementById("btn-close-crisis").addEventListener("click", () => {
  document.getElementById("crisis-modal").classList.add("hidden");
});

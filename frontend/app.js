// ─── CONFIG ───────────────────────────────────────────────────────────────────
const API = ""; // same origin — backend serves frontend at root

// ─── RULER DATA ───────────────────────────────────────────────────────────────
// El catálogo es la fuente única del backend; se obtiene de GET /api/emotions.
let QUADRANTS = null;

// ─── STATE ────────────────────────────────────────────────────────────────────
let state = {
  currentScreen: "mood",
  selectedQuadrant: null,
  selectedEmotion: null,
  audioBlob: null,
  pendingText: null,
  rulerResult: null,
  inputMode: "voz",
};

// ─── HORA LOCAL ───────────────────────────────────────────────────────────────
// ISO 8601 con offset local (ej. 2026-05-17T21:34:00-06:00).
function localISOTime() {
  const d = new Date();
  const off = -d.getTimezoneOffset(); // minutos respecto a UTC
  const sign = off >= 0 ? "+" : "-";
  const pad = n => String(Math.floor(Math.abs(n))).padStart(2, "0");
  return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate())
    + "T" + pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds())
    + sign + pad(off / 60) + ":" + pad(off % 60);
}

// ─── CATÁLOGO DE EMOCIONES ─────────────────────────────────────────────────────
let _catalogPromise = null;
// Promesa cacheada: taps tempranos no disparan fetches duplicados; al terminar
// se libera para que el botón de reintento pueda volver a pedir el catálogo.
function loadCatalog() {
  if (_catalogPromise) return _catalogPromise;
  document.getElementById("app-error").classList.add("hidden");
  _catalogPromise = (async () => {
    try {
      const res = await fetch(`${API}/api/emotions`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      QUADRANTS = await res.json();
    } catch (err) {
      console.error("No se pudo cargar el catálogo de emociones", err);
      document.getElementById("app-error").classList.remove("hidden");
    } finally {
      _catalogPromise = null;
    }
  })();
  return _catalogPromise;
}

// ─── NAVIGATION ───────────────────────────────────────────────────────────────
function showScreen(name) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  document.getElementById(`screen-${name}`)?.classList.add("active");
  document.querySelectorAll(".tab-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.screen === name);
  });
  state.currentScreen = name;
  // Mueve el foco al título de la pantalla para lectores de pantalla.
  const heading = document.querySelector(`#screen-${name} [data-screen-title]`);
  if (heading) { heading.setAttribute("tabindex", "-1"); heading.focus({ preventScroll: true }); }
  if (name === "history") loadHistory();
  if (name === "patterns") loadPatterns();
}

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => showScreen(btn.dataset.screen));
});

// ─── MOOD METER ───────────────────────────────────────────────────────────────
document.querySelectorAll(".quadrant").forEach(q => {
  q.addEventListener("click", () => {
    if (!QUADRANTS) { loadCatalog(); return; }
    state.selectedQuadrant = q.dataset.q;
    const meter = document.querySelector(".mood-meter");
    q.classList.add("zooming");
    meter.classList.add("dimmed");
    // 380ms: se cambia de pantalla antes de que el zoom (0.42s) termine;
    // el "snap" del cuadrante al quitar la clase queda oculto tras screen-words.
    setTimeout(() => {
      q.classList.remove("zooming");
      meter.classList.remove("dimmed");
      renderSubmatrix(q.dataset.q);
      showScreen("words");
    }, 380);
  });
});

function renderSubmatrix(quadrant) {
  const data = QUADRANTS[quadrant];
  const stage = document.querySelector(".submatrix-stage");
  stage.className = `submatrix-stage q-${quadrant}`;
  const wordsTitleEl = document.getElementById("words-title");
  wordsTitleEl.textContent = data.name;
  animateWords(wordsTitleEl);
  document.getElementById("axis-top").textContent = `↑ ${data.axisTop}`;
  document.getElementById("axis-bottom").textContent = `${data.axisBottom} ↓`;
  document.getElementById("axis-side").textContent = data.axisSide;

  const grid = document.getElementById("submatrix-grid");
  grid.innerHTML = "";
  const n = data.emotions.length;
  // Más intensa arriba: se invierte el arreglo (que va de leve a intensa).
  [...data.emotions].reverse().forEach((word, idx) => {
    const t = (n - 1 - idx) / (n - 1); // 1 = más intensa, 0 = más leve
    const tile = document.createElement("button");
    tile.type = "button";
    tile.className = "sub-emotion" + (t >= 0.55 ? " is-intense" : "");
    tile.style.setProperty("--t", t.toFixed(3));
    // Emergen desde el centro de la rejilla 3x4: el delay crece con la distancia.
    const row = Math.floor(idx / 3), col = idx % 3;
    const dist = Math.hypot(row - 1.5, col - 1);
    tile.style.animationDelay = `${0.04 + dist * 0.05}s`;
    tile.textContent = word;
    tile.addEventListener("click", () => {
      document.querySelectorAll(".sub-emotion").forEach(c => c.classList.remove("selected"));
      tile.classList.add("selected");
      state.selectedEmotion = word;
      document.getElementById("selected-emotion-badge").textContent = word;
      setTimeout(() => showScreen("record"), 260);
    });
    grid.appendChild(tile);
  });
}

document.getElementById("btn-back-words").addEventListener("click", () => showScreen("mood"));
document.getElementById("btn-back-record").addEventListener("click", () => showScreen("words"));

// ─── AUDIO RECORDING ──────────────────────────────────────────────────────────
let mediaRecorder = null;
let audioChunks = [];
let animFrame = null;
let analyser = null;
let audioStream = null;
let audioCtx = null;
let recordStartTime = 0;
let recordTimerInterval = null;
// Máquina de estados: idle | arming (pidiendo micrófono) | recording | stopping
let recState = "idle";
let recMode = null;          // "hold" | "toggle" — cómo terminará la grabación
let pressStartTs = 0;
let stopWhenReady = false;   // el gesto "hold" terminó mientras se pedía el micrófono

const TAP_THRESHOLD_MS = 350;  // por debajo: fue un toque → modo manos libres
const MIN_RECORDING_MS = 500;  // ignora toques accidentales demasiado cortos

const recordBtn = document.getElementById("record-btn");
const recordStatus = document.getElementById("record-status");
const waveCanvas = document.getElementById("waveform");
const waveCtx = waveCanvas.getContext("2d");

// ─── SELECTOR HABLAR / ESCRIBIR ───────────────────────────────────────────────
const modeVoz = document.getElementById("mode-voz");
const modeTexto = document.getElementById("mode-texto");
const paneVoz = document.getElementById("pane-voz");
const paneTexto = document.getElementById("pane-texto");

function setInputMode(mode) {
  state.inputMode = mode;
  const isVoz = mode === "voz";
  modeVoz.classList.toggle("active", isVoz);
  modeTexto.classList.toggle("active", !isVoz);
  modeVoz.setAttribute("aria-selected", String(isVoz));
  modeTexto.setAttribute("aria-selected", String(!isVoz));
  paneVoz.classList.toggle("hidden", !isVoz);
  paneTexto.classList.toggle("hidden", isVoz);
  if (!isVoz && mediaRecorder && mediaRecorder.state === "recording") cancelRecording();
}
modeVoz.addEventListener("click", () => setInputMode("voz"));
modeTexto.addEventListener("click", () => setInputMode("texto"));

// ─── TEMPORIZADOR Y BOTÓN CANCELAR ───────────────────────────────────────────
const btnCancelRecord = document.getElementById("btn-cancel-record");
const recordTimerEl = document.getElementById("record-timer");

function startRecordTimer() {
  recordTimerEl.classList.remove("hidden");
  const tick = () => {
    const s = Math.floor((Date.now() - recordStartTime) / 1000);
    recordTimerEl.textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  };
  tick();
  recordTimerInterval = setInterval(tick, 250);
}

function stopRecordTimer() {
  clearInterval(recordTimerInterval);
  recordTimerInterval = null;
  recordTimerEl.classList.add("hidden");
}

function cancelRecording() {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.onstop = () => releaseAudioResources();
    mediaRecorder.stop();
  } else {
    releaseAudioResources();
  }
  cancelAnimationFrame(animFrame);
  stopRecordTimer();
  recState = "idle";
  recMode = null;
  stopWhenReady = false;
  audioChunks = [];
  recordBtn.classList.remove("recording", "toggle");
  btnCancelRecord.classList.add("hidden");
  recordStatus.textContent = "Toca o mantén presionado para hablar";
}
btnCancelRecord.addEventListener("click", cancelRecording);

// ─── MODO TEXTO — botón Continuar ─────────────────────────────────────────────
document.getElementById("btn-text-continue").addEventListener("click", () => {
  const txt = document.getElementById("text-input").value.trim();
  if (txt.length < 3) {
    document.getElementById("text-input").focus();
    return;
  }
  analyzeText(txt); // definido en la Task 6
});

async function analyzeText(text) {
  state.pendingText = text;
  startAnalyzingCopy();
  showScreen("analyzing");
  try {
    const res = await fetch(`${API}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: text,
        emocion_seleccionada: state.selectedEmotion,
        client_time: localISOTime(),
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    data.emocion_seleccionada = state.selectedEmotion;
    data.transcripcion = text;
    onAnalysisReady(data);
  } catch (err) {
    stopAnalyzingCopy();
    console.error(err);
    showAnalyzingError("");
  }
}

recordBtn.addEventListener("pointerdown", e => {
  // setPointerCapture: el botón conserva el pointerup aunque el dedo se deslice fuera.
  try { recordBtn.setPointerCapture(e.pointerId); } catch {}
  // Si ya graba en modo manos libres, este toque la finaliza.
  if (recState === "recording" && recMode === "toggle") {
    finishRecording();
    return;
  }
  if (recState !== "idle") return; // ignora gestos mientras arma/detiene
  pressStartTs = Date.now();
  recMode = "hold";                // por defecto; pointerup puede pasarlo a "toggle"
  stopWhenReady = false;
  beginRecording();
});

recordBtn.addEventListener("pointerup", () => {
  if (recMode !== "hold") return;  // ya pasó a toggle, o no hay gesto activo
  const held = Date.now() - pressStartTs;
  if (held < TAP_THRESHOLD_MS) {
    // Toque corto → modo manos libres: sigue grabando hasta el próximo toque.
    recMode = "toggle";
    if (recState === "recording") {
      recordBtn.classList.add("toggle");
      recordStatus.textContent = "Grabando… toca para terminar";
    }
    // Si aún está en "arming", beginRecording verá recMode === "toggle" y continuará.
  } else if (recState === "recording") {
    finishRecording();             // se mantuvo presionado → termina al soltar
  } else {
    stopWhenReady = true;          // soltó durante "arming" → terminar al estar listo
  }
});

recordBtn.addEventListener("pointercancel", () => {
  if (recMode === "hold") {
    if (recState === "recording") finishRecording();
    else stopWhenReady = true;
  }
});

// Soporte de teclado: Enter/Espacio alterna la grabación (modo manos libres).
recordBtn.addEventListener("click", e => {
  if (e.detail !== 0) return; // ignora el click sintético que sigue al pointer
  if (recState === "recording") {
    finishRecording();
  } else if (recState === "idle") {
    recMode = "toggle";
    stopWhenReady = false;
    beginRecording();
  }
});

async function beginRecording() {
  recState = "arming";
  if (!navigator.mediaDevices?.getUserMedia) {
    recordStatus.textContent = "La grabación necesita HTTPS o localhost.";
    recState = "idle";
    recMode = null;
    return;
  }
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    recordStatus.textContent = "No se pudo acceder al micrófono. Revisa los permisos.";
    console.error(err);
    recState = "idle";
    recMode = null;
    return;
  }
  // Algo canceló la grabación mientras se pedía el permiso (cambio de pestaña,
  // cancelar, navegación): descartar el stream y no grabar.
  if (recState !== "arming") {
    stream.getTracks().forEach(t => t.stop());
    return;
  }
  // El gesto fue un "hold" demasiado corto que terminó mientras se pedía el
  // permiso: descartar el stream sin grabar nada.
  if (stopWhenReady && recMode === "hold") {
    stream.getTracks().forEach(t => t.stop());
    recState = "idle";
    recMode = null;
    stopWhenReady = false;
    recordStatus.textContent = "Toca o mantén presionado para hablar";
    return;
  }

  audioStream = stream;
  audioCtx = new AudioContext();
  const source = audioCtx.createMediaStreamSource(audioStream);
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 256;
  source.connect(analyser);

  audioChunks = [];
  mediaRecorder = new MediaRecorder(audioStream);
  mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
  mediaRecorder.start();
  recordStartTime = Date.now();
  recState = "recording";

  recordBtn.classList.add("recording");
  if (recMode === "toggle") {
    recordBtn.classList.add("toggle");
    recordStatus.textContent = "Grabando… toca para terminar";
  } else {
    recordStatus.textContent = "Grabando…";
  }
  btnCancelRecord.classList.remove("hidden");
  startRecordTimer();
  resizeWaveCanvas();
  drawWaveform();

  // Si mientras se pedía el micrófono el usuario ya soltó un "hold" largo.
  if (stopWhenReady) finishRecording();
}

function finishRecording() {
  if (recState !== "recording" || !mediaRecorder) return;
  const elapsed = Date.now() - recordStartTime;
  recState = "stopping";
  recMode = null;
  stopWhenReady = false;
  recordBtn.classList.remove("recording", "toggle");
  stopRecordTimer();
  btnCancelRecord.classList.add("hidden");
  cancelAnimationFrame(animFrame);

  mediaRecorder.onstop = () => {
    releaseAudioResources();
    recState = "idle";
    if (elapsed < MIN_RECORDING_MS) {
      recordStatus.textContent = "Mantén presionado o toca para grabar un poco más.";
      return;
    }
    analyzeEntry(new Blob(audioChunks, { type: "audio/webm" }));
  };
  mediaRecorder.stop();
}

// Libera el micrófono y el AudioContext — sin esto el indicador de micrófono
// queda encendido y el navegador deja de crear AudioContext tras varias grabaciones.
function releaseAudioResources() {
  if (audioStream) {
    audioStream.getTracks().forEach(t => t.stop());
    audioStream = null;
  }
  if (audioCtx && audioCtx.state !== "closed") {
    audioCtx.close();
    audioCtx = null;
  }
  analyser = null;
  mediaRecorder = null;
}

function resizeWaveCanvas() {
  // El buffer del canvas debe igualar su tamaño real en píxeles;
  // si no, el navegador estira los 300x150 por defecto y se ve borroso.
  const dpr = window.devicePixelRatio || 1;
  const rect = waveCanvas.getBoundingClientRect();
  waveCanvas.width = Math.round(rect.width * dpr);
  waveCanvas.height = Math.round(rect.height * dpr);
  waveCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function drawWaveform() {
  animFrame = requestAnimationFrame(drawWaveform);
  if (!analyser) return;
  const data = new Uint8Array(analyser.frequencyBinCount);
  analyser.getByteTimeDomainData(data);
  const w = waveCanvas.clientWidth;
  const h = waveCanvas.clientHeight;
  waveCtx.clearRect(0, 0, w, h);
  waveCtx.strokeStyle = "#7D72D6";
  waveCtx.lineWidth = 2.5;
  waveCtx.lineJoin = "round";
  waveCtx.beginPath();
  data.forEach((v, i) => {
    const x = (i / data.length) * w;
    const y = (v / 128) * (h / 2);
    i === 0 ? waveCtx.moveTo(x, y) : waveCtx.lineTo(x, y);
  });
  waveCtx.stroke();
}

// ─── ANALYZING (mascota: transcribe + analiza) ────────────────────────────────
let analyzingTimer = null;
const ANALYZING_MESSAGES = [
  "Escuchando lo que compartiste…",
  "Reconociendo tu emoción…",
  "Buscando el patrón…",
  "Casi listo…",
];

function onAnalysisReady(data) {
  state.rulerResult = data;
  stopAnalyzingCopy();
  if (data.crisis_flag) showCrisisModal();
  const box = document.getElementById("transcription-box");
  if (data.transcripcion) {
    box.textContent = data.transcripcion;
    box.classList.remove("hidden");
  } else {
    box.classList.add("hidden");
  }
  renderRulerDisplay(data);
  // /api/entry y /api/analyze no devuelven acompañamiento → se pasa null
  // explícitamente para que renderAcompanamiento lo oculte. El acompañamiento
  // real llega al guardar, en el handler de Guardar.
  renderAcompanamiento(null);
  showScreen("confirm");
}

async function analyzeEntry(blob) {
  state.audioBlob = blob;
  startAnalyzingCopy();
  showScreen("analyzing");

  const form = new FormData();
  form.append("audio", blob, "recording.webm");
  form.append("emocion_seleccionada", state.selectedEmotion);
  form.append("client_time", localISOTime());

  try {
    const res = await fetch(`${API}/api/entry`, { method: "POST", body: form });
    if (!res.ok) {
      // El backend mapea los errores de audio (corto, sin voz, formato inválido)
      // a un HTTPException con `detail` — mostramos ese mensaje específico.
      const errData = await res.json().catch(() => ({}));
      const e = new Error(errData.detail || "No se pudo procesar el audio.");
      e.userFacing = true;
      throw e;
    }
    const data = await res.json();
    onAnalysisReady(data);
  } catch (err) {
    stopAnalyzingCopy();
    console.error(err);
    // Si el error trae un mensaje del backend lo mostramos; si es de red, genérico.
    showAnalyzingError(err.userFacing ? err.message : "");
  }
}

function startAnalyzingCopy() {
  document.getElementById("analyzing-main").classList.remove("hidden");
  document.getElementById("analyzing-error").classList.add("hidden");
  const el = document.getElementById("analyzing-status");
  let i = 0;
  el.textContent = ANALYZING_MESSAGES[0];
  clearInterval(analyzingTimer);
  analyzingTimer = setInterval(() => {
    i = (i + 1) % ANALYZING_MESSAGES.length;
    el.style.animation = "none";
    void el.offsetWidth; // fuerza reflow para reiniciar la animación
    el.textContent = ANALYZING_MESSAGES[i];
    el.style.animation = "";
  }, 2200);
}

function stopAnalyzingCopy() {
  clearInterval(analyzingTimer);
  analyzingTimer = null;
}

function showAnalyzingError(message) {
  document.getElementById("analyzing-main").classList.add("hidden");
  document.getElementById("analyzing-error").classList.remove("hidden");
  document.getElementById("analyzing-error-msg").textContent =
    message || "Revisa tu conexión e inténtalo otra vez.";
}

document.getElementById("btn-analyzing-retry").addEventListener("click", () => {
  // En modo texto se reintenta el texto; el audioBlob puede haber quedado de un
  // intento de voz previo sin limpiar (la navegación por tabs no lo resetea).
  if (state.inputMode === "texto" && state.pendingText) analyzeText(state.pendingText);
  else if (state.audioBlob) analyzeEntry(state.audioBlob);
  else if (state.pendingText) analyzeText(state.pendingText);
});
document.getElementById("btn-analyzing-back").addEventListener("click", () => {
  resetRecordState();
  showScreen("record");
});

// ─── RULER DISPLAY ────────────────────────────────────────────────────────────
function renderRulerDisplay(ruler) {
  const container = document.getElementById("ruler-display");
  const colorMap = { rojo: "q-rojo", amarillo: "q-amarillo", azul: "q-azul", verde: "q-verde" };
  container.innerHTML = `
    <div class="info-card">
      <p class="info-label">Emoción principal</p>
      <p class="text-lg font-bold ${colorMap[ruler.cuadrante] || ''}">${ruler.emocion_primaria || ""}</p>
      ${ruler.emociones_secundarias?.length ? `<p class="text-xs t-dim mt-1">${ruler.emociones_secundarias.join(", ")}</p>` : ""}
    </div>
    <div class="info-card">
      <p class="info-label">Disparador</p>
      <p class="text-sm t-strong">${ruler.disparador || "—"}</p>
    </div>
    <div class="info-card">
      <p class="info-label">Intensidad</p>
      <div class="flex gap-1 mt-1">
        ${Array.from({length:10},(_,i)=>`<div class="h-2 flex-1 rounded-full ${i < (ruler.intensidad||0) ? "bg-indigo-500" : "track"}"></div>`).join("")}
      </div>
    </div>
    <div class="info-card">
      <p class="info-label">Resumen</p>
      <p class="text-sm t-soft italic">${ruler.resumen || "—"}</p>
    </div>
    ${ruler.pensamientos?.length ? `<div class="info-card"><p class="info-label mb-2">Pensamientos</p>${ruler.pensamientos.map(t=>`<p class="text-sm t-soft">• ${t}</p>`).join("")}</div>` : ""}
  `;
}

// ─── ACOMPAÑAMIENTO DE MIRA ───────────────────────────────────────────────────
// Render seguro (textContent): el mensaje viene del LLM, nunca como HTML.
function renderAcompanamiento(acomp) {
  const el = document.getElementById("companion-card");
  el.innerHTML = "";
  if (!acomp || !acomp.mensaje) { el.classList.add("hidden"); return; }
  const bubble = document.createElement("div");
  bubble.className = "companion-bubble";
  const img = document.createElement("img");
  img.src = "/assets/mira.png";
  img.alt = "";
  img.className = "companion-mira";
  img.onerror = () => img.classList.add("img-missing");
  const p = document.createElement("p");
  p.textContent = acomp.mensaje;
  bubble.append(img, p);
  el.append(bubble);
  el.classList.remove("hidden");
}

// Mensaje contextual de Mira al abrir la app — solo si el pipeline interviene.
async function loadHomeCompanion() {
  const el = document.getElementById("home-companion");
  if (!el) return;
  try {
    const res = await fetch(`${API}/api/companion`);
    if (!res.ok) return;
    const data = await res.json();
    if (!data.intervenir || !data.mensaje) { el.classList.add("hidden"); return; }
    el.innerHTML = "";
    const bubble = document.createElement("div");
    bubble.className = "companion-bubble companion-home";
    const p = document.createElement("p");
    p.textContent = data.mensaje;
    const close = document.createElement("button");
    close.className = "companion-close";
    close.type = "button";
    close.setAttribute("aria-label", "Descartar mensaje");
    close.textContent = "✕";
    close.addEventListener("click", () => el.classList.add("hidden"));
    bubble.append(p, close);
    el.append(bubble);
    el.classList.remove("hidden");
  } catch {
    /* el acompañamiento es opcional — si falla, no se muestra nada */
  }
}

// ─── CONFIRM ──────────────────────────────────────────────────────────────────
// El registro NO se guarda durante el análisis: aquí el usuario decide.
const btnConfirmSave = document.getElementById("btn-confirm-save");
const confirmActions = document.querySelector(".confirm-actions");
const btnConfirmDone = document.getElementById("btn-confirm-done");

btnConfirmSave.addEventListener("click", async () => {
  if (!state.rulerResult) return;
  btnConfirmSave.disabled = true;
  btnConfirmSave.textContent = "Guardando…";
  try {
    const res = await fetch(`${API}/api/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.rulerResult),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    // Mira reflexiona tras guardar: si el pipeline intervino, mostramos su mensaje
    // y dejamos al usuario en Confirmar con un solo botón "Listo".
    if (data.acompanamiento && data.acompanamiento.mensaje) {
      renderAcompanamiento(data.acompanamiento);
      confirmActions.classList.add("hidden");
      btnConfirmDone.classList.remove("hidden");
    } else {
      resetRecordState();
      showScreen("mood");
    }
  } catch (err) {
    console.error(err);
    btnConfirmSave.textContent = "Reintentar guardar";
  } finally {
    btnConfirmSave.disabled = false;
  }
});

document.getElementById("btn-confirm-cancel").addEventListener("click", () => {
  resetRecordState();
  showScreen("mood");
});

btnConfirmDone.addEventListener("click", () => {
  resetRecordState();
  showScreen("mood");
});

function resetRecordState() {
  state.audioBlob = null;
  state.pendingText = null;
  state.rulerResult = null;
  recState = "idle";
  recMode = null;
  stopWhenReady = false;
  const box = document.getElementById("transcription-box");
  box.classList.add("hidden");
  box.textContent = "";
  recordBtn.classList.remove("recording", "toggle");
  recordStatus.textContent = "Toca o mantén presionado para hablar";
  setInputMode("voz");
  document.getElementById("text-input").value = "";
  stopRecordTimer();
  btnCancelRecord.classList.add("hidden");
  // Resetear UI de Confirmar para la siguiente vez.
  btnConfirmSave.disabled = false;
  btnConfirmSave.textContent = "Guardar";
  confirmActions.classList.remove("hidden");
  btnConfirmDone.classList.add("hidden");
  renderAcompanamiento(null);
}

// ─── HISTORY ──────────────────────────────────────────────────────────────────
async function loadHistory() {
  const container = document.getElementById("history-list");
  container.setAttribute("aria-busy", "true");
  container.innerHTML = skeletonCards(4);
  try {
    const res = await fetch(`${API}/api/history?limit=30`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data.entries?.length) {
      container.removeAttribute("aria-busy");
      container.innerHTML = `<p class="empty-state">Aún no hay registros.<br/>Tu primer momento aparecerá aquí.</p>`;
      return;
    }
    container.removeAttribute("aria-busy");
    container.innerHTML = data.entries.map(e => `
      <div class="entry-card ${e.cuadrante || 'azul'}">
        <div class="flex justify-between items-start">
          <div>
            <span class="font-medium t-strong">${e.emocion_primaria || "—"}</span>
            ${e.emociones_secundarias ? `<span class="text-xs t-dim ml-2">${Array.isArray(e.emociones_secundarias) ? e.emociones_secundarias.join(", ") : e.emociones_secundarias}</span>` : ""}
          </div>
          <span class="text-xs t-dim">${formatDate(e.saved_at)}</span>
        </div>
        <p class="text-sm t-dim mt-1">${e.resumen || ""}</p>
        ${e.disparador ? `<p class="text-xs t-faint mt-1">↳ ${e.disparador}</p>` : ""}
      </div>
    `).join("");
  } catch (err) {
    container.removeAttribute("aria-busy");
    container.innerHTML = `<p class="error-state">No se pudo cargar el historial.</p>`;
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
  container.setAttribute("aria-busy", "true");
  container.innerHTML = skeletonCards(3);
  try {
    const res = await fetch(`${API}/api/patterns`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const moodColors = { rojo: "#C2553B", amarillo: "#B0852A", azul: "#4E6E88", verde: "#557A58" };
    const moodEntries = Object.entries(data.mini_mood_meter || {});
    const total = moodEntries.reduce((s, [,v]) => s + v, 0);

    container.removeAttribute("aria-busy");
    container.innerHTML = `
      <div class="info-card">
        <h3 class="text-sm font-semibold t-strong mb-3">Distribución emocional</h3>
        ${moodEntries.length ? moodEntries.map(([q, count]) => `
          <div class="flex items-center gap-2 mb-2">
            <span class="text-xs w-16 t-dim capitalize">${q}</span>
            <div class="flex-1 track rounded-full h-2">
              <div class="h-2 rounded-full" style="width:${total ? Math.round(count/total*100) : 0}%;background:${moodColors[q]||'#5B53C9'}"></div>
            </div>
            <span class="text-xs t-dim">${count}</span>
          </div>`).join("") : `<p class="t-dim text-sm">Sin datos aún</p>`}
      </div>

      <div class="info-card">
        <h3 class="text-sm font-semibold t-strong mb-3">Emociones más frecuentes</h3>
        <div class="flex flex-wrap gap-2">
          ${(data.palabras_frecuentes || []).map(w => `<span class="emotion-chip emotion-chip-sm">${w}</span>`).join("") || `<p class="t-dim text-sm">Sin datos aún</p>`}
        </div>
      </div>

      ${(data.insights && data.insights.length) ? `
      <div class="info-card">
        <h3 class="text-sm font-semibold t-strong mb-3">Lo que Mirror nota</h3>
        ${data.insights.map(i => `<p class="insight-line">${i.texto}</p>`).join("")}
      </div>` : ""}

      <div class="info-card">
        <h3 class="text-sm font-semibold t-strong mb-2">Patrón detectado</h3>
        <p class="text-sm t-dim">${data.patron_detectado || "—"}</p>
        ${data.racha_registro ? `<p class="text-xs t-faint mt-2">Llevas ${data.racha_registro} día(s) seguidos registrando.</p>` : ""}
      </div>
    `;
  } catch (err) {
    container.removeAttribute("aria-busy");
    container.innerHTML = `<p class="error-state">No se pudieron cargar los patrones.</p>`;
  }
}

// ─── CHAT ─────────────────────────────────────────────────────────────────────
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const btnSendChat = document.getElementById("btn-send-chat");

btnSendChat.addEventListener("click", sendChat);
chatInput.addEventListener("keydown", e => { if (e.key === "Enter") sendChat(); });

async function sendChat() {
  const q = chatInput.value.trim();
  if (!q) return;
  chatInput.value = "";
  btnSendChat.disabled = true;
  appendBubble(q, "user");
  const thinking = appendBubble("…", "ai");
  thinking.classList.add("bubble-thinking");

  try {
    const res = await fetch(`${API}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    thinking.classList.remove("bubble-thinking");
    thinking.textContent = data.answer || "No pude responder.";
  } catch {
    thinking.classList.remove("bubble-thinking");
    thinking.textContent = "Error de conexión.";
  } finally {
    btnSendChat.disabled = false;
  }
}

function appendBubble(text, role) {
  const div = document.createElement("div");
  div.className = `chat-bubble ${role === "user" ? "bubble-user self-end ml-auto" : "bubble-ai self-start"}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

// ─── CRISIS MODAL ─────────────────────────────────────────────────────────────
let crisisLastFocus = null;

function showCrisisModal() {
  const modal = document.getElementById("crisis-modal");
  crisisLastFocus = document.activeElement;
  modal.classList.add("visible");
  document.getElementById("btn-close-crisis").focus();
  document.addEventListener("keydown", onCrisisKeydown);
}

function closeCrisisModal() {
  const modal = document.getElementById("crisis-modal");
  modal.classList.remove("visible");
  document.removeEventListener("keydown", onCrisisKeydown);
  if (crisisLastFocus && typeof crisisLastFocus.focus === "function") crisisLastFocus.focus();
}

// Cierra con Escape y atrapa el foco dentro del modal (Tab cíclico).
function onCrisisKeydown(e) {
  if (e.key === "Escape") { closeCrisisModal(); return; }
  if (e.key !== "Tab") return;
  const f = document.getElementById("crisis-modal").querySelectorAll('a[href], button');
  if (!f.length) return;
  const first = f[0], last = f[f.length - 1];
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
}

document.getElementById("btn-close-crisis").addEventListener("click", closeCrisisModal);

// ─── UTILIDADES DE ANIMACIÓN ──────────────────────────────────────────────────

/** Anima la entrada de un elemento texto palabra por palabra. */
function animateWords(el) {
  const words = el.textContent.trim().split(/\s+/);
  el.textContent = "";
  el.classList.add("word-anim");
  words.forEach((w, i) => {
    const span = document.createElement("span");
    span.className = "word";
    span.textContent = w;
    span.style.animationDelay = `${i * 0.07}s`;
    el.appendChild(span);
    if (i < words.length - 1) el.appendChild(document.createTextNode(" "));
  });
}

/** Genera n tarjetas skeleton para indicar carga. */
function skeletonCards(n = 4) {
  return Array.from({ length: n }, () => `
    <div class="skeleton-card">
      <div class="skel-line w-40"></div>
      <div class="skel-line w-80"></div>
      <div class="skel-line w-60"></div>
    </div>`).join("");
}

// ─── ARRANQUE ─────────────────────────────────────────────────────────────────

// Anima la tagline de la pantalla principal al cargar la app.
const taglineEl = document.querySelector("#screen-mood .tagline");
if (taglineEl) animateWords(taglineEl);

document.getElementById("btn-app-retry").addEventListener("click", loadCatalog);
loadCatalog();

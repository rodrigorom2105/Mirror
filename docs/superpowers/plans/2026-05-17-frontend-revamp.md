# Mirror — Revamp del Frontend · Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Llevar el frontend de Mirror a un tema claro "cream", con sub-matriz de emociones, sin emojis, más animación, y con modos voz/texto + guardar/cancelar.

**Architecture:** Frontend vanilla (HTML/CSS/JS) en `frontend/`, servido por el backend FastAPI en la raíz. Un único cambio de backend separa "analizar" de "guardar" para que Cancelar no deje basura. La implementación se hace por tareas; cada una deja la app funcionando.

**Tech Stack:** HTML/CSS/JS vanilla, Lucide icons, Tailwind compilado (`tailwind.css`), FastAPI + pytest (backend).

**Spec:** `docs/superpowers/specs/2026-05-17-frontend-revamp-design.md`

---

## Antes de empezar

- **Invoca las skills `ui-ux-pro-max` y `frontend-design`** al iniciar la implementación: guían la calidad visual (espaciado, sombras, curvas de animación, jerarquía). Este plan fija los contratos duros (variables de color, datos de emociones, lógica JS, API); el pulido estético lo afinan esas skills.
- El frontend **no tiene framework de tests JS**. La verificación de las tareas de frontend es **en navegador** con las herramientas de Chrome DevTools MCP (screenshot, snapshot, click). El backend sí usa pytest.
- **Levantar la app para verificar:**
  - Solo-UI (sin backend pesado): `cd frontend && python3 -m http.server 4173` → abrir `http://localhost:4173`. Las llamadas `/api/*` fallarán; suficiente para tareas visuales.
  - Flujo completo (Tareas 5–6): `cd backend && .venv/bin/python main.py` → abrir `http://localhost:8000`.
- No se commitea nada fuera del alcance: cada `git add` lista archivos explícitos.
- Referencias por **función/selector**, no por número de línea (el working tree puede moverse con GitButler).

---

## Task 1: Paleta "Crema clara" (tema claro)

Migrar de tema oscuro azul a tema claro cálido. Es una tarea grande pero cohesiva: la app no se ve bien "a medias".

**Files:**
- Modify: `frontend/styles.css`
- Modify: `frontend/index.html`
- Modify: `frontend/app.js`

- [ ] **Step 1: Reemplazar el bloque `:root` en `styles.css`**

Sustituir el `:root` actual por:

```css
:root {
  /* Cuadrantes — tono base (texto/borde) y superficie pastel */
  --red: #C2553B;        --red-soft: #F3DDD4;
  --yellow: #B0852A;     --yellow-soft: #F6ECD6;
  --blue: #4E6E88;       --blue-soft: #E0E8EE;
  --green: #557A58;      --green-soft: #E2EBE2;
  /* Acento (índigo cálido — tono de la mascota Mira) */
  --indigo: #5B53C9;
  --indigo-light: #7D72D6;
  /* Superficies y texto */
  --bg: #F7F1E6;
  --surface: #FCF8F0;
  --surface-2: #F1E9D8;
  --border: rgba(120, 100, 70, 0.16);
  --text: #4A4338;
  --text-dim: #9A9082;
  --tab-h: 68px;
  --safe-b: env(safe-area-inset-bottom, 0px);
  --safe-t: env(safe-area-inset-top, 0px);
  --ease-soft: cubic-bezier(0.22, 1, 0.36, 1);
  --ease-spring: cubic-bezier(0.34, 1.4, 0.5, 1);
}
```

- [ ] **Step 2: Actualizar el fondo del `body`**

Reemplazar `background-color`/`background-image` de la regla `body` por un fondo crema con gradientes cálidos:

```css
body {
  margin: 0;
  background-color: var(--bg);
  background-image:
    radial-gradient(circle at 50% -15%, rgba(125, 114, 214, 0.10) 0%, transparent 60%),
    radial-gradient(circle at 100% 110%, rgba(194, 85, 59, 0.06) 0%, transparent 45%);
  background-attachment: fixed;
  color: var(--text);
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  overscroll-behavior-y: contain;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
```

- [ ] **Step 3: Adaptar los 4 cuadrantes del Mood Meter a pastel**

Reemplazar las reglas `.quadrant-red/.quadrant-yellow/.quadrant-blue/.quadrant-green` (y sus `::before`/glow) por superficies pastel claras con sombra cálida. Para cada cuadrante, patrón:

```css
.quadrant-red {
  background: linear-gradient(160deg, #FFFFFF 0%, var(--red-soft) 100%);
  border: 1px solid color-mix(in srgb, var(--red) 35%, transparent);
  box-shadow: 0 10px 26px rgba(120, 100, 70, 0.10);
}
.quadrant-red .q-title { color: var(--red); }
```

Repetir para `yellow`/`blue`/`green` con sus variables. Eliminar los `drop-shadow` de glow de `.q-emoji` (ese selector se elimina en la Task 2).

- [ ] **Step 4: Convertir las superficies "glassmorphism" oscuras a crema**

En `styles.css`, donde haya `background: rgba(255,255,255,.0X)` o `rgba(9,13,22,...)` (tarjetas `.info-card`, `.entry-card`, `.transcription-box`, `.emotion-chip`, `#tab-bar`, `.chat-header`, `.chat-input-row`, `#crisis-modal`, `.crisis-card`, `#chat-input`, `#waveform`), sustituir por `var(--surface)` / `var(--surface-2)` y bordes `var(--border)`. El backdrop del modal de crisis pasa a `rgba(74, 67, 56, 0.45)`. Las sombras `rgba(0,0,0,...)` o glow de color pasan a `rgba(120,100,70,0.10–0.16)`. El `#tab-bar` usa `background: rgba(252, 248, 240, 0.88)`.

- [ ] **Step 5: Ajustar textos con color claro hardcodeado en `styles.css`**

Buscar valores `#fff`, `#cbd5e1`, `#94a3b8`, `#64748b`, `#e0e7ff`, `#c7d2fe`, `#f87171`, `#818cf8` usados como color de texto y mapearlos: títulos `#fff`→`var(--text)`; secundarios→`var(--text-dim)`. El gradiente del `h1` de `#screen-mood` pasa a `linear-gradient(135deg, #7D72D6 0%, #5B53C9 60%, #C2553B 120%)`. El `.error-state` mantiene un rojo legible: `#C2553B`. El placeholder de `.mira-body.img-missing` mantiene su gradiente índigo (es la mascota).

- [ ] **Step 6: Definir clases semánticas de texto y fills**

Añadir al final de la sección base de `styles.css`:

```css
/* Clases semánticas — reemplazan utilidades Tailwind de color en plantillas JS */
.t-strong { color: var(--text); }
.t-soft   { color: #6A6356; }
.t-dim    { color: var(--text-dim); }
.t-faint  { color: #B3A994; }
.q-rojo     { color: var(--red); }
.q-amarillo { color: var(--yellow); }
.q-azul     { color: var(--blue); }
.q-verde    { color: var(--green); }
.track    { background: rgba(120, 100, 70, 0.10); }
```

- [ ] **Step 7: Reemplazar utilidades Tailwind de color en `app.js`**

En las plantillas de string de `app.js` (funciones `renderRulerDisplay`, `loadHistory`, `loadPatterns`), reemplazar **todas** las apariciones de estas clases de color (las utilidades de layout/tamaño como `flex`, `gap-1`, `text-sm`, `font-bold` se conservan):

| Buscar | Reemplazar |
|---|---|
| `text-white` | `t-strong` |
| `text-slate-200` | `t-strong` |
| `text-slate-300` | `t-soft` |
| `text-slate-400` | `t-dim` |
| `text-slate-500` | `t-faint` |
| `bg-white/10` | `track` |
| `bg-white/5` | `track` |

Y reemplazar el objeto `colorMap` de `renderRulerDisplay`:

```js
const colorMap = { rojo: "q-rojo", amarillo: "q-amarillo", azul: "q-azul", verde: "q-verde" };
```

- [ ] **Step 8: Actualizar `moodColors` en `loadPatterns` y la barra de intensidad**

En `loadPatterns`, cambiar `moodColors` a los tonos crema:

```js
const moodColors = { rojo: "#C2553B", amarillo: "#B0852A", azul: "#4E6E88", verde: "#557A58" };
```

En `styles.css`, la regla `#ruler-display .bg-indigo-500` (degradado de intensidad) pasa a `linear-gradient(90deg, #557A58, #B0852A 55%, #C2553B) !important`.

- [ ] **Step 9: Actualizar `theme-color` en `index.html`**

Cambiar `<meta name="theme-color" content="#090d16" />` por `content="#F7F1E6"`.

- [ ] **Step 10: Verificar en el navegador**

`cd frontend && python3 -m http.server 4173`. Con Chrome DevTools MCP: navegar a `http://localhost:4173`, tomar screenshot de cada pantalla (Registrar, Historial, Patrones, Chat — usar el tab bar). Confirmar: fondo crema, texto legible (sin texto blanco invisible), 4 cuadrantes pastel, tab bar claro. Revisar contraste de texto sobre crema (debe cumplir AA).

- [ ] **Step 11: Commit**

```bash
git add frontend/styles.css frontend/index.html frontend/app.js
git commit -m "feat(frontend): tema claro 'cream' — paleta, superficies y textos"
```

---

## Task 2: Eliminar emojis · iconos Lucide

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/styles.css`
- Modify: `frontend/app.js`

- [ ] **Step 1: Sustituir los emojis de cuadrante por iconos Lucide en `index.html`**

En `#screen-mood`, en cada `.quadrant`, reemplazar `<span class="q-emoji" aria-hidden="true">🔥</span>` por `<span class="q-icon" aria-hidden="true"><i data-lucide="flame"></i></span>`. Iconos por cuadrante: rojo→`flame`, amarillo→`sun`, azul→`cloud-rain`, verde→`leaf`.

- [ ] **Step 2: Renombrar `.q-emoji` → `.q-icon` en `styles.css`**

Reemplazar la regla `.q-emoji` por:

```css
.q-icon {
  margin-bottom: 8px;
  line-height: 0;
}
.q-icon svg {
  width: clamp(30px, 8vw, 44px);
  height: clamp(30px, 8vw, 44px);
  stroke-width: 1.75;
}
.quadrant-red .q-icon    { color: var(--red); }
.quadrant-yellow .q-icon { color: var(--yellow); }
.quadrant-blue .q-icon   { color: var(--blue); }
.quadrant-green .q-icon  { color: var(--green); }
```

- [ ] **Step 3: Quitar emojis de los textos de los botones "Atrás"**

En `index.html`, los botones `#btn-back-words` y `#btn-back-record` cambian de `← Atrás` a:
`<i data-lucide="arrow-left" aria-hidden="true"></i><span>Atrás</span>`. En `styles.css`, `.back-btn svg { width: 18px; height: 18px; }`.

- [ ] **Step 4: Quitar los emojis de color de las etiquetas de `QUADRANTS` en `app.js`**

En el objeto `QUADRANTS`, quitar el prefijo emoji de cada `label` (`"🔴 Rojo"` → `"Rojo"`, etc.). (El objeto se reestructura por completo en la Task 3; este paso solo elimina el rastro de emoji por si la Task 3 se ejecuta después.)

- [ ] **Step 5: Confirmar que Lucide procesa los iconos de pantallas ocultas**

Los iconos nuevos (cuadrantes, botones Atrás) son estáticos en `index.html`. El `<script>` que llama `lucide.createIcons()` corre al cargar y procesa **todos** los `[data-lucide]` del DOM, incluso dentro de pantallas con `display:none`. No hace falta re-ejecutarlo. Solo confirmar que la llamada `lucide.createIcons()` sigue presente en `index.html` después de cargar `app.js`.

- [ ] **Step 6: Verificar en el navegador**

Servir el frontend, navegar a `http://localhost:4173`. Confirmar con screenshot: los 4 cuadrantes muestran iconos de línea (no emojis), botones Atrás con icono. Buscar en el DOM que no quede ningún emoji.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html frontend/styles.css frontend/app.js
git commit -m "feat(frontend): reemplazar emojis por iconos Lucide"
```

---

## Task 3: Mood Meter — más emociones, sub-matriz con ejes y zoom

**Files:**
- Modify: `frontend/app.js`
- Modify: `frontend/index.html`
- Modify: `frontend/styles.css`

- [ ] **Step 1: Reestructurar el objeto `QUADRANTS` en `app.js`**

Reemplazar el objeto `QUADRANTS` completo por (emociones ordenadas de **menor a mayor intensidad**):

```js
const QUADRANTS = {
  rojo: {
    name: "Alta tensión", icon: "flame",
    emotions: ["nervioso","inquieto","preocupado","tenso","ansioso","irritado",
               "molesto","frustrado","estresado","abrumado","enojado","furioso"],
    axisTop: "Más alterado", axisBottom: "Más calmado", axisSide: "Más desagradable",
  },
  amarillo: {
    name: "Energía positiva", icon: "sun",
    emotions: ["optimista","motivado","animado","alegre","feliz","entusiasmado",
               "inspirado","orgulloso","emocionado","sorprendido","eufórico","radiante"],
    axisTop: "Más intenso", axisBottom: "Más sereno", axisSide: "Más agradable",
  },
  azul: {
    name: "Baja energía", icon: "cloud-rain",
    emotions: ["desganado","aburrido","nostálgico","melancólico","desanimado","decepcionado",
               "triste","solo","agotado","vacío","derrotado","abatido"],
    axisTop: "Más leve", axisBottom: "Más hundido", axisSide: "Más desagradable",
  },
  verde: {
    name: "Paz interior", icon: "leaf",
    emotions: ["cómodo","contento","satisfecho","tranquilo","relajado","calmado",
               "sereno","agradecido","pleno","seguro","en paz","descansado"],
    axisTop: "Más activo", axisBottom: "Más profundo", axisSide: "Más agradable",
  },
};
```

- [ ] **Step 2: Rediseñar el markup de `#screen-words` como sub-matriz en `index.html`**

Reemplazar el contenido de `<div id="screen-words" class="screen">` por:

```html
<div id="screen-words" class="screen">
  <button id="btn-back-words" class="back-btn" type="button">
    <i data-lucide="arrow-left" aria-hidden="true"></i><span>Atrás</span>
  </button>
  <h2 id="words-title" data-screen-title></h2>
  <p id="words-subtitle" class="submatrix-sub">¿Cuál te describe mejor?</p>
  <div class="submatrix-stage">
    <p class="submatrix-axis axis-top" id="axis-top"></p>
    <div class="submatrix-row">
      <p class="submatrix-axis axis-side" id="axis-side"></p>
      <div id="submatrix-grid" class="submatrix-grid"></div>
    </div>
    <p class="submatrix-axis axis-bottom" id="axis-bottom"></p>
  </div>
</div>
```

- [ ] **Step 3: Reescribir la navegación cuadrante→sub-matriz en `app.js`**

Reemplazar `showWordScreen` y el listener de `.quadrant` por:

```js
document.querySelectorAll(".quadrant").forEach(q => {
  q.addEventListener("click", () => {
    state.selectedQuadrant = q.dataset.q;
    const meter = document.querySelector(".mood-meter");
    q.classList.add("zooming");
    meter.classList.add("dimmed");
    setTimeout(() => {
      q.classList.remove("zooming");
      meter.classList.remove("dimmed");
      renderSubmatrix(q.dataset.q);
      showScreen("words");
    }, 260);
  });
});

function renderSubmatrix(quadrant) {
  const data = QUADRANTS[quadrant];
  const stage = document.querySelector(".submatrix-stage");
  stage.className = `submatrix-stage q-${quadrant}`;
  document.getElementById("words-title").textContent = data.name;
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
    tile.style.animationDelay = `${idx * 0.03}s`;
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
```

- [ ] **Step 4: Estilos de la sub-matriz en `styles.css`**

Añadir:

```css
.submatrix-sub { text-align: center; color: var(--text-dim); font-size: 0.9rem; margin: -8px 0 14px; }
.submatrix-stage { flex: 1; display: flex; flex-direction: column; justify-content: center; min-height: 0; }
.submatrix-stage.q-rojo     { --q-base: var(--red);    --q-soft: var(--red-soft);    --q-ink: var(--red); }
.submatrix-stage.q-amarillo { --q-base: var(--yellow); --q-soft: var(--yellow-soft); --q-ink: #8A6618; }
.submatrix-stage.q-azul     { --q-base: var(--blue);   --q-soft: var(--blue-soft);   --q-ink: var(--blue); }
.submatrix-stage.q-verde    { --q-base: var(--green);  --q-soft: var(--green-soft);  --q-ink: var(--green); }
.submatrix-axis { color: var(--text-dim); font-size: 0.62rem; font-weight: 700;
  letter-spacing: 0.09em; text-transform: uppercase; text-align: center; margin: 0; }
.submatrix-row { display: flex; align-items: stretch; gap: 8px; margin: 9px 0; }
.axis-side { writing-mode: vertical-rl; transform: rotate(180deg); flex-shrink: 0; }
.submatrix-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 9px; flex: 1; }
.sub-emotion {
  --t: 0;
  border: 1px solid color-mix(in srgb, var(--q-base) 30%, transparent);
  border-radius: 14px;
  padding: 14px 6px;
  font: inherit; font-size: 0.82rem; font-weight: 600;
  cursor: pointer;
  color: var(--q-ink);
  background: color-mix(in srgb, var(--q-base) calc(18% + var(--t) * 70%), var(--q-soft));
  transition: transform 0.18s var(--ease-spring), box-shadow 0.18s ease;
  animation: chipIn 0.4s var(--ease-soft) both;
}
.sub-emotion.is-intense { color: #fff; }
.sub-emotion:active { transform: scale(0.94); }
.sub-emotion.selected { box-shadow: 0 0 0 2.5px var(--q-base); transform: scale(1.04); }
@media (hover: hover) { .sub-emotion:hover { transform: translateY(-2px); } }

/* Zoom del cuadrante al entrar a la sub-matriz */
.mood-meter.dimmed .quadrant:not(.zooming) { opacity: 0.15; transform: scale(0.9); }
.quadrant.zooming { transform: scale(1.35); z-index: 2; }
.mood-meter .quadrant { transition: transform 0.26s var(--ease-soft), opacity 0.26s ease; }
#screen-words.active { animation: submatrixIn 0.4s var(--ease-soft) both; }
@keyframes submatrixIn {
  from { opacity: 0; transform: scale(0.86); }
  to   { opacity: 1; transform: scale(1); }
}
```

Eliminar las reglas viejas de `.words-grid` y los `#words-grid .emotion-chip:nth-child(...)` si ya no se usan (la nube de chips se reemplazó). Conservar `.emotion-chip`/`.emotion-chip-sm` (los usa Patrones).

- [ ] **Step 5: Verificar en el navegador**

Servir el frontend. Tocar cada uno de los 4 cuadrantes: confirmar el zoom del cuadrante, que la sub-matriz abre con 12 emociones en rejilla 3×4, degradado de color (intensa arriba), etiquetas de eje correctas. Tocar una emoción → pasa a Grabar con el badge correcto. Botón Atrás regresa al Mood Meter. Verificar `lucide.createIcons()` redibujó el icono del botón Atrás.

- [ ] **Step 6: Commit**

```bash
git add frontend/app.js frontend/index.html frontend/styles.css
git commit -m "feat(frontend): sub-matriz de emociones con ejes RULER y zoom"
```

---

## Task 4: Pantalla Grabar — modos Hablar / Escribir + Cancelar + temporizador

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/styles.css`
- Modify: `frontend/app.js`

- [ ] **Step 1: Rediseñar el markup de `#screen-record` en `index.html`**

Reemplazar el contenido de `<div id="screen-record" class="screen">` por:

```html
<div id="screen-record" class="screen">
  <button id="btn-back-record" class="back-btn" type="button">
    <i data-lucide="arrow-left" aria-hidden="true"></i><span>Atrás</span>
  </button>
  <h2 class="sr-only" data-screen-title>Cuéntale a Mira</h2>

  <div class="record-stage">
    <span id="selected-emotion-badge" class="emotion-badge"></span>

    <div class="mode-switch" role="tablist" aria-label="Forma de registrar">
      <button id="mode-voz" class="mode-btn active" type="button" role="tab" aria-selected="true">
        <i data-lucide="mic" aria-hidden="true"></i><span>Hablar</span>
      </button>
      <button id="mode-texto" class="mode-btn" type="button" role="tab" aria-selected="false">
        <i data-lucide="pencil" aria-hidden="true"></i><span>Escribir</span>
      </button>
    </div>

    <div id="pane-voz" class="record-pane">
      <canvas id="waveform" aria-hidden="true"></canvas>
      <p id="record-timer" class="record-timer hidden">0:00</p>
      <button id="record-btn" class="record-btn" type="button"
        aria-label="Tocar o mantener presionado para grabar tu voz">
        <i data-lucide="mic" aria-hidden="true"></i>
      </button>
      <p id="record-status" class="record-status" aria-live="polite">Toca o mantén presionado para hablar</p>
      <button id="btn-cancel-record" class="btn-cancel hidden" type="button">
        <i data-lucide="x" aria-hidden="true"></i><span>Cancelar</span>
      </button>
    </div>

    <div id="pane-texto" class="record-pane hidden">
      <label for="text-input" class="sr-only">Escribe cómo te sientes</label>
      <textarea id="text-input" rows="5"
        placeholder="Escribe lo que sientes y por qué…"></textarea>
      <button id="btn-text-continue" class="btn-primary" type="button">Continuar</button>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Estilos del selector, panes, temporizador, cancelar y textarea en `styles.css`**

Añadir:

```css
.mode-switch { display: inline-flex; background: var(--surface-2); border-radius: 999px;
  padding: 4px; gap: 2px; }
.mode-btn { display: inline-flex; align-items: center; gap: 6px; border: none; cursor: pointer;
  background: none; color: var(--text-dim); font: inherit; font-size: 0.85rem; font-weight: 600;
  padding: 8px 18px; border-radius: 999px; transition: background 0.2s var(--ease-soft), color 0.2s ease; }
.mode-btn svg { width: 16px; height: 16px; }
.mode-btn.active { background: linear-gradient(135deg, var(--indigo-light), var(--indigo));
  color: #fff; box-shadow: 0 4px 12px rgba(91, 83, 201, 0.3); }
.record-pane { display: flex; flex-direction: column; align-items: center; gap: 18px;
  width: 100%; animation: paneIn 0.32s var(--ease-soft) both; }
@keyframes paneIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.record-timer { font-variant-numeric: tabular-nums; font-size: 1.2rem; font-weight: 800;
  color: var(--red); margin: 0; }
.btn-cancel { display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--border);
  background: var(--surface); color: var(--text-dim); font: inherit; font-size: 0.85rem;
  font-weight: 600; padding: 8px 18px; border-radius: 999px; cursor: pointer;
  transition: transform 0.18s var(--ease-spring), background 0.18s ease; }
.btn-cancel svg { width: 15px; height: 15px; }
.btn-cancel:active { transform: scale(0.96); background: var(--surface-2); }
#text-input { width: 100%; background: var(--surface); border: 1px solid var(--border);
  border-radius: 16px; padding: 14px 16px; font: inherit; font-size: 1rem; color: var(--text);
  resize: none; outline: none; transition: border-color 0.18s ease; }
#text-input:focus { border-color: var(--indigo); }
#text-input::placeholder { color: var(--text-dim); }
#pane-texto .btn-primary { margin-top: 4px; }
```

El `.record-btn` ya existe; actualizar su `background` al acento crema (`linear-gradient(135deg, var(--indigo-light), var(--indigo))`) y la sombra a `rgba(91,83,201,0.35)`. El estado `.recording` mantiene rojo (`var(--red)`). Añadir `.record-btn svg { width: 30px; height: 30px; color: #fff; }`.

- [ ] **Step 3: Lógica del selector Hablar/Escribir en `app.js`**

Añadir `inputMode: "voz"` al objeto `state`. Añadir:

```js
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
```

- [ ] **Step 4: Botón Cancelar y temporizador de grabación en `app.js`**

Añadir `recordTimerInterval` a las variables de grabación. Añadir:

```js
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
  }
  cancelAnimationFrame(animFrame);
  stopRecordTimer();
  toggleMode = false;
  audioChunks = [];
  recordBtn.classList.remove("recording", "toggle");
  btnCancelRecord.classList.add("hidden");
  recordStatus.textContent = "Toca o mantén presionado para hablar";
}
btnCancelRecord.addEventListener("click", cancelRecording);
```

En `startRecording`, tras `recordBtn.classList.add("recording")`, añadir `btnCancelRecord.classList.remove("hidden"); startRecordTimer();`. En `finishRecording` (dentro de `mediaRecorder.onstop`, antes de `analyzeEntry`) y al inicio de `finishRecording`, añadir `stopRecordTimer(); btnCancelRecord.classList.add("hidden");`.

- [ ] **Step 5: Modo texto — botón Continuar en `app.js`**

Añadir:

```js
document.getElementById("btn-text-continue").addEventListener("click", () => {
  const txt = document.getElementById("text-input").value.trim();
  if (txt.length < 3) {
    document.getElementById("text-input").focus();
    return;
  }
  analyzeText(txt); // definido en la Task 6
});
```

(En esta tarea `analyzeText` aún no existe; se crea en la Task 6. Para que la Task 4 deje la app sin errores de runtime, definir un stub temporal `function analyzeText(t){ console.warn("pendiente Task 6", t); }` y eliminarlo en la Task 6.)

- [ ] **Step 6: Resetear modo y limpiar en `resetRecordState`**

En `resetRecordState`, añadir: `setInputMode("voz"); document.getElementById("text-input").value = ""; stopRecordTimer(); btnCancelRecord.classList.add("hidden");`.

- [ ] **Step 7: Verificar en el navegador**

Servir el frontend. En la pantalla de Grabar: alternar Hablar/Escribir (panes cambian con animación). En Hablar: mantener presionado el botón → aparece temporizador y botón Cancelar; Cancelar detiene y oculta ambos; el indicador de micrófono del navegador se apaga al cancelar. En Escribir: el textarea acepta texto y Continuar con <3 caracteres no avanza. Verificar que tap corto sigue activando modo manos libres.

- [ ] **Step 8: Commit**

```bash
git add frontend/index.html frontend/styles.css frontend/app.js
git commit -m "feat(frontend): pantalla Grabar con modos Hablar/Escribir, cancelar y temporizador"
```

---

## Task 5: Backend — separar análisis de guardado

`/api/entry` hoy transcribe + analiza + **guarda**. Se le quita el guardado; `/api/save` recibe el pipeline de acompañamiento.

> **Nota de estado intermedio:** al terminar esta tarea, el frontend actual aún llama a `/api/entry` esperando que guarde — la app **no guardará** entradas hasta completar la Task 6. Ejecutar Task 5 y Task 6 seguidas.

**Files:**
- Modify: `backend/routes/emotion.py`
- Test: `backend/tests/test_emotion_route.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_emotion_route.py`:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routes.emotion as emotion_route


def _client():
    app = FastAPI()
    app.include_router(emotion_route.router, prefix="/api")
    return TestClient(app)


def test_entry_analyzes_without_saving(monkeypatch):
    calls = {"save": 0}
    monkeypatch.setattr(emotion_route, "extract_ruler",
                        lambda text: {"emocion_primaria": "tenso", "cuadrante": "rojo"})

    def fake_save(ruler):
        calls["save"] += 1
        return (1, "2026-05-17T00:00:00")
    monkeypatch.setattr(emotion_route, "save_entry", fake_save)

    import services.audio_pipeline as ap
    monkeypatch.setattr(ap, "transcribe_audio",
                        lambda path: {"text": "hola", "duration": 2.0})

    r = _client().post(
        "/api/entry",
        files={"audio": ("a.webm", b"\x00" * 100, "audio/webm")},
        data={"emocion_seleccionada": "tenso"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["emocion_seleccionada"] == "tenso"
    assert body["transcripcion"] == "hola"
    assert "id" not in body
    assert calls["save"] == 0


def test_save_persists_and_returns_id(monkeypatch):
    saved = {}

    def fake_save(ruler):
        saved["ruler"] = ruler
        return (7, "2026-05-17T01:00:00")
    monkeypatch.setattr(emotion_route, "save_entry", fake_save)
    monkeypatch.setattr(emotion_route, "_update_profile", lambda ruler, bg: None)
    monkeypatch.setattr(emotion_route, "_acompanamiento_post_entry", lambda: None)

    r = _client().post("/api/save",
                        json={"emocion_primaria": "tenso", "cuadrante": "rojo"})
    assert r.status_code == 200
    assert r.json()["id"] == 7
    assert saved["ruler"]["emocion_primaria"] == "tenso"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd backend && .venv/bin/python -m pytest tests/test_emotion_route.py -v`
Expected: FAIL — `test_entry_analyzes_without_saving` falla porque `/api/entry` aún guarda (`calls["save"] == 1`) y la respuesta trae `"id"`.

- [ ] **Step 3: Quitar el guardado de `/api/entry`**

En `backend/routes/emotion.py`, en la función `entry(...)`, eliminar las llamadas a `save_entry`, `_update_profile` y `_acompanamiento_post_entry`, y devolver solo el `ruler`. El cuerpo del `try` queda:

```python
        from services.audio_pipeline import transcribe_audio

        transcription = transcribe_audio(tmp_path)
        full_text = f"Emoción seleccionada: {emocion_seleccionada}. {transcription['text']}"
        _log.info("Extrayendo RULER con el LLM…")
        ruler = extract_ruler(full_text)
        ruler["emocion_seleccionada"] = emocion_seleccionada
        ruler["transcripcion"] = transcription["text"]
        ruler["crisis_flag"] = contains_crisis(full_text)
        if ruler["crisis_flag"]:
            _log.warning("crisis_flag activado en esta entrada")
        return ruler
```

Quitar el parámetro `background: BackgroundTasks` de la firma de `entry(...)` (ya no se usa) y, si queda sin uso, el import de `BackgroundTasks` se conserva solo si `save` lo sigue usando (sí lo usa).

- [ ] **Step 4: Mover el acompañamiento a `/api/save`**

En `backend/routes/emotion.py`, la función `save(...)` queda:

```python
@router.post("/save")
async def save(ruler: dict, background: BackgroundTasks):
    entry_id, saved_at = save_entry(ruler)
    ruler["saved_at"] = saved_at
    _update_profile(ruler, background)
    acompanamiento = _acompanamiento_post_entry()
    return {"id": entry_id, "saved_at": saved_at, "acompanamiento": acompanamiento}
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `cd backend && .venv/bin/python -m pytest tests/test_emotion_route.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Correr la suite de backend para no romper nada**

Run: `cd backend && .venv/bin/python -m pytest -q`
Expected: sin fallos nuevos respecto al baseline (los tests de audio/STT que dependan de modelos pueden saltarse/skipear como ya lo hagan).

- [ ] **Step 7: Commit**

```bash
git add backend/routes/emotion.py backend/tests/test_emotion_route.py
git commit -m "feat(backend): separar análisis (/api/entry) de guardado (/api/save)"
```

---

## Task 6: Pantalla Confirmar — Guardar / Cancelar + cablear endpoints

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/styles.css`
- Modify: `frontend/app.js`

- [ ] **Step 1: Reemplazar el botón único de `#screen-confirm` por Guardar/Cancelar en `index.html`**

Sustituir `<button id="btn-confirm-done" class="btn-primary" type="button">Listo</button>` por:

```html
<div class="confirm-actions">
  <button id="btn-confirm-save" class="btn-primary" type="button">Guardar</button>
  <button id="btn-confirm-cancel" class="btn-ghost" type="button">Cancelar</button>
</div>
```

- [ ] **Step 2: Estilo de `.confirm-actions` en `styles.css`**

```css
.confirm-actions { display: flex; flex-direction: column; gap: 10px; }
```

- [ ] **Step 3: Crear `analyzeText` y reemplazar el stub en `app.js`**

Eliminar el stub `analyzeText` de la Task 4 y añadir la función real, que llama al endpoint de texto sin guardar:

```js
async function analyzeText(text) {
  startAnalyzingCopy();
  showScreen("analyzing");
  const fullText = `Emoción seleccionada: ${state.selectedEmotion}. ${text}`;
  try {
    const res = await fetch(`${API}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: fullText }),
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
```

- [ ] **Step 4: Refactorizar `analyzeEntry` y centralizar el resultado del análisis en `app.js`**

`analyzeEntry` ya **no** guarda (el backend de la Task 5 ya no guarda en `/api/entry`). Extraer el render común a `onAnalysisReady`:

```js
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
  showScreen("confirm");
}
```

En `analyzeEntry`, reemplazar el bloque que iba desde `state.rulerResult = data;` hasta `showScreen("confirm");` por una sola llamada `onAnalysisReady(data);`.

- [ ] **Step 5: Implementar Guardar y Cancelar en `app.js`**

Reemplazar el listener de `btn-confirm-done` por:

```js
const btnConfirmSave = document.getElementById("btn-confirm-save");

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
    resetRecordState();
    showScreen("mood");
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
```

En `resetRecordState`, añadir el reset del botón: `btnConfirmSave.disabled = false; btnConfirmSave.textContent = "Guardar";`.

- [ ] **Step 6: Verificar el flujo completo (backend real)**

`cd backend && .venv/bin/python main.py`, abrir `http://localhost:8000`. Recorrer: cuadrante → emoción → Grabar.
- **Voz:** grabar unos segundos → análisis → confirmación con transcripción + RULER. **Cancelar** → vuelve a Registrar; ir a Historial y confirmar que **no** se agregó la entrada. Repetir y **Guardar** → ir a Historial y confirmar que **sí** aparece.
- **Texto:** modo Escribir → escribir → Continuar → confirmación → Guardar → aparece en Historial.

Si el stack completo (Ollama/STT) no está disponible, verificar al menos que el frontend hace `POST /api/entry`/`/api/analyze` al analizar y `POST /api/save` solo al pulsar Guardar (pestaña Network de DevTools), y que Cancelar no dispara `/api/save`.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html frontend/styles.css frontend/app.js
git commit -m "feat(frontend): confirmación con Guardar/Cancelar y modo texto cableado"
```

---

## Task 7: Animaciones de texto, skeletons de carga y transiciones

**Files:**
- Modify: `frontend/styles.css`
- Modify: `frontend/app.js`
- Modify: `frontend/index.html`

- [ ] **Step 1: Animación de entrada por palabras para títulos clave**

Añadir a `app.js` una utilidad que envuelve cada palabra de un elemento en `<span>` con delay incremental:

```js
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
```

CSS en `styles.css`:

```css
.word-anim .word { display: inline-block; animation: wordIn 0.5s var(--ease-soft) both; }
@keyframes wordIn {
  from { opacity: 0; transform: translateY(0.5em); }
  to   { opacity: 1; transform: translateY(0); }
}
```

Llamar `animateWords` sobre la `.tagline` de `#screen-mood` al cargar la app y sobre `#words-title` dentro de `renderSubmatrix` (tras asignar su texto).

- [ ] **Step 2: Cross-fade de los textos de estado**

En `styles.css`, dar a `#record-status` y `#analyzing-status` una transición suave. Para `#analyzing-status`, en `startAnalyzingCopy`, en cada cambio de mensaje aplicar un reinicio de animación:

```js
analyzingTimer = setInterval(() => {
  i = (i + 1) % ANALYZING_MESSAGES.length;
  el.style.animation = "none";
  void el.offsetWidth;          // fuerza reflow para reiniciar la animación
  el.style.animation = "";
  el.textContent = ANALYZING_MESSAGES[i];
}, 2200);
```

(El keyframe `statusFade` ya existe; basta con reiniciarlo.)

- [ ] **Step 3: Skeleton loaders para Historial y Patrones**

Añadir CSS de skeleton:

```css
.skeleton-card {
  border-radius: 18px; padding: 16px; background: var(--surface);
  border: 1px solid var(--border); border-left: 5px solid var(--surface-2);
}
.skel-line {
  height: 12px; border-radius: 6px; margin: 6px 0;
  background: linear-gradient(90deg, var(--surface-2) 25%, #EDE3CF 50%, var(--surface-2) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.3s linear infinite;
}
.skel-line.w-60 { width: 60%; } .skel-line.w-40 { width: 40%; } .skel-line.w-80 { width: 80%; }
@keyframes shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }
```

En `app.js`, añadir un helper y usarlo en lugar del `<div class="spinner">` al inicio de `loadHistory` y `loadPatterns`:

```js
function skeletonCards(n = 4) {
  return Array.from({ length: n }, () => `
    <div class="skeleton-card">
      <div class="skel-line w-40"></div>
      <div class="skel-line w-80"></div>
      <div class="skel-line w-60"></div>
    </div>`).join("");
}
```

`loadHistory`: `container.innerHTML = skeletonCards(4);`
`loadPatterns`: `container.innerHTML = skeletonCards(3);`

- [ ] **Step 4: Pantalla de análisis más viva**

En `styles.css`, intensificar la pantalla `#screen-analyzing`: añadir una cuarta partícula `spark-4` (declararla también en `index.html` dentro de `.mascota-orb` junto a las otras), y un anillo de progreso con shimmer alrededor del orbe:

```css
.mascota-orb::after {
  content: ''; position: absolute; inset: 0; border-radius: 50%;
  border: 2px solid transparent;
  border-top-color: var(--indigo-light);
  border-right-color: color-mix(in srgb, var(--indigo-light) 40%, transparent);
  animation: spin 1.6s linear infinite;
}
.spark-4 { bottom: 40px; left: 28px; width: 5px; height: 5px;
  animation: sparkle 2.4s ease-in-out infinite 1.1s; }
```

- [ ] **Step 5: Transiciones suaves consistentes**

Revisar que todos los elementos interactivos (`.mode-btn`, `.sub-emotion`, `.btn-cancel`, `.confirm-actions button`, `.tab-btn`, `.crisis-line`) tengan `transition` con `--ease-soft`/`--ease-spring`. Añadir `transition` donde falte. Confirmar que el bloque `@media (prefers-reduced-motion: reduce)` al final de `styles.css` sigue anulando todas las animaciones nuevas (usa selector universal, así que cubre `wordIn`, `shimmer`, `paneIn`, `submatrixIn`; el `.spinner` y el anillo `::after` se permiten).

- [ ] **Step 6: Verificar en el navegador**

Servir el frontend. Confirmar: la tagline y el título de la sub-matriz entran palabra por palabra; Historial y Patrones muestran skeletons antes del contenido; la pantalla de análisis tiene anillo de progreso y 4 partículas; las transiciones se sienten suaves. Activar `prefers-reduced-motion` en DevTools (Rendering → Emulate CSS media) y confirmar que las animaciones se anulan.

- [ ] **Step 7: Commit**

```bash
git add frontend/styles.css frontend/app.js frontend/index.html
git commit -m "feat(frontend): animación de textos, skeletons de carga y transiciones"
```

---

## Verificación final

- [ ] Recorrer el flujo completo en navegador (voz y texto), Guardar y Cancelar.
- [ ] Confirmar que no queda ningún emoji en la UI.
- [ ] Confirmar tema crema en las 7 pantallas (Registrar, Sub-matriz, Grabar, Analizando, Confirmar, Historial, Patrones, Chat).
- [ ] Confirmar que el micrófono se apaga al terminar de grabar y al cancelar.
- [ ] `cd backend && .venv/bin/python -m pytest tests/test_emotion_route.py -v` en verde.
- [ ] Revisar contraste WCAG AA del texto sobre la paleta crema.
- [ ] Verificar `prefers-reduced-motion`.

## Notas

- **Fuera de alcance:** modo noche, reproducir el audio grabado, editar la transcripción en Confirmar, rediseño estructural de Historial/Patrones/Chat.
- `tailwind.css` está compilado; este plan no recompila Tailwind — solo reemplaza las utilidades de **color** en plantillas JS por clases propias (las de layout siguen funcionando).

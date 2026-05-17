# Mirror — Feedback Emocional Contextual + Pulido de UX

**Fecha:** 2026-05-17
**Rama:** `feat/frontend-revamp`
**Estado:** Diseño aprobado — listo para plan de implementación

## Contexto

Mirror es una PWA privada de autoconocimiento emocional. El usuario registra cómo se
siente con la voz o texto, la app aplica el método **RULER** (Mood Meter de 4 cuadrantes:
energía × agrado), guarda la entrada y muestra patrones. Mira es la compañera emocional.

Backend: FastAPI + Ollama (`qwen3:4b-instruct` + `qwen3-embedding:0.6b`). Entradas
emocionales en ChromaDB; perfil y sesiones de chat en SQLite.

Frontend: PWA vanilla en `frontend/` (`index.html`, `app.js`, `styles.css`, `sw.js`).

Este proyecto tiene dos partes acopladas:
- **Backend** — rehacer cómo se genera el feedback de la IA, corregir la intensidad
  emocional, recibir la hora local del usuario, y registrar la reacción del usuario.
- **Frontend** — rehacer el botón de grabación, la transición del Mood Meter, la
  animación de carga y la pantalla de resultados; agregar un bottom drawer reutilizable.

## Objetivos

1. El feedback de la IA se genera específicamente al **registrar una emoción** (no en chat).
2. La intensidad emocional se calcula **dinámicamente** (60% emociones + 40% contenido).
3. Feedback contextual y cálido cuando la emoción es negativa e intensa; mensaje ligero
   cuando es positiva o neutra.
4. El frontend envía la **hora local** del usuario en cada registro.
5. El usuario puede indicar si el feedback le ayudó; esa señal mejora respuestas futuras.
6. El botón de grabación soporta **tap** y **hold** de forma confiable.
7. La transición de los 4 cuadrantes a las emociones se siente orgánica y premium.
8. La animación de carga ("Mira reflexionando") se siente estética y suave.
9. La pantalla de resultados muestra el feedback de la IA, permite corregir el texto
   detectado, y abre los detalles en un bottom drawer reutilizable.

## Decisiones tomadas (brainstorming)

- **Chat:** se conserva como pantalla aparte con su propio prompt. El feedback se
  desacopla del chat: se genera solo al registrar emociones.
- **Intensidad 60%:** por posición de la emoción elegida en la sub-matriz, combinada con
  las emociones secundarias que extrae el LLM.
- **Feedback del usuario:** se guarda la reacción (me ayudó / no me ayudó) y los mensajes
  "que ayudaron" se reutilizan como ejemplos para guiar el tono.
- **Botón de grabación:** hoy funciona mal/inconsistente; se rehace la lógica.
- **Persistencia del feedback:** se guarda como metadata de la entrada en ChromaDB
  (no se crea tabla SQLite nueva) — más simple, sin migración, y el detalle del
  historial lo obtiene gratis.

---

# Parte A · Backend

## A1 · Generación del feedback enfocada en el registro emocional

Hoy `services/reasoning_pipeline.py:run_companion_pipeline()` genera el feedback
**después** de guardar (`trigger="post_entry"`) y al abrir la app (`trigger="on_open"`,
endpoint `/api/companion`). Tiene una compuerta que a veces no devuelve nada.

**Nuevo diseño:**

- Módulo nuevo `services/entry_feedback.py` con
  `generate_entry_feedback(ruler, selected_emotion, client_time) -> dict`.
  Devuelve `{"mensaje": str, "modo": "apoyo" | "ligero"}`.
- El feedback se genera **siempre** (sin compuerta que devuelva nada) y **al analizar**,
  para que la pantalla de resultados lo muestre antes de guardar.
- `entry_feedback.py` reutiliza `profile_service` (contexto del usuario),
  `relevance` (filtrado de fuentes), `llm_service` (generación) y el catálogo de
  emociones (A2).
- Se **retira** el disparador `on_open` y el endpoint `/api/companion` (`routes/companion.py`);
  el feedback ya no aparece al abrir la app. `reasoning_pipeline.py` queda en el repo
  sin disparadores activos (limpieza posterior fuera de alcance).
- Prompt nuevo `prompts/entry_feedback.txt`, específico del registro emocional, con los
  dos modos descritos en A3. Reemplaza el uso de `prompts/companion.txt` para este flujo.
- El chat (`routes/chat.py`, `prompts/chat_system.txt`) **no se toca**.

## A2 · Intensidad emocional dinámica (60 / 40)

Hoy la intensidad la asigna el LLM en `extract_ruler()` (1-10) y tiende a quedarse en
valores centrales (5-6), saliendo casi siempre igual.

**Nueva fórmula, calculada en código** (función `compute_intensity()` en
`services/entry_feedback.py`):

```
intensidad_final = round( 0.60 · intensidad_emocion + 0.40 · intensidad_contenido )
intensidad_final = clamp(intensidad_final, 1, 10)
```

**`intensidad_emocion` (60%)** — determinista, por posición en la sub-matriz:

- Catálogo nuevo `services/emotion_catalog.py`: las mismas 4 listas de 12 emociones
  ordenadas de leve→intensa que el `QUADRANTS` del frontend. Es la fuente única para
  mapear nombre→posición. Debe mantenerse sincronizado con `frontend/app.js` (comentario
  explícito en ambos archivos).
- Posición `i` (0-11) → intensidad `1 + i · (9/11)` → rango [1, 10].
- Combinación con secundarias:
  ```
  intensidad_emocion = 0.70 · pos(emoción elegida) + 0.30 · promedio(pos(secundarias))
  ```
  Si no hay secundarias válidas, se usa solo `pos(emoción elegida)`.
- Las emociones secundarias vienen de `ruler["emociones_secundarias"]` (LLM); se buscan
  en el catálogo normalizando acentos y mayúsculas. Las que no se encuentran se ignoran.
- Si la emoción elegida no está en el catálogo, `intensidad_emocion` cae a
  `intensidad_contenido` (es decir, `intensidad_final = intensidad_contenido`).

**`intensidad_contenido` (40%)** — el valor `intensidad` (1-10) que extrae el LLM del
transcript/texto. Además se mejora `prompts/ruler_extraction.txt` con anclas de
calibración (`1 = apenas perceptible … 10 = desbordante`) para que también varíe.

El `intensidad_final` reemplaza el campo `intensidad` del dict `ruler` antes de
devolverlo al frontend y persistirlo.

## A3 · Feedback contextual en dos modos

`generate_entry_feedback()` elige el modo según el resultado del análisis:

- **Modo `apoyo`** — cuadrante `rojo` o `azul` **y** `intensidad_final > 5`.
  Feedback cálido y contextual. El prompt recibe contexto del perfil del usuario:
  disparadores recurrentes, `fuentes_de_bienestar`, tendencia reciente, franja horaria
  (A4). Ofrece 1-2 sugerencias **sanas, éticas y realistas** para ayudar al usuario a
  sentirse mejor. Tono humano y cercano, nada genérico.
- **Modo `ligero`** — cuadrante `amarillo`/`verde`, o negativo pero con
  `intensidad_final ≤ 5`. Mensaje más corto y luminoso: felicita, refuerza hábitos
  positivos, sugiere continuar o compartir algo de las `fuentes_de_bienestar` del
  usuario (ej. "compartir este momento con alguien importante").

En ambos modos: 1-2 frases, sin diagnóstico ni consejo médico, sin inventar actividades
que no estén en la evidencia del perfil. El modal de crisis (`crisis_flag`) sigue
funcionando independiente del feedback.

## A4 · Timestamp / hora local del usuario

- El frontend envía `client_time`: ISO 8601 con offset local
  (ej. `2026-05-17T21:34:00-06:00`) en `/api/entry` y `/api/analyze`.
- El backend deriva una **franja horaria** (`madrugada` 0-5, `mañana` 6-11,
  `tarde` 12-18, `noche` 19-23) y el día de la semana, y los pasa al contexto del
  prompt de feedback ("según hora del día, hábitos y patrones").
- `client_time` se persiste en la metadata de la entrada junto a `saved_at`.
- Si `client_time` falta o es inválido, el backend usa su hora UTC como respaldo.

## A5 · Sistema de feedback del usuario

- Tras leer el feedback, el usuario puede reaccionar: `me_ayudo` o `no_me_ayudo`
  (o ninguna). La reacción se elige en la pantalla de resultados antes de guardar.
- **Persistencia (sin tabla nueva):** al guardar, la metadata de la entrada en ChromaDB
  incluye `feedback_mensaje` (str), `feedback_modo` (str) y `feedback_reaccion`
  (str: `me_ayudo` / `no_me_ayudo` / `""` si no hay). Los valores de metadata de
  ChromaDB son escalares; se usa `""` para "sin reacción".
- `/api/save` acepta un campo opcional `reaccion_feedback` y lo guarda en la metadata.
- `POST /api/feedback/reaction` con `{entry_id, reaccion}` actualiza
  `feedback_reaccion` de una entrada ya guardada (vía `collection.update()` de ChromaDB);
  lo usa el detalle del historial.
- **Uso ligero:** al generar feedback nuevo, `entry_feedback.py` consulta ChromaDB con
  filtro de metadata `feedback_reaccion == "me_ayudo"`, toma hasta 2 entradas recientes
  e inyecta sus `feedback_mensaje` en el prompt como ejemplos de mensajes que ayudaron,
  para guiar el tono.

## A6 · Contratos de API resultantes

- **`POST /api/analyze`** — request `{text, emocion_seleccionada, client_time}`.
  Response: dict `ruler` con `intensidad` ya calculada (A2) + `crisis_flag` +
  `feedback` (`{mensaje, modo}`).
- **`POST /api/entry`** — multipart: `audio`, `emocion_seleccionada`, `client_time`.
  Response: igual que `/api/analyze` + `transcripcion`.
- **`POST /api/save`** — body: el dict `ruler` (ya incluye `feedback`, `client_time`) +
  campo opcional `reaccion_feedback`. Response: `{id, saved_at}`. Ya **no** genera
  feedback ni devuelve `acompanamiento`.
- **`POST /api/feedback/reaction`** — `{entry_id, reaccion}` → `{ok: true}`.
- **`/api/companion`** — se elimina.

---

# Parte B · Frontend

## B1 · Botón de grabación tap / hold (rehacer)

Se rehace la lógica de grabación como una máquina de estados clara:

- **`pointerdown`** → inicia adquisición del micrófono y grabación; guarda `pressStart`.
- **`pointerup`:**
  - Si ya venía en *modo toggle* (de un tap previo) → **detiene**.
  - Si la presión duró `< TAP_THRESHOLD_MS` (350 ms) → entra a *modo toggle*: el
    micrófono sigue activo, la UI indica "toca para terminar"; el siguiente tap detiene.
  - Si la presión duró `≥ 350 ms` → **detiene** al soltar (hold).
- **Bug raíz a corregir:** `getUserMedia` es asíncrono. Si el usuario suelta antes de
  que el stream esté listo, hoy el estado queda inconsistente. La lógica nueva espera el
  stream y, si la presión ya terminó, cancela limpio sin dejar grabación colgada.
- **Garantía de micrófono:** `releaseAudioResources()` corre en **todas** las salidas —
  tap-detener, hold-soltar, cancelar y error.
- Se conserva `MIN_RECORDING_MS` para descartar toques accidentales.
- Soporte de teclado (Enter/Espacio = modo toggle) se conserva.

## B2 · Transición del Mood Meter más orgánica

Se reemplaza el `scale(1.35)` + dimmer actual por una transición en capas:

1. El cuadrante tocado **se expande hasta llenar la pantalla** desde su propia posición;
   los otros 3 se desvanecen y encogen suavemente.
2. Las 12 emociones **emergen escalonadas desde el centro** del cuadrante (scale
   `0.6→1` + fade, con `animation-delay` incremental) — el bloque se "divide" en las
   emociones.
3. Las etiquetas de eje RULER y el título **aparecen al final**, sutiles y progresivas.
4. El botón atrás revierte la animación (zoom inverso).
5. Todo respeta `prefers-reduced-motion: reduce` (las animaciones se anulan).

La sub-matriz mantiene **12 emociones** por cuadrante (definido en el revamp anterior).

## B3 · Animación de carga ("Mira está reflexionando")

Se elimina el anillo giratorio (`.mascota-orb::after` con `spin`) — el "círculo feo".
En su lugar:

- **Aura que respira:** anillos concéntricos suaves que se expanden lento desde Mira
  (como un latido/sonar calmado), sin rotación dura.
- Motas flotando con movimiento orgánico (no parpadeo mecánico).
- El color del aura se toma del **cuadrante elegido**, para que el loading "sienta" la
  emoción registrada.
- Se conserva el texto de estado con cross-fade entre mensajes.
- Respeta `prefers-reduced-motion`.

## B4 · Pantalla de resultados

`#screen-confirm` se reordena, de arriba a abajo:

1. **Mira + el feedback contextual de la IA** como protagonista. Ahora siempre presente,
   viene en la respuesta del análisis (ya no después de guardar).
2. Control minimalista **"¿Te ayudó?"** en la tarjeta del feedback: dos botones discretos
   (me ayudó / no me ayudó). La reacción se guarda en el estado del frontend y viaja en
   el payload de `/api/save` (`reaccion_feedback`).
3. **Campo editable** (`<textarea>`) con el transcript/texto detectado, para corregir
   errores. Si el usuario lo edita, aparece un botón sutil **"Actualizar análisis"** que
   re-llama a `/api/analyze` con el texto corregido y refresca el resultado.
4. Botón minimalista **"Ver detalles"** → abre el bottom drawer (B5) con el desglose
   RULER completo.
5. Botones **Guardar** / **Cancelar** abajo, como hoy. Cancelar descarta sin registrar.

## B5 · Bottom drawer reutilizable

Componente nuevo: hoja inferior que **anima de abajo hacia arriba**, con backdrop
oscurecido. Se cierra por tap en el backdrop, arrastre hacia abajo, o tecla Escape.
Atrapa el foco mientras está abierto (accesible, igual que el modal de crisis).

Se usa en dos lugares con el mismo componente:

- **"Ver detalles"** en resultados → desglose RULER completo: emoción primaria,
  emociones secundarias, cuadrante, disparador, intensidad, pensamientos, contexto.
- **Detalle del historial** → las tarjetas de `#screen-history` (hoy no clicables) se
  vuelven clicables y abren el mismo drawer con el RULER de esa entrada **y** el
  feedback que dio Mira (`feedback_mensaje` de la metadata). Desde aquí el usuario
  también puede reaccionar (`POST /api/feedback/reaction`).

## B6 · Timestamp

El frontend calcula `client_time` con `new Date()` serializado a ISO 8601 con offset
local, y lo envía:
- en `/api/entry` como campo del `FormData`,
- en `/api/analyze` como campo del cuerpo JSON.

---

## Archivos afectados

**Backend — crear:**
- `backend/services/entry_feedback.py` — generación de feedback + `compute_intensity()`.
- `backend/services/emotion_catalog.py` — catálogo ordenado de emociones.
- `backend/prompts/entry_feedback.txt` — prompt del feedback en dos modos.

**Backend — modificar:**
- `backend/routes/emotion.py` — `/api/analyze`, `/api/entry`, `/api/save`,
  nuevo `/api/feedback/reaction`; integrar `entry_feedback` e intensidad.
- `backend/services/memory_service.py` — guardar `feedback_*` y `client_time` en
  metadata; `collection.update()` para la reacción; consulta de mensajes "que ayudaron".
- `backend/prompts/ruler_extraction.txt` — anclas de calibración de intensidad.
- `backend/main.py` — quitar el registro de `routes/companion.py`.

**Backend — eliminar:**
- `backend/routes/companion.py` y el endpoint `/api/companion`.

**Frontend — modificar:**
- `frontend/app.js` — máquina de estados de grabación, transición Mood Meter, envío de
  `client_time`, pantalla de resultados, componente drawer, historial clicable.
- `frontend/index.html` — `#screen-confirm` reordenado, marcado del bottom drawer,
  control "¿Te ayudó?".
- `frontend/styles.css` — transición Mood Meter, aura de carga, estilos del drawer,
  estilos del campo editable y del control de reacción.

## Flujo completo (después del cambio)

```
Mood Meter (4 cuadrantes)
  └─ tap cuadrante ──[expansión orgánica]──> Sub-matriz (12 emociones)
       └─ tap emoción ──> Grabar (tap/hold) o Escribir
            └──> Analizando (aura de Mira; sin guardar)
                  · backend: intensidad 60/40 + feedback contextual
                  └──> Resultados
                        · feedback de la IA  + "¿Te ayudó?"
                        · texto editable (→ "Actualizar análisis")
                        · "Ver detalles" → bottom drawer (RULER)
                        ├─ Guardar  → /api/save (ruler + reacción) → Mood Meter
                        └─ Cancelar → descarta → Mood Meter

Historial ── tap tarjeta ──> bottom drawer (RULER + feedback + reacción)
```

## Pruebas

- **Backend (pytest):** `compute_intensity()` con distintas emociones/secundarias da
  valores distintos; selección de modo (`apoyo` vs `ligero`) según cuadrante e
  intensidad; lookup del catálogo con acentos/mayúsculas; derivación de franja horaria;
  contratos de `/api/analyze`, `/api/entry`, `/api/save`, `/api/feedback/reaction`.
- **Frontend (navegador, Chrome DevTools MCP):** grabación tap y hold, cancelar, que el
  micrófono se apague siempre; transición orgánica del Mood Meter; aura de carga;
  pantalla de resultados con feedback, edición de texto y "Actualizar análisis";
  bottom drawer desde resultados y desde el historial; reacción "¿Te ayudó?".
- Verificar `prefers-reduced-motion`.
- Verificar que el feedback varíe entre registros (intensidad y tono distintos).

## Fuera de alcance

- Bucle completo de personalización con ML (solo se reutilizan ejemplos "que ayudaron").
- Modo noche / `prefers-color-scheme`.
- Reproducir el audio grabado.
- Rediseño del chat, de Patrones o del Historial más allá de lo descrito.
- Limpieza/eliminación de `services/reasoning_pipeline.py` (queda inactivo).
- Unificar el catálogo de emociones en una fuente compartida backend↔frontend
  (por ahora se duplica con un comentario de sincronización).

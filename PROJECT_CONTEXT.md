# Mirror — Project Context

> Proyecto para **Guadalahacks 2026** — Track: Inteligencia Artificial en el Borde (Edge AI)
> Equipo de 4 personas · 21 horas restantes para entrega

---

## 1. Resumen ejecutivo

**Mirror** es una app móvil de autoconocimiento emocional impulsada por IA local. Usa el framework **RULER** (Yale Center for Emotional Intelligence) para ayudar al usuario a identificar, etiquetar y entender sus emociones. El usuario registra cómo se siente en un Mood Meter, explica por voz qué lo causó, y la IA local extrae estructura emocional rica (causa, contexto, pensamientos asociados, intensidad). Toda la información persiste en una base de datos vectorial local, permitiendo detectar patrones emocionales, hábitos asociados a estados de ánimo, y servir como apoyo de autorreflexión a lo largo del tiempo.

**Diferenciador clave:** todo corre 100% local. Las emociones del usuario nunca salen de su hardware. Nada de OpenAI, Gemini, Claude APIs ni servicios en la nube — cumple las reglas del track y convierte la restricción en ventaja competitiva real (privacidad emocional).

**Posicionamiento:** herramienta de **autoconocimiento emocional**, NO sustituto de terapia. Incluye detección básica de crisis con derivación a líneas de ayuda profesionales.

---

## 2. Contexto del hackathon

### Track: Inteligencia Artificial en el Borde

IA corriendo directamente en el dispositivo sin nube, sin API, sin conexión.

### Reglas obligatorias

- ✅ Modelo local obligatorio — la IA debe correr en el dispositivo
- ✅ Contacto con el usuario — interfaz que alguien pueda usar
- ✅ Cualquier plataforma — móvil, web, escritorio, embebido
- ✅ Frameworks open source — cualquier herramienta libre
- ❌ Sin APIs de IA externas — nada de OpenAI, Gemini, Claude
- ❌ Sin inferencia remota — no enviar datos a un servidor para IA

### Nota sobre arquitectura

Se permite usar una laptop como servidor local que corra el modelo, y hacer requests desde el celular vía LAN. No es Edge AI estricto pero cumple el requerimiento principal: modelo local, sin nube, sin APIs externas.

---

## 3. Historial de decisiones del proyecto

### Ideas exploradas y descartadas

1. **Agente personalizable universal (descartada).** Inicialmente se consideró una interfaz tipo "configura tu propio agente" (psicólogo, contador, asistente de reuniones). Se descartó porque diluye el diferenciador y se percibe como wrapper genérico de Ollama.

2. **Asistente de reuniones con memoria persistente (no elegida).** Buena idea con tesis clara (privacidad de reuniones empresariales), pero se prefirió enfoque en salud mental por mayor impacto emocional.

### Decisión final

**App de autoconocimiento emocional con framework RULER + memoria vectorial persistente + interfaz por voz.**

Razones por las que ganó:

- Framework académico respaldado (RULER de Yale) da seriedad y diferenciación
- "Local" no es gimmick, es ventaja real (privacidad emocional)
- Demo visualmente potente (Mood Meter, timeline emocional)
- Profundidad técnica con vector DB, RAG, embeddings locales
- Caso de uso emocionalmente resonante para jueces

---

## 4. Framework RULER

RULER es un enfoque de educación emocional desarrollado por el Yale Center for Emotional Intelligence (Marc Brackett). El acrónimo:

- **R**ecognizing — reconocer emociones en uno mismo y otros
- **U**nderstanding — entender causas y consecuencias de las emociones
- **L**abeling — etiquetar emociones con vocabulario preciso
- **E**xpressing — expresarlas apropiadamente
- **R**egulating — regularlas efectivamente

### Mood Meter

Herramienta central de RULER. Grilla 2D con dos ejes:

- **Eje X:** Valencia (desagradable ← → agradable)
- **Eje Y:** Energía (baja ↓ ↑ alta)

Esto produce 4 cuadrantes con colores asociados:

| Cuadrante | Color | Energía | Valencia | Ejemplos emocionales |
|-----------|-------|---------|----------|----------------------|
| Superior izquierdo | 🔴 Rojo | Alta | Desagradable | furioso, enojado, frustrado, irritado, ansioso, tenso, preocupado, abrumado |
| Superior derecho | 🟡 Amarillo | Alta | Agradable | emocionado, eufórico, feliz, optimista, motivado, inspirado, orgulloso, alegre |
| Inferior izquierdo | 🔵 Azul | Baja | Desagradable | triste, decepcionado, desanimado, solo, agotado, vacío, melancólico, derrotado |
| Inferior derecho | 🟢 Verde | Baja | Agradable | calmado, sereno, agradecido, satisfecho, en paz, relajado, contento, tranquilo |

---

## 5. Flujo de usuario (MVP)

### Flujo principal de registro

1. Usuario abre la PWA en el celular → ve el **Mood Meter**
2. Toca un cuadrante → ve 8 palabras emocionales específicas de ese cuadrante
3. Elige una etiqueta emocional → botón "hablar sobre esto"
4. Mantiene presionado el botón y graba voz libre explicando qué pasó
5. Audio sube al backend → **Whisper.cpp** transcribe local
6. **LLM local (Qwen 2.5 7B)** extrae estructura emocional en JSON
7. Se generan embeddings → se guarda en **ChromaDB** con metadatos
8. Pantalla de confirmación: "Esto es lo que entendí" muestra estructura

### Flujo de insight

9. Vista **Timeline**: historial de entradas con cards coloreadas por cuadrante
10. Vista **Patrones**: 3 cards con insights (mini Mood Meter semanal, palabras frecuentes, patrón detectado)
11. Vista **Chat**: modo conversación con RAG ("¿cómo me he sentido esta semana?")

### Detección de crisis

Si el texto contiene palabras clave (suicidio, autolesión, etc.), modal a pantalla completa con:

- **SAPTEL:** 55 5259-8121
- **Línea de la Vida:** 800-911-2000

---

## 6. Stack técnico definitivo

### Backend (corre en la laptop)

| Componente | Tecnología | Notas |
|------------|------------|-------|
| Lenguaje | Python 3.11+ | |
| Framework web | FastAPI 0.110+ con Uvicorn | ASGI, async |
| Comunicación | REST + WebSocket opcional | |
| STT | `whisper.cpp` con `ggml-small.bin` multilingüe | Fallback: `faster-whisper` si pelean con compilación |
| LLM | Ollama corriendo `qwen2.5:7b-instruct` | Fallback: `llama3.1:8b-instruct` |
| Embeddings | `nomic-embed-text` vía Ollama | Mismo runtime, simplifica deploy |
| Vector DB | ChromaDB 0.4+ con `PersistentClient` | Persistencia local en disco |
| Audio | `pydub` + `ffmpeg` | Conversión de formatos |
| Schemas | `pydantic` | |
| Uploads | `python-multipart` | |
| HTTP client | `httpx` | Para llamar a Ollama |

### Frontend (PWA en el celular)

| Componente | Tecnología | Notas |
|------------|------------|-------|
| Stack | HTML + JavaScript vanilla + Tailwind CSS vía CDN | Cero build tools |
| Grabación | MediaRecorder API | |
| Networking | `fetch` | REST calls |
| Persistencia local | `localStorage` | Sesión del usuario |
| Visualización audio | Web Audio API | Opcional |
| Gráficos | Chart.js vía CDN | Solo si sobra tiempo |
| Iconos | Lucide o emojis | |
| PWA | `manifest.json` + service worker básico | Para instalación en celular |

### Infraestructura local

- Laptop y celular en la misma red WiFi
- Backend escucha en `0.0.0.0:8000`
- Celular accede vía IP local (`http://192.168.x.x:8000`)
- Configuración: archivo `.env` único
- Persistencia: `./data/chroma_db/` y `./data/audio/` (audios temporales)

### Datos pre-cargados para demo

Script `seed_data.py` genera 25-30 entradas emocionales sintéticas distribuidas en 3 semanas pasadas, con:

- Variedad de cuadrantes RULER
- Temas diversos (trabajo, familia, salud, sueño, ejercicio)
- Patrones detectables intencionalmente (ej: lunes con baja energía, domingos con alta valencia)

---

## 7. Estructura del repositorio

```
mirror/
├── backend/
│   ├── main.py                    # FastAPI app
│   ├── routes/
│   │   ├── audio.py               # /transcribe
│   │   ├── emotion.py             # /analyze, /save
│   │   ├── history.py             # /history, /patterns
│   │   └── chat.py                # /chat (RAG)
│   ├── services/
│   │   ├── whisper_service.py
│   │   ├── llm_service.py
│   │   ├── embedding_service.py
│   │   └── memory_service.py
│   ├── prompts/
│   │   ├── ruler_extraction.txt
│   │   └── chat_system.txt
│   ├── crisis_keywords.py
│   ├── seed_data.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   ├── manifest.json
│   └── sw.js
├── data/
│   ├── chroma_db/
│   └── models/
└── README.md
```

---

## 8. Contratos de API

| Método | Endpoint | Request | Response |
|--------|----------|---------|----------|
| POST | `/api/transcribe` | `multipart/form-data` con audio | `{text, duration}` |
| POST | `/api/analyze` | `{text}` | Estructura RULER completa |
| POST | `/api/save` | Estructura RULER completa | `{id, saved_at}` |
| POST | `/api/entry` | `multipart/form-data` con audio + emocion_seleccionada | Orquesta transcribe + analyze + save |
| GET | `/api/history?limit=20` | — | Lista de entradas pasadas |
| GET | `/api/patterns` | — | 3 insights detectados |
| POST | `/api/chat` | `{question}` | `{answer, sources}` |

### Schema de estructura RULER (response de `/analyze`)

```json
{
  "emocion_primaria": "abrumado",
  "emociones_secundarias": ["ansioso", "frustrado"],
  "cuadrante": "azul",
  "valencia": -0.6,
  "energia": 0.3,
  "intensidad": 7,
  "disparador": "presentación de trabajo mañana",
  "contexto": {
    "personas": ["jefe"],
    "lugar": "casa",
    "actividad": "preparando trabajo"
  },
  "pensamientos": ["no voy a lograrlo", "todos van a notar que no sé"],
  "resumen": "Estrés anticipatorio por presentación laboral",
  "crisis_flag": false
}
```

---

## 9. División de tareas por persona

### Persona 1 — Audio Engineer (Pipeline de voz)

**Misión:** entrada de audio del celular → texto transcrito confiable en español, rápido.

**Stack:** whisper.cpp (o faster-whisper), pydub, ffmpeg, MediaRecorder API.

**Entregables:**

1. Instalar y compilar whisper.cpp con `ggml-small.bin`. Switch a `faster-whisper` si pelea >90 min.
2. Función `transcribe(audio_path: str) -> str` con conversión de formato (webm/ogg → wav 16kHz mono).
3. Endpoint `POST /api/transcribe`.
4. Frontend: lógica de grabación con MediaRecorder, botón "mantener presionado para hablar", indicador visual.
5. Manejo de errores (audio corto, corrupto, timeout).
6. **Después de hora 10:** apoyo + implementar `crisis_keywords.py`.

**Criterio de éxito:** en hora 6, grabar audio en celular → ver transcripción en español.

---

### Persona 2 — Brain Engineer (LLM + memoria + RAG)

**Misión:** extracción RULER, gestión de memoria vectorial, respuestas con contexto.

**Stack:** Ollama API, prompts en español, ChromaDB, embeddings, RAG.

**Entregables:**

1. Instalar Ollama, descargar `qwen2.5:7b-instruct` y `nomic-embed-text`.
2. Diseñar y probar **prompt de extracción RULER** que devuelva JSON estricto.
3. `llm_service.py` con `extract_ruler(text: str) -> dict` y parsing JSON robusto.
4. `embedding_service.py` con `embed(text: str) -> list[float]`.
5. `memory_service.py` con `save_entry`, `get_history`, `search_similar`, `compute_patterns`.
6. **Modo conversación:** prompt + RAG con top-5 entradas similares. Respuestas empáticas/reflexivas, NUNCA consejeras.
7. `seed_data.py` con 25-30 entradas sintéticas con patrones intencionales.

**Criterio de éxito:** en hora 6, pegar texto → JSON RULER válido. En hora 10, preguntas con contexto recuperado.

---

### Persona 3 — Frontend Engineer (PWA y experiencia visual)

**Misión:** la cara del producto. Mayor impacto en percepción de jueces.

**Stack:** HTML, Tailwind CSS, JS vanilla, MediaRecorder, fetch, animaciones CSS.

**Entregables:**

1. Estructura PWA (index.html, app.js, manifest.json, sw.js), instalable en celular.
2. **Pantalla 1 — Mood Meter:** grilla 2D con 4 cuadrantes coloreados, 8 palabras emocionales por cuadrante. Debe verse HERMOSO.
3. **Pantalla 2 — Grabación:** botón "mantener presionado", indicador visual, transcripción visible.
4. **Pantalla 3 — Confirmación:** muestra estructura RULER extraída de forma bonita. Botón guardar/corregir.
5. **Pantalla 4 — Timeline:** cards coloreadas por cuadrante, ordenadas por fecha, scroll vertical.
6. **Pantalla 5 — Patrones:** 3 cards (mini Mood Meter semanal, palabras frecuentes, patrón detectado).
7. **Pantalla 6 — Chat:** burbujas de mensajes, input texto + micrófono, indicador "pensando".
8. Tab bar inferior con 4 secciones (Registrar, Historial, Patrones, Chat).
9. **Modal de crisis** a pantalla completa con SAPTEL y Línea de la Vida.

**Criterio de éxito:** en hora 6, las 6 pantallas con UI completa y datos mock. En hora 10, conectadas al backend real.

---

### Persona 4 — Integration Engineer + Tech Lead

**Misión:** que todo conecte. Visión de sistema completo, coordinación de interfaces, lidera la demo.

**Stack:** FastAPI, arquitectura general, debugging cross-component, presentación.

**Entregables:**

1. Setup inicial del repo, estructura, `requirements.txt`, README.
2. Esqueleto FastAPI con todos los endpoints stub y schemas Pydantic. **CRÍTICO:** destraba al resto.
3. Publicar contratos de API en hora 2 para que P1, P2, P3 trabajen en paralelo con mocks.
4. CORS configurado para acceso desde celular.
5. **Hora 10-14:** integración profunda. Conecta servicios en endpoints orquestados (`/api/entry`).
6. **Hora 14-17:** dashboard simple de logs/debug para usar durante demo.
7. **Hora 17+:** lidera pitch. Slides (máximo 5: problema, RULER, arquitectura, privacidad, futuro). Coordina ensayos.
8. Backup plan: datos pre-cargados, video grabado de respaldo del flujo completo.

**Criterio de éxito:** en hora 10, `/api/entry` funciona end-to-end. En hora 19, demo ensayada 3 veces sin fallas.

---

## 10. Plan hora por hora (21 horas)

| Horas | Fase | Objetivo |
|-------|------|----------|
| 0–2 | Setup | Cada quien corre SU pieza aislada. Repos, instalaciones, contratos de API publicados. |
| 2–6 | Componentes aislados | Cada componente funciona standalone con tests manuales. |
| 6–10 | Integración del flujo principal | Audio → transcripción → análisis → guardado funciona end-to-end. |
| 10–14 | Historial, patrones, conversación | Timeline, 3 cards de patrones, modo chat con RAG. **Hora 14 = línea de no retorno.** |
| 14–17 | Datos sintéticos + pulido UI | Cargar seed_data, verificar patrones, pulir CSS y transiciones. |
| 17–19 | Bug fixing + script de demo | Solo arreglar críticos. Cero features nuevas. Diseñar pitch y slides. |
| 19–20 | Ensayo de pitch | Practicar pitch completo 3 veces. |
| 20–21 | Buffer sagrado | Hora intocable para imprevistos. Si todo está bien, descansar. |

### Checkpoints obligatorios

- **Hora 2:** cada quien corre su pieza aislada
- **Hora 6:** componentes funcionan standalone
- **Hora 10:** flujo principal end-to-end funciona
- **Hora 14:** flujo completo (incluyendo patrones y chat). **Si no, recortar features.**
- **Hora 17:** equipo prueba demo completa y anota TODOS los bugs

---

## 11. Reglas de colaboración

1. **Contratos primero, código después.** Hora 2: P4 publica APIs, demás trabajan con mocks.
2. **Check-ins cada 4 horas.** 10 min en hora 4, 8, 12, 16, 20. Qué terminé, dónde atorado, qué necesito.
3. **Commits frecuentes a rama compartida.** Branches por persona al inicio, merges tempranos.
4. **Canal único de comunicación rápido** (WhatsApp/Discord). Preguntas técnicas por escrito.
5. **Bloqueo >30 min → pedir ayuda.** Sin orgullo.
6. **Una sola laptop de demo** (la de P4). Tests finales y demo ahí.
7. **Duerman.** Turnos de descanso de 3-4 horas escalonados entre horas 8-16.

---

## 12. Demo script (4 minutos)

### 0:00–0:30 — Hook

> "El 76% de la gente no sabe nombrar lo que siente más allá de 'bien' o 'mal'. Las apps de salud mental existen, pero envían tus emociones más íntimas a servidores en EU. Hicimos Mirror: tus emociones, en tu hardware, sin excepción."

### 0:30–1:00 — RULER

Brackett, Yale, framework validado. Mood Meter, vocabulario emocional preciso. "No es 'me siento mal', es 'me siento desalentado'."

### 1:00–2:30 — Demo en vivo

1. Abrir PWA → tocar cuadrante azul → elegir "abrumado"
2. Grabar 20 segundos (texto preparado, no improvisado)
3. Mostrar estructura RULER extraída
4. **Desconectar WiFi en vivo** → "todo esto, sin internet"
5. Mostrar timeline pre-cargado (3 semanas de datos sintéticos)
6. Mostrar patrones detectados
7. Pregunta al chat: "¿cómo me he sentido esta semana?" → leer respuesta

### 2:30–3:30 — Arquitectura

Slide 10 segundos: Whisper.cpp + Qwen 2.5 + ChromaDB + nomic-embed. "Todo open source, todo local, replicable."

### 3:30–4:00 — Cierre

Mostrar detección de crisis con líneas de ayuda. "No reemplazamos terapia, la complementamos con autoconocimiento privado. Mirror."

---

## 13. Lo que NO está en el MVP (no caer en la tentación)

- ❌ TTS (que la IA hable). Solo texto en pantalla.
- ❌ Login, autenticación, usuarios múltiples
- ❌ Notificaciones push, recordatorios
- ❌ Gráficos complejos (Chart.js solo si sobra tiempo)
- ❌ Sincronización entre dispositivos
- ❌ Configuración de modelos, settings UI
- ❌ Análisis emocional en tiempo real durante grabación
- ❌ Multi-idioma (solo español)

---

## 14. Riesgos identificados y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Latencia alta (audio → respuesta >8s) | Streaming de respuesta del LLM, modelo más pequeño si necesario, mostrar texto antes de TTS |
| LLM rompe el JSON estructurado | Parsing robusto con fallback, iterar prompt 5-6 veces, ejemplos few-shot |
| Whisper falla con audio del navegador | Conversión explícita a wav 16kHz mono con pydub |
| Posicionamiento como "terapia" | Disclaimer explícito en UI y pitch: "autoconocimiento, no terapia" |
| Detección de crisis no dispara | Lista de keywords clara + tests manuales con frases reales |
| Demo falla en vivo | Video de respaldo grabado + datos pre-cargados listos |
| Equipo agotado en hora 20 | Turnos de descanso obligatorios entre horas 8-16 |

---

## 15. Líneas de ayuda (México) — para integración en app

- **SAPTEL:** 55 5259-8121 (24/7, gratis, anónimo)
- **Línea de la Vida:** 800-911-2000 (24/7, gratis)

---

## 16. Posicionamiento ético

Mirror es una **herramienta de autoconocimiento emocional**, NO un sustituto de atención psicológica profesional.

- ✅ Refleja, pregunta, ayuda a etiquetar
- ❌ No diagnostica
- ❌ No da consejos médicos
- ❌ No minimiza emociones
- ✅ Deriva a profesionales en casos de crisis

El LLM opera como **espejo** (reflejar lo que el usuario expresa), no como terapeuta.

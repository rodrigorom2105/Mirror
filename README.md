# Mirror — Autoconocimiento Emocional

> Hackathon Guadalahacks 2026 · Track: IA en el Borde

App móvil PWA de autoconocimiento emocional basada en el framework **RULER** (Yale Center for Emotional Intelligence). Todo corre 100% local — sin APIs de IA externas, sin nube.

## Setup rápido (Persona 4 — Integration Lead)

```bash
# 1. Clonar y entrar al repo
cd mirror

# 2. Backend — entorno virtual e instalación
cd backend
python3 -m venv .venv
source .venv/bin/activate          # actívalo en cada terminal nueva
pip install -r requirements.txt
cp ../.env.example ../.env         # editar con tus paths reales

# 3. Instalar Ollama y modelos
ollama pull qwen3:4b-instruct
ollama pull qwen3-embedding:0.6b

# 4. Instalar el motor de transcripción de voz (WhisperKit, macOS)
brew install whisperkit-cli
# whisperkit-cli descarga el modelo CoreML solo la primera vez que se usa.
# Alternativa multiplataforma: STT_ENGINE=faster_whisper en .env + pip install faster-whisper

# 5. Crear directorios de datos
mkdir -p ../data/chroma_db ../data/audio ../data/models

# 6. Cargar datos sintéticos de demo
python seed_data.py

# 7. Levantar servidor (con el venv activo)
python main.py
# → http://0.0.0.0:8000

# Opcional — elegir el modelo de transcripción de voz al arrancar:
python main.py --stt-model small
# Opciones, de más rápido a más preciso:
#   tiny · base · small · large-v2 · large-v3 · large-v3-turbo · distil-large-v3
# Sin el flag se usa WHISPERKIT_MODEL del .env. `python main.py --help` las lista.

# Desde el celular (misma red WiFi):
# → http://<IP-de-la-laptop>:8000
```

## Estructura

```
mirror/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── routes/              # audio, emotion, history, chat
│   ├── services/            # stt/, audio, llm, embedding, memory, perfil, feedback
│   ├── prompts/             # ruler_extraction, entry_feedback, chat_system…
│   ├── crisis_keywords.py
│   ├── seed_data.py         # 15 entradas sintéticas para demo
│   └── requirements.txt
├── frontend/
│   ├── index.html           # pantallas + modal de crisis + drawer
│   ├── app.js               # lógica completa
│   ├── styles.css
│   ├── manifest.json        # PWA instalable
│   └── sw.js                # service worker
├── data/
│   ├── chroma_db/           # vector DB (gitignored)
│   └── models/              # whisper model (gitignored)
├── .env.example
└── .gitignore
```

## API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/transcribe` | Audio → texto (WhisperKit) |
| POST | `/api/analyze` | Texto → estructura RULER + feedback de Mira |
| POST | `/api/entry` | Audio + emoción → transcribe, analiza y genera feedback |
| POST | `/api/save` | Persiste la entrada y actualiza el perfil |
| GET  | `/api/emotions` | Catálogo de emociones (sub-matriz RULER) |
| GET  | `/api/history` | Historial de entradas |
| GET  | `/api/patterns` | Insights y patrones detectados |
| POST | `/api/feedback/reaction` | Registra si el feedback de Mira ayudó |
| POST | `/api/chat` | Chat con RAG sobre entradas pasadas |

## Fallbacks

- **STT:** motor por defecto WhisperKit. Alternativa: `STT_ENGINE=faster_whisper` en `.env` (+ `pip install faster-whisper`). Modelo ajustable con `WHISPERKIT_MODEL` en `.env` o el flag `--stt-model` al arrancar.
- **LLM:** ajustable con `LLM_MODEL` en `.env` (ej. `qwen3:8b-instruct` para más calidad)

## Líneas de ayuda (integradas en app)

- **SAPTEL:** 55 5259-8121 · 24/7 · Gratuito · Anónimo
- **Línea de la Vida:** 800-911-2000 · 24/7 · Gratuito

---

*Mirror es una herramienta de autoconocimiento emocional. No reemplaza la atención psicológica profesional.*

# Mirror — Autoconocimiento Emocional

> Hackathon Guadalahacks 2026 · Track: IA en el Borde

App móvil PWA de autoconocimiento emocional basada en el framework **RULER** (Yale Center for Emotional Intelligence). Todo corre 100% local — sin APIs de IA externas, sin nube.

## Setup rápido

```bash
# 1. Clonar y entrar al repo
cd mirror

# 2. Backend — entorno virtual e instalación
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
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

# Desde el celular (misma red WiFi):
# → http://<IP-de-la-laptop>:8000
```

### Flag `--stt-model`

```bash
python main.py --stt-model small
# Opciones (más rápido → más preciso):
#   tiny · base · small · large-v2 · large-v3 · large-v3-turbo · distil-large-v3
# Sin el flag usa WHISPERKIT_MODEL del .env
```

## Estructura

```
mirror/
├── backend/
│   ├── main.py                  # FastAPI app (sirve también el frontend)
│   ├── logging_config.py        # Logger estructurado + DEV_MODE
│   ├── crisis_keywords.py       # Lista de palabras clave de crisis
│   ├── seed_data.py             # 15 entradas sintéticas para demo
│   ├── requirements.txt
│   ├── routes/
│   │   ├── audio.py             # /transcribe
│   │   ├── emotion.py           # /analyze, /save, /entry, /emotions
│   │   ├── history.py           # /history, /patterns
│   │   └── chat.py              # /chat (RAG), /feedback/reaction
│   ├── services/
│   │   ├── audio_pipeline.py    # Orquesta STT + warm-up
│   │   ├── audio_convert.py     # webm/ogg → wav 16 kHz mono
│   │   ├── audio_errors.py      # Tipos de error de audio
│   │   ├── crisis_detector.py   # Detección de crisis por keywords
│   │   ├── db.py                # SQLite (perfil + historial de chat)
│   │   ├── embedding_service.py # Embeddings vía Ollama
│   │   ├── emotion_catalog.py   # Catálogo RULER + sub-matriz
│   │   ├── entry_feedback.py    # Genera el mensaje de Mira
│   │   ├── llm_service.py       # Llamadas a Ollama (extracción RULER)
│   │   ├── memory_service.py    # ChromaDB (guardar + buscar entradas)
│   │   ├── profile_service.py   # Perfil emocional consolidado
│   │   ├── relevance.py         # Scoring de relevancia para RAG
│   │   ├── session_service.py   # Historial de conversación por sesión
│   │   └── signals_engine.py    # Detección de patrones emocionales
│   └── prompts/
│       ├── ruler_extraction.txt
│       ├── entry_feedback.txt
│       ├── chat_system.txt
│       ├── companion.txt
│       └── profile_synthesis.txt
├── frontend/
│   ├── index.html               # Pantallas + modal de crisis + drawer
│   ├── app.js                   # Lógica completa (máquina de estados)
│   ├── styles.css               # Estilos custom + tema oscuro/claro
│   ├── tailwind.css             # Build de Tailwind
│   ├── manifest.json            # PWA instalable
│   ├── sw.js                    # Service worker (caché v7)
│   ├── icon-192.png
│   ├── icon-512.png
│   └── apple-touch-icon.png
├── data/
│   ├── chroma_db/               # Vector DB (gitignored)
│   ├── audio/                   # Audios temporales (gitignored)
│   └── models/                  # Modelos Whisper (gitignored)
├── .env.example
└── .gitignore
```

## Persistencia

| Capa | Tecnología | Contenido |
|------|------------|-----------|
| Entradas RULER | ChromaDB (vector DB) | Transcripciones + metadatos emocionales + embeddings |
| Perfil consolidado | SQLite (WAL) | Resumen emocional generado periódicamente |
| Historial de chat | SQLite (WAL) | Mensajes de sesión para contexto conversacional |

## API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/transcribe` | Audio → texto (WhisperKit / faster-whisper) |
| POST | `/api/analyze` | Texto → estructura RULER + feedback de Mira |
| POST | `/api/entry` | Audio + emoción → transcribe + analiza + guarda (orquestado) |
| POST | `/api/save` | Persiste una entrada RULER en ChromaDB |
| GET  | `/api/emotions` | Catálogo de emociones por cuadrante (sub-matriz RULER) |
| GET  | `/api/history` | Historial de entradas |
| GET  | `/api/patterns` | Insights y patrones detectados |
| POST | `/api/feedback/reaction` | Registra si el feedback de Mira ayudó |
| POST | `/api/chat` | Chat con RAG sobre entradas pasadas |

## Fallbacks

- **STT:** motor por defecto WhisperKit (macOS/CoreML). Alternativa: `STT_ENGINE=faster_whisper` en `.env` + `pip install faster-whisper`. Modelo ajustable con `WHISPERKIT_MODEL` en `.env` o `--stt-model` al arrancar.
- **LLM:** ajustable con `LLM_MODEL` en `.env` (ej. `qwen3:8b-instruct` para más calidad)

## Líneas de ayuda (integradas en app)

- **SAPTEL:** 55 5259-8121 · 24/7 · Gratuito · Anónimo
- **Línea de la Vida:** 800-911-2000 · 24/7 · Gratuito

---

*Mirror es una herramienta de autoconocimiento emocional. No reemplaza la atención psicológica profesional.*

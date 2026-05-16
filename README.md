# Mirror — Autoconocimiento Emocional

> Hackathon Guadalahacks 2026 · Track: IA en el Borde

App móvil PWA de autoconocimiento emocional basada en el framework **RULER** (Yale Center for Emotional Intelligence). Todo corre 100% local — sin APIs de IA externas, sin nube.

## Setup rápido (Persona 4 — Integration Lead)

```bash
# 1. Clonar y entrar al repo
cd mirror

# 2. Backend
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env   # editar con tus paths reales

# 3. Instalar Ollama y modelos
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text

# 4. Instalar whisper.cpp (o descomentar faster-whisper en whisper_service.py)
# Ver: https://github.com/ggerganov/whisper.cpp
# Modelo: https://huggingface.co/ggerganov/whisper.cpp -> ggml-small.bin -> data/models/

# 5. Crear directorios de datos
mkdir -p ../data/chroma_db ../data/audio ../data/models

# 6. Cargar datos sintéticos de demo
python seed_data.py

# 7. Levantar servidor
python main.py
# → http://0.0.0.0:8000

# Desde el celular (misma red WiFi):
# → http://<IP-de-la-laptop>:8000
```

## Estructura

```
mirror/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── routes/              # audio, emotion, history, chat
│   ├── services/            # whisper, llm, embedding, memory
│   ├── prompts/             # ruler_extraction.txt, chat_system.txt
│   ├── crisis_keywords.py
│   ├── seed_data.py         # 15 entradas sintéticas para demo
│   └── requirements.txt
├── frontend/
│   ├── index.html           # 6 pantallas + modal crisis
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
| POST | `/api/transcribe` | Audio → texto (Whisper) |
| POST | `/api/analyze` | Texto → estructura RULER |
| POST | `/api/entry` | Audio + emoción → flujo completo |
| GET  | `/api/history` | Historial de entradas |
| GET  | `/api/patterns` | 3 insights detectados |
| POST | `/api/chat` | Chat con RAG sobre entradas pasadas |

## Fallbacks

- **STT:** si whisper.cpp no compila → descomentar `faster-whisper` en `backend/services/whisper_service.py`
- **LLM:** si qwen2.5 es lento → cambiar `LLM_MODEL=llama3.1:8b-instruct` en `.env`

## Líneas de ayuda (integradas en app)

- **SAPTEL:** 55 5259-8121 · 24/7 · Gratuito · Anónimo
- **Línea de la Vida:** 800-911-2000 · 24/7 · Gratuito

---

*Mirror es una herramienta de autoconocimiento emocional. No reemplaza la atención psicológica profesional.*

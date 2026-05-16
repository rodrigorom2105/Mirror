# Contrato de audio — `POST /api/transcribe`

Para quien construya la UI de grabación. El backend de audio garantiza este
contrato; la UI solo debe cumplir con el formato de envío.

## Request

- **Método/ruta:** `POST /api/transcribe`
- **Content-Type:** `multipart/form-data`
- **Campo:** `audio` — el archivo de audio grabado (la clave del `FormData`).

Ejemplo desde el navegador:

```js
const form = new FormData();
form.append("audio", blob, "recording.webm");
await fetch("/api/transcribe", { method: "POST", body: form });
```

## Response

`200 OK` — JSON:

```json
{ "text": "la transcripción en español", "duration": 12.4 }
```

Si la respuesta es `200`, `text` siempre contiene texto (el audio sin voz
detectable devuelve `422`, no un `text` vacío).

## Formatos aceptados

El backend reconvierte con `ffmpeg`, así que acepta cualquier formato que
`ffmpeg` decodifique:

- **Chrome / Android:** `audio/webm` (códec Opus) — default de `MediaRecorder`.
- **Safari / iOS:** `audio/mp4` (códec AAC).

La UI **no** necesita forzar sample rate ni canales; el backend normaliza a
WAV 16 kHz mono.

## Límites

- Duración: **0.5 s – 120 s**.
- Tamaño: **≤ 25 MB**.

La UI debería validar la duración en el cliente **antes** de enviar: el audio
fuera del rango 0.5–120 s se rechaza con `422` y obliga al usuario a regrabar.

## Errores

Todos devuelven JSON `{ "detail": "mensaje en español" }`:

| Código | Causa |
|--------|-------|
| `400` | El archivo no es audio (`Content-Type` no empieza con `audio/`). |
| `413` | El archivo supera 25 MB. |
| `422` | Audio vacío, corrupto, muy corto, muy largo, o sin voz detectable. |
| `504` | La transcripción tardó demasiado. |
| `500` / `503` | Fallo o indisponibilidad del motor de transcripción. |

## Aviso importante para iOS

Safari en iOS produce `audio/mp4`, no `audio/webm`. La UI **no debe hardcodear**
el MIME type del `Blob`. Debe usar el MIME real del `MediaRecorder`:

```js
const blob = new Blob(chunks, { type: mediaRecorder.mimeType });
```

> Nota: el `app.js` actual hardcodea `audio/webm` en la línea ~110. Eso rompe la
> grabación en iPhone y debe corregirse al implementar la UI (fuera del alcance
> del audio pipeline).

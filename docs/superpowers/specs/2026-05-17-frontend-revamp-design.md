# Mirror — Revamp del Frontend

**Fecha:** 2026-05-17
**Rama:** `feat/frontend-ui-polish`
**Estado:** Diseño aprobado — listo para plan de implementación

## Contexto

Mirror es una PWA privada de autoconocimiento emocional. El usuario registra cómo
se siente con la voz, la app transcribe y aplica el método **RULER** (Mood Meter de
4 cuadrantes: energía × agrado), guarda la entrada y muestra patrones.

El frontend vive en `frontend/` y lo sirve el backend en la raíz:
- `frontend/index.html` — todas las pantallas en un solo documento
- `frontend/app.js` — navegación, grabación, llamadas a la API
- `frontend/styles.css` — estilos mobile-first (Tailwind compilado en `tailwind.css`)
- `frontend/sw.js` — service worker

Este revamp es de UI/UX. Hay un único cambio de backend (sección 9), necesario para
que el botón Cancelar de la pantalla de confirmación no deje basura registrada.

## Objetivos

1. Más opciones de emociones por cuadrante.
2. Al tocar un cuadrante, desplegar una **sub-matriz** de emociones de ese cuadrante.
3. Eliminar todo emoji de la UI; usar iconos de alta calidad.
4. Más animación en los textos.
5. Más animación durante la carga.
6. Paleta de colores más "cream".
7. Transiciones suaves en toda la app.
8. Poder cancelar/regrabar y poder escribir texto en vez de grabar.
9. Grabar por tap o por hold; apagar el micrófono al terminar.

## Decisiones tomadas (brainstorming con compañero visual)

- **Paleta:** tema claro "Crema clara" (opción A). El modo noche queda como mejora futura.
- **Sub-matriz:** opción C — el cuadrante hace zoom a pantalla completa y revela una
  matriz con ejes RULER, donde la posición = intensidad y el color va graduado.
- **Pantalla Grabar:** selector Hablar/Escribir; botón Cancelar mientras se graba;
  **sin** paso de revisión — al terminar de grabar se procesa automáticamente.
- **Pantalla Confirmar:** la entrada no se guarda hasta confirmar; dos botones,
  Guardar y Cancelar.

---

## 1 · Paleta "Crema clara" (tema claro)

Migrar de tema oscuro azul marino a tema claro cálido. Reemplazar las variables
CSS de `:root` en `styles.css`:

| Variable | Valor actual | Valor nuevo |
|---|---|---|
| `--bg` | `#090d16` | `#F7F1E6` (crema cálido) |
| `--surface` | `rgba(255,255,255,.045)` | `#FCF8F0` |
| `--surface-2` | `rgba(255,255,255,.07)` | `#F1E9D8` |
| `--border` | `rgba(255,255,255,.09)` | `rgba(120,100,70,.14)` |
| `--text` | `#f1f5f9` | `#4A4338` |
| `--text-dim` | `#94a3b8` | `#9A9082` |
| `--indigo` / acento | `#6366f1` | `#5B53C9` (índigo cálido) |
| `--indigo-light` | `#818cf8` | `#7D72D6` |

Cuadrantes — base (texto/borde) y superficie pastel:
- **rojo:** base `#C2553B`, pastel `#F3DDD4`
- **amarillo:** base `#B0852A`, pastel `#F6ECD6`
- **azul:** base `#4E6E88`, pastel `#E0E8EE`
- **verde:** base `#557A58`, pastel `#E2EBE2`

Detalles:
- Gradientes de fondo radiales en tonos cálidos (no índigo frío).
- Sombras marrón suave (`rgba(120,100,70,…)`), eliminar los box-shadow tipo "glow".
- `<meta name="theme-color">` → color crema.
- Verificar contraste WCAG AA de todo el texto sobre crema (los tonos base de
  cuadrante listados ya están elegidos para cumplir AA sobre superficie pastel).
- `prefers-color-scheme` no se usa todavía (modo noche futuro).

## 2 · Mood Meter con más emociones + sub-matriz

**Datos.** Reemplazar `QUADRANTS` en `app.js` por una estructura con ~12 emociones
por cuadrante, ordenadas de menor a mayor intensidad (la intensidad alimenta el
degradado y la posición en la sub-matriz):

- **rojo:** nervioso, inquieto, preocupado, tenso, ansioso, irritado, molesto,
  frustrado, estresado, abrumado, enojado, furioso
- **amarillo:** optimista, motivado, animado, alegre, feliz, entusiasmado,
  inspirado, orgulloso, emocionado, sorprendido, eufórico, radiante
- **azul:** desganado, aburrido, nostálgico, melancólico, desanimado, decepcionado,
  triste, solo, agotado, vacío, derrotado, abatido
- **verde:** cómodo, contento, satisfecho, tranquilo, relajado, calmado, sereno,
  agradecido, pleno, seguro, en paz, descansado

**Interacción.**
- El Mood Meter de 4 cuadrantes sigue siendo la pantalla de entrada (`screen-mood`).
- Al tocar un cuadrante: transición de **zoom** — el cuadrante escala hasta llenar
  la pantalla y se revela la sub-matriz de ese cuadrante.
- La pantalla de palabras (`screen-words`) se rediseña como **sub-matriz**:
  rejilla de 3 columnas × 4 filas (12 emociones), con la emoción más intensa
  arriba y la más leve abajo; color graduado de saturado (intenso) a suave (leve).
- Etiquetas de eje RULER alrededor de la rejilla (ej. "↑ más alterado / más
  calmado ↓" y el eje de agrado), reflejando el cuadrante elegido.
- Tap a una emoción → pantalla de Grabar (igual que hoy).
- Botón atrás → vuelve al Mood Meter con zoom inverso.

## 3 · Sin emojis — iconos de alta calidad

Eliminar **todos** los emojis de la UI:
- Emojis de cuadrante en `index.html`: 🔥 ⚡ 🌧️ 🌿 (`.q-emoji`).
- Prefijos `🔴 🟡 🔵 🟢` en las etiquetas de `QUADRANTS` (`app.js`).
- Cualquier otro emoji en textos/mensajes.

Sustituir por **Lucide** (ya cargado en `index.html` para el tab bar y el modal de
crisis). Iconos de línea, coloreados según el cuadrante:
- rojo → `flame`, amarillo → `sun`, azul → `cloud-rain`, verde → `leaf`
- mic / teclado / enviar / atrás / etc. → iconos Lucide correspondientes

La mascota **Mira** se conserva tal cual (es una ilustración, `assets/mira.png`).
`lucide.createIcons()` debe re-ejecutarse tras inyectar iconos en contenido dinámico.

## 4 · Más animación en los textos

- Títulos clave entran con stagger por palabra (ej. la tagline "¿Cómo te sientes
  ahora?", títulos de pantalla). Implementar envolviendo palabras en `<span>` con
  `animation-delay` incremental.
- Estados de texto que cambian (mensajes de la pantalla de análisis, `record-status`)
  con cross-fade suave en vez de cambio brusco.
- Labels y taglines entran escalonados al activarse su pantalla.
- Todo respeta `prefers-reduced-motion: reduce` (las animaciones se anulan).

## 5 · Más animación durante la carga

- **Pantalla de análisis:** orbe de Mira más vivo — más partículas/sparks, un
  shimmer de progreso, transición de mensajes más fluida.
- **Historial y Patrones:** reemplazar el spinner por **skeleton loaders**
  (tarjetas placeholder con shimmer) que igualen el layout final.
- Animación de entrada al abrir la app (la primera pantalla aparece con su intro).

## 6 · Transiciones suaves en todo

- Transiciones de pantalla consistentes: zoom para cuadrante→sub-matriz; slide/fade
  para el resto (ya existe `screenIn`).
- Estados hover/active/focus de todos los elementos interactivos suavizados con
  las curvas `--ease-soft` / `--ease-spring` ya definidas.
- El cambio Hablar/Escribir y Guardar/Cancelar también animados.

## 7 · Pantalla Grabar — Hablar / Escribir

`screen-record` se rediseña con un **selector segmentado** arriba: *Hablar* / *Escribir*.

**Modo Hablar:**
- Badge de la emoción seleccionada, waveform, botón de micrófono grande.
- Tap o hold para grabar — la lógica actual de `app.js` (`TAP_THRESHOLD_MS`,
  `pointerdown/up`, `toggleMode`) ya implementa esto; se conserva y se pule.
- Mientras graba: temporizador (mm:ss) y botón **Cancelar** (aborta sin procesar).
- Al terminar de grabar: el micrófono se libera de inmediato (`releaseAudioResources()`
  ya lo hace) y se pasa a la pantalla de análisis automáticamente.

**Modo Escribir:**
- Un `<textarea>` para escribir lo que se siente + botón **Continuar**.
- Para cuando el usuario no pueda o no quiera grabar.
- Continuar → pantalla de análisis.

Ambos modos desembocan en análisis → confirmación.

## 8 · Pantalla Confirmar — Guardar / Cancelar

- La entrada **no se persiste** durante el análisis; solo se analiza.
- `screen-confirm` muestra la transcripción + el resumen RULER y **dos botones**:
  - **Guardar** (primario) → llama a `/api/save`, persiste la entrada.
  - **Cancelar** (ghost) → descarta el resultado, no se registra nada, vuelve al
    Mood Meter.
- El modal de crisis (si `crisis_flag`) sigue mostrándose tras el análisis,
  independientemente de Guardar/Cancelar.

## 9 · Cambio en el backend

Hoy `POST /api/entry` (en `backend/routes/emotion.py`) transcribe + analiza +
**guarda** + actualiza el perfil + corre el pipeline de acompañamiento, todo en una
llamada. Para que Cancelar no deje basura, se separa **analizar** de **guardar**:

- **Voz:** el endpoint de audio transcribe + analiza y **no guarda**; devuelve el
  dict `ruler` (con `transcripcion` y `crisis_flag`). Se elimina de él la llamada a
  `save_entry`, `_update_profile` y `_acompanamiento_post_entry`.
- **Texto:** `POST /api/analyze` ya existe, recibe `{text}` y no guarda — se
  reutiliza para el modo Escribir.
- **Guardar:** `POST /api/save` ya existe y persiste un `ruler`. Se le mueven
  `_update_profile` y `_acompanamiento_post_entry` (hoy dentro de `/api/entry`).
  Debe devolver el `acompanamiento` para que el frontend lo siga mostrando si aplica.

El frontend, en Guardar, envía a `/api/save` el `ruler` recibido del análisis.

> Nota: `backend/routes/emotion.py` es parte del audio pipeline (propiedad de Max).
> El plan de implementación debe tratar este cambio con cuidado y probarlo aparte.

## Flujo completo (después del revamp)

```
Mood Meter (4 cuadrantes)
  └─ tap cuadrante ──[zoom]──> Sub-matriz (12 emociones, ejes RULER)
       └─ tap emoción ──> Grabar
            ├─ Hablar: tap/hold graba → Cancelar | terminar
            └─ Escribir: textarea → Continuar
                 └──> Analizando (sin guardar)
                       └──> Confirmar (transcripción + RULER)
                             ├─ Guardar  → /api/save → Mood Meter
                             └─ Cancelar → descarta  → Mood Meter
```

## Pruebas

- Implementación con las skills `ui-ux-pro-max` y `frontend-design`.
- Pruebas en navegador (Chrome DevTools MCP): recorrer el flujo completo en voz y
  en texto, verificar Guardar y Cancelar, el zoom de la sub-matriz, el cambio de
  tema, y que no quede ningún emoji.
- Verificar `prefers-reduced-motion`.
- Verificar que el micrófono se apaga al terminar de grabar y al cancelar.
- Verificar contraste WCAG AA del texto sobre la paleta crema.

## Fuera de alcance

- Modo noche / `prefers-color-scheme` (mejora futura).
- Reproducir el audio grabado (no hay paso de revisión).
- Editar la transcripción en la pantalla de confirmación (para corregir, el
  usuario usa el modo Escribir).
- Rediseño de Historial, Patrones y Chat más allá de la paleta, iconos,
  animaciones y skeleton loaders.

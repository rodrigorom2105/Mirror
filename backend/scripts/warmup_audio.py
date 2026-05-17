"""Pre-calienta el motor STT antes del demo.

Genera voz real con el TTS de macOS (`say`) y la pasa por el pipeline completo.
Esto fuerza la descarga del modelo y la compilación CoreML (lentas la primera
vez). Correr ANTES del demo, desde backend/:

    python scripts/warmup_audio.py
"""
import os
import subprocess
import sys
import tempfile

# Permite importar el paquete `services` al correr el script directamente.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.audio_pipeline import transcribe_audio  # noqa: E402


def main() -> int:
    fd, aiff = tempfile.mkstemp(suffix=".aiff")
    os.close(fd)
    subprocess.run(
        ["say", "-o", aiff, "hola, esto es una prueba de calentamiento"],
        check=True,
    )
    try:
        print("Calentando motor STT (descarga + compilación CoreML)...")
        result = transcribe_audio(aiff)
        print(f"Motor STT listo. Transcripción de prueba: {result['text']!r}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Warmup falló: {exc}", file=sys.stderr)
        return 1
    finally:
        if os.path.exists(aiff):
            os.unlink(aiff)


if __name__ == "__main__":
    raise SystemExit(main())

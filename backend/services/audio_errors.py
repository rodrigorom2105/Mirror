"""Excepciones del audio pipeline.

Cada excepción lleva el código HTTP que le corresponde, para que el endpoint
las mapee de forma genérica. `detail` es el mensaje por defecto si la excepción
se levanta sin argumentos.
"""


class AudioError(Exception):
    """Base de todos los errores del audio pipeline."""

    status_code = 500
    detail = "Error procesando el audio."


class AudioCorruptError(AudioError):
    status_code = 422
    detail = "El audio está corrupto o en un formato no soportado."


class AudioTooShortError(AudioError):
    status_code = 422
    detail = "El audio es demasiado corto."


class AudioTooLongError(AudioError):
    status_code = 422
    detail = "El audio es demasiado largo."


class EmptyTranscriptionError(AudioError):
    status_code = 422
    detail = "No se detectó voz en el audio."


class TranscriptionTimeout(AudioError):
    status_code = 504
    detail = "La transcripción tardó demasiado."


class TranscriptionFailedError(AudioError):
    status_code = 500
    detail = "Falló la transcripción del audio."


class EngineUnavailableError(AudioError):
    status_code = 503
    detail = "El motor de transcripción no está disponible."

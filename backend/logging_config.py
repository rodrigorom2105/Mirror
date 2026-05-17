"""Configuración de logging del backend.

Con DEV_MODE activo, el logger `mirror` imprime a la consola en nivel DEBUG
todo lo de la app (transcripción, pasos del pipeline, peticiones a la API).
Fuera de dev queda en WARNING para no ensuciar.
"""
import logging
import os
import sys

DEV_MODE = os.getenv("DEV_MODE", "false").strip().lower() in ("1", "true", "yes", "on")


def setup_logging() -> None:
    """Configura el logger `mirror` con su propio handler a stdout.

    Idempotente: puede llamarse en cada reload sin duplicar handlers.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s  %(levelname)-7s %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logger = logging.getLogger("mirror")
    logger.setLevel(logging.DEBUG if DEV_MODE else logging.WARNING)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger hijo de `mirror` (p. ej. get_logger('stt'))."""
    return logging.getLogger(f"mirror.{name}")

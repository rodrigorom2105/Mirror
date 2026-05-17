"""Run once to load synthetic demo data: python seed_data.py"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("CHROMA_PATH", "./data/chroma_db")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

from services.memory_service import save_entry
from datetime import datetime, timedelta
import random

BASE = datetime.utcnow() - timedelta(days=21)

ENTRIES = [
    # Semana 1
    {"emocion_primaria": "ansioso", "emociones_secundarias": ["tenso", "preocupado"], "cuadrante": "rojo", "valencia": -0.7, "energia": 0.8, "intensidad": 7, "disparador": "examen de cálculo mañana", "contexto": {"personas": [], "lugar": "cuarto", "actividad": "estudiando"}, "pensamientos": ["no voy a pasar", "debí haber empezado antes"], "resumen": "Ansiedad anticipatoria por examen académico", "days_ago": 21},
    {"emocion_primaria": "satisfecho", "emociones_secundarias": ["tranquilo"], "cuadrante": "verde", "valencia": 0.6, "energia": 0.3, "intensidad": 5, "disparador": "terminé el proyecto de la semana", "contexto": {"personas": [], "lugar": "casa", "actividad": "trabajando"}, "pensamientos": ["lo logré", "puedo descansar"], "resumen": "Satisfacción al completar proyecto semanal", "days_ago": 20},
    {"emocion_primaria": "frustrado", "emociones_secundarias": ["irritado"], "cuadrante": "rojo", "valencia": -0.6, "energia": 0.7, "intensidad": 6, "disparador": "discusión con compañero de equipo", "contexto": {"personas": ["compañero"], "lugar": "universidad", "actividad": "proyecto grupal"}, "pensamientos": ["no escucha", "siempre igual"], "resumen": "Frustración por conflicto en trabajo en equipo", "days_ago": 19},
    {"emocion_primaria": "triste", "emociones_secundarias": ["decepcionado", "solo"], "cuadrante": "azul", "valencia": -0.7, "energia": 0.2, "intensidad": 6, "disparador": "extraño a mi familia", "contexto": {"personas": ["mamá", "papá"], "lugar": "departamento", "actividad": "noche de domingo"}, "pensamientos": ["están lejos", "ojalá pudiera verlos"], "resumen": "Melancolía dominical por distancia familiar", "days_ago": 18},
    {"emocion_primaria": "motivado", "emociones_secundarias": ["emocionado"], "cuadrante": "amarillo", "valencia": 0.8, "energia": 0.9, "intensidad": 8, "disparador": "hackathon anunciado por la universidad", "contexto": {"personas": ["equipo"], "lugar": "cafetería", "actividad": "planeando"}, "pensamientos": ["podemos ganar", "qué idea tan buena"], "resumen": "Motivación alta ante nuevo reto competitivo", "days_ago": 17},
    # Semana 2
    {"emocion_primaria": "agotado", "emociones_secundarias": ["abrumado"], "cuadrante": "azul", "valencia": -0.5, "energia": 0.1, "intensidad": 7, "disparador": "tres noches seguidas durmiendo mal", "contexto": {"personas": [], "lugar": "cuarto", "actividad": "intentando dormir"}, "pensamientos": ["no puedo apagar el cerebro", "mañana va a ser horrible"], "resumen": "Agotamiento acumulado por insomnio recurrente", "days_ago": 14},
    {"emocion_primaria": "calmado", "emociones_secundarias": ["sereno", "agradecido"], "cuadrante": "verde", "valencia": 0.7, "energia": 0.2, "intensidad": 4, "disparador": "mañana de domingo con café y música", "contexto": {"personas": [], "lugar": "balcón", "actividad": "descanso"}, "pensamientos": ["esto es lo que necesitaba", "qué bonita la mañana"], "resumen": "Paz matutina en momento de descanso", "days_ago": 13},
    {"emocion_primaria": "orgulloso", "emociones_secundarias": ["feliz"], "cuadrante": "amarillo", "valencia": 0.9, "energia": 0.7, "intensidad": 8, "disparador": "aprobé el examen de cálculo con 90", "contexto": {"personas": ["profesor"], "lugar": "universidad", "actividad": "revisando calificaciones"}, "pensamientos": ["sí pude", "el esfuerzo valió la pena"], "resumen": "Orgullo y alivio al ver calificación aprobatoria", "days_ago": 12},
    {"emocion_primaria": "irritado", "emociones_secundarias": ["frustrado"], "cuadrante": "rojo", "valencia": -0.5, "energia": 0.6, "intensidad": 5, "disparador": "lunes pesado con muchas clases seguidas", "contexto": {"personas": [], "lugar": "universidad", "actividad": "clases"}, "pensamientos": ["no aguanto los lunes", "necesito un descanso"], "resumen": "Irritación por carga académica intensa de lunes", "days_ago": 11},
    {"emocion_primaria": "ansioso", "emociones_secundarias": ["nervioso", "tenso"], "cuadrante": "rojo", "valencia": -0.7, "energia": 0.8, "intensidad": 7, "disparador": "presentación importante con nuevo jefe de área", "contexto": {"personas": ["jefe"], "lugar": "trabajo", "actividad": "preparando presentación"}, "pensamientos": ["qué tal que no le gusta", "tengo que quedar bien"], "resumen": "Ansiedad por exposición ante figura de autoridad", "days_ago": 10},
    {"emocion_primaria": "aliviado", "emociones_secundarias": ["tranquilo"], "cuadrante": "verde", "valencia": 0.7, "energia": 0.4, "intensidad": 6, "disparador": "la presentación salió bien", "contexto": {"personas": ["jefe", "equipo"], "lugar": "trabajo", "actividad": "tras la presentación"}, "pensamientos": ["lo logré", "para qué me preocupé tanto"], "resumen": "Alivio post-presentación exitosa", "days_ago": 10},
    # Semana 3
    {"emocion_primaria": "decepcionado", "emociones_secundarias": ["triste"], "cuadrante": "azul", "valencia": -0.6, "energia": 0.3, "intensidad": 6, "disparador": "amigo canceló planes que esperaba mucho", "contexto": {"personas": ["amigo"], "lugar": "casa", "actividad": "esperando"}, "pensamientos": ["siempre pasa lo mismo", "estaba contando con eso"], "resumen": "Decepción por cancelación de planes esperados", "days_ago": 7},
    {"emocion_primaria": "eufórico", "emociones_secundarias": ["emocionado", "feliz"], "cuadrante": "amarillo", "valencia": 0.95, "energia": 0.95, "intensidad": 9, "disparador": "primer día del hackathon, el equipo está súper bien", "contexto": {"personas": ["equipo"], "lugar": "hackathon", "actividad": "kickoff"}, "pensamientos": ["podemos ganar", "qué buena idea la de Mirror"], "resumen": "Euforia colectiva al iniciar competencia", "days_ago": 6},
    {"emocion_primaria": "agotado", "emociones_secundarias": ["abrumado", "ansioso"], "cuadrante": "azul", "valencia": -0.6, "energia": 0.2, "intensidad": 8, "disparador": "9 horas codificando sin parar en el hackathon", "contexto": {"personas": ["equipo"], "lugar": "hackathon", "actividad": "programando"}, "pensamientos": ["quedan 12 horas", "no sé si vamos a terminar"], "resumen": "Agotamiento intenso a mitad del hackathon", "days_ago": 5},
    {"emocion_primaria": "satisfecho", "emociones_secundarias": ["orgulloso", "sereno"], "cuadrante": "verde", "valencia": 0.85, "energia": 0.4, "intensidad": 7, "disparador": "el demo funcionó perfecto en el hackathon", "contexto": {"personas": ["equipo", "jueces"], "lugar": "hackathon", "actividad": "presentando"}, "pensamientos": ["lo logramos", "todo valió la pena"], "resumen": "Satisfacción profunda tras demo exitosa", "days_ago": 4},
]

def main():
    print("Cargando datos sintéticos...")
    for i, e in enumerate(ENTRIES):
        days_ago = e.pop("days_ago", 0)
        offset = timedelta(days=days_ago, hours=random.randint(8, 22))
        e["saved_at"] = (datetime.utcnow() - offset).isoformat()
        e["crisis_flag"] = False
        entry_id, _ = save_entry(e)
        print(f"  [{i+1}/{len(ENTRIES)}] {e['emocion_primaria']} ({e['cuadrante']}) → {entry_id[:8]}")
    print(f"\nListo. {len(ENTRIES)} entradas cargadas en ChromaDB.")

if __name__ == "__main__":
    main()

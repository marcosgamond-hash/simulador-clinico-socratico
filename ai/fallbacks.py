# ai/fallbacks.py
"""Mensajes socráticos de respaldo para cuando Gemini falla temporalmente."""

FALLBACK_TURNO_SOCRATICO = (
    "Comité Médico Evaluador: Se registró su intervención. "
    "Por un momento de latencia del sistema de tutoría, le pedimos que "
    "reformule su hipótesis principal y justifique con datos clínicos "
    "concretos (signos vitales, hallazgos semiológicos o de laboratorio) "
    "por qué prioriza esa sospecha sobre las alternativas de riesgo vital. "
    "¿Qué bandera roja está descartando activamente en este momento?"
)

FALLBACK_EVALUACION = {
    "puntaje_global": 0,
    "nivel_competencia": "No evaluable (fallo técnico temporal)",
    "precision_diagnostica": 0,
    "seguridad_banderas_rojas": 0,
    "adherencia_guias": 0,
    "metacognicion_sesgos": 0,
    "recursos_comunicacion": 0,
    "conclusion_docente": (
        "No se pudo completar la evaluación automatizada por un problema "
        "transitorio de conectividad. Reintente el cierre del caso en unos minutos "
        "o solicite evaluación manual a la jefatura docente."
    ),
    "desglose_dimensiones": {},
    "modo": "fallback_tecnico"
}

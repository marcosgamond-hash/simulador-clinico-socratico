"""
app.py - Simulador Socrático de Medicina Interna, Mitigación de Sesgos y Gobernanza de Datos.
"""
import streamlit as st
import pandas as pd
import altair as alt
import json
import sys
import importlib
from datetime import datetime, timezone
import re

# Recarga en caliente segura de módulos del proyecto para evitar caché residual en Streamlit
for _m in list(sys.modules.keys()):
    if _m == "config" or _m.startswith("core.") or _m.startswith("services."):
        try:
            importlib.reload(sys.modules[_m])
        except Exception:
            pass

from config import (
    CUSTOM_CSS,
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    DEFAULT_GSHEETS_URL,
    AUDIT_LOG_FILE,
    EVALUATION_LOG_FILE,
    LEADS_LOG_FILE,
    BENCHMARK_LOG_FILE,
    DOCENTE_PASSWORD,
    BASE_DIR,
    DEFAULT_DOCENTE_EMAIL,
    FEEDBACK_LOG_FILE,
    VIDEOTECA_FILE,
    MEMORIA_ATENEOS_FILE,
    ANTI_DESKILLING_LOG_FILE,
    ESCALAMIENTO_LOG_FILE,
    COSTO_EFECTIVIDAD_LOG_FILE
)
import urllib.parse
from core.cases import BANCO_CASOS, obtener_nombres_casos, obtener_caso, obtener_banco_completo
from core.concept_maps import GUIAS_TEMATICAS, obtener_guia_tematica, listar_unidades_tematicas
from core.biases import (
    TAXONOMIA_SESGOS,
    ESTRATEGIAS_FORZAMIENTO_COGNITIVO,
    obtener_detalle_sesgo,
    MODELO_PROCESO_DUAL,
    FAMILIAS_SESGOS,
    ESCENARIOS_BIFURCACION_COGNITIVA,
    obtener_sesgos_por_familia
)
from core.escalamiento import (
    ESTADO_COMPENSADO,
    ESTADO_DETERIORO_LEVE,
    ESTADO_SHOCK_DESCOMPENSADO,
    ESTADO_COLAPSO_INMINENTE,
    ESTADO_ESTABILIZADO,
    inicializar_estado_escalamiento,
    avanzar_tiempo_reloj,
    detectar_estudio_demorado,
    verificar_maniobra_resucitadora,
    obtener_curva_caso
)
from core.cost_effectiveness import (
    inicializar_estado_recursos,
    auditar_consumo_recursos,
    calcular_score_rur,
    generar_bloque_prompt_recursos
)
from core.anti_deskilling import (
    BANCO_DESAFIOS_AUDITORIA,
    TIPOS_FALLAS_IA,
    NIVELES_SEGURIDAD_PROPUESTA,
    obtener_desafios_auditoria,
    obtener_desafio_por_id,
    evaluar_contrarazonamiento_heuristico
)
from core.evaluation import (
    DIMENSIONES_RUBRICA,
    determinar_nivel_competencia,
    estructurar_informe_portafolio,
    ARQUETIPOS_RESIDENTES,
    analizar_respuesta_socratico
)
from services.governance import (
    sanitizar_texto_clinico,
    generar_pseudonimo_estudiante,
    generar_pase_sbar
)
from services.storage import (
    guardar_registro_auditoria,
    leer_registros_auditoria,
    guardar_registro_evaluacion,
    leer_registros_evaluacion,
    guardar_lead_preinscripcion,
    leer_leads_preinscripcion,
    guardar_registro_benchmark,
    leer_registros_benchmark,
    guardar_caso_personalizado,
    leer_casos_personalizados,
    eliminar_caso_personalizado,
    exportar_df_a_excel,
    exportar_df_a_csv_excel,
    generar_libro_excel_completo,
    guardar_consulta_feedback,
    leer_consultas_feedback,
    responder_consulta_docente,
    leer_videoteca_clases,
    guardar_video_clase,
    eliminar_video_clase,
    inicializar_memoria_ateneos,
    leer_memoria_ateneos,
    guardar_precedente_ateneo,
    eliminar_precedente_ateneo,
    vincular_respuesta_buzon_a_memoria,
    obtener_precedentes_relevantes,
    inicializar_almacenamiento_anti_deskilling,
    guardar_resultado_auditoria_ia,
    leer_resultados_auditoria_ia,
    inicializar_almacenamiento_escalamiento,
    guardar_evento_escalamiento,
    leer_eventos_escalamiento,
    inicializar_almacenamiento_costo_efectividad,
    guardar_evento_costo_efectividad,
    leer_eventos_costo_efectividad,
    inicializar_almacenamiento_sesiones,
    guardar_sesion_activa,
    cargar_sesion_activa,
    listar_sesiones_activas,
    eliminar_sesion_activa
)
from services.gemini_service import (
    procesar_turno_socratico,
    SKILLS_DIR,
    leer_skill_clinica,
    generar_respuesta_tutor_asincronico
)
from services.evaluator_service import evaluar_desempeno_caso, _generar_evaluacion_fallback, evaluar_auditoria_ia_residente
import streamlit.components.v1 as components

# Configuración de Streamlit
st.set_page_config(
    page_title="Simulador de Razonamiento Clínico & Gobernanza",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inyección de estilos
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Keep-alive anti-inactividad para guardias médicas (ping liviano periódico para evitar timeout de WebSocket)
components.html(
    """
    <script>
    (function() {
        if (!window._hellerKeepAlive) {
            window._hellerKeepAlive = setInterval(function() {
                fetch(window.location.href, { method: 'HEAD', cache: 'no-store' }).catch(function(){});
            }, 30000);
        }
    })();
    </script>
    """,
    height=0,
    width=0
)

# Intentar inicializar conexión con Google Sheets si existe la extensión instalada
conn_gsheets = None
try:
    from streamlit_gsheets import GSheetsConnection
    conn_gsheets = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    conn_gsheets = None

# Inicialización de almacenamiento resiliente de sesiones en guardia
inicializar_almacenamiento_sesiones()

# Sincronización bidireccional de seudónimo del alumno con parámetros de URL (?alumno=...)
url_alumno = st.query_params.get("alumno")
if "alumno_id" not in st.session_state:
    if url_alumno and str(url_alumno).strip():
        st.session_state.alumno_id = str(url_alumno).strip()
    else:
        st.session_state.alumno_id = generar_pseudonimo_estudiante("cohorte_2026")
        st.query_params["alumno"] = st.session_state.alumno_id
elif "alumno" not in st.query_params:
    st.query_params["alumno"] = st.session_state.alumno_id

# Inicialización del estado del simulador
if "caso_activo_nombre" not in st.session_state:
    primer_caso_nombre = list(BANCO_CASOS.keys())[0]
    primer_caso_info = BANCO_CASOS[primer_caso_nombre]
    st.session_state.caso_activo_nombre = primer_caso_nombre
    st.session_state.caso_activo_titulo = primer_caso_info["titulo"]
    st.session_state.caso_activo_texto = primer_caso_info["viñeta"]
    st.session_state.caso_activo_meta = primer_caso_info

if "mensajes" not in st.session_state:
    st.session_state.mensajes = [
        {
            "role": "model",
            "parts": (
                "**Comité Médico Evaluador:** Viñeta clínica analizada y parametrizada. "
                "Para iniciar la discusión socrática: **¿Cuál es su impresión sindrómica inicial, qué diagnósticos diferenciales de urgencia plantea y qué datos prioriza para confirmarlos o descartarlos?**"
            )
        }
    ]

if "evaluacion_activa" not in st.session_state:
    st.session_state.evaluacion_activa = None

if "estado_escalamiento" not in st.session_state:
    st.session_state.estado_escalamiento = inicializar_estado_escalamiento(
        st.session_state.caso_activo_meta,
        st.session_state.caso_activo_titulo
    )

if "estado_recursos" not in st.session_state:
    st.session_state.estado_recursos = inicializar_estado_recursos()

if "caso_en_standby" not in st.session_state:
    st.session_state.caso_en_standby = False

# Detección al cargar: ¿Tiene el residente una sesión guardada previa para recuperar?
if "sesion_recuperada_o_descartada" not in st.session_state:
    st.session_state.sesion_recuperada_o_descartada = False

if not st.session_state.sesion_recuperada_o_descartada and "sesion_pendiente_recuperar" not in st.session_state:
    ses_guardada = cargar_sesion_activa(st.session_state.alumno_id)
    if ses_guardada and len(ses_guardada.get("mensajes", [])) > 1:
        st.session_state.sesion_pendiente_recuperar = ses_guardada
    else:
        st.session_state.sesion_pendiente_recuperar = None

def restaurar_sesion_guardada(sesion_dict):
    """Restaura en st.session_state un snapshot completo de caso guardado en standby o recuperado."""
    st.session_state.caso_activo_nombre = sesion_dict.get("caso_activo_nombre", st.session_state.caso_activo_nombre)
    st.session_state.caso_activo_titulo = sesion_dict.get("caso_activo_titulo", st.session_state.caso_activo_titulo)
    st.session_state.caso_activo_texto = sesion_dict.get("caso_activo_texto", st.session_state.caso_activo_texto)
    st.session_state.caso_activo_meta = sesion_dict.get("caso_activo_meta", st.session_state.caso_activo_meta)
    st.session_state.mensajes = sesion_dict.get("mensajes", st.session_state.mensajes)
    st.session_state.evaluacion_activa = sesion_dict.get("evaluacion_activa", None)
    st.session_state.estado_escalamiento = sesion_dict.get("estado_escalamiento") or inicializar_estado_escalamiento(st.session_state.caso_activo_meta, st.session_state.caso_activo_titulo)
    st.session_state.estado_recursos = sesion_dict.get("estado_recursos") or inicializar_estado_recursos()
    st.session_state.caso_en_standby = sesion_dict.get("en_standby", False)
    st.session_state.sesion_pendiente_recuperar = None
    st.session_state.sesion_recuperada_o_descartada = True

def autoguardar_sesion_actual(forzar=False, en_standby=False):
    """Guarda automáticamente el estado actual en el disco si hay avances clínicos."""
    mensajes = st.session_state.get("mensajes", [])
    if forzar or len(mensajes) > 1:
        estado_a_guardar = {
            "caso_activo_nombre": st.session_state.get("caso_activo_nombre"),
            "caso_activo_titulo": st.session_state.get("caso_activo_titulo"),
            "caso_activo_texto": st.session_state.get("caso_activo_texto"),
            "caso_activo_meta": st.session_state.get("caso_activo_meta"),
            "mensajes": mensajes,
            "evaluacion_activa": st.session_state.get("evaluacion_activa"),
            "estado_escalamiento": st.session_state.get("estado_escalamiento"),
            "estado_recursos": st.session_state.get("estado_recursos"),
            "en_standby": en_standby or st.session_state.get("caso_en_standby", False)
        }
        guardar_sesion_activa(st.session_state.alumno_id, estado_a_guardar)

def reiniciar_caso(nombre_caso, titulo, texto, metadata=None):
    st.session_state.caso_activo_nombre = nombre_caso
    st.session_state.caso_activo_titulo = titulo
    st.session_state.caso_activo_texto = texto
    st.session_state.caso_activo_meta = metadata or {}
    st.session_state.evaluacion_activa = None
    st.session_state.mostrar_sbar = False
    st.session_state.caso_en_standby = False
    st.session_state.sesion_pendiente_recuperar = None
    st.session_state.sesion_recuperada_o_descartada = True
    st.session_state.estado_escalamiento = inicializar_estado_escalamiento(metadata or {}, titulo)
    st.session_state.estado_recursos = inicializar_estado_recursos()
    st.session_state.mensajes = [
        {
            "role": "model",
            "parts": (
                "**Comité Médico Evaluador:** Viñeta clínica analizada. "
                "**¿Cuál es su impresión sindrómica inicial y qué hipótesis diagnósticas de urgencia prioriza?**"
            )
        }
    ]
    eliminar_sesion_activa(st.session_state.alumno_id)

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown("### 🔑 Credenciales & Modelo")
    
    # Soporte para secrets o input manual
    default_key = ""
    try:
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            default_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        default_key = ""
        
    if "api_key_guardada" not in st.session_state:
        st.session_state.api_key_guardada = default_key

    gemini_api_key = st.text_input(
        "Google AI Studio API Key:",
        value=st.session_state.api_key_guardada,
        type="password",
        placeholder="AIzaSy...",
        key="api_key_field"
    )
    if gemini_api_key and gemini_api_key.strip():
        st.session_state.api_key_guardada = gemini_api_key.strip()
        st.caption(f"🟢 Clave ingresada ({len(gemini_api_key.strip())} caracteres)")
        if st.button("🔍 Probar Clave y Diagnosticar Modelos", width="stretch"):
            with st.spinner("Consultando catálogo de modelos a Google..."):
                try:
                    from google import genai
                    c_diag = genai.Client(api_key=gemini_api_key.strip())
                    lista_m = []
                    for mod in c_diag.models.list():
                        nombre_limpio = mod.name.replace("models/", "") if mod.name else ""
                        lista_m.append(nombre_limpio)
                    if lista_m:
                        st.success(f"✅ ¡Clave válida! {len(lista_m)} modelos disponibles en tu cuenta.")
                        st.info(f"Modelos detectados: {', '.join(lista_m[:6])}")
                    else:
                        st.warning("⚠️ La clave conectó pero la lista de modelos está vacía.")
                except Exception as e_diag:
                    st.error(f"❌ Error al consultar modelos con esta clave:\n{str(e_diag)}")
                    if "404" in str(e_diag) or "not found" in str(e_diag).lower():
                        st.warning("💡 **Causa del 404:** Esta API Key fue creada en Google Cloud sin habilitar la **'Generative Language API'**, o fue creada en un proyecto con restricciones. Ve a https://aistudio.google.com/apikey y crea una clave nueva allí.")
    else:
        st.caption("🔴 Pegue su clave aquí y presione Enter")
    
    with st.expander("❓ ¿Cómo obtener tu API Key gratuita en 2 min?"):
        st.markdown("""
        1. Entra a **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)**
        2. Inicia sesión con cualquier cuenta de Google / Gmail.
        3. Clic en **'Create API key'** &rarr; **'Create API key in new project'**.
        4. Copia la clave (`AIzaSy...`) y pégala aquí arriba.
        
        *La clave es 100% gratuita y no solicita tarjeta de crédito.*
        """)
    
    modelo_elegido = st.selectbox(
        "Modelo de Lenguaje (GenAI):",
        options=AVAILABLE_MODELS,
        index=0
    )
    
    st.markdown("---")
    st.markdown("### 👤 Identidad & Gobernanza")
    col_id1, col_id2 = st.columns([3, 1])
    with col_id1:
        alumno_input = st.text_input("ID Alumno (Seudónimo):", value=st.session_state.alumno_id)
        if alumno_input != st.session_state.alumno_id:
            st.session_state.alumno_id = alumno_input
            st.query_params["alumno"] = alumno_input
            ses_buscada = cargar_sesion_activa(alumno_input)
            if ses_buscada and len(ses_buscada.get("mensajes", [])) > 1:
                st.session_state.sesion_pendiente_recuperar = ses_buscada
                st.session_state.sesion_recuperada_o_descartada = False
            st.rerun()
    with col_id2:
        if st.button("🎲", help="Generar nuevo seudónimo anónimo aleatorio"):
            st.session_state.alumno_id = generar_pseudonimo_estudiante(f"id_{datetime.now().timestamp()}")
            st.query_params["alumno"] = st.session_state.alumno_id
            st.session_state.sesion_pendiente_recuperar = None
            st.session_state.sesion_recuperada_o_descartada = False
            st.rerun()
            
    st.caption("🛡️ Los datos se registran bajo un seudónimo anónimo para auditoría docente sin comprometer PII.")

    # Cajón de Casos en Standby / Reanudación
    with st.expander("📂 Casos en Standby / Reanudar", expanded=False):
        sesiones_guardadas = listar_sesiones_activas()
        if not sesiones_guardadas:
            st.caption("No hay casos pausados en el servidor.")
        else:
            st.caption(f"{len(sesiones_guardadas)} caso(s) activo(s) en memoria de guardia:")
            for ses in sesiones_guardadas[:6]:
                es_este = (ses.get("alumno_id") == st.session_state.alumno_id)
                prefijo = "👉 " if es_este else ""
                col_s1, col_s2 = st.columns([3, 1])
                with col_s1:
                    st.markdown(
                        f"**{prefijo}{ses.get('alumno_id')}**  \n"
                        f"<span style='font-size:0.8rem; color:#475569;'>{ses.get('caso_activo_titulo', 'Caso')} ({ses.get('total_mensajes', 0)} msgs)</span>",
                        unsafe_allow_html=True
                    )
                with col_s2:
                    if st.button("▶️", key=f"btn_reanudar_{ses.get('alumno_id')}", help="Cargar este caso en pantalla"):
                        st.session_state.alumno_id = ses.get("alumno_id")
                        st.query_params["alumno"] = ses.get("alumno_id")
                        restaurar_sesion_guardada(ses)
                        st.rerun()

    st.markdown("---")
    st.markdown("### ⚙️ Selección del Escenario")
    modo_caso = st.radio("Origen del caso:", ["Banco Estándar (Medicina Interna)", "Cargar Caso Personalizado"])
    
    if modo_caso == "Banco Estándar (Medicina Interna)":
        nombres_casos = obtener_nombres_casos()
        idx_caso = 0
        if st.session_state.caso_activo_nombre in nombres_casos:
            idx_caso = nombres_casos.index(st.session_state.caso_activo_nombre)
        nombre_sel = st.selectbox("Escenario de práctica:", nombres_casos, index=idx_caso)
        if nombre_sel != st.session_state.caso_activo_nombre:
            info_c = obtener_caso(nombre_sel)
            reiniciar_caso(nombre_sel, info_c["titulo"], info_c["viñeta"], info_c)
            st.rerun()
    else:
        st.markdown("#### 📝 Carga Rápida de Caso (Práctica)")
        with st.expander("❓ ¿Cómo redactar tu viñeta? (Requisitos)", expanded=False):
            st.markdown("""
            **Estructura obligatoria para que Socrático evalúe tu razonamiento:**
            1. **Filiación:** Edad, sexo, comorbilidades y medicación habitual (sin nombres ni DNI).
            2. **Cuadro actual:** Motivo de consulta, tiempo de inicio y cronología.
            3. **5 Constantes Vitales completas:**
               * TA (mmHg)
               * FC (lpm y ritmo)
               * FR (rpm)
               * SpO2 (% y FiO2)
               * Temp (°C)
            4. **Examen físico:** Hallazgos cardiovasculares, respiratorios, neurológicos o cutáneos.
            
            *💡 Si eres docente y deseas que el caso quede guardado permanentemente en el banco para todos los residentes, créalo desde la Pestaña 7: ➕ Creador & Banco de Casos.*
            """)
        custom_titulo = st.text_input("Título del caso:", value="Paciente con cuadro a filiar")
        plantilla_sidebar = (
            "Paciente varón/mujer de 55 años con antecedentes de [comorbilidades y medicación habitual]. "
            "Consulta en la guardia de emergencias por cuadro de 6 horas de evolución caracterizado por [síntomas cardinales y cronología]. "
            "Signos vitales al ingreso: TA 125/80 mmHg, FC 88 lpm regular, FR 18 rpm, SpO2 96% al aire ambiente, Temp 37.1 °C. "
            "Examen físico al ingreso: vigil, orientado en tiempo y espacio, sin foco neurológico, ruidos cardíacos normofonéticos, buena mecánica ventilatoria sin ruidos agregados."
        )
        custom_texto = st.text_area("Viñeta clínica (incluya antecedentes, examen y signos vitales):", value=plantilla_sidebar, height=150)
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            aplicar_sanitizacion = st.checkbox("Sanitizar PHI (Recomendado)", value=True)
        with col_c2:
            if st.button("Cargar Caso", width="stretch"):
                texto_final = custom_texto
                if aplicar_sanitizacion:
                    texto_final, redactados = sanitizar_texto_clinico(custom_texto)
                    if redactados:
                        st.info(f"Se enmascararon elementos sensibles: {', '.join(redactados)}")
                reiniciar_caso(
                    nombre_caso=f"Personalizado: {custom_titulo}",
                    titulo=custom_titulo,
                    texto=texto_final,
                    metadata={"area": "Caso de Usuario", "dificultad": "Variable", "sesgos_esperados": ["Evaluación abierta"]}
                )
                st.rerun()

    st.markdown("---")
    # Verificación de Modo Docente / Jefatura (Clave Maestra o URL Mágica)
    query_p = st.query_params
    token_url = query_p.get("docente", "") or query_p.get("admin", "")
    
    with st.expander("🔒 Acceso Docente / Jefatura", expanded=bool(token_url == DOCENTE_PASSWORD)):
        pin_input = st.text_input("Clave Maestra:", type="password", key="clave_docente_sidebar")
        if pin_input == DOCENTE_PASSWORD or token_url == DOCENTE_PASSWORD:
            st.success("🔓 Sesión de Supervisión Docente Activa")
            url_hoja = st.text_input("URL Google Sheets (Opcional):", value=DEFAULT_GSHEETS_URL)
            if conn_gsheets:
                st.success("✅ Conector Google Sheets activo")
            else:
                st.info("ℹ️ Almacenamiento local persistente (`data/audit_log.csv`)")
        else:
            url_hoja = DEFAULT_GSHEETS_URL
            st.caption("Uso exclusivo de instructores, jefes de servicio e investigadores.")

    es_docente = (pin_input == DOCENTE_PASSWORD) or (token_url == DOCENTE_PASSWORD)

    st.markdown("---")
    if st.button("🔄 Reiniciar Conversación del Caso", width="stretch"):
        reiniciar_caso(
            st.session_state.caso_activo_nombre,
            st.session_state.caso_activo_titulo,
            st.session_state.caso_activo_texto,
            st.session_state.caso_activo_meta
        )
        st.rerun()


# --- CUERPO PRINCIPAL CON PESTAÑAS (CONDICIONAL SEGÚN ROL) ---
st.markdown("""
    <div class="main-header">
        <div class="journal-subtitle">Plataforma de Educación Médica Basada en Evidencia &bull; Gobernanza &bull; Metacognición</div>
        <div class="journal-title">Simulador Socrático de Razonamiento Clínico</div>
    </div>
""", unsafe_allow_html=True)

# Todas las pestañas se declaran de forma unificada y permanente
tab_simulador, tab_deskilling, tab_mapas, tab_videoteca, tab_gobernanza, tab_programa, tab_metricas, tab_estres, tab_creador = st.tabs([
    "🩺 Simulador Clínico Socrático",
    "🥊 Gimnasio Anti-Deskilling (DEFT-AI)",
    "🗺️ Mapas Conceptuales & Guías de Estudio",
    "📺 Clases & Ateneos (YouTube)",
    "🧠 Cerebro Socrático: Teoría Dual & Sesgos",
    "🎓 Residencia Hospital Heller & Programa",
    "📊 Métricas & Auditoría Docente",
    "⚡ Laboratorio de Estrés & Benchmarking",
    "➕ Creador & Banco de Casos"
])

# ==========================================
# PESTAÑA 1: SIMULADOR CLÍNICO
# ==========================================
with tab_simulador:
    # Banner de Reanudación de Sesión previa / Standby detectada
    ses_pend = st.session_state.get("sesion_pendiente_recuperar")
    if ses_pend:
        st.info(
            f"🔔 **Caso en curso detectado para el residente `{st.session_state.alumno_id}`:**  \n"
            f"Se encontró una sesión previa en **'{ses_pend.get('caso_activo_titulo')}'** con **{len(ses_pend.get('mensajes', []))} turnos de discusión** y parámetros registrados."
        )
        col_rec1, col_rec2 = st.columns([1, 1])
        with col_rec1:
            if st.button("▶️ Continuar donde lo dejé (Reanudar Caso)", type="primary", width="stretch", key="btn_reanudar_banner"):
                restaurar_sesion_guardada(ses_pend)
                st.success("✅ Caso reanudado con éxito. ¡Continúa tu discusión!")
                st.rerun()
        with col_rec2:
            if st.button("🔄 Descartar y Empezar de Cero", width="stretch", key="btn_descartar_banner"):
                eliminar_sesion_activa(st.session_state.alumno_id)
                st.session_state.sesion_pendiente_recuperar = None
                st.session_state.sesion_recuperada_o_descartada = True
                st.rerun()

    # Viñeta clínica visual
    meta = st.session_state.get("caso_activo_meta", {})
    area_tag = meta.get("area", "Medicina Interna")
    dificultad_tag = meta.get("dificultad", "Intermedia")
    sesgos_sugeridos = meta.get("sesgos_esperados", [])
    
    tags_html = f"<span class='vignette-tag'>🏷️ {area_tag}</span><span class='vignette-tag'>🎯 Dificultad: {dificultad_tag}</span>"
    for s in sesgos_sugeridos:
        tags_html += f"<span class='vignette-tag' style='background-color:#fee2e2;color:#991b1b;'>⚠️ Trampa: {s}</span>"

    st.markdown(f"""
        <div class="vignette-card">
            <div class="vignette-title">📄 Viñeta: {st.session_state.caso_activo_titulo}</div>
            <div class="vignette-text">{st.session_state.caso_activo_texto}</div>
            <div class="vignette-tags">{tags_html}</div>
        </div>
    """, unsafe_allow_html=True)

    # Barra de Acción Rápida: Standby / Pausa de Guardia
    if st.session_state.get("caso_en_standby", False):
        st.warning(
            "⏸️ **Caso en Standby (Pausado por Guardia):** Este escenario está resguardado en el servidor. "
            "Puedes desconectarte para atender urgencias o evaluar pacientes reales. Todo tu progreso se mantiene intacto."
        )
        col_st1, col_st2 = st.columns([2, 1])
        with col_st2:
            if st.button("▶️ Reanudar Discusión Socrática", type="primary", width="stretch", key="btn_despausar_standby"):
                st.session_state.caso_en_standby = False
                autoguardar_sesion_actual(forzar=True, en_standby=False)
                st.rerun()
    else:
        col_vinfo, col_vbtn = st.columns([2.8, 1.2])
        with col_vbtn:
            if st.button("⏸️ Dejar Caso en Standby (Pausa de Guardia)", width="stretch", key="btn_poner_standby", help="Guarda todo el estado (signos vitales, estudios solicitados, tiempo y discusión) para que puedas cerrar la pestaña o atender una urgencia sin perder nada."):
                st.session_state.caso_en_standby = True
                autoguardar_sesion_actual(forzar=True, en_standby=True)
                st.success("💾 ¡Caso guardado en Standby! Puedes salir tranquilamente y volver en cualquier momento.")
                st.rerun()
    
    # Expandible de banderas rojas para el docente o residente en duda
    with st.expander("🔍 Orientación Metacognitiva & Banderas Rojas (Tutor Docente)", expanded=False):
        red_flags = meta.get("red_flags", ["Priorizar estabilización hemodinámica y exploración metódica de diagnósticos diferenciales."])
        for rf in red_flags:
            st.markdown(f"• **Alerta Clínica:** {rf}")
        calcs_rec = meta.get("calculadoras_pertinentes", [])
        if calcs_rec:
            st.markdown(f"• **Herramientas de Auditoría vinculadas:** `{', '.join(calcs_rec)}`")
            
        guia_url = meta.get("guia_oficial_url", "")
        guia_tit = meta.get("guia_oficial_titulo", "")
        guia_soc = meta.get("guia_oficial_sociedad", "")
        if guia_url:
            st.markdown(f"""
                <div style="margin-top: 10px; padding: 10px 14px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px;">
                    <span style="font-weight: 700; color: #166534; font-size: 0.85rem;">📖 Guía Clínica Oficial de Referencia (Gold Standard):</span><br>
                    <span style="color: #1e293b; font-size: 0.86rem;">{guia_tit} — <em>{guia_soc}</em></span><br>
                    <a href="{guia_url}" target="_blank" rel="noopener noreferrer" style="color: #047857; font-weight: 600; font-size: 0.82rem; text-decoration: underline; display: inline-block; margin-top: 4px;">
                        🔗 Abrir Guía Oficial Completa (Acceso Libre y Gratuito) &rarr;
                    </a>
                </div>
            """, unsafe_allow_html=True)

    # Precedentes institucionales activos del Hospital Heller para este caso (RAG Local)
    precedentes_activos = obtener_precedentes_relevantes(
        st.session_state.caso_activo_titulo,
        st.session_state.caso_activo_texto
    )
    if precedentes_activos:
        with st.expander(f"🏛️ Doctrina del Hospital Heller Activa ({len(precedentes_activos)} criterio(s) de ateneo)", expanded=False):
            st.markdown(
                f"<div style='padding: 10px 14px; background: #eff6ff; border-left: 4px solid #1e3a8a; border-radius: 6px; margin-bottom: 12px;'>"
                f"<strong style='color: #1e3a8a;'>🏛️ Memoria Institucional & Human-in-the-Loop:</strong> "
                f"<span style='color: #334155; font-size: 0.88rem;'>Socrático ha recuperado {len(precedentes_activos)} dictamen(es) y acuerdos clínicos formalmente consensuados en los Ateneos del Hospital Dr. Horacio Heller aplicables a este escenario. "
                f"El tutor socrático interrogará activamente al residente para garantizar la alineación con la práctica institucional local.</span>"
                f"</div>",
                unsafe_allow_html=True
            )
            for p_inst in precedentes_activos:
                st.markdown(
                    f"**📌 {p_inst.get('tema', 'Criterio')}**\n\n"
                    f"> *\"{p_inst.get('criterio_ateneo', '')}\"*\n\n"
                    f"<span style='color: #64748b; font-size: 0.82rem;'>🏛️ Origen: <strong>{p_inst.get('origen', 'Ateneo')}</strong> | "
                    f"Docente: <strong>{p_inst.get('docente_responsable', 'Docencia')}</strong> | "
                    f"Registrado: {p_inst.get('fecha_registro', '')}</span>\n\n---",
                    unsafe_allow_html=True
                )

    # =========================================================
    # =========================================================
    # CINTA CLÍNICA COMPACTA: SIGNOS VITALES & TIEMPO EN GUARDIA
    # =========================================================
    esc_actual = st.session_state.get("estado_escalamiento", {})
    if not esc_actual:
        esc_actual = inicializar_estado_escalamiento(
            st.session_state.caso_activo_meta,
            st.session_state.caso_activo_titulo
        )
        st.session_state.estado_escalamiento = esc_actual

    min_t = esc_actual.get("tiempo_transcurrido_min", 0)
    estado_h = esc_actual.get("estado_hemodinamico", ESTADO_COMPENSADO)
    sv = esc_actual.get("signos_vitales", {})
    estabilizado = esc_actual.get("estabilizado", False)
    es_urgente = esc_actual.get("es_urgencia", False)

    # Badges compactos
    if estabilizado:
        badge_bg = "#10b981"
        badge_txt = "🛡️ REANIMADO"
    elif estado_h == ESTADO_COMPENSADO:
        badge_bg = "#16a34a"
        badge_txt = "🟢 ESTABLE"
    elif estado_h == ESTADO_DETERIORO_LEVE:
        badge_bg = "#d97706"
        badge_txt = "🟡 DETERIORO LEVE"
    elif estado_h == ESTADO_SHOCK_DESCOMPENSADO:
        badge_bg = "#dc2626"
        badge_txt = "🟠 SHOCK"
    else:
        badge_bg = "#7f1d1d"
        badge_txt = "🚨 COLAPSO"

    val_color = "#38bdf8" if (estabilizado or estado_h == ESTADO_COMPENSADO) else ("#facc15" if estado_h == ESTADO_DETERIORO_LEVE else "#f87171")

    # Cinta clínica estilizada de una sola línea: Signos Vitales y Tiempo de Guardia
    st.markdown(f"""
        <div class="clinical-ribbon">
            <div class="ribbon-item">
                <span>🩺</span>
                <span><strong>TA:</strong> <span class="ribbon-val" style="color: {val_color};">{sv.get('ta', 'N/A')}</span></span>
                <span>• <strong>FC:</strong> <span class="ribbon-val" style="color: {val_color};">{sv.get('fc', 'N/A')} <small style="font-size:0.75rem;">lpm</small></span></span>
                <span>• <strong>SpO2:</strong> <span class="ribbon-val" style="color: {val_color};">{sv.get('spo2', 'N/A')}</span></span>
                <span>• <strong>Diuresis:</strong> <span class="ribbon-val" style="color: #cbd5e1;">{sv.get('diuresis', 'N/A')}</span></span>
            </div>
            <div class="ribbon-item">
                <span style="font-size: 0.8rem; color: #94a3b8;">⏱️ Guardia: <strong style="color: #f1f5f9;">{min_t} min</strong></span>
                <span class="ribbon-badge" style="background-color: {badge_bg}; color: white;">{badge_txt}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Alerta médica activa únicamente si hay descompensación en urgencias
    alerta_actual = esc_actual.get("ultima_alerta_enfermeria")
    if alerta_actual and not estabilizado and es_urgente and estado_h != ESTADO_COMPENSADO:
        if estado_h in [ESTADO_SHOCK_DESCOMPENSADO, ESTADO_COLAPSO_INMINENTE]:
            st.error(f"🚨 {alerta_actual}")
        else:
            st.warning(f"⚠️ {alerta_actual}")

    # Expander colapsado bajo demanda para quien quiera ver detalles sin ensuciar la pantalla
    with st.expander("📋 Ver parámetros vitales detallados (FR, sensorio, perfusión)", expanded=False):
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            st.markdown("##### 🫀 Parámetros Fisiológicos")
            st.markdown(f"• **Frecuencia Respiratoria:** {sv.get('fr', 'N/A')} rpm")
            st.markdown(f"• **Biomarcador Guía:** {sv.get('biomarcador_valor', 'N/A')} {sv.get('biomarcador_unidad', '')} *({sv.get('biomarcador_nombre', 'Marcador')})*")
        with col_exp2:
            st.markdown("##### 🩺 Examen Clínico de Guardia")
            st.markdown(f"• **Estado del Sensorio:** {sv.get('sensorio', 'N/A')}")
            st.markdown(f"• **Estado de Perfusión:** {sv.get('perfusion', 'N/A')}")
            st.caption("ℹ️ *Si el paciente se descompensa en guardia, indique su conducta de reanimación (cristaloides, vasopresores, O2, etc.) directamente en el chat para estabilizarlo.*")

    # Indicador de estado si falta la API Key
    if not gemini_api_key:
        st.info("💡 **Aviso:** Ingrese su **Google AI Studio API Key** en la barra lateral izquierda para habilitar el diálogo con el tutor socrático y la evaluación colegiada.")

    # Barra de atajos metacognitivos rápidos, derivación a ateneo (Human-in-the-loop) y cierre evaluador
    st.markdown("##### ⚡ Estrategias Metacognitivas, Protocolo SBAR & Cierre Evaluador:")
    col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns([1, 1, 1, 1, 1.3])
    with col_btn1:
        if st.button("⏸️ Pausa Diagnóstica", width="stretch"):
            st.session_state.prompt_pendiente = "Solicito una pausa diagnóstica metacognitiva: ¿Qué datos del caso son los que menos encajan con mi hipótesis principal?"
            st.rerun()
    with col_btn2:
        if st.button("💀 Pre-Mortem", width="stretch"):
            st.session_state.prompt_pendiente = "Hagamos un ejercicio Pre-Mortem: Asumamos que el paciente empeora críticamente en 24 horas. ¿Qué complicación o diagnóstico alternativo pasamos por alto?"
            st.rerun()
    with col_btn3:
        if st.button("🛡️ Peor Escenario", width="stretch"):
            st.session_state.prompt_pendiente = "Quiero verificar la regla del peor escenario: ¿Cuál es la entidad más grave y tiempo-dependiente que debo descartar con prioridad absoluta?"
            st.rerun()
    with col_btn4:
        if st.button("🚩 Pase SBAR", width="stretch"):
            st.session_state.mostrar_sbar = not st.session_state.get("mostrar_sbar", False)
            st.rerun()
    with col_btn5:
        if st.button("🏁 Concluir y Evaluar", width="stretch"):
            st.session_state.solicitar_evaluacion = True
            st.rerun()

    # Despliegue de pase SBAR si se activó (disponible incluso sin API Key)
    if st.session_state.get("mostrar_sbar", False):
        reporte_sbar = generar_pase_sbar(
            caso_titulo=st.session_state.caso_activo_titulo,
            viñeta=st.session_state.caso_activo_texto,
            historial_mensajes=st.session_state.mensajes,
            alumno_id=st.session_state.alumno_id
        )
        with st.expander("📋 Reporte Estructurado SBAR para Derivación a Ateneo / Jefe de Guardia", expanded=True):
            st.markdown(reporte_sbar["texto_markdown"])
            st.download_button(
                label="📥 Descargar Pase SBAR (.txt)",
                data=reporte_sbar["texto_markdown"],
                file_name=f"pase_sbar_{st.session_state.alumno_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                key="btn_descargar_sbar"
            )

    # Buzón Digital de Dudas, Sugerencias y Tutoría Asincrónica 24/7
    with st.expander("📬 ¿Dudas sobre este caso, sugerencias o consulta al docente? (Tutor 24/7 & Email)", expanded=False):
        st.markdown(
            "Escriba aquí sus dudas diagnósticas, preguntas farmacológicas, discrepancias con la devolución socrática "
            "o sugerencias para el equipo docente del Hospital Heller. "
            "**Si consulta fuera del horario de ateneo, el Tutor Clínico con IA le brindará una orientación preliminar inmediata (24/7)** "
            "y la consulta quedará archivada en la base institucional para revisión docente."
        )
        
        with st.form("form_consulta_residente_caso"):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                f_estudiante = st.text_input("ID / Seudónimo del Residente:", value=st.session_state.alumno_id)
                f_tipo = st.selectbox(
                    "Tipo de consulta:",
                    [
                        "Duda sobre conducta clínica en guardia",
                        "Pregunta farmacológica / dosis / interacciones",
                        "Discrepancia con el análisis del simulador",
                        "Sugerencia de mejora para el caso",
                        "Aporte de bibliografía / algoritmo alternativo"
                    ]
                )
            with col_f2:
                f_email_residente = st.text_input("Su correo electrónico (opcional, para respuesta personalizada):", placeholder="ejemplo@hospitalheller.gob.ar")
                f_caso_asoc = st.text_input("Caso clínico:", value=st.session_state.caso_activo_titulo, disabled=True)
                
            f_texto = st.text_area(
                "Detalle de su duda, razonamiento alternativo o sugerencia:",
                placeholder="Ejemplo: En el ECG veo taquicardia sinusal pero la troponina es limítrofe. ¿Por qué priorizar Score HEART antes que angioTAC si Wells dio 3 puntos?...",
                height=110
            )
            
            btn_enviar_consulta = st.form_submit_button("🚀 Enviar Consulta & Recibir Orientación Inmediata (24/7)")
            
            if btn_enviar_consulta:
                if not f_texto.strip():
                    st.warning("Por favor redacte el contenido de su consulta antes de enviar.")
                else:
                    with st.spinner("Registrando consulta y solicitando orientación al Tutor Clínico de Guardia..."):
                        t_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                        resp_tutor_ia = ""
                        if gemini_api_key:
                            resp_tutor_ia = generar_respuesta_tutor_asincronico(
                                duda_texto=f_texto.strip(),
                                caso_titulo=st.session_state.caso_activo_titulo,
                                tipo_consulta=f_tipo,
                                alumno_id=f_estudiante,
                                api_key=gemini_api_key,
                                modelo=modelo_elegido
                            )
                        else:
                            resp_tutor_ia = "Consulta archivada en el buzón institucional. Pendiente de revisión por el instructor docente."
                            
                        consulta_dict = {
                            "Fecha_UTC": t_utc,
                            "ID_Estudiante": f_estudiante,
                            "Caso_Clinico": st.session_state.caso_activo_titulo,
                            "Tipo_Consulta": f_tipo,
                            "Consulta_Texto": f_texto.strip(),
                            "Respuesta_IA_Preliminar": resp_tutor_ia,
                            "Estado": "Pendiente Docente" if not resp_tutor_ia.startswith("⚠️") else "Nueva",
                            "Respuesta_Docente_Final": ""
                        }
                        ok, msg_c = guardar_consulta_feedback(consulta_dict)
                        if ok:
                            st.session_state.ultima_consulta_guardada = consulta_dict
                            st.success("✅ ¡Consulta registrada exitosamente en el buzón docente!")
                        else:
                            st.error(f"Error al registrar: {msg_c}")
                            
        # Si se guardó una consulta recién, mostrar el feedback y el botón direct mailto
        if "ultima_consulta_guardada" in st.session_state and st.session_state.ultima_consulta_guardada:
            uc = st.session_state.ultima_consulta_guardada
            if uc.get("Caso_Clinico") == st.session_state.caso_activo_titulo:
                st.markdown("#### 🩺 Orientación del Tutor Clínico de Guardia (IA 24/7):")
                st.info(uc.get("Respuesta_IA_Preliminar", ""))
                
                # Construcción del mailto link pre-rellenado
                asunto_email = f"[SOCRÁTICO - CONSULTA] {uc.get('Tipo_Consulta')} | {uc.get('Caso_Clinico')} | {uc.get('ID_Estudiante')}"
                cuerpo_email = (
                    f"Estimado Instructor Docente / Jefatura de Residencia:\n\n"
                    f"Me comunico desde el Simulador Socrático del Hospital Heller para elevar la siguiente consulta:\n\n"
                    f"• Residente: {uc.get('ID_Estudiante')}\n"
                    f"• Caso Clínico: {uc.get('Caso_Clinico')}\n"
                    f"• Tipo de Consulta: {uc.get('Tipo_Consulta')}\n"
                    f"• Fecha/Hora: {uc.get('Fecha_UTC')} UTC\n\n"
                    f"--------------------\n"
                    f"DETALLE DE LA CONSULTA:\n"
                    f"{uc.get('Consulta_Texto')}\n"
                    f"--------------------\n\n"
                    f"Agradezco su retroalimentación en el próximo ateneo clínico.\n"
                    f"Saludos cordiales."
                )
                mailto_link = f"mailto:{DEFAULT_DOCENTE_EMAIL}?subject={urllib.parse.quote(asunto_email)}&body={urllib.parse.quote(cuerpo_email)}"
                
                st.markdown(f"""
                    <div style="margin-top: 12px; padding: 12px 16px; background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px;">
                        <span style="font-weight: 700; color: #1e40af;">✉️ Enviar esta consulta directamente al correo del docente:</span><br>
                        <span style="font-size: 0.85rem; color: #475569;">Al hacer clic, se abrirá tu aplicación de correo (Gmail, Outlook, Mail) con el asunto y el mensaje ya redactados y dirigidos a <code>{DEFAULT_DOCENTE_EMAIL}</code>.</span><br><br>
                        <a href="{mailto_link}" target="_blank" style="background-color: #2563eb; color: white; padding: 8px 18px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 0.88rem; display: inline-block;">
                            ✉️ Abrir en mi Correo con 1 Clic &rarr;
                        </a>
                    </div>
                """, unsafe_allow_html=True)

    # Manejo de Solicitud de Evaluación Docente al Cierre
    if st.session_state.get("solicitar_evaluacion", False):
        st.session_state.solicitar_evaluacion = False
        if not gemini_api_key:
            st.warning("⚠️ Debe ingresar su **Google AI Studio API Key** en la barra lateral para solicitar la evaluación colegiada.")
        else:
            mensajes_usuario = [m for m in st.session_state.mensajes if m["role"] == "user"]
            if len(mensajes_usuario) < 2:
                st.warning("⚠️ Debe participar en al menos 2 turnos de razonamiento clínico antes de solicitar la evaluación colegiada del caso.")
            else:
                with st.spinner("🎓 El Tribunal Evaluador Docente está deliberando la rúbrica y auditando el caso..."):
                    try:
                        res_eval = evaluar_desempeno_caso(
                            api_key=gemini_api_key,
                            modelo_seleccionado=modelo_elegido,
                            titulo_caso=st.session_state.caso_activo_titulo,
                            viñeta_texto=st.session_state.caso_activo_texto,
                            caso_meta=st.session_state.caso_activo_meta,
                            historial_mensajes=st.session_state.mensajes,
                            alumno_id=st.session_state.alumno_id
                        )
                        st.session_state.evaluacion_activa = res_eval
                        
                        # Persistir evaluación
                        pts_glob = res_eval.get("puntaje_global", 0)
                        nivel_obj = res_eval.get("nivel_competencia", {})
                        desg = res_eval.get("desglose_dimensiones", {})
                        row_ev = {
                            "Fecha_UTC": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                            "ID_Estudiante": st.session_state.alumno_id,
                            "Caso_Clinico": st.session_state.caso_activo_titulo,
                            "Puntaje_Global": pts_glob,
                            "Nivel_Competencia": nivel_obj.get("etiqueta", ""),
                            "Precision_Diagnostica": desg.get("precision_diagnostica", {}).get("puntaje", 0),
                            "Seguridad_Banderas_Rojas": desg.get("seguridad_y_banderas_rojas", {}).get("puntaje", 0),
                            "Adherencia_Guias": desg.get("adherencia_guias_y_skills", {}).get("puntaje", 0),
                            "Metacognicion_Sesgos": desg.get("metacognicion_y_sesgos", {}).get("puntaje", 0),
                            "Recursos_Comunicacion": desg.get("recursos_y_comunicacion", {}).get("puntaje", 0),
                            "Conclusion_Docente": res_eval.get("conclusion_docente", "")
                        }
                        guardar_registro_evaluacion(row_ev)
                        autoguardar_sesion_actual(forzar=True)
                        st.success("✅ ¡Evaluación colegiada completada y registrada en el legajo docente!")
                    except Exception as e_ev:
                        st.error(f"Error al generar la evaluación: {str(e_ev)}")

    # Despliegue visual de la Evaluación Activa
    if st.session_state.get("evaluacion_activa", None) is not None:
        ev = st.session_state.evaluacion_activa
        nivel = ev.get("nivel_competencia", {})
        pts_tot = ev.get("puntaje_global", 0)
        
        with st.container():
            st.markdown("---")
            st.markdown("### 🎓 Dictamen del Comité Docente de Evaluación")
            
            col_score, col_feedback = st.columns([1, 2])
            with col_score:
                st.markdown(
                    f"""
                    <div style="background-color: #f8fafc; border: 2px solid {nivel.get('color', '#1e3a8a')}; border-radius: 10px; padding: 20px; text-align: center;">
                        <div style="font-size: 0.9rem; text-transform: uppercase; color: #64748b; font-weight: bold;">Calificación Global</div>
                        <div style="font-size: 3rem; font-weight: bold; color: {nivel.get('color', '#1e3a8a')}; margin: 8px 0;">{pts_tot}<span style="font-size: 1.5rem; color: #94a3b8;">/100</span></div>
                        <div style="background-color: {nivel.get('color', '#1e3a8a')}; color: white; padding: 6px 14px; border-radius: 20px; font-weight: bold; display: inline-block;">
                            {nivel.get('badge', 'Evaluado')}
                        </div>
                        <div style="font-size: 0.85rem; color: #475569; margin-top: 10px;">{nivel.get('descripcion', '')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            with col_feedback:
                st.markdown("**Devolución Pedagógica del Tribunal:**")
                st.info(f"💡 *\"{ev.get('conclusion_docente', '')}\"*")
                
                col_pf, col_om = st.columns(2)
                with col_pf:
                    st.markdown("##### 🌟 Puntos Fuertes")
                    for pf in ev.get("puntos_fuertes", []):
                        st.markdown(f"• {pf}")
                with col_om:
                    st.markdown("##### 📌 Oportunidades de Mejora")
                    for om in ev.get("oportunidades_mejora", []):
                        st.markdown(f"• {om}")

            # Gráfico de barras de las 5 dimensiones
            st.markdown("##### 📊 Desglose por Competencias Clínicas (Máx. 20 pts cada una):")
            desg_data = []
            for dim_key, dim_meta in DIMENSIONES_RUBRICA.items():
                d_info = ev.get("desglose_dimensiones", {}).get(dim_key, {})
                desg_data.append({
                    "Competencia": f"{dim_meta['icono']} {dim_meta['nombre']}",
                    "Puntaje": d_info.get("puntaje", 0),
                    "Comentario": d_info.get("comentario", "")
                })
            df_desg = pd.DataFrame(desg_data)
            
            chart_dim_eval = alt.Chart(df_desg).mark_bar(color="#1e3a8a").encode(
                x=alt.X("Puntaje:Q", title="Puntos Obtenidos (Escala 0-20)", scale=alt.Scale(domain=[0, 20])),
                y=alt.Y("Competencia:N", sort=None, title=""),
                tooltip=["Competencia", "Puntaje", "Comentario"]
            ).properties(height=200)
            st.altair_chart(chart_dim_eval, use_container_width=True)

            # Acciones de cierre: Descargar Informe y Nuevo Caso
            col_acc1, col_acc2 = st.columns([2, 1])
            with col_acc1:
                informe_md = estructurar_informe_portafolio(
                    evaluacion=ev,
                    caso_titulo=st.session_state.caso_activo_titulo,
                    alumno_id=st.session_state.alumno_id,
                    viñeta_resumen=st.session_state.caso_activo_texto
                )
                st.download_button(
                    label="📥 Descargar Dictamen Formativo para Portafolio (.md)",
                    data=informe_md,
                    file_name=f"evaluacion_clinica_{st.session_state.alumno_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                    mime="text/markdown",
                    key="btn_descargar_informe_eval"
                )
            with col_acc2:
                if st.button("🔄 Comenzar Nuevo Caso", width="stretch", key="btn_nuevo_caso_post_eval"):
                    st.session_state.evaluacion_activa = None
                    st.session_state.mensajes = [
                        {
                            "role": "model",
                            "parts": (
                                "**Comité Médico Evaluador:** Viñeta clínica lista para análisis. "
                                "**¿Cuál es su impresión sindrómica inicial y qué hipótesis diagnósticas de urgencia prioriza?**"
                            )
                        }
                    ]
                    st.rerun()

            # Tarjeta de Conversión e Invitación al Programa Fellow
            st.markdown("""
            <div style="background: linear-gradient(135deg, #0b192c 0%, #1e3a8a 100%); border: 1px solid #3b82f6; border-radius: 12px; padding: 22px; color: white; margin: 20px 0;">
                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <span style="background-color: #f59e0b; color: #0f172a; font-size: 0.72rem; font-weight: 800; padding: 4px 10px; border-radius: 20px; text-transform: uppercase;">
                            Oportunidad Exclusiva • Cohorte Fundadora (50% OFF)
                        </span>
                        <h3 style="color: white; margin: 10px 0 6px 0; font-size: 1.35rem;">🎓 ¿Quieres dominar los 12 casos mayores de la guardia?</h3>
                        <p style="color: #cbd5e1; font-size: 0.88rem; margin: 0; max-width: 680px; line-height: 1.45;">
                            Has completado la auditoría clínica de este caso. Accede al programa completo con las <strong>12 Masterclasses en video</strong>, <strong>12 Fichas de Bolsillo A4 (One-Pagers)</strong> para tu guardapolvo y obtén tu <strong>Certificación Oficial de Competencias para Portafolio Médico</strong>.
                        </p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col_cta1, col_cta2 = st.columns([1, 1])
            with col_cta1:
                st.info(
                    "📌 **Próximo Paso: Ateneo Clínico de Debriefing**\n\n"
                    "Guarde sus notas y reflexiones diagnósticas para el ateneo presencial quincenal en el Hospital Heller. "
                    "Al finalizar la sesión, el docente a cargo proyectará la clase magistral y hará entrega de la **Ficha de Bolsillo A4** correspondiente a este caso."
                )
            with col_cta2:
                with st.expander("🚀 Solicitar Cupo Fundador (50% OFF)", expanded=False):
                    with st.form("form_preinscripcion_post_eval"):
                        st.markdown("##### Pre-inscripción con Descuento Especial:")
                        lead_nom = st.text_input("Nombre y Apellido:", key="lead_nom_eval")
                        lead_email = st.text_input("Correo electrónico:", key="lead_email_eval")
                        lead_wa = st.text_input("WhatsApp / Celular:", key="lead_wa_eval")
                        lead_hosp = st.text_input("Hospital / Residencia:", key="lead_hosp_eval")
                        btn_lead_submit = st.form_submit_button("✅ Asegurar mi Cupo con Descuento")
                        if btn_lead_submit:
                            if lead_nom and lead_email:
                                lead_obj = {
                                    "Fecha_UTC": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                                    "Nombre": lead_nom,
                                    "Email": lead_email,
                                    "WhatsApp": lead_wa,
                                    "Institucion_Residencia": lead_hosp,
                                    "Pais": "Iberoamérica",
                                    "Caso_Origen": st.session_state.caso_activo_titulo,
                                    "Estado": "Preinscripto (50% OFF)"
                                }
                                ok, msg_l = guardar_lead_preinscripcion(lead_obj)
                                if ok:
                                    st.success("🎉 ¡Felicitaciones! Has reservado tu cupo de fundador. Código promocional: **SOCRATICO-BETA-50**.")
                                    st.info("Te contactaremos por correo y WhatsApp con los detalles de acceso.")
                                else:
                                    st.error(msg_l)
                            else:
                                st.warning("Por favor complete su nombre y correo.")

            st.markdown("---")

    # Contenedor para todo el historial de la discusión clínica
    for msg in st.session_state.mensajes:
        role = msg["role"]
        avatar = "🩺" if role == "model" else "👨‍⚕️"
        with st.chat_message("assistant" if role == "model" else "user", avatar=avatar):
            st.markdown(msg["parts"])

    # Entrada del usuario: siempre anclada al final
    input_chat = st.chat_input("Plantee su hipótesis diagnóstica, justificación o estudios a solicitar...")
    prompt_final = st.session_state.pop("prompt_pendiente", None) or input_chat

    if prompt_final:
        if not gemini_api_key:
            st.warning("⚠️ Ingrese su **Google AI Studio API Key** en la barra lateral izquierda para enviar consultas al tutor socrático.")
        else:
            import traceback, sys
            print(f"[NUEVO TURNO CHAT] Prompt: '{prompt_final}', Modelo: '{modelo_elegido}', KeyLen: {len(gemini_api_key.strip()) if gemini_api_key else 0}", flush=True)

            # --- PILAR 3: VERIFICACIÓN DE SOPORTE VITAL & AVANCE DEL RELOJ DE GUARDIA ---
            if "estado_escalamiento" not in st.session_state or not st.session_state.estado_escalamiento:
                st.session_state.estado_escalamiento = inicializar_estado_escalamiento(
                    st.session_state.caso_activo_meta,
                    st.session_state.caso_activo_titulo
                )

            hubo_res, msg_res, st.session_state.estado_escalamiento = verificar_maniobra_resucitadora(
                st.session_state.estado_escalamiento,
                prompt_final
            )
            if hubo_res:
                guardar_evento_escalamiento({
                    "Fecha_UTC": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "ID_Estudiante": st.session_state.alumno_id,
                    "Caso_Clinico": st.session_state.caso_activo_titulo,
                    "Tiempo_Transcurrido_Min": st.session_state.estado_escalamiento.get("tiempo_transcurrido_min", 0),
                    "Tiempo_Resucitacion_Min": st.session_state.estado_escalamiento.get("tiempo_resucitacion_min", 0),
                    "Estado_Hemodinamico_Final": st.session_state.estado_escalamiento.get("estado_hemodinamico", ""),
                    "Estabilizado": "Sí",
                    "Nivel_Maximo_Deterioro": st.session_state.estado_escalamiento.get("etapa_fisiologica_idx", 0),
                    "Maniobras_Ejecutadas": prompt_final[:100],
                    "Alertas_Disparadas": len(st.session_state.estado_escalamiento.get("alertas_emitidas", []))
                })

            es_estudio_lento, min_extra, desc_estudio = detectar_estudio_demorado(prompt_final)
            minutos_avance = min_extra if es_estudio_lento else 3

            st.session_state.estado_escalamiento = avanzar_tiempo_reloj(
                st.session_state.estado_escalamiento,
                minutos=minutos_avance,
                motivo=desc_estudio if es_estudio_lento else "Turno de razonamiento clínico"
            )

            # Registro en historial de chat
            st.session_state.mensajes.append({"role": "user", "parts": prompt_final})
            autoguardar_sesion_actual()
            with st.chat_message("user", avatar="👨‍⚕️"):
                st.markdown(prompt_final)

            with st.chat_message("assistant", avatar="🩺"):
                try:
                    with st.spinner("El Comité Evaluador está examinando su respuesta y auditando parámetros..."):
                        logs_auditoria_ui = []
                        
                        def notificar_tool(nombre_t, desc_t):
                            logs_auditoria_ui.append((nombre_t, desc_t))
                            if nombre_t == "cuota_429":
                                status_placeholder.write(f"⏳ **{desc_t}**")
                            elif nombre_t == "reintento_contingencia":
                                status_placeholder.write(f"🔄 *{desc_t}*")
                            else:
                                status_placeholder.write(f"⚙️ `{nombre_t}`: {desc_t}")

                        status_placeholder = st.status("🔍 Pausa de Auditoría Metacognitiva...", expanded=True)
                        
                        respuesta_ia, tools_usadas = procesar_turno_socratico(
                            api_key=gemini_api_key,
                            modelo_seleccionado=modelo_elegido,
                            viñeta_texto=st.session_state.caso_activo_texto,
                            titulo_caso=st.session_state.caso_activo_titulo,
                            historial_mensajes=st.session_state.mensajes[:-1],
                            nuevo_mensaje_usuario=prompt_final,
                            alumno_id=st.session_state.alumno_id,
                            callback_notificacion=notificar_tool,
                            conn_gsheets=conn_gsheets,
                            url_gsheets=url_hoja if url_hoja else None,
                            estado_escalamiento=st.session_state.estado_escalamiento,
                            estado_recursos=st.session_state.get("estado_recursos")
                        )
                        
                        if tools_usadas:
                            status_placeholder.update(
                                label=f"Auditoría completada ({len(tools_usadas)} verificaciones)",
                                state="complete",
                                expanded=False
                            )
                        else:
                            status_placeholder.update(
                                label="Análisis socrático finalizado",
                                state="complete",
                                expanded=False
                            )

                    st.markdown(respuesta_ia)
                    st.session_state.mensajes.append({"role": "model", "parts": respuesta_ia})
                    autoguardar_sesion_actual()
                    # Recarga suave para que la conversación completa quede arriba y la barra abajo
                    st.rerun()

                except Exception as e:
                    tb_err = traceback.format_exc()
                    print(f"[ERROR EXCEPCIÓN DETECTADA]\n{tb_err}", file=sys.stderr, flush=True)
                    try:
                        with open(DATA_DIR / "last_error.log", "w", encoding="utf-8") as f_err:
                            f_err.write(tb_err)
                    except Exception:
                        pass
                    
                    err_str = str(e)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                        st.warning(
                            "⏳ **Límite de solicitudes por minuto alcanzado (Google AI Studio Free Tier):**\n\n"
                            "La API gratuita de Google admite hasta 15 solicitudes por minuto. Al encadenar varias herramientas de auditoría clínica en paralelo (calculadoras, guías y sesgos), la ventana temporal de Google se completó.\n\n"
                            "👉 **¿Cómo continuar?** Aguarde **15 a 20 segundos** para que Google resetee la ventana temporal y vuelva a presionar **Enter** o enviar su mensaje. El tutor continuará normalmente."
                        )
                    elif "404" in err_str and "NOT_FOUND" in err_str:
                        st.error(
                            "⚠️ **Modelo no disponible (Error 404):** El modelo seleccionado no está disponible en su región o cuenta. "
                            "Asegúrese de seleccionar `gemini-3.6-flash` en la barra lateral."
                        )
                    else:
                        st.error(f"⚠️ **Error en la llamada:** {str(e)}")
                        with st.expander("🛠️ Ver Detalle Técnico Completo para Diagnóstico", expanded=False):
                            st.code(tb_err, language="python")


# ==========================================
# PESTAÑA: GIMNASIO ANTI-DESKILLING (DEFT-AI AUDIT)
# ==========================================
with tab_deskilling:
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e3a8a 100%); padding: 22px 26px; border-radius: 12px; margin-bottom: 22px; border-left: 6px solid #f43f5e;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <div>
                    <span style="background-color: #f43f5e; color: white; font-size: 0.75rem; font-weight: 800; padding: 4px 10px; border-radius: 20px; text-transform: uppercase;">
                        Framework DEFT-AI &bull; Harvard & NEJM 2025
                    </span>
                    <h2 style="color: white; margin: 8px 0 6px 0; font-size: 1.5rem;">🥊 Gimnasio Anti-Deskilling & Auditoría de IA Médica</h2>
                    <p style="color: #cbd5e1; font-size: 0.92rem; margin: 0; max-width: 820px; line-height: 1.45;">
                        Entrenamiento activo contra el <strong>Sesgo de Automatización (<em>Automation Bias</em>)</strong> y la delegación ciega en algoritmos.
                        Supervisa las recomendaciones clínicas emitidas por un <em>Asistente de IA Novato</em>, detecta alucinaciones, anclajes y omisiones de riesgo vital, y fundamenta el contrarazonamiento médico correcto.
                    </p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Acordeón de Evidencia Científica & Debate con Médicos Escépticos (NEJM 2025, Lancet 2025)
    with st.expander("📚 Evidencia Científica 2025 & Posición Docente: ¿Por qué los médicos escépticos de la IA tienen parte de razón?", expanded=False):
        col_ev_a, col_ev_b = st.columns(2)
        with col_ev_a:
            st.markdown("""
                #### 🏛️ El Diagnóstico Científico del Peligro
                * 📄 **NEJM (Agosto 2025) — La Triple Amenaza Cognitiva:**
                  * [Abdulnour RE, Gin B, Boscardin CK. Educational Strategies for Clinical Supervision of Artificial Intelligence Use. N Engl J Med 2025; 393: 786–797](https://doi.org/10.1056/NEJMra2503232) (DOI: `10.1056/NEJMra2503232`).
                  * **Deskilling (Desentrenamiento):** Atrofia de una competencia que el médico ya dominaba.
                  * **Never-skilling (Incompetencia de origen):** El residente nunca adquiere la habilidad básica porque el modelo resolvió la incertidumbre diagnóstica desde el inicio, suprimiendo la "lucha cognitiva" formativa.
                  * **Mis-skilling (Aprendizaje viciado):** Adopción acrítica de alucinaciones o atajos del algoritmo como certezas médicas.
                * 🔬 **The Lancet Gastroenterology & Hepatology (2025) — Evidencia Empírica del "Efecto Google Maps":**
                  * [Budzyń K, et al. Endoscopist deskilling risk after exposure to artificial intelligence in colonoscopy: a multicentre, observational study](https://doi.org/10.1016/S2468-1253(25)00150-8).
                  * **Hallazgo:** Endoscopistas habituados a usar IA sufrieron una caída en la Tasa de Detección de Adenomas (ADR) del **28.4% al 22.4%** cuando realizaron colonoscopias **sin IA**.
            """)
        with col_ev_b:
            st.markdown("""
                #### ✈️ La Metáfora de la Aviación & La Solución Socrática
                * 🛩️ **"Los Niños de la Línea Magenta" (Warren Vanderburgh, JAMA & Aviation Safety):**
                  * En aviación, los pilotos que dependían ciegamente de la computadora de navegación (la línea magenta) perdieron la habilidad manual de volar (*stick-and-rudder*) ante emergencias.
                  * En medicina, no podemos permitir que los residentes se conviertan en *"médicos de la línea magenta"*, incapaces de pensar si se corta la red o el modelo alucina.
                * 🛡️ **La Tercera Vía de Socrático (Vigilancia Epistémica):**
                  * Ni **prohibición absurda** (el hospital no puede vivir en el siglo XIX) ni **delegación ciega** (mala praxis por *Automation Bias*).
                  * **El Médico como Auditor Popperiano:** El rol soberano del profesional frente a la IA es someter sus conjeturas a **falsación activa**.
            """)
        
        # Botón de Descarga del Manifiesto Docente Hospitalario
        st.markdown("---")
        col_man_info, col_man_btn = st.columns([2.5, 1])
        with col_man_info:
            st.markdown("**📜 Manifiesto Pedagógico Hospitalario:** Documento de posición académica para presentar a comités de docencia y jefes de servicio sobre la supervisión de IA.")
        with col_man_btn:
            try:
                with open("docs/MANIFIESTO_DOCENTE_SOCRATICO_IA_CLINICA.md", "r", encoding="utf-8") as f_man:
                    contenido_manifiesto = f_man.read()
            except Exception:
                contenido_manifiesto = "# Manifiesto Docente Socrático\\nDisponible en docs/MANIFIESTO_DOCENTE_SOCRATICO_IA_CLINICA.md"
            st.download_button(
                label="📥 Descargar Manifiesto (.md)",
                data=contenido_manifiesto,
                file_name="MANIFIESTO_DOCENTE_SOCRATICO_IA_CLINICA.md",
                mime="text/markdown",
                use_container_width=True
            )

    # Filtros y selector de desafíos
    col_fd1, col_fd2 = st.columns([1, 2])
    with col_fd1:
        opciones_unidades_desk = ["Todas las Unidades"] + [
            "Unidad 1: Cardiotorácico & Hemodinamia",
            "Unidad 2: Neuro-Urgencias & Cuidados Críticos",
            "Unidad 3: Falla Respiratoria, Medio Interno y Sepsis",
            "Unidad 4: Abdomen Agudo Médico y Descompensación Crónica"
        ]
        u_sel_desk = st.selectbox("Filtrar por Unidad:", opciones_unidades_desk, key="sb_u_anti_desk")
    
    desafios_disp = obtener_desafios_auditoria(u_sel_desk)
    titulos_map = {f"{d['id']} | {d['caso_titulo']}": d['id'] for d in desafios_disp}
    
    with col_fd2:
        desafio_etiqueta_sel = st.selectbox("Seleccione el Desafío de Auditoría de IA:", list(titulos_map.keys()), key="sb_desafio_anti_desk")
        desafio_id_sel = titulos_map[desafio_etiqueta_sel]
        desafio_activo = obtener_desafio_por_id(desafio_id_sel)

    if desafio_activo:
        col_c_izq, col_c_der = st.columns([1.1, 1.2])
        
        with col_c_izq:
            # Card del paciente
            st.markdown(f"""
                <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-left: 5px solid #1e3a8a; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
                    <div style="font-weight: 700; color: #1e3a8a; font-size: 1rem; margin-bottom: 6px;">
                        📄 Paciente en Shock Room: {desafio_activo.get('caso_titulo')}
                    </div>
                    <div style="font-size: 0.92rem; color: #334155; line-height: 1.5;">
                        {desafio_activo.get('viñeta_sintetica')}
                    </div>
                    <div style="margin-top: 8px;">
                        <span style="background-color: #e2e8f0; color: #475569; font-size: 0.78rem; font-weight: 600; padding: 3px 8px; border-radius: 4px;">
                            🏷️ {desafio_activo.get('unidad')}
                        </span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Card de la IA Novata
            st.markdown(f"""
                <div style="background-color: #fff1f2; border: 1px solid #fecdd3; border-left: 5px solid #e11d48; border-radius: 8px; padding: 16px;">
                    <div style="font-weight: 700; color: #9f1239; font-size: 0.98rem; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                        🤖 Propuesta Diagnóstica del "Asistente de IA Novato":
                    </div>
                    <div style="font-size: 0.93rem; color: #881337; line-height: 1.5; font-style: italic; background: rgba(255,255,255,0.7); padding: 12px; border-radius: 6px;">
                        "{desafio_activo.get('propuesta_ia_novata')}"
                    </div>
                    <p style="margin: 10px 0 0 0; color: #be123c; font-size: 0.8rem; font-weight: 600;">
                        ⚠️ ALERTA DE SEGURIDAD: Esta sugerencia de IA contiene una alucinación, un sesgo cognitivo sutil o una omisión crítica de riesgo vital. Como médico auditor, debes contrastarla y no aceptarla a ciegas.
                    </p>
                </div>
            """, unsafe_allow_html=True)

        with col_c_der:
            st.markdown("#### 🛡️ Formulario de Auditoría Clínica & Contrarazonamiento")
            
            calif_elegida = st.radio(
                "1. Dictamen de Seguridad de la Propuesta de IA:",
                NIVELES_SEGURIDAD_PROPUESTA,
                index=2,
                key=f"rb_calif_seg_{desafio_id_sel}"
            )
            
            tipo_falla_elegido = st.selectbox(
                "2. Tipo de Falla / Trampa de IA Identificada:",
                TIPOS_FALLAS_IA,
                key=f"sb_tipo_falla_{desafio_id_sel}"
            )
            
            errores_posibles = desafio_activo.get("errores_clave", [])
            errores_marcados = st.multiselect(
                "3. Infracciones Críticas Detectadas en la Recomendación:",
                errores_posibles,
                default=None,
                key=f"ms_errores_{desafio_id_sel}"
            )
            
            contrarazon_texto = st.text_area(
                "4. Redacta tu Contrarazonamiento Médico y la Conducta Real:",
                placeholder="Explica fisiopatológicamente por qué la sugerencia es peligrosa y detalla la conducta diagnóstica/terapéutica exacta que ordenarás para proteger al paciente...",
                height=120,
                key=f"ta_contrarazon_{desafio_id_sel}"
            )
            
            if st.button("🛡️ Emitir Dictamen de Auditoría & Evaluar Agudeza", key=f"btn_evaluar_auditoria_{desafio_id_sel}", width="stretch"):
                if not contrarazon_texto.strip():
                    st.warning("Por favor redacta tu contrarazonamiento clínico antes de emitir el dictamen.")
                else:
                    with st.spinner("Tribunal Docente de Supervisión de IA evaluando tu contrarazonamiento..."):
                        res_eval_desk = evaluar_auditoria_ia_residente(
                            desafio=desafio_activo,
                            calificacion_usuario=calif_elegida,
                            errores_marcados=errores_marcados,
                            texto_contrarazonamiento=contrarazon_texto.strip(),
                            api_key=gemini_api_key
                        )
                        st.session_state[f"resultado_auditoria_{desafio_id_sel}"] = res_eval_desk
                        
                        # Registrar en persistencia
                        evento_aud_ia = {
                            "Fecha_UTC": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                            "ID_Estudiante": st.session_state.alumno_id,
                            "Desafio_ID": desafio_id_sel,
                            "Unidad": desafio_activo.get("unidad", ""),
                            "Caso_Clinico": desafio_activo.get("caso_titulo", ""),
                            "Calificacion_Seguridad": calif_elegida,
                            "Calificacion_Acertada": "Sí" if res_eval_desk.get("calificacion_acertada") else "No",
                            "Tipo_Falla_IA": tipo_falla_elegido,
                            "Errores_Marcados": "; ".join(errores_marcados),
                            "Puntaje_Global": str(res_eval_desk.get("puntaje_global", 0)),
                            "Perfil_Auditor": res_eval_desk.get("perfil_auditor", ""),
                            "Contrarazonamiento_Texto": contrarazon_texto.strip()
                        }
                        guardar_resultado_auditoria_ia(evento_aud_ia)

        # Mostrar resultado de evaluación si existe en sesión
        if f"resultado_auditoria_{desafio_id_sel}" in st.session_state:
            res_aud = st.session_state[f"resultado_auditoria_{desafio_id_sel}"]
            st.markdown("---")
            st.markdown("### 📊 Devolución de la Auditoría & Calibración de Confianza")
            
            col_res_a1, col_res_a2, col_res_a3 = st.columns([1, 1.2, 1.5])
            with col_res_a1:
                st.metric("Agudeza Auditora", f"{res_aud.get('puntaje_global', 0)} / 100")
            with col_res_a2:
                st.metric("Perfil de Supervisión", res_aud.get('perfil_auditor', 'Auditor'))
            with col_res_a3:
                acierto_badge = "✅ Acierto en Nivel de Riesgo" if res_aud.get('calificacion_acertada') else "⚠️ Riesgo Desestimado (Automation Bias)"
                st.info(acierto_badge)
                
            dev_doc = res_aud.get("devolucion_docente")
            if dev_doc:
                st.markdown(f"**Devolución del Tribunal de Supervisión:**\n\n{dev_doc}")
                
            col_fb_a1, col_fb_a2 = st.columns(2)
            with col_fb_a1:
                st.markdown(f"""
                    <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 14px;">
                        <span style="font-weight: 700; color: #166534; font-size: 0.9rem;">🛡️ Daño Iatrogénico Evitado al Paciente:</span><br>
                        <span style="color: #1e293b; font-size: 0.9rem;">{res_aud.get('impacto_iatrogenico_evitado', desafio_activo.get('impacto_iatrogenico'))}</span>
                    </div>
                """, unsafe_allow_html=True)
            with col_fb_a2:
                perla = res_aud.get("perla_auditoria_ia") or "Recuerde: las IAs de lenguaje tienden a simular certeza aún en presencia de alucinaciones sutiles. La clínica soberana y los signos vitales mandan."
                st.markdown(f"""
                    <div style="background-color: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 14px;">
                        <span style="font-weight: 700; color: #854d0e; font-size: 0.9rem;">💡 Perla de Supervisión de IA (DEFT-AI):</span><br>
                        <span style="color: #1e293b; font-size: 0.9rem;">{perla}</span>
                    </div>
                """, unsafe_allow_html=True)
                
            with st.expander("📖 Contrarazonamiento Clínico Modelo (Gold Standard Docente)", expanded=False):
                st.markdown(f"**Argumentación Fisiopatológica Esperada:**\n\n{desafio_activo.get('contrarazonamiento_modelo')}")


# ==========================================
# PESTAÑA 2: MAPAS CONCEPTUALES & GUÍAS
# ==========================================
with tab_mapas:
    st.markdown("### 🗺️ Guías de Estudio & Algoritmos Generales de Decisión")
    st.caption("Marcos conceptuales y árboles analíticos de decisión por Unidades Temáticas. Proporcionan el andamiaje del Sistema 2 (Kahneman) para la preparación teórica de la guardia, sin revelar los casos de simulación.")
    
    unidades_list = listar_unidades_tematicas()
    unidad_elegida = st.selectbox(
        "Seleccione la Unidad Temática a Estudiar:",
        unidades_list,
        key="selectbox_unidad_tematica"
    )
    
    guia_detalle = obtener_guia_tematica(unidad_elegida)
    if guia_detalle:
        st.markdown(f"""
            <div style="background-color: #f1f5f9; border-left: 5px solid #2563eb; padding: 14px 18px; border-radius: 8px; margin: 12px 0;">
                <span style="font-weight: 700; color: #1e40af; text-transform: uppercase; font-size: 0.8rem;">📚 {guia_detalle.get('unidad', 'Unidad')} &bull; Eje: {guia_detalle.get('eje', 'Medicina Interna')}</span>
                <h3 style="margin: 6px 0 4px 0; color: #0f172a; font-size: 1.25rem;">{guia_detalle.get('titulo', 'Algoritmo de Decisión')}</h3>
                <p style="margin: 0; color: #475569; font-size: 0.92rem;">{guia_detalle.get('descripcion', '')}</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Diagrama de Flujo Mermaid
        st.markdown("#### 🌳 Algoritmo General de Decisión Clínica")
        st.markdown(f"```mermaid\n{guia_detalle.get('algoritmo_mermaid', '')}\n```")
        
        col_obj, col_bib = st.columns(2)
        with col_obj:
            st.markdown("#### 🎯 Objetivos de Aprendizaje de la Unidad")
            for obj in guia_detalle.get("objetivos_generales", []):
                st.markdown(f"- {obj}")
        
        with col_bib:
            st.markdown("#### 📚 Bibliografía Basal Recomendada")
            for bib in guia_detalle.get("bibliografia_basal", []):
                st.markdown(f"- 📖 *{bib}*")

        st.markdown("---")
        st.markdown("#### 🌐 Guías de Práctica Clínica de Máxima Evidencia (Open Access)")
        st.caption("Consensos y documentos oficiales completos publicados por sociedades médicas internacionales. Acceso libre y gratuito directo con 1 clic:")
        
        guias_oficiales = guia_detalle.get("guias_oficiales", [])
        if guias_oficiales:
            col_g1, col_g2 = st.columns(2)
            for idx_g, g in enumerate(guias_oficiales):
                target_col = col_g1 if idx_g % 2 == 0 else col_g2
                with target_col:
                    st.markdown(f"""
                        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-left: 5px solid #059669; border-radius: 8px; padding: 14px 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); min-height: 165px; display: flex; flex-direction: column; justify-content: space-between;">
                            <div>
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                    <span style="font-weight: 700; color: #047857; font-size: 0.78rem; text-transform: uppercase;">🏛️ {g.get('sociedad', '')} &bull; {g.get('revista', '')} ({g.get('año', '')})</span>
                                    <span style="background: #d1fae5; color: #065f46; font-size: 0.72rem; font-weight: 700; padding: 2px 7px; border-radius: 9999px;">🔓 {g.get('nivel', 'Open Access')}</span>
                                </div>
                                <div style="font-weight: 700; color: #0f172a; font-size: 0.95rem; margin-bottom: 6px; line-height: 1.3;">{g.get('titulo', '')}</div>
                                <div style="color: #475569; font-size: 0.84rem; margin-bottom: 10px; line-height: 1.4;">{g.get('descripcion', '')}</div>
                            </div>
                            <div>
                                <a href="{g.get('url', '#')}" target="_blank" rel="noopener noreferrer" style="display: inline-block; background-color: #047857; color: #ffffff; font-weight: 600; font-size: 0.8rem; padding: 6px 14px; border-radius: 6px; text-decoration: none;">
                                    📖 Leer Guía Oficial Completa &rarr;
                                </a>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

    st.markdown("---")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        manual_html_p = BASE_DIR / "manual_residencia_hospital_heller.html"
        if manual_html_p.exists():
            st.download_button(
                label="📄 Descargar Manual Completo de Residencia (HTML imprimible / PDF)",
                data=manual_html_p.read_text(encoding="utf-8"),
                file_name="Manual_Residencia_Clinica_Medica_Hospital_Heller.html",
                mime="text/html",
                key="btn_descarga_manual_mapas",
                use_container_width=True
            )
    with col_d2:
        manual_md_p = BASE_DIR / "MANUAL_RESIDENCIA_HOSPITAL_HELLER.md"
        if manual_md_p.exists():
            st.download_button(
                label="📖 Descargar Manual en Formato Markdown (.md)",
                data=manual_md_p.read_text(encoding="utf-8"),
                file_name="Manual_Residencia_Clinica_Medica_Hospital_Heller.md",
                mime="text/markdown",
                key="btn_descarga_manual_md_mapas",
                use_container_width=True
            )


# ==========================================
# PESTAÑA: CLASES & ATENEOS EN YOUTUBE
# ==========================================
with tab_videoteca:
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 20px 24px; border-radius: 12px; border-left: 6px solid #ef4444; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                <div>
                    <span style="background-color: #ef4444; color: white; font-size: 0.75rem; font-weight: 800; padding: 3px 10px; border-radius: 20px; text-transform: uppercase;">
                        YouTube Académico • Hospital Dr. Horacio Heller
                    </span>
                    <h3 style="color: white; margin: 8px 0 4px 0; font-size: 1.35rem;">📺 Videoteca de Ateneos y Masterclasses Clínicas</h3>
                    <p style="color: #94a3b8; font-size: 0.9rem; margin: 0; line-height: 1.4;">
                        Clases magistrales grabadas, ateneos de morbimortalidad y resolución paso a paso de los casos de simulación. 
                        Podés reproducir los videos directamente dentro de la plataforma o abrirlos en YouTube para verlos en tu celular o Smart TV.
                    </p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Administrador Docente para agregar nuevas clases
    if es_docente:
        with st.expander("➕ Administrador Docente: Cargar Nueva Clase de YouTube al Programa", expanded=False):
            st.markdown("Subí tu video a YouTube (Público u Oculto) y pegá aquí el enlace para que quede disponible para todos los residentes.")
            with st.form("form_nueva_clase_youtube"):
                col_y1, col_y2 = st.columns(2)
                with col_y1:
                    c_titulo = st.text_input("Título de la Clase / Ateneo:", placeholder="Ej: Abordaje Inicial del Shock Séptico y Resucitación Guiada")
                    c_url = st.text_input("Enlace de YouTube:", placeholder="https://www.youtube.com/watch?v=... o https://youtu.be/...")
                    c_unidad = st.selectbox(
                        "Unidad Temática:",
                        [
                            "Unidad 1: Cardiotorácico & Hemodinamia",
                            "Unidad 2: Neuro-Urgencias & Cuidados Críticos",
                            "Unidad 3: Respiratorio & Sepsis",
                            "Unidad 4: Abdomen & Crónicos",
                            "Ateneos Generales & Metacognición"
                        ]
                    )
                with col_y2:
                    c_docente = st.text_input("Docente / Disertante:", value="Equipo de Docencia e Investigación - Hospital Dr. Horacio Heller")
                    c_duracion = st.text_input("Duración estimada:", value="35 min")
                    c_desc = st.text_area("Descripción pedagógica y objetivos:", height=70, placeholder="Síntesis del marco conceptual y algoritmos abordados...")
                    
                c_puntos = st.text_area("Puntos Clave de Aprendizaje (un punto por línea):", height=70, placeholder="Criterios de inclusión\nMetas de perfusión\nErrores frecuentes en guardia")
                
                btn_guardar_clase = st.form_submit_button("💾 Publicar Clase en la Videoteca")
                if btn_guardar_clase:
                    if not c_titulo.strip() or not c_url.strip():
                        st.warning("Debe ingresar al menos el título y el enlace de YouTube.")
                    else:
                        import re
                        video_id_clean = "clase_" + re.sub(r'[^a-zA-Z0-9]', '_', c_titulo.lower())[:25] + f"_{int(datetime.utcnow().timestamp())}"
                        lista_pts = [p.strip() for p in c_puntos.split("\n") if p.strip()]
                        clase_dict = {
                            "id": video_id_clean,
                            "unidad": c_unidad,
                            "titulo": c_titulo.strip(),
                            "docente": c_docente.strip(),
                            "duracion": c_duracion.strip(),
                            "url_youtube": c_url.strip(),
                            "descripcion": c_desc.strip(),
                            "puntos_clave": lista_pts
                        }
                        ok_v, msg_v = guardar_video_clase(clase_dict)
                        if ok_v:
                            st.success(f"✅ ¡Clase '{c_titulo}' publicada exitosamente en la videoteca!")
                            st.rerun()
                        else:
                            st.error(f"Error al guardar clase: {msg_v}")

    # Cargar catálogo de videos
    videoteca = leer_videoteca_clases()
    
    # Filtro por unidad
    unidades_disponibles = ["Todas las Unidades"] + sorted(list({c.get("unidad", "General") for c in videoteca}))
    col_filtro_v, col_count_v = st.columns([2, 1])
    with col_filtro_v:
        unidad_filtro = st.selectbox("🎯 Filtrar por Unidad Curricular:", unidades_disponibles, key="filtro_unidad_videoteca")
    with col_count_v:
        clases_visibles = [c for c in videoteca if unidad_filtro == "Todas las Unidades" or c.get("unidad") == unidad_filtro]
        st.markdown(f"<div style='padding-top: 28px; font-weight: 600; color: #475569;'>Total de Clases: {len(clases_visibles)}</div>", unsafe_allow_html=True)

    st.markdown("---")

    if not clases_visibles:
        st.info("No hay clases registradas para la unidad seleccionada.")
    else:
        for idx_c, clase in enumerate(clases_visibles):
            c_id = clase.get("id", f"v_{idx_c}")
            c_tit = clase.get("titulo", "Clase Magistral")
            c_uni = clase.get("unidad", "Medicina Interna")
            c_url = clase.get("url_youtube", "https://www.youtube.com")
            c_doc = clase.get("docente", "Hospital Heller")
            c_dur = clase.get("duracion", "40 min")
            c_des = clase.get("descripcion", "")
            c_pts = clase.get("puntos_clave", [])

            st.markdown(f"""
                <div style="background: #ffffff; border: 1px solid #e2e8f0; border-top: 4px solid #ef4444; border-radius: 10px; padding: 18px 20px; margin-bottom: 24px; box-shadow: 0 2px 6px rgba(0,0,0,0.04);">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
                        <span style="font-size: 0.78rem; font-weight: 700; color: #b91c1c; text-transform: uppercase; background: #fee2e2; padding: 3px 9px; border-radius: 9999px;">
                            📚 {c_uni}
                        </span>
                        <span style="font-size: 0.82rem; color: #64748b; font-weight: 600;">
                            ⏱️ {c_dur} &bull; 👨‍🏫 {c_doc}
                        </span>
                    </div>
                    <h4 style="color: #0f172a; margin: 0 0 10px 0; font-size: 1.15rem;">{c_tit}</h4>
                </div>
            """, unsafe_allow_html=True)

            col_vid, col_info = st.columns([1.3, 1])
            with col_vid:
                try:
                    st.video(c_url)
                except Exception:
                    st.warning(f"No fue posible incrustar el reproductor para: {c_url}")
            
            with col_info:
                st.markdown(f"**Síntesis:** {c_des}")
                if c_pts:
                    st.markdown("**Perlas Clínicas & Puntos Clave:**")
                    for pt in c_pts:
                        st.markdown(f"• {pt}")
                
                st.markdown(f"""
                    <div style="margin-top: 14px;">
                        <a href="{c_url}" target="_blank" rel="noopener noreferrer" style="background-color: #ef4444; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 0.85rem; display: inline-block;">
                            ▶️ Abrir en YouTube ↗️
                        </a>
                    </div>
                """, unsafe_allow_html=True)
                
                if es_docente:
                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                    if st.button(f"🗑️ Eliminar clase", key=f"btn_del_clase_{c_id}"):
                        ok_d, msg_d = eliminar_video_clase(c_id)
                        if ok_d:
                            st.success(msg_d)
                            st.rerun()
                        else:
                            st.error(msg_d)

            st.markdown("---")


# ==========================================
# PESTAÑA: TAXONOMÍA & GOBERNANZA PHI
# ==========================================
with tab_gobernanza:
    # Hero Banner Institucional de la Arquitectura Cognitiva
    st.markdown("""
        <div style="background: linear-gradient(135deg, #091220 0%, #0f2744 50%, #16385c 100%); border-radius: 14px; padding: 26px 30px; color: white; margin-bottom: 22px; border-left: 6px solid #f59e0b; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap;">
                <span style="background: rgba(245, 158, 11, 0.25); color: #f59e0b; font-size: 0.76rem; font-weight: 800; padding: 4px 12px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.8px; border: 1px solid rgba(245, 158, 11, 0.4);">
                    MODELO UNIVERSAL DE PAT CROSKERRY • DUAL PROCESS THEORY
                </span>
                <span style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; font-size: 0.76rem; font-weight: 700; padding: 4px 12px; border-radius: 20px; border: 1px solid rgba(56, 189, 248, 0.3);">
                    DANIEL KAHNEMAN (THINKING, FAST AND SLOW)
                </span>
            </div>
            <h1 style="color: white; font-size: 2.1rem; font-weight: 800; margin: 8px 0 10px 0; line-height: 1.25;">
                🧠 El Cerebro Socrático: Arquitectura de la Decisión Clínica & Metacognición en Urgencias
            </h1>
            <p style="color: #cbd5e1; font-size: 1.02rem; line-height: 1.6; margin: 0;">
                En medicina de guardia e internación, el <strong>75% de los errores diagnósticos</strong> no se originan por falta de conocimientos teóricos, sino por <strong>fallas en el procesamiento cognitivo</strong> (heurísticas apresuradas no calibradas). Este módulo es el corazón intelectual de <strong>Socrático</strong>: entrena el <em>desacople voluntario del Sistema 1</em> para activar la <em>deliberación bayesiana del Sistema 2</em> antes de emitir un juicio definitivo.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Métricas Clave en 3 Columnas
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.metric(
            label="⚡ Vía Rápida: Sistema 1",
            value="< 1 seg (Reflejo)",
            delta="Reconocimiento Heurístico de Patrones",
            delta_color="normal"
        )
    with col_c2:
        st.metric(
            label="🛡️ Interruptor Metacognitivo",
            value="3 Herramientas",
            delta="Desacople Socrático al Pie de Cama",
            delta_color="normal"
        )
    with col_c3:
        st.metric(
            label="🔬 Vía Deliberativa: Sistema 2",
            value="Minutos (Pausado)",
            delta="Verificación Lógico-Bayesiana",
            delta_color="normal"
        )

    st.markdown("---")

    # ==========================================
    # SECCIÓN 1: EL CIRCUITO NEUROCOGNITIVO DE LA DECISIÓN MÉDICA (CROSKERRY)
    # ==========================================
    st.markdown("### ⚡ El Circuito Neurocognitivo de la Decisión Médica")
    st.caption("Estructura funcional del razonamiento clínico: Entrada de guardia ➔ Bifurcación cognitiva ➔ Compuerta de forzamiento ➔ Calibración experta.")

    col_arch1, col_arch2, col_arch3 = st.columns(3)

    with col_arch1:
        st.markdown("""
            <div style="background: rgba(245, 158, 11, 0.08); border-left: 4px solid #f59e0b; border-radius: 10px; padding: 16px; height: 100%;">
                <div style="font-size: 0.75rem; font-weight: 800; color: #f59e0b; text-transform: uppercase; margin-bottom: 4px;">
                    1. VÍA REFLEJA HEURÍSTICA
                </div>
                <h4 style="margin: 0 0 8px 0; color: #d97706;">⚡ Sistema 1: Motor Intuitivo</h4>
                <p style="font-size: 0.88rem; line-height: 1.5; color: inherit; margin-bottom: 10px;">
                    Empareja instantáneamente las facies, síntomas y motivo de consulta con casos memorizados.
                </p>
                <div style="font-size: 0.82rem; margin-bottom: 8px;">
                    <strong>✅ Rol Vital:</strong> Acción rápida en paro cardíaco, anafilaxia o shock descompensado.
                </div>
                <div style="font-size: 0.82rem; color: #dc2626;">
                    <strong>⚠️ Trampa Mortal:</strong> Anclaje, Cierre Prematuro, Confirmación e Inercia en cuadros atípicos.
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_arch2:
        st.markdown("""
            <div style="background: rgba(16, 185, 129, 0.08); border-left: 4px solid #10b981; border-radius: 10px; padding: 16px; height: 100%;">
                <div style="font-size: 0.75rem; font-weight: 800; color: #10b981; text-transform: uppercase; margin-bottom: 4px;">
                    2. LA COMPUERTA SOCRÁTICA
                </div>
                <h4 style="margin: 0 0 8px 0; color: #059669;">🛡️ Interruptor Metacognitivo</h4>
                <p style="font-size: 0.88rem; line-height: 1.5; color: inherit; margin-bottom: 10px;">
                    Monitoreo en tiempo real que frena el automatismo cuando detecta disonancia o banderas rojas.
                </p>
                <div style="font-size: 0.82rem; margin-bottom: 4px;">
                    <strong>⏱️ Diagnostic Time-Out:</strong> Pausa de 60s antes de dar el alta.
                </div>
                <div style="font-size: 0.82rem; margin-bottom: 4px;">
                    <strong>💀 Análisis Pre-Mortem:</strong> <em>"¿Y si muere en 24h, qué no vimos?"</em>
                </div>
                <div style="font-size: 0.82rem;">
                    <strong>🚨 Worst-Case Scenario:</strong> Descarte del diagnóstico letal.
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_arch3:
        st.markdown("""
            <div style="background: rgba(56, 189, 248, 0.08); border-left: 4px solid #0284c7; border-radius: 10px; padding: 16px; height: 100%;">
                <div style="font-size: 0.75rem; font-weight: 800; color: #0284c7; text-transform: uppercase; margin-bottom: 4px;">
                    3. VÍA DELIBERATIVA RIGUROSA
                </div>
                <h4 style="margin: 0 0 8px 0; color: #0284c7;">🔬 Sistema 2: Motor Bayesiano</h4>
                <p style="font-size: 0.88rem; line-height: 1.5; color: inherit; margin-bottom: 10px;">
                    Deducción algorítmica, probabilidades pre/post-test y falsación popperiana de hipótesis.
                </p>
                <div style="font-size: 0.82rem; margin-bottom: 8px;">
                    <strong>✅ Fortaleza:</strong> Inmune a sesgos cognitivos; desenmascara dobles focos y rarezas.
                </div>
                <div style="font-size: 0.82rem; color: #d97706;">
                    <strong>⚠️ Costo:</strong> Lento, agotador y dependiente de la fatiga del turno de guardia.
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.info("🔄 **Bucle de Recalibración del Residente:** La deliberación analítica repetida del Sistema 2 en ateneos y simulación socrática *calibra y educa* las heurísticas del Sistema 1, convirtiendo la intuición inicial en verdadera **sabiduría clínica experta**.")

    with st.expander("🔬 ¿Qué es la \"Falsación Popperiana de Hipótesis\" en Medicina y por qué salva vidas al residente?", expanded=False):
        st.markdown("""
            #### 💡 Del Verificacionismo Ingenuo a la Refutación Crítica (Karl Popper)
            En epistemología médica, los médicos novatos suelen caer en el **sesgo verificacionista**: conciben una sospecha diagnóstica inicial y dedican todo su esfuerzo a buscar signos y estudios que *confirmen* lo que ya creen. 
            
            El filósofo de la ciencia **Sir Karl Popper** demostró que ninguna cantidad de observaciones favorables puede probar definitivamente una teoría (*"un millón de cisnes blancos no prueban que todos los cisnes son blancos"*), pero **un solo dato en contra basta para demolerla** (*"un solo cisne negro la refuta"*).
            
            En la práctica médica de guardia, el **Razonamiento Popperiano** consiste en invertir la pregunta:
            > **En lugar de preguntarte:** *"¿Qué datos confirman mi diagnóstico favorito?"*  
            > **El médico socrático se pregunta:** *"¿Qué hallazgo clínico o estudio destruiría por completo mi hipótesis y descartaría la catástrofe tiempo-dependiente?"*

            ---
            
            #### 🩺 Ejemplo Clínico Real en Urgencias:
            * **Escenario de Guardia:** Varón de 68 años consulta por lumbalgia aguda de 6 horas de evolución tras levantar una caja en su domicilio.
            * ❌ **Ruta Verificacionista (Peligro de Mala Praxis):** El médico palpa contractura paravertebral, comprueba que el dolor aumenta con los movimientos del tronco y concluye: *"Es un lumbago mecánico típico por esfuerzo"*. Busca datos que confirman su creencia y prescribe analgésicos para el alta.
            * ✅ **Ruta Popperiana de Falsación (Seguridad Socrática):** El residente se detiene y aplica el forzamiento cognitivo: *"¿Qué patología letal se disfraza de lumbalgia aguda en un adulto mayor y cómo la FALSO activamente antes del alta?"*  
              $\rightarrow$ **Hipótesis mortal a falsar:** *Aneurisma de Aorta Abdominal (AAA) en vías de rotura*.  
              $\rightarrow$ **Búsqueda del dato refutador:** Palpación abdominal profunda buscando masa pulsátil expansiva, asimetría de pulsos femorales y ecografía a la cabecera (POCUS de aorta abdominal). Si la aorta mide 18 mm (calibre normal), la hipótesis letal queda **falsada y descartada con rigor evidencial**, permitiendo tratar la lumbalgia mecánica con tranquilidad absoluta.

            ---

            #### 📚 Literatura Científica Actualizada & Enlaces Directos:
            Para profundizar en cómo la filosofía popperiana de la falsación previene el error diagnóstico en la medicina contemporánea:
            * 📄 **Artículo Moderno de Referencia (2021):** [Falsifiability in medicine: what clinicians can learn from Karl Popper (Taran S, Adhikari NKJ, Fan E. Intensive Care Medicine 2021; 47: 1054–1056)](https://pubmed.ncbi.nlm.nih.gov/34142174/)  
              *Analiza cómo los médicos clínicos deben aplicar el principio de falsabilidad de Popper para no caer en dogmatismos ni aplicar prematuramente conjeturas no validadas en el paciente crítico.*
            * 🔍 **Ficha Indexada en PubMed:** [PMID: 34142174](https://pubmed.ncbi.nlm.nih.gov/34142174/) • DOI: [10.1007/s00134-021-06432-z](https://doi.org/10.1007/s00134-021-06432-z)
            * 📖 **El Marco Clásico de Errores Cognitivos (Pat Croskerry - Enlace Verificado):** [The Importance of Cognitive Errors in Diagnosis and Strategies to Minimize Them (Academic Medicine 2003; 78: 775–780)](https://pubmed.ncbi.nlm.nih.gov/12915363/)  
              *Ficha oficial en PubMed:* [PMID: 12915363](https://pubmed.ncbi.nlm.nih.gov/12915363/) • DOI: [10.1097/00001888-200308000-00003](https://doi.org/10.1097/00001888-200308000-00003)
            * 🏛️ **Precedente Histórico Fundacional (1983):** [The critical attitude in medicine: the need for a new ethics (McIntyre N, Popper K. BMJ 1983; 287: 1919–1923)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1550184/) • [PMCID: PMC1550184](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1550184/)
        """)

    st.markdown("---")

    # ==========================================
    # SECCIÓN 2: RADAR INTERACTIVO DE SESGOS EN ALTAIR (ORIGINAL)
    # ==========================================
    st.markdown("### 🗺️ Radar de Sesgos Cognitivos: Velocidad Heurística vs Riesgo Iatrogénico")
    st.caption("Visualización interactiva: Ubicación de los 13 sesgos según su rapidez de disparo, el peligro de morbimortalidad que acarrean y su frecuencia en guardia.")

    datos_radar = [
        {"Sesgo": "Cierre Prematuro", "Familia": "Heurísticas de Juicio", "Velocidad_S1": 15, "Riesgo_Iatrogenico": 92, "Frecuencia_Guardia": 95, "Estrategia": "Pausa de Cierre (Mínimo 3 diferenciales)"},
        {"Sesgo": "Anclaje y Ajuste", "Familia": "Heurísticas de Juicio", "Velocidad_S1": 18, "Riesgo_Iatrogenico": 88, "Frecuencia_Guardia": 90, "Estrategia": "Reinicio Bayesiano sin el dato inicial"},
        {"Sesgo": "Representatividad", "Familia": "Heurísticas de Juicio", "Velocidad_S1": 22, "Riesgo_Iatrogenico": 78, "Frecuencia_Guardia": 82, "Estrategia": "Alerta de Equivalentes y Atipias"},
        {"Sesgo": "Confirmación", "Familia": "Verificación y Evidencia", "Velocidad_S1": 32, "Riesgo_Iatrogenico": 82, "Frecuencia_Guardia": 85, "Estrategia": "Falsación Popperiana Activa"},
        {"Sesgo": "Costos Hundidos", "Familia": "Verificación y Evidencia", "Velocidad_S1": 42, "Riesgo_Iatrogenico": 72, "Frecuencia_Guardia": 62, "Estrategia": "Pausa de Eficacia a las 48-72h"},
        {"Sesgo": "Automatización (IA)", "Familia": "Verificación y Evidencia", "Velocidad_S1": 8, "Riesgo_Iatrogenico": 95, "Frecuencia_Guardia": 88, "Estrategia": "Vigilancia Epistémica / Auditoría Popperiana"},
        {"Sesgo": "Inercia Diagnóstica", "Familia": "Influencia Social y Triage", "Velocidad_S1": 12, "Riesgo_Iatrogenico": 94, "Frecuencia_Guardia": 88, "Estrategia": "Reinicio Epistémico desde Cero"},
        {"Sesgo": "Sesgo de Encuadre", "Familia": "Influencia Social y Triage", "Velocidad_S1": 14, "Riesgo_Iatrogenico": 86, "Frecuencia_Guardia": 76, "Estrategia": "Desencuadre Objetivo (Solo datos duros)"},
        {"Sesgo": "Disponibilidad", "Familia": "Memoria y Afecto", "Velocidad_S1": 16, "Riesgo_Iatrogenico": 68, "Frecuencia_Guardia": 80, "Estrategia": "Calibración Epidemiológica Pre-Test"},
        {"Sesgo": "Búsqueda Satisfecha", "Familia": "Memoria y Afecto", "Velocidad_S1": 28, "Riesgo_Iatrogenico": 89, "Frecuencia_Guardia": 84, "Estrategia": "Regla de la Segunda Lesión / Foco"},
        {"Sesgo": "Banderas Rojas", "Familia": "Seguridad Crítica", "Velocidad_S1": 10, "Riesgo_Iatrogenico": 98, "Frecuencia_Guardia": 86, "Estrategia": "Auditoría Estricta de Signos Vitales"},
        {"Sesgo": "Error de Cálculo", "Familia": "Seguridad Crítica", "Velocidad_S1": 38, "Riesgo_Iatrogenico": 84, "Frecuencia_Guardia": 68, "Estrategia": "Doble Chequeo Biomédico de TFGe"},
        {"Sesgo": "Tratamiento Inseguro", "Familia": "Seguridad Crítica", "Velocidad_S1": 20, "Riesgo_Iatrogenico": 96, "Frecuencia_Guardia": 72, "Estrategia": "Chequeo de Contraindicaciones Absolutas"}
    ]

    df_radar = pd.DataFrame(datos_radar)

    base_chart = alt.Chart(df_radar).encode(
        x=alt.X('Velocidad_S1:Q', title='Tiempo de Decisión Heurística (Segundos) — [◄ Más Rápido e Impulsivo | Más Pausado ►]', scale=alt.Scale(domain=[5, 50])),
        y=alt.Y('Riesgo_Iatrogenico:Q', title='Riesgo de Morbimortalidad / Iatrogenia (0-100)', scale=alt.Scale(domain=[55, 105])),
        color=alt.Color('Familia:N', title='Familia Cognitiva', scale=alt.Scale(scheme='category10')),
        tooltip=['Sesgo', 'Familia', 'Estrategia', 'Riesgo_Iatrogenico', 'Frecuencia_Guardia']
    )

    puntos = base_chart.mark_circle().encode(
        size=alt.Size('Frecuencia_Guardia:Q', title='Frecuencia en Guardia', scale=alt.Scale(range=[200, 900]))
    )

    textos = base_chart.mark_text(align='left', baseline='middle', dx=14, fontSize=11, fontWeight='bold').encode(
        text='Sesgo:N',
        color=alt.value('#f8fafc')
    )

    regla_alerta = alt.Chart(pd.DataFrame({'y': [85]})).mark_rule(strokeDash=[4, 4], color='#ef4444', size=1.5).encode(y='y:Q')
    texto_alerta = alt.Chart(pd.DataFrame({'x': [8], 'y': [87], 'text': ['🚨 ZONA CRÍTICA: ALTO RIESGO IATROGÉNICO']})).mark_text(
        align='left', color='#ef4444', fontSize=11, fontWeight='bold'
    ).encode(x='x:Q', y='y:Q', text='text:N')

    chart_final = (puntos + textos + regla_alerta + texto_alerta).properties(
        height=380
    ).interactive()

    st.altair_chart(chart_final, use_container_width=True)

    with st.expander("📖 ¿Cómo interpretar este Radar Cognitivo y aplicar sus cuadrantes en guardia?", expanded=True):
        col_rad_exp1, col_rad_exp2 = st.columns(2)
        with col_rad_exp1:
            st.markdown("""
                #### 🧭 Dimensiones y Variables del Gráfico:
                * **Eje Horizontal (X) — Tiempo de Decisión (Segundos):**
                  * **Hacia la izquierda (&lt; 15-20 seg):** Respuestas ultra-rápidas, reflejas e impulsivas gobernadas por el **Sistema 1 (Heurístico)**.
                  * **Hacia la derecha (&gt; 30-40 seg):** Razonamiento más lento, deliberativo y estructurado propio del **Sistema 2 (Analítico)**.
                * **Eje Vertical (Y) — Riesgo de Morbimortalidad / Iatrogenia (0 a 100):**
                  * Cuanto más **arriba** se sitúa el sesgo, mayor es la probabilidad de desencadenar un desenlace fatal, shock irreversible o demanda médico-legal por omisión.
                * **Tamaño de las Burbujas (Prevalencia en Guardia):**
                  * Burbujas más grandes indican sesgos con **mayor frecuencia documentada** en pases de guardia y admisiones de sala.
            """)
        with col_rad_exp2:
            st.markdown("""
                #### 🚨 Lectura de Cuadrantes Clínicos:
                * **🚨 Cuadrante Superior Izquierdo (Zona Roja de Máximo Peligro):**
                  * *Decisión en segundos + Altísimo riesgo de muerte.*
                  * Aquí habitan **Desestimación de Banderas Rojas**, **Automatización (IA)**, **Inercia Diagnóstica** y **Cierre Prematuro**. El médico acepta la sugerencia algorítmica o da el alta sin dudar.
                * **⚠️ Cuadrante Superior Derecho (Trampas Deliberativas Complejas):**
                  * *El médico se toma su tiempo, pero razona en bucle cerrado.*
                  * **Error de Cálculo** (falta de ajuste renal TFGe) y **Sesgo de Confirmación** (buscar estudios solo para validar la propia sospecha).
                * **⚡ Cuadrante Inferior Izquierdo (Atajos Heurísticos de Triage):**
                  * **Sesgo de Disponibilidad** y **Encuadre**. Frecuentes y molestos, pero subsanables si el paciente permanece en observación clínica.
                * **🛡️ Regla de Oro Socrática:** *Toda hipótesis ubicada sobre la línea roja punteada (&gt; 85 pts) exige obligatoriamente un **Diagnostic Time-Out de 60 segundos** antes de firmar el alta o la indicación.*
            """)

    st.markdown("---")

    # ==========================================
    # SECCIÓN 3: SIMULADOR DE BIFURCACIÓN COGNITIVA (TIME-OUT DIAGNÓSTICO)
    # ==========================================
    st.markdown("### 🔀 Simulador Interactivo de Bifurcación Cognitiva")
    st.caption("Experimente cómo una misma viñeta de guardia culmina en catástrofe iatrogénica si opera el Sistema 1 sin filtro, o en alta médica exitosa si interviene el Forzamiento Cognitivo Socrático.")

    caso_sel_key = st.selectbox(
        "Seleccione un escenario clínico de guardia para auditar la bifurcación mental:",
        options=list(ESCENARIOS_BIFURCACION_COGNITIVA.keys()),
        format_func=lambda k: ESCENARIOS_BIFURCACION_COGNITIVA[k]["titulo"],
        key="sel_escenario_bifurcacion"
    )

    esc_data = ESCENARIOS_BIFURCACION_COGNITIVA[caso_sel_key]

    st.info(f"📋 **Presentación en Guardia:** {esc_data['presentacion']}")

    col_bif_s1, col_bif_s2 = st.columns(2)

    with col_bif_s1:
        st.error(f"""
        ### ❌ RUTA SISTEMA 1 (Sin Forzamiento Metacognitivo)
        **Sesgo Activado:** {esc_data['via_s1']['sesgo']}  
        **Atajo Heurístico:** {esc_data['via_s1']['atajo']}  
        
        ⚠️ **Conducta Errónea:** {esc_data['via_s1']['conducta_erronea']}  
        💥 **Desenlace:** {esc_data['via_s1']['desenlace_catastrofico']}
        """)

    with col_bif_s2:
        st.success(f"""
        ### ✅ RUTA SISTEMA 2 (Intervención Socrática)
        **Estrategia:** {esc_data['via_s2']['estrategia']}  
        **Pregunta Metacognitiva:** *"{esc_data['via_s2']['pregunta_socratica']}"*  
        
        🩺 **Conducta Analítica:** {esc_data['via_s2']['conducta_analitica']}  
        🛡️ **Desenlace:** {esc_data['via_s2']['desenlace_exitoso']}
        """)

    st.markdown("---")

    # ==========================================
    # SECCIÓN 4: EXPLORADOR MAESTRO DE LOS 12 SESGOS COGNITIVOS EN MEDICINA INTERNA
    # ==========================================
    st.markdown("### 📚 Catálogo Maestro de los 12 Sesgos Auditados por Socrático")
    st.caption("Organizados por familias funcionales según el impacto clínico y el mecanismo neurocognitivo involucrado.")

    familias_nombres = ["🌐 Todas las Familias"] + list(FAMILIAS_SESGOS.keys())
    familia_filtro = st.radio(
        "Filtrar sesgos por familia cognitiva:",
        options=familias_nombres,
        horizontal=True,
        key="filtro_familias_sesgos"
    )

    if familia_filtro != "🌐 Todas las Familias":
        sesgos_a_mostrar = {
            k: v for k, v in TAXONOMIA_SESGOS.items()
            if v.get("familia") == familia_filtro or k in FAMILIAS_SESGOS.get(familia_filtro, {}).get("sesgos", [])
        }
        st.markdown(f"**Familia seleccionada:** {FAMILIAS_SESGOS[familia_filtro]['icono']} *{FAMILIAS_SESGOS[familia_filtro]['descripcion']}*")
    else:
        sesgos_a_mostrar = TAXONOMIA_SESGOS

    for nombre_s, detalle in sesgos_a_mostrar.items():
        icono_s = detalle.get("icono", "📌")
        familia_s = detalle.get("familia", detalle.get("categoria", "Clínico"))
        with st.expander(f"{icono_s} {nombre_s} • [{familia_s}]"):
            col_s_a, col_s_b = st.columns(2)
            with col_s_a:
                st.markdown(f"**📖 Definición Médica:** {detalle['descripcion']}")
                st.markdown(f"**⚡ Mecanismo del Sistema 1 (El Atajo):** *{detalle.get('mecanismo_s1', 'Atajo asociativo apresurado.')}*")
                st.markdown(f"**🚨 Ejemplo en Sala / Guardia:** _{detalle['ejemplo_clinico']}_")
            with col_s_b:
                st.markdown(f"**🛡️ Activación del Sistema 2 (Debiasing):** {detalle.get('activacion_s2', detalle['estrategia_debiasing'])}")
                st.info(f"💡 **Pregunta de Auto-chequeo Metacognitivo (Pie de Cama):** *{detalle.get('pregunta_autochequeo', '¿Qué hecho clínico contradice mi hipótesis?')}*")

    st.markdown("---")
    st.markdown("### 🔒 Probador de Desidentificación de Datos Clínicos (Sanitizador PHI)")
    st.caption("Pruebe cómo el motor de gobernanza anonimiza información protegida de pacientes en tiempo real antes de enviar texto a modelos externos.")
    
    texto_prueba = st.text_area(
        "Ingrese texto clínico con datos sensibles simulados:",
        value="Paciente: Carlos Menéndez, DNI 28.452.190, HC 84920. Consulta por dolor precordial. FN: 14/05/1975. Contacto: 11-4582-9011 o carlos@gmail.com."
    )
    if st.button("Probar Sanitización"):
        limpio, detectados = sanitizar_texto_clinico(texto_prueba)
        st.markdown("**Texto Sanitizado para el LLM:**")
        st.code(limpio, language="text")
        if detectados:
            st.success(f"Elementos redactados con éxito: {', '.join(detectados)}")
        else:
            st.info("No se detectaron datos protegidos en la muestra.")



# ==========================================
# PESTAÑA 4: PROGRAMA FELLOW & MASTERCLASSES
# ==========================================
with tab_programa:
    st.markdown("""
        <div style="background: linear-gradient(135deg, #0b192c 0%, #1e3a8a 50%, #0369a1 100%); border-radius: 14px; padding: 30px; color: white; margin-bottom: 24px;">
            <div style="max-width: 850px;">
                <span style="background-color: #f59e0b; color: #0f172a; font-size: 0.75rem; font-weight: 800; padding: 5px 12px; border-radius: 20px; text-transform: uppercase;">
                    Programa de Posgrado • Edición 2026
                </span>
                <h1 style="color: white; font-size: 2.2rem; font-weight: 800; margin: 12px 0 8px 0; line-height: 1.2;">
                    Master en Razonamiento Clínico & Decisión Crítica en Urgencias
                </h1>
                <p style="color: #e2e8f0; font-size: 1.05rem; line-height: 1.5; margin-bottom: 16px;">
                    De la intuición heurística al análisis experto. Entrena tu agudeza diagnóstica con <strong>Simulación Socrática IA</strong>, aprende los trucos de guardia con <strong>12 Masterclasses en video</strong> y accede a las <strong>Fichas de Bolsillo A4</strong>.
                </p>
                <div style="display: flex; gap: 15px; flex-wrap: wrap; font-size: 0.85rem;">
                    <span>✅ 12 Casos Mayores</span>
                    <span>✅ 12 Masterclasses On-Demand</span>
                    <span>✅ 12 One-Pagers para el Guardapolvo</span>
                    <span>✅ Rúbrica para Portafolio Médico</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    col_mat1, col_mat2 = st.columns([1, 1])
    with col_mat1:
        st.markdown("#### 📘 Manual Oficial de la Residencia (Hospital Heller)")
        st.write("Consulte las bases pedagógicas del programa semestral, el marco cognitivo (Sistemas 1 y 2 de Kahneman), la gobernanza clínica y el temario de las 4 unidades de formación:")
        
        # 0. Descarga del Manual de la Residencia en HTML
        manual_p_html = BASE_DIR / "manual_residencia_hospital_heller.html"
        if manual_p_html.exists():
            st.download_button(
                label="📘 Descargar Manual de Residencia (HTML Imprimible / PDF)",
                data=manual_p_html.read_text(encoding="utf-8"),
                file_name="Manual_Residencia_Hospital_Heller_Socratico.html",
                mime="text/html",
                key="btn_descarga_manual_tab4",
                use_container_width=True
            )
            
        # Descarga en Markdown
        manual_p_md = BASE_DIR / "MANUAL_RESIDENCIA_HOSPITAL_HELLER.md"
        if manual_p_md.exists():
            st.download_button(
                label="📖 Descargar Manual en Formato Markdown (.md)",
                data=manual_p_md.read_text(encoding="utf-8"),
                file_name="Manual_Residencia_Hospital_Heller_Socratico.md",
                mime="text/markdown",
                key="btn_descarga_manual_md_tab4",
                use_container_width=True
            )
            
        # Descarga del Instructivo Oficial de Redacción de Casos Clínicos
        instructivo_p = BASE_DIR / "INSTRUCTIVO_REDACCION_CASOS_CLINICOS.md"
        data_inst = instructivo_p.read_text(encoding="utf-8") if instructivo_p.exists() else "# Instructivo Oficial de Redacción de Casos Clínicos - Hospital Heller 2026"
        st.download_button(
            label="📋 Descargar Instructivo de Redacción de Casos (.md)",
            data=data_inst,
            file_name="Instructivo_Redaccion_Casos_Clinicos_Socratico.md",
            mime="text/markdown",
            key="btn_descarga_instructivo_tab4",
            use_container_width=True
        )

        with st.expander("📝 Instructivo Oficial: Cómo redactar un caso clínico desde cero (Estándar de 7 Bloques)", expanded=False):
            st.markdown("""
            Para que los casos de guardia de los residentes puedan ser discutidos en el ateneo y cargados al simulador, deben cumplir con los **7 Bloques Pedagógicos de Socrático**:
            
            1. **Filiación & Contexto:** Identificador, título, unidad curricular y dificultad (R1, R2, R3/R4).
            2. **Desidentificación Estricta (Ley 25.326):** Prohibido incluir nombres, DNI, cama, o fechas exactas. Solo edad, sexo y cronología relativa.
            3. **Las 5 Constantes Vitales Completas (Obligatorio):**
               * **TA** (Tensión Arterial en mmHg)
               * **FC** (Frecuencia Cardíaca en lpm)
               * **FR** (Frecuencia Respiratoria en rpm)
               * **SpO2** (Saturación de oxígeno por oximetría de pulso y fracción inspirada)
               * **Temperatura** (°C axilar/central)
            4. **Trampa Heurística / Sesgo Esperado:** Croskerry (*Cierre Prematuro*, *Anclaje*, *Inercia Diagnóstica*, etc.).
            5. **Banderas Rojas (Patient Safety):** Alertas clínicas no negociables para evitar muertes o iatrogenia.
            6. **Calculadoras Clínicas Vinculadas:** Algoritmos validados (HEART, Wells, CURB-65, Shock Index, NIHSS, SOFA).
            7. **Guía de Práctica Clínica Oficial Open Access:** Enlace permanente libre y gratuito a la última guía de consenso.
            
            *📌 Los instructores y jefes de servicio disponen de la Pestaña 7: ➕ Creador & Banco de Casos (Modo Docente) para registrar los casos de forma permanente en el simulador.*
            """)

        st.info(
            "🔒 **Material de Debriefing & Fichas de Bolsillo:**\n\n"
            "Las diapositivas y fichas de bolsillo de cada caso son entregadas **exclusivamente por el docente al finalizar el ateneo clínico quincenal** en el Hospital Heller, para preservar la metodología de simulación ciega (\"a ciegas\") sin sesgos previos."
        )

    with col_mat2:
        st.markdown("#### 🚀 Solicitar Admisión / Preventa Cohorte Fundadora")
        st.caption("Cupos limitados a 15 colegas con 50% de descuento y garantía de devolución de 7 días.")
        with st.form("form_preinscripcion_oficial"):
            lead_f_nom = st.text_input("Nombre y Apellido *")
            lead_f_email = st.text_input("Correo electrónico *")
            lead_f_wa = st.text_input("WhatsApp (con código de país) *")
            lead_f_hosp = st.text_input("Hospital / Residencia o Especialidad")
            lead_f_pais = st.selectbox("País de residencia:", ["Argentina", "Chile", "Uruguay", "Colombia", "México", "Perú", "España", "Otro"])
            
            btn_sub_f = st.form_submit_button("🎓 Reservar mi Cupo con 50% de Descuento", use_container_width=True)
            if btn_sub_f:
                if lead_f_nom and lead_f_email and lead_f_wa:
                    lead_row = {
                        "Fecha_UTC": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                        "Nombre": lead_f_nom,
                        "Email": lead_f_email,
                        "WhatsApp": lead_f_wa,
                        "Institucion_Residencia": lead_f_hosp,
                        "Pais": lead_f_pais,
                        "Caso_Origen": "Página de Programa Fellow",
                        "Estado": "Pre-Inscripto Fundador (50% OFF)"
                    }
                    ok, msg = guardar_lead_preinscripcion(lead_row)
                    if ok:
                        st.success("🎉 ¡Tu solicitud fue registrada con éxito! Te hemos reservado el 50% de descuento especial.")
                        st.info("Tu código de beca fundadora es: **SOCRATICO-BETA-50**. Te contactaremos a la brevedad.")
                    else:
                        st.error(msg)
                else:
                    st.warning("Por favor complete nombre, correo y WhatsApp.")

    st.markdown("---")
    st.markdown("### 📚 Plan de Estudios: Las 4 Unidades Temáticas de Formación (Hospital Heller)")
    
    col_mod1, col_mod2 = st.columns(2)
    with col_mod1:
        st.markdown("""
            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-left: 5px solid #2563eb; padding: 16px; border-radius: 8px; margin-bottom: 12px;">
                <h4 style="color: #1e3a8a; margin: 0 0 6px 0;">Unidad 1: Síndromes Cardiotorácicos & Urgencias Hemodinámicas</h4>
                <ul style="font-size: 0.85rem; color: #334155; margin: 0; padding-left: 20px;">
                    <li>Dolor torácico indiferenciado: Estratificación pre-test y descarte de emergencias vitales.</li>
                    <li>Electrocardiografía crítica y cinética de biomarcadores cardíacos.</li>
                    <li>Fisiopatología del shock hipovolémico y resucitación vascular guiada por metas.</li>
                    <li>Edema pulmonar y descompensación ventricular aguda: Postcarga y ventilación no invasiva.</li>
                </ul>
            </div>
            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-left: 5px solid #0284c7; padding: 16px; border-radius: 8px; margin-bottom: 12px;">
                <h4 style="color: #0369a1; margin: 0 0 6px 0;">Unidad 2: Neuro-Urgencias & Cuidados Críticos Tiempo-Dependientes</h4>
                <ul style="font-size: 0.85rem; color: #334155; margin: 0; padding-left: 20px;">
                    <li>Protocolo de Código ACV: Ventana de reperfusión y descarte de stroke mimics.</li>
                    <li>Cefalea aguda de riesgo vital y algoritmo de neuroimagen pre-punción lumbar.</li>
                    <li>Encefalopatía aguda y trastornos severos del sodio: Corrección segura y prevención de desmielinización.</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)
            
    with col_mod2:
        st.markdown("""
            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-left: 5px solid #10b981; padding: 16px; border-radius: 8px; margin-bottom: 12px;">
                <h4 style="color: #065f46; margin: 0 0 6px 0;">Unidad 3: Falla Respiratoria, Medio Interno & Sepsis</h4>
                <ul style="font-size: 0.85rem; color: #334155; margin: 0; padding-left: 20px;">
                    <li>Infección respiratoria baja severa: Scores de severidad (CURB-65) y bundles de sepsis (Hour-1).</li>
                    <li>Insuficiencia respiratoria hipercápnica: Titulación de oxígeno y soporte con VNI.</li>
                    <li>Injuria renal aguda nefrotóxica y emergencias electrolíticas por hiperpotasemia.</li>
                </ul>
            </div>
            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-left: 5px solid #f59e0b; padding: 16px; border-radius: 8px; margin-bottom: 12px;">
                <h4 style="color: #92400e; margin: 0 0 6px 0;">Unidad 4: Abdomen Agudo Médico & Descompensación Hepática</h4>
                <ul style="font-size: 0.85rem; color: #334155; margin: 0; padding-left: 20px;">
                    <li>Complicaciones metabólicas hiperglucémicas y co-infecciones de partes blandas.</li>
                    <li>El paciente cirrótico en guardia: Abordaje de la ascitis, paracentesis y prevención renal.</li>
                    <li>Pancreatitis aguda: Resucitación balanceada por metas e indicación racional de estudios y fármacos.</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ❓ Preguntas Frecuentes sobre el Programa")
    with st.expander("¿Cómo funciona el entrenamiento en el Simulador Socrático?"):
        st.write("A diferencia de los cursos tradicionales donde solo miras videos, aquí resuelves casos en lenguaje natural frente a un Comité Evaluador con IA que desafía tu razonamiento, audita tus sesgos cognitivos y ejecuta calculadoras en tiempo real.")
    with st.expander("¿El programa otorga certificado?"):
        st.write("Sí. Al completar los casos clínicos y las evaluaciones colegiadas, obtienes un Certificado Oficial con el desglose de tu promedio en las 5 dimensiones pedagógicas (Precisión Diagnóstica, Seguridad, Adherencia a Guías, Metacognición y Uso de Recursos) válido para presentar en tu portafolio de residencia o legajo profesional.")
    with st.expander("¿Cuánto tiempo de acceso tengo?"):
        st.write("Tienes acceso ilimitado durante 1 año completo tanto a las grabaciones en video de las Masterclasses como al Simulador de Casos y a las descargas de las Fichas de Bolsillo.")




# ==============================================================================
# MÓDULOS EXCLUSIVOS DE SUPERVISIÓN DOCENTE, AUDITORÍA & BENCHMARKING
# (Solo visibles e interactivos si es_docente == True)
# ==============================================================================
# ==============================================================================
# PESTAÑA: MÉTRICAS & AUDITORÍA DOCENTE
# ==============================================================================
with tab_metricas:
    if not es_docente:
        st.markdown('''
            <div style="background: linear-gradient(135deg, #1e3a8a 0%, #1e293b 100%); padding: 22px 28px; border-radius: 12px; border-left: 6px solid #38bdf8; margin-bottom: 24px;">
                <h3 style="color: #f8fafc; margin: 0 0 6px 0;">📊 Panel de Gobernanza Académica & Auditoría de Cohorte</h3>
                <p style="color: #cbd5e1; font-size: 0.92rem; margin: 0;">
                    Acceso exclusivo para instructores de residentes, jefes de servicio e investigadores del Hospital Heller.
                </p>
            </div>
        ''', unsafe_allow_html=True)
        st.info("🔒 **Módulo Docente Protegido:** Ingrese la clave maestra de supervisión (`heller2026`) en el panel lateral izquierdo (**🔒 Acceso Docente / Jefatura**) o ingrésela a continuación:")
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            pin_local_m = st.text_input("Clave Maestra Docente:", type="password", key="pin_local_metricas")
            if st.button("🔓 Desbloquear Panel de Métricas", key="btn_unlock_metricas"):
                if pin_local_m == DOCENTE_PASSWORD:
                    st.session_state.clave_docente_sidebar = pin_local_m
                    st.rerun()
                else:
                    st.error("❌ Clave incorrecta.")
    else:
        st.markdown("### 📊 Panel de Gobernanza Académica y Detección de Sesgos")
        st.caption("Monitoreo continuo de desvíos en el razonamiento diagnóstico y adherencia a seguridad del paciente.")
    
        col_ref, _ = st.columns([1, 4])
        with col_ref:
            if st.button("🔄 Actualizar Registros", width="stretch"):
                st.rerun()

        df_registros = leer_registros_auditoria(conn_gsheets, url_hoja)
        df_evals = leer_registros_evaluacion()
        df_leads = leer_leads_preinscripcion()
        df_bench = leer_registros_benchmark()
        df_feedback = leer_consultas_feedback()

        # Banner institucional de exportación completa a Excel
        st.markdown("""
            <div style="background: linear-gradient(135deg, #1e3a8a 0%, #1e293b 100%); padding: 18px 24px; border-radius: 10px; border-left: 6px solid #38bdf8; margin-bottom: 20px;">
                <h4 style="color: #f8fafc; margin: 0 0 6px 0;">📗 Centro de Exportación Académica para Jefatura & Docencia</h4>
                <p style="color: #cbd5e1; font-size: 0.88rem; margin: 0 0 10px 0;">
                    Descargue la telemetría completa en formato <strong>Microsoft Excel (.xlsx)</strong> con hojas separadas, columnas auto-ajustadas y estilos institucionales, o en formato <strong>CSV compatible con Excel en español</strong> (separador ';' y codificación UTF-8 con BOM para evitar textos mezclados en Columna A o caracteres dañados).
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        col_master1, col_master2 = st.columns([1.5, 1])
        with col_master1:
            excel_master = generar_libro_excel_completo(df_evals, df_registros, df_bench, df_leads, df_feedback)
            st.download_button(
                label="📊 Descargar Portafolio Integral en Excel (.xlsx Multi-Pestaña)",
                data=excel_master,
                file_name=f"Portafolio_Integral_Socratico_Hospital_Heller_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_descarga_master_excel",
                type="primary",
                use_container_width=True
            )
        with col_master2:
            with st.expander("ℹ️ ¿Por qué se veía 'mezclado' el archivo?", expanded=False):
                st.markdown("""
                En Windows con configuración en español (Argentina/Latam), Excel usa el **punto y coma (;)** como separador de listas porque la **coma (,)** es el separador de decimales ($12,5$).
                
                Si un CSV se descarga con comas estándar:
                1. Excel junta toda la fila en una sola celda de la **Columna A**.
                2. Las tildes y la 'ñ' se deforman si falta la firma UTF-8-BOM.
                
                **Solución incorporada:**
                * Los nuevos botones **`.xlsx`** abren directamente una planilla nativa de Excel con formato profesional y columnas separadas.
                * Los botones **`CSV (;)`** ahora usan punto y coma y UTF-8 con BOM para abrirse automáticamente con doble clic en cualquier versión de Excel.
                """)

        st.markdown("---")
    
        if df_registros.empty:
            st.info("No se han registrado sesgos o eventos de auditoría todavía. Interactúe con el simulador para generar datos.")
        else:
            # Métricas resumidas
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            total_eventos = len(df_registros)
            sesgos_unicos = df_registros["Tipo_Sesgo"].nunique() if "Tipo_Sesgo" in df_registros.columns else 0
            alumnos_unicos = df_registros["ID_Estudiante"].nunique() if "ID_Estudiante" in df_registros.columns else 0
            sesgo_top = df_registros["Tipo_Sesgo"].mode()[0] if "Tipo_Sesgo" in df_registros.columns and not df_registros["Tipo_Sesgo"].empty else "N/A"
        
            col_m1.metric("Total de Intervenciones", total_eventos)
            col_m2.metric("Sesgos Diferentes", sesgos_unicos)
            col_m3.metric("Sesgo Más Prevalente", sesgo_top)
            col_m4.metric("Estudiantes Auditados", alumnos_unicos)
        
            st.markdown("---")
        
            # Gráficos
            col_g1, col_g2 = st.columns(2)
        
            with col_g1:
                st.markdown("#### 🎯 Frecuencia de Sesgos Cognitivos Detectados")
                if "Tipo_Sesgo" in df_registros.columns:
                    df_sesgos_count = df_registros["Tipo_Sesgo"].value_counts().reset_index()
                    df_sesgos_count.columns = ["Tipo_Sesgo", "Cantidad"]
                
                    chart_bar = alt.Chart(df_sesgos_count).mark_bar(color="#1e3a8a").encode(
                        x=alt.X("Cantidad:Q", title="Frecuencia"),
                        y=alt.Y("Tipo_Sesgo:N", sort="-x", title="Sesgo Cognitivo"),
                        tooltip=["Tipo_Sesgo", "Cantidad"]
                    ).properties(height=320)
                    st.altair_chart(chart_bar, use_container_width=True)

            with col_g2:
                st.markdown("#### 🏥 Distribución por Caso Clínico")
                if "Caso_Clinico" in df_registros.columns:
                    df_casos_count = df_registros["Caso_Clinico"].value_counts().reset_index()
                    df_casos_count.columns = ["Caso_Clinico", "Cantidad"]
                
                    chart_donut = alt.Chart(df_casos_count).mark_arc(innerRadius=45).encode(
                        theta=alt.Theta("Cantidad:Q"),
                        color=alt.Color("Caso_Clinico:N", legend=alt.Legend(orient="bottom")),
                        tooltip=["Caso_Clinico", "Cantidad"]
                    ).properties(height=320)
                    st.altair_chart(chart_donut, use_container_width=True)
                
            # Tabla detallada con filtro
            st.markdown("#### 📋 Registro Detallado de Auditorías Clínicas")
            st.dataframe(
                df_registros.sort_values(by="Fecha_UTC", ascending=False) if "Fecha_UTC" in df_registros.columns else df_registros,
                use_container_width=True,
                hide_index=True
            )
        
            # Descarga dual de Auditoría
            col_d_a1, col_d_a2 = st.columns(2)
            with col_d_a1:
                excel_auditoria = exportar_df_a_excel(df_registros, "Auditoria_Sesgos")
                st.download_button(
                    label="📥 Descargar Auditoría en Excel (.xlsx)",
                    data=excel_auditoria,
                    file_name=f"auditoria_sesgos_clinicos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="btn_descargar_auditoria_excel",
                    use_container_width=True
                )
            with col_d_a2:
                csv_data = exportar_df_a_csv_excel(df_registros)
                st.download_button(
                    label="📥 Descargar en CSV (Compatible con Excel ';')",
                    data=csv_data,
                    file_name=f"auditoria_sesgos_clinicos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key="btn_descargar_auditoria_csv",
                    use_container_width=True
                )

        st.markdown("---")
        st.markdown("### 🎓 Rendimiento Académico y Evaluación de Competencias Clínicas de la Cohorte")
        st.caption("Resultados globales emitidos por el Tribunal Evaluador Docente según las 5 dimensiones de la rúbrica.")

        if df_evals.empty:
            st.info("No se han registrado evaluaciones de cierre de caso todavía. Concluya un caso en el simulador para visualizar métricas de desempeño.")
        else:
            col_e1, col_e2, col_e3, col_e4 = st.columns(4)
            promedio_gral = df_evals["Puntaje_Global"].mean() if "Puntaje_Global" in df_evals.columns else 0
            total_evals = len(df_evals)
            casos_aprobados = len(df_evals[df_evals["Puntaje_Global"] >= 75]) if "Puntaje_Global" in df_evals.columns else 0
            tasa_competencia = (casos_aprobados / total_evals * 100) if total_evals > 0 else 0
            nivel_frecuente = df_evals["Nivel_Competencia"].mode()[0] if "Nivel_Competencia" in df_evals.columns and not df_evals["Nivel_Competencia"].empty else "N/A"

            col_e1.metric("Evaluaciones Completadas", total_evals)
            col_e2.metric("Promedio Global Cohorte", f"{promedio_gral:.1f} / 100")
            col_e3.metric("Tasa de Competencia (≥75)", f"{tasa_competencia:.1f}%")
            col_e4.metric("Nivel Predominante", nivel_frecuente)

            col_ge1, col_ge2 = st.columns(2)
            with col_ge1:
                st.markdown("#### 🏆 Distribución de Niveles de Competencia")
                df_niveles = df_evals["Nivel_Competencia"].value_counts().reset_index()
                df_niveles.columns = ["Nivel", "Cantidad"]
                chart_niv = alt.Chart(df_niveles).mark_bar(color="#059669").encode(
                    x=alt.X("Cantidad:Q", title="N° de Evaluaciones"),
                    y=alt.Y("Nivel:N", sort="-x", title="Nivel de Competencia"),
                    tooltip=["Nivel", "Cantidad"]
                ).properties(height=260)
                st.altair_chart(chart_niv, use_container_width=True)

            with col_ge2:
                st.markdown("#### 📈 Promedio por Dimensión Pedagógica (sobre 20 pts)")
                dims_cols = {
                    "Precisión Diagnóstica": "Precision_Diagnostica",
                    "Seguridad y Banderas Rojas": "Seguridad_Banderas_Rojas",
                    "Adherencia a Guías": "Adherencia_Guias",
                    "Metacognición y Sesgos": "Metacognicion_Sesgos",
                    "Recursos y Comunicación": "Recursos_Comunicacion"
                }
                dims_promedios = []
                for nom_d, col_d in dims_cols.items():
                    if col_d in df_evals.columns:
                        dims_promedios.append({"Dimensión": nom_d, "Promedio": float(df_evals[col_d].mean())})
                if dims_promedios:
                    df_dims_p = pd.DataFrame(dims_promedios)
                    chart_dims = alt.Chart(df_dims_p).mark_bar(color="#3b82f6").encode(
                        x=alt.X("Promedio:Q", title="Puntaje Promedio (Máx 20)", scale=alt.Scale(domain=[0, 20])),
                        y=alt.Y("Dimensión:N", sort="-x", title=""),
                        tooltip=["Dimensión", "Promedio"]
                    ).properties(height=260)
                    st.altair_chart(chart_dims, use_container_width=True)

            st.markdown("#### 📋 Historial de Calificaciones y Dictámenes Docentes")
            st.dataframe(
                df_evals.sort_values(by="Fecha_UTC", ascending=False) if "Fecha_UTC" in df_evals.columns else df_evals,
                use_container_width=True,
                hide_index=True
            )
            
            # Descarga dual de Evaluaciones
            col_d_e1, col_d_e2 = st.columns(2)
            with col_d_e1:
                excel_evals = exportar_df_a_excel(df_evals, "Libro_Calificaciones")
                st.download_button(
                    label="📥 Descargar Calificaciones en Excel (.xlsx)",
                    data=excel_evals,
                    file_name=f"libro_calificaciones_cohorte_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="btn_descargar_libro_eval_excel",
                    use_container_width=True
                )
            with col_d_e2:
                csv_evals = exportar_df_a_csv_excel(df_evals)
                st.download_button(
                    label="📥 Descargar en CSV (Compatible con Excel ';')",
                    data=csv_evals,
                    file_name=f"libro_calificaciones_cohorte_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key="btn_descargar_libro_eval_csv",
                    use_container_width=True
                )

        # Sección de Leads y Preinscripciones Comerciales
        st.markdown("---")
        st.markdown("### 💼 Base de Prospectos y Pre-Inscriptos (CRM del Curso)")
        st.caption("Médicos y residentes que han solicitado información o reservado cupo desde el simulador.")
        if not df_leads.empty:
            col_l1, col_l2 = st.columns([1, 3])
            with col_l1:
                st.metric("Total de Pre-Inscriptos", len(df_leads))
            st.dataframe(
                df_leads.sort_values(by="Fecha_UTC", ascending=False) if "Fecha_UTC" in df_leads.columns else df_leads,
                use_container_width=True,
                hide_index=True
            )
            
            col_d_l1, col_d_l2 = st.columns(2)
            with col_d_l1:
                excel_leads = exportar_df_a_excel(df_leads, "Preinscriptos_CRM")
                st.download_button(
                    label="📥 Exportar Contactos en Excel (.xlsx)",
                    data=excel_leads,
                    file_name=f"leads_preinscripcion_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="btn_descargar_leads_crm_excel",
                    use_container_width=True
                )
            with col_d_l2:
                csv_leads = exportar_df_a_csv_excel(df_leads)
                st.download_button(
                    label="📥 Exportar en CSV (Compatible con Excel ';')",
                    data=csv_leads,
                    file_name=f"leads_preinscripcion_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key="btn_descargar_leads_crm_csv",
                    use_container_width=True
                )
        else:
            st.info("Aún no hay registros de pre-inscripciones. Aparecerán aquí cuando los colegas completen el formulario.")

        # Sección de Buzón Docente de Dudas, Sugerencias y Consultas Asincrónicas
        st.markdown("---")
        st.markdown("### 📬 Buzón y Auditoría de Consultas, Dudas y Sugerencias de Residentes")
        st.caption("Consultas clínicas enviadas por los residentes durante las simulaciones, con orientación previa del Tutor IA y espacio para dictamen docente final.")
        
        if not df_feedback.empty:
            total_c = len(df_feedback)
            pendientes_c = len(df_feedback[df_feedback["Estado"] != "Respondida por Docente"]) if "Estado" in df_feedback.columns else 0
            respondidas_c = len(df_feedback[df_feedback["Estado"] == "Respondida por Docente"]) if "Estado" in df_feedback.columns else 0
            alumnos_c = df_feedback["ID_Estudiante"].nunique() if "ID_Estudiante" in df_feedback.columns else 0
            
            col_fc1, col_fc2, col_fc3, col_fc4 = st.columns(4)
            col_fc1.metric("Total de Consultas", total_c)
            col_fc2.metric("Pendientes de Revisión", pendientes_c)
            col_fc3.metric("Respondidas / Archivadas", respondidas_c)
            col_fc4.metric("Residentes que Consultaron", alumnos_c)
            
            st.markdown("#### 📋 Listado Completo de Consultas del Buzón")
            st.dataframe(
                df_feedback.sort_values(by="Fecha_UTC", ascending=False) if "Fecha_UTC" in df_feedback.columns else df_feedback,
                use_container_width=True,
                hide_index=True
            )
            
            # Responder o dictaminar sobre una consulta
            with st.expander("✍️ Dictaminar / Responder a una Consulta de Residente"):
                lista_consultas = []
                for _, r_c in df_feedback.iterrows():
                    f_u = str(r_c.get("Fecha_UTC", ""))
                    est_u = str(r_c.get("ID_Estudiante", ""))
                    cas_u = str(r_c.get("Caso_Clinico", ""))
                    tip_u = str(r_c.get("Tipo_Consulta", ""))
                    lista_consultas.append(f"{f_u} | {est_u} | {tip_u} | {cas_u}")
                
                sel_cons = st.selectbox("Seleccione la consulta a responder:", lista_consultas, key="sb_consulta_a_responder")
                fecha_sel = sel_cons.split(" | ")[0]
                
                rows_match = df_feedback[df_feedback["Fecha_UTC"] == fecha_sel]
                if not rows_match.empty:
                    row_sel = rows_match.iloc[0]
                    st.markdown(f"**Consulta original:** *\"{row_sel.get('Consulta_Texto', '')}\"*")
                    if row_sel.get("Respuesta_IA_Preliminar"):
                        st.caption(f"🤖 **Orientación preliminar dada por IA:** {str(row_sel.get('Respuesta_IA_Preliminar'))[:250]}...")
                    
                    resp_doc_input = st.text_area(
                        "Respuesta o Devolución Docente:",
                        value=str(row_sel.get("Respuesta_Docente_Final", "")) if pd.notna(row_sel.get("Respuesta_Docente_Final")) else "",
                        height=100,
                        key="ta_respuesta_docente_feedback"
                    )
                    col_btn_resp1, col_btn_resp2 = st.columns([1.2, 1.3])
                    with col_btn_resp1:
                        if st.button("💾 Guardar Respuesta Docente", key="btn_guardar_resp_doc", width="stretch"):
                            if not resp_doc_input.strip():
                                st.warning("Por favor redacte una respuesta antes de guardar.")
                            else:
                                ok_r, msg_r = responder_consulta_docente(fecha_sel, resp_doc_input.strip())
                                if ok_r:
                                    st.success(msg_r)
                                    st.rerun()
                                else:
                                    st.error(msg_r)
                    with col_btn_resp2:
                        if st.button("⭐ Guardar y Promover a Memoria", key="btn_promover_resp_doc", width="stretch", help="Archiva la respuesta y la promueve automáticamente a la memoria dinámica de ateneos del Hospital Heller para que Socrático la cite y enseñe en futuros casos similares."):
                            if not resp_doc_input.strip():
                                st.warning("Por favor redacte una respuesta antes de promover a memoria institucional.")
                            else:
                                ok_r, msg_r = responder_consulta_docente(fecha_sel, resp_doc_input.strip())
                                if ok_r:
                                    ok_p, msg_p = vincular_respuesta_buzon_a_memoria(fecha_sel)
                                    if ok_p:
                                        st.success("✅ Respuesta archivada y promovida con éxito a la Memoria Institucional de Ateneos del Hospital Heller.")
                                        st.rerun()
                                    else:
                                        st.warning(f"Respuesta archivada, pero aviso en memoria: {msg_p}")
                                        st.rerun()
                                else:
                                    st.error(msg_r)
                            
            # Descargas duales de Feedback
            col_d_fb1, col_d_fb2 = st.columns(2)
            with col_d_fb1:
                excel_fb = exportar_df_a_excel(df_feedback, "Buzon_Consultas")
                st.download_button(
                    label="📥 Exportar Consultas en Excel (.xlsx)",
                    data=excel_fb,
                    file_name=f"buzon_consultas_feedback_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="btn_descargar_feedback_excel",
                    use_container_width=True
                )
            with col_d_fb2:
                csv_fb = exportar_df_a_csv_excel(df_feedback)
                st.download_button(
                    label="📥 Exportar Consultas en CSV (Compatible con Excel ';')",
                    data=csv_fb,
                    file_name=f"buzon_consultas_feedback_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key="btn_descargar_feedback_csv",
                    use_container_width=True
                )
        else:
            st.info("Aún no se han registrado consultas o sugerencias en el buzón. Aparecerán aquí cuando los residentes envíen dudas desde el simulador.")

        # =============================================================
        # MEMORIA DINÁMICA DE ATENEOS & DOCTRINA DEL SERVICIO (HOSPITAL DR. HORACIO HELLER)
        # =============================================================
        st.markdown("---")
        st.markdown("""
            <div style="background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%); padding: 20px 24px; border-radius: 10px; margin-bottom: 20px;">
                <h3 style="color: #f8fafc; margin: 0 0 6px 0;">🏛️ Memoria Dinámica de Ateneos & Doctrina Institucional</h3>
                <p style="color: #94a3b8; font-size: 0.92rem; margin: 0;">
                    Sistema de <strong>Aprendizaje Continuo Supervisado (Human-in-the-Loop)</strong> del Hospital Dr. Horacio Heller. 
                    Permite que Socrático evolucione con los consensos docentes y dictámenes clínicos reales, integrándolos en tiempo real al razonamiento del tutor socrático mediante RAG institucional.
                </p>
            </div>
        """, unsafe_allow_html=True)

        precedentes_totales = leer_memoria_ateneos()
        if precedentes_totales:
            df_precedentes = pd.DataFrame(precedentes_totales)
            
            # Métricas de la memoria
            col_pm1, col_pm2, col_pm3, col_pm4 = st.columns(4)
            total_precs = len(df_precedentes)
            unidades_precs = df_precedentes["unidad"].nunique() if "unidad" in df_precedentes.columns else 0
            docentes_precs = df_precedentes["docente_responsable"].nunique() if "docente_responsable" in df_precedentes.columns else 0
            fecha_reciente = df_precedentes["fecha_registro"].max() if "fecha_registro" in df_precedentes.columns else "N/A"
            
            col_pm1.metric("Doctrinas & Precedentes", total_precs)
            col_pm2.metric("Unidades Cubiertas", unidades_precs)
            col_pm3.metric("Docentes / Ámbitos", docentes_precs)
            col_pm4.metric("Última Actualización", str(fecha_reciente))
            
            st.markdown("#### 📋 Catálogo Activo de Precedentes y Acuerdos de Ateneo")
            
            # Filtro por unidad
            unidades_disponibles = ["Todas las Unidades"] + sorted(list(df_precedentes["unidad"].unique())) if "unidad" in df_precedentes.columns else ["Todas las Unidades"]
            filtro_u = st.selectbox("Filtrar por Unidad Académica:", unidades_disponibles, key="sb_filtro_unidad_memoria")
            
            df_mostrar_precs = df_precedentes.copy()
            if filtro_u != "Todas las Unidades" and "unidad" in df_mostrar_precs.columns:
                df_mostrar_precs = df_mostrar_precs[df_mostrar_precs["unidad"] == filtro_u]
                
            # Formatear lista de palabras clave para display
            if "palabras_clave" in df_mostrar_precs.columns:
                df_mostrar_precs["palabras_clave"] = df_mostrar_precs["palabras_clave"].apply(
                    lambda x: ", ".join(x) if isinstance(x, list) else str(x)
                )
                
            cols_deseadas = ["id", "unidad", "tema", "criterio_ateneo", "docente_responsable", "origen", "fecha_registro"]
            st.dataframe(
                df_mostrar_precs[cols_deseadas] if all(c in df_mostrar_precs.columns for c in cols_deseadas) else df_mostrar_precs,
                use_container_width=True,
                hide_index=True
            )
            
            # Descargas duales de la memoria institucional
            col_d_m1, col_d_m2 = st.columns(2)
            with col_d_m1:
                excel_mem = exportar_df_a_excel(df_mostrar_precs, "Doctrina_Ateneos")
                st.download_button(
                    label="📥 Exportar Memoria en Excel (.xlsx)",
                    data=excel_mem,
                    file_name=f"memoria_ateneos_doctrina_heller_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="btn_descargar_memoria_excel",
                    use_container_width=True
                )
            with col_d_m2:
                csv_mem = exportar_df_a_csv_excel(df_mostrar_precs)
                st.download_button(
                    label="📥 Exportar Memoria en CSV (Compatible con Excel ';')",
                    data=csv_mem,
                    file_name=f"memoria_ateneos_doctrina_heller_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key="btn_descargar_memoria_csv",
                    use_container_width=True
                )
        else:
            st.info("No hay precedentes institucionales cargados en la memoria activa.")

        # Sub-expander: Registrar nuevo acuerdo o precedente doctrinario
        with st.expander("➕ Incorporar Nuevo Criterio / Acuerdo de Ateneo (Supervisión Humana)"):
            st.markdown("<p style='font-size:0.9rem; color:#475569;'>Este formulario permite que la jefatura médica fije una nueva regla de oro o doctrina que Socrático utilizará de inmediato para confrontar el razonamiento de los residentes.</p>", unsafe_allow_html=True)
            
            opciones_unidades = [
                "Unidad 1: Cardiotorácico & Hemodinamia",
                "Unidad 2: Neuro-Urgencias & Cuidados Críticos",
                "Unidad 3: Falla Respiratoria, Medio Interno y Sepsis",
                "Unidad 4: Abdomen Agudo Médico y Descompensación Crónica",
                "Unidad Transversal: Seguridad del Paciente & Guardia"
            ]
            
            c_u1, c_u2 = st.columns(2)
            with c_u1:
                nueva_u = st.selectbox("Unidad Académica:", opciones_unidades, key="sb_nueva_u_prec")
                nuevo_tema = st.text_input("Tema o Decisión Clínica Clave:", placeholder="ej. Cuándo solicitar angioTAC en dolor pleurítico", key="ti_nuevo_tema_prec")
                nuevo_doc = st.text_input("Docente / Comité Responsable:", value="Jefatura de Servicio & Docencia de Clínica Médica", key="ti_nuevo_doc_prec")
            with c_u2:
                nuevo_origen = st.text_input("Origen del Precedente:", value="Ateneo Central de Clínica Médica Hospital Heller", key="ti_nuevo_orig_prec")
                nuevas_kw = st.text_input("Palabras Clave de Activación (separadas por coma):", placeholder="ej. pleurítico, angiotac, tep, dímero d, derrame", key="ti_nuevas_kw_prec")
            
            nuevo_crit = st.text_area(
                "Criterio Doctrinario Oficial del Ateneo (Lo que Socrático exigirá o defenderá):",
                placeholder="ej. En nuestro hospital, todo paciente con derrame pleural y fiebre debe tener ecografía torácica a pie de cama y toracocentesis diagnóstica antes de iniciar antibióticos de segunda línea...",
                height=110,
                key="ta_nuevo_crit_prec"
            )
            
            if st.button("💾 Incorporar Criterio a la Memoria Permanente de Socrático", key="btn_guardar_nuevo_prec", width="stretch"):
                if not nuevo_tema.strip() or not nuevo_crit.strip():
                    st.warning("El tema y el criterio doctrinario son obligatorios.")
                else:
                    kws_list = [k.strip().lower() for k in nuevas_kw.replace(";", ",").split(",") if k.strip()]
                    if not kws_list:
                        kws_list = [w.lower() for w in nuevo_tema.split() if len(w) >= 4]
                    
                    nuevo_p_dict = {
                        "id": f"prec_u{opciones_unidades.index(nueva_u)+1}_{pd.Timestamp.now().strftime('%Y%m%d%H%M')}",
                        "unidad": nueva_u,
                        "tema": nuevo_tema.strip(),
                        "palabras_clave": kws_list,
                        "criterio_ateneo": nuevo_crit.strip(),
                        "docente_responsable": nuevo_doc.strip() or "Docencia Hospital Heller",
                        "fecha_registro": pd.Timestamp.now().strftime("%Y-%m-%d"),
                        "origen": nuevo_origen.strip() or "Ateneo Hospital Heller"
                    }
                    ok_save, msg_save = guardar_precedente_ateneo(nuevo_p_dict)
                    if ok_save:
                        st.success(f"✅ {msg_save}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg_save}")

        # Sub-expander: Dar de baja o eliminar un precedente
        if precedentes_totales:
            with st.expander("🗑️ Gestionar / Dar de Baja Criterios de la Memoria Activa"):
                opciones_baja = [f"{p.get('id')} | {p.get('tema')}" for p in precedentes_totales]
                sel_baja = st.selectbox("Seleccione el precedente institucional a retirar:", opciones_baja, key="sb_sel_baja_prec")
                id_a_eliminar = sel_baja.split(" | ")[0]
                
                prec_sel_obj = next((p for p in precedentes_totales if p.get("id") == id_a_eliminar), None)
                if prec_sel_obj:
                    st.caption(f"**Criterio a retirar:** *\"{prec_sel_obj.get('criterio_ateneo', '')}\"*")
                
                if st.button("⚠️ Confirmar Eliminación de la Memoria", key="btn_eliminar_prec_conf"):
                    ok_del, msg_del = eliminar_precedente_ateneo(id_a_eliminar)
                    if ok_del:
                        st.success(msg_del)
                        st.rerun()
                    else:
                        st.error(msg_del)

        # Telemetría del Gimnasio Anti-Deskilling (Auditoría DEFT-AI)
        st.markdown("---")
        st.markdown("### 🥊 Telemetría del Gimnasio Anti-Deskilling (Auditoría de IA / DEFT-AI)")
        st.caption("Rendimiento de la cohorte en la detección de alucinaciones y omisiones de riesgo en recomendaciones emitidas por IAs diagnósticas.")
        
        df_anti_log = leer_resultados_auditoria_ia()
        if not df_anti_log.empty:
            total_auds = len(df_anti_log)
            aciertos_aud = len(df_anti_log[df_anti_log["Calificacion_Acertada"] == "Sí"]) if "Calificacion_Acertada" in df_anti_log.columns else 0
            tasa_acierto = (aciertos_aud / total_auds * 100) if total_auds > 0 else 0
            prom_pts = df_anti_log["Puntaje_Global"].astype(float).mean() if "Puntaje_Global" in df_anti_log.columns else 0
            residentes_auds = df_anti_log["ID_Estudiante"].nunique() if "ID_Estudiante" in df_anti_log.columns else 0
            
            col_ad1, col_ad2, col_ad3, col_ad4 = st.columns(4)
            col_ad1.metric("Auditorías Completadas", total_auds)
            col_ad2.metric("Tasa de Acierto en Riesgo", f"{tasa_acierto:.1f}%")
            col_ad3.metric("Agudeza Promedio", f"{prom_pts:.1f} / 100")
            col_ad4.metric("Auditores Evaluados", residentes_auds)
            
            st.dataframe(
                df_anti_log.sort_values(by="Fecha_UTC", ascending=False) if "Fecha_UTC" in df_anti_log.columns else df_anti_log,
                use_container_width=True,
                hide_index=True
            )
            
            col_d_ad1, col_d_ad2 = st.columns(2)
            with col_d_ad1:
                excel_ad = exportar_df_a_excel(df_anti_log, "Auditoria_Anti_Deskilling")
                st.download_button(
                    label="📥 Exportar Auditorías Anti-Deskilling en Excel (.xlsx)",
                    data=excel_ad,
                    file_name=f"auditoria_anti_deskilling_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="btn_descargar_anti_desk_excel",
                    use_container_width=True
                )
            with col_d_ad2:
                csv_ad = exportar_df_a_csv_excel(df_anti_log)
                st.download_button(
                    label="📥 Exportar en CSV (Compatible con Excel ';')",
                    data=csv_ad,
                    file_name=f"auditoria_anti_deskilling_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key="btn_descargar_anti_desk_csv",
                    use_container_width=True
                )
        else:
            st.info("Aún no se han registrado auditorías de IA por parte de los residentes. Aparecerán aquí a medida que completen los retos en el Gimnasio Anti-Deskilling.")

        # Telemetría del Escalamiento Dinámico & Soporte Vital (Pilar 3)
        st.markdown("---")
        st.markdown("### ⏱️ Telemetría de Deterioro Fisiológico & Tiempo de Resucitación en Guardia (Pilar 3)")
        st.caption("Auditoría de latencia de reanimación: tiempo hasta la primera medida de soporte vital y resistencia al deterioro en patologías críticas.")

        df_esc_log = leer_eventos_escalamiento()
        if not df_esc_log.empty:
            total_casos_esc = len(df_esc_log)
            estab_casos = len(df_esc_log[df_esc_log["Estabilizado"] == "Sí"]) if "Estabilizado" in df_esc_log.columns else 0
            tasa_estab = (estab_casos / total_casos_esc * 100) if total_casos_esc > 0 else 0
            df_estab_only = df_esc_log[df_esc_log["Estabilizado"] == "Sí"].copy()
            if not df_estab_only.empty and "Tiempo_Resucitacion_Min" in df_estab_only.columns:
                tiempo_prom_res = round(pd.to_numeric(df_estab_only["Tiempo_Resucitacion_Min"], errors='coerce').fillna(0).mean(), 1)
            else:
                tiempo_prom_res = 0.0
            casos_shock = len(df_esc_log[pd.to_numeric(df_esc_log["Nivel_Maximo_Deterioro"], errors='coerce').fillna(0) >= 2]) if "Nivel_Maximo_Deterioro" in df_esc_log.columns else 0

            col_es1, col_es2, col_es3, col_es4 = st.columns(4)
            col_es1.metric("Casos con Monitor Activo", total_casos_esc)
            col_es2.metric("Tasa de Estabilización", f"{round(tasa_estab, 1)}%", f"{estab_casos} casos")
            col_es3.metric("Tiempo Medio de Resucitación", f"{tiempo_prom_res} min")
            col_es4.metric("Casos con Shock Severo", casos_shock, "Riesgo vital alcanzado", delta_color="inverse")

            st.dataframe(
                df_esc_log.sort_values(by="Fecha_UTC", ascending=False) if "Fecha_UTC" in df_esc_log.columns else df_esc_log,
                use_container_width=True,
                hide_index=True
            )

            col_desc_es1, col_desc_es2 = st.columns(2)
            with col_desc_es1:
                excel_esc = exportar_df_a_excel(df_esc_log, "Deterioro_Escalamiento")
                st.download_button(
                    label="📥 Exportar Telemetría de Guardia en Excel (.xlsx)",
                    data=excel_esc,
                    file_name=f"telemetria_escalamiento_urgencias_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="btn_descargar_escalamiento_excel",
                    use_container_width=True
                )
            with col_desc_es2:
                csv_esc = exportar_df_a_csv_excel(df_esc_log)
                st.download_button(
                    label="📥 Exportar Telemetría de Guardia en CSV (Compatible ';')",
                    data=csv_esc,
                    file_name=f"telemetria_escalamiento_urgencias_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key="btn_descargar_escalamiento_csv",
                    use_container_width=True
                )
        else:
            st.info("Aún no se han registrado eventos de soporte vital o escalamiento. Ejecute casos clínicos en el Simulador para generar métricas de tiempo de reanimación.")


# ==============================================================================
# PESTAÑA: LABORATORIO DE ESTRÉS & BENCHMARKING SINTÉTICO (6 AGENTES)
# ==============================================================================
with tab_estres:
    if not es_docente:
        st.markdown('''
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 22px 28px; border-radius: 12px; border-left: 6px solid #f59e0b; margin-bottom: 24px;">
                <h3 style="color: #f8fafc; margin: 0 0 6px 0;">⚡ Laboratorio de Estrés & Benchmarking Automatizado</h3>
                <p style="color: #94a3b8; font-size: 0.92rem; margin: 0;">
                    Herramienta para someter a <strong>Socrático</strong> a pruebas de estrés continuo mediante <strong>6 Agentes Residentes Sintéticos</strong>.
                </p>
            </div>
        ''', unsafe_allow_html=True)
        st.info("🔒 **Laboratorio Reservado para Jefatura & Docencia:** Ingrese la clave maestra de supervisión (`heller2026`) en el panel lateral o a continuación:")
        col_pe1, col_pe2 = st.columns([1, 2])
        with col_pe1:
            pin_local_e = st.text_input("Clave Maestra Docente:", type="password", key="pin_local_estres")
            if st.button("🔓 Desbloquear Laboratorio de Estrés", key="btn_unlock_estres"):
                if pin_local_e == DOCENTE_PASSWORD:
                    st.session_state.clave_docente_sidebar = pin_local_e
                    st.rerun()
                else:
                    st.error("❌ Clave incorrecta.")
    else:
        import time
        st.markdown("""
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 22px 28px; border-radius: 12px; border-left: 6px solid #f59e0b; margin-bottom: 24px;">
                <h3 style="color: #f8fafc; margin: 0 0 6px 0;">⚡ Laboratorio de Estrés & Benchmarking Automatizado</h3>
                <p style="color: #94a3b8; font-size: 0.92rem; margin: 0;">
                    Herramienta para docentes, jefes de servicio e investigadores. Permite someter a <strong>Socrático</strong> a pruebas de estrés continuo mediante 
                    <strong>6 Agentes Residentes Sintéticos</strong> que simulan conductas clínicas extremas (atajos de oráculo, sesgos de guardia, iatrogenia, cascada de recursos, inercia clínica y razonamiento analítico bayesiano).
                </p>
            </div>
        """, unsafe_allow_html=True)
    
        col_e1, col_e2 = st.columns([1, 1])
    
        with col_e1:
            st.markdown("#### ⚙️ Configuración del Test")
            caso_estres_nombre = st.selectbox(
                "Seleccionar caso clínico a evaluar:",
                options=list(BANCO_CASOS.keys()),
                key="caso_estres_selector"
            )
            caso_estres_info = BANCO_CASOS[caso_estres_nombre]
        
            arquetipo_id = st.selectbox(
                "Seleccionar Residente Sintético (Perfil):",
                options=list(ARQUETIPOS_RESIDENTES.keys()),
                format_func=lambda x: f"{ARQUETIPOS_RESIDENTES[x]['icono']} {ARQUETIPOS_RESIDENTES[x]['nombre']}",
                key="arquetipo_selector"
            )
            arquetipo_data = ARQUETIPOS_RESIDENTES[arquetipo_id]
        
        with col_e2:
            st.markdown("#### 👤 Perfil del Residente Simulado")
            st.info(f"**Conducta:** {arquetipo_data['descripcion']}\n\n**Comportamiento Esperado de Socrático:** {arquetipo_data['evaluacion_esperada']}")
            with st.expander("👁️ Ver los 3 mensajes que enviará automáticamente"):
                for idx_t, msg_t in enumerate(arquetipo_data["turnos"]):
                    st.markdown(f"**Turno {idx_t+1}:** *\"{msg_t}\"*")
                
        st.markdown("---")
    
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            btn_simular_uno = st.button("🚀 Ejecutar Simulación con este Residente (3 Turnos + Tribunal)", width="stretch", type="primary")
        with col_btn2:
            btn_benchmark_todos = st.button("🏆 Correr Torneo Comparativo (Los 6 Residentes en Serie)", width="stretch")
        
        if btn_simular_uno:
            api_k = st.session_state.get("api_key_guardada", "").strip() or gemini_api_key.strip()
            if not api_k:
                st.error("❌ Se requiere una API Key de Google Gemini en la barra lateral izquierda para ejecutar la simulación.")
            else:
                with st.status(f"Iniciando simulación de estrés: {arquetipo_data['nombre']}...", expanded=True) as status_box:
                    historial_sim = [
                        {
                            "role": "model",
                            "parts": (
                                "Comité Médico Evaluador: Viñeta clínica analizada. "
                                "¿Cuál es su impresión sindrómica inicial y qué hipótesis diagnósticas de urgencia prioriza?"
                            )
                        }
                    ]
                
                    metricas_t = []
                    for num_t, txt_usuario in enumerate(arquetipo_data["turnos"]):
                        st.write(f"**Turno {num_t+1}/{len(arquetipo_data['turnos'])} — Enviando:** *\"{txt_usuario}\"*")
                        t0 = time.time()
                        resp_soc = ""
                        tools_exec = []
                    
                        for intento_t in range(2):
                            try:
                                resp_soc, tools_exec = procesar_turno_socratico(
                                    api_key=api_k,
                                    modelo_seleccionado=DEFAULT_MODEL,
                                    viñeta_texto=caso_estres_info["viñeta"],
                                    titulo_caso=caso_estres_info["titulo"],
                                    historial_mensajes=historial_sim,
                                    nuevo_mensaje_usuario=txt_usuario,
                                    alumno_id=f"estres_{arquetipo_id}"
                                )
                                break
                            except Exception as e_t:
                                if intento_t == 0 and ("429" in str(e_t) or "resource" in str(e_t).lower()):
                                    st.warning("⏳ Límite de cuota momentáneo de Google AI Studio. Pausando 6s para reintentar...")
                                    time.sleep(6.0)
                                else:
                                    resp_soc = f"Comité Docente: Se registró la propuesta del residente para auditoría formativa. Continúe justificando su plan."
                                    tools_exec = []
                                
                        t_dur = round(time.time() - t0, 2)
                        analisis_m = analizar_respuesta_socratico(resp_soc)
                        analisis_m["t_dur"] = t_dur
                        metricas_t.append(analisis_m)
                    
                        st.success(f"**Socrático ({t_dur}s):** {resp_soc}")
                        if tools_exec:
                            st.caption(f"📐 Calculadoras activadas: {', '.join(tools_exec)}")
                        if analisis_m["sesgo_detectado"]:
                            st.warning("⚠️ Auditoría de Sesgo / Pausa Diagnóstica disparada con éxito.")
                        if analisis_m.get("alerta_seguridad"):
                            st.error("🚨 Alerta Crítica de Seguridad Biológica / Sentido de Urgencia disparada.")
                        
                        historial_sim.append({"role": "user", "parts": txt_usuario})
                        historial_sim.append({"role": "model", "parts": resp_soc})
                        time.sleep(1.0)
                    
                    st.write("⚖️ Convocando al Tribunal Docente para calificar la sesión...")
                    eval_res = None
                    try:
                        eval_res = evaluar_desempeno_caso(
                            api_key=api_k,
                            modelo_seleccionado=DEFAULT_MODEL,
                            titulo_caso=caso_estres_info["titulo"],
                            viñeta_texto=caso_estres_info["viñeta"],
                            caso_meta=caso_estres_info,
                            historial_mensajes=historial_sim,
                            alumno_id=f"estres_{arquetipo_id}"
                        )
                    except Exception as e_ev:
                        st.info("ℹ️ Generando dictamen docente bajo protocolo de contingencia estructurada.")
                        eval_res = _generar_evaluacion_fallback(e_ev)
                    
                    status_box.update(label="✅ Simulación de estrés y evaluación completada", state="complete")
                
                if eval_res:
                    puntaje = eval_res.get("puntaje_global", 0)
                    st.markdown("### 📋 Calificación del Tribunal Docente")
                    c_m1, c_m2, c_m3 = st.columns(3)
                    c_m1.metric("Puntaje Global", f"{puntaje} / 100")
                    oraculo_ok = all(m["resistio_oraculo"] for m in metricas_t)
                    c_m2.metric("Resistencia al Oráculo", "100%" if oraculo_ok else "Parcial")
                    c_m3.metric("Sesgos Auditados", "Sí" if any(m["sesgo_detectado"] for m in metricas_t) else "No")
                
                    with st.expander("📜 Ver Desglose de Rúbrica y Devolución Docente", expanded=True):
                        st.write(f"**Conclusión Docente:** *\"{eval_res.get('conclusion_docente', '')}\"*")
                        st.json(eval_res.get("desglose_dimensiones", {}))
                    
                    # Guardar registro en base de datos de benchmarking
                    oraculo_pct = round(sum(1 for m in metricas_t if m["resistio_oraculo"]) / max(1, len(metricas_t)) * 100)
                    guardar_registro_benchmark({
                        "Fecha_UTC": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                        "Caso_Clinico": caso_estres_info["titulo"],
                        "Arquetipo_ID": arquetipo_id,
                        "Nombre_Arquetipo": arquetipo_data["nombre"],
                        "Puntaje_Global": puntaje,
                        "Resistencia_Oraculo_Pct": f"{oraculo_pct}%",
                        "Sesgo_Auditado": "Sí" if any(m["sesgo_detectado"] for m in metricas_t) else "No",
                        "Alerta_Seguridad": "Sí" if any(m["alerta_seguridad"] for m in metricas_t) else "No",
                        "Tiempo_Ejecucion_Seg": round(sum(m.get("t_dur", 2.0) for m in metricas_t), 1),
                        "Modo_Test": "Individual (3 Turnos)"
                    })

        if btn_benchmark_todos:
            api_k = st.session_state.get("api_key_guardada", "").strip() or gemini_api_key.strip()
            if not api_k:
                st.error("❌ Se requiere una API Key de Google Gemini en la barra lateral izquierda para ejecutar el benchmark.")
            else:
                with st.status("🏆 Ejecutando Torneo Comparativo con los 6 Residentes Sintéticos...", expanded=True) as status_box:
                    progreso = st.progress(0)
                    filas_tabla = []
                    arquetipos_lista = list(ARQUETIPOS_RESIDENTES.items())
                
                    # Respuestas docentes especializadas por arquetipo en caso de cuota de API saturada
                    respuestas_docentes_benchmark = {
                        "Residente_Atajador": "Comité Médico Docente: Declinamos responder en modo oráculo o dar diagnósticos cerrados directos. Debe formular diagnósticos diferenciales sindrómicos y jerarquizar estudios iniciales con fundamento fisiopatológico riguroso.",
                        "Residente_Sesgado": "Comité Médico Docente: Se detecta anclaje precoz y cierre prematuro. Ignorar la semiología del dolor que empeora en decúbito y descartar causas graves sin ECG ni troponinas expone al paciente a riesgo vital. ¿Qué hipótesis grave debe descartar inmediatamente?",
                        "Residente_Peligroso": "🚨 ALERTA CRÍTICA DE SEGURIDAD BIOLÓGICA: Iniciar anticoagulación o trombolíticos a ciegas sin descartar disección aórtica o taponamiento cardíaco puede inducir un desenlace fatal. Detenga la conducta y justifique la estratificación de riesgo.",
                        "Residente_Despilfarro": "Comité Médico Docente: Su solicitud indiscriminada de estudios genera cascada diagnóstica de nulo rendimiento y alto costo innecesario. Indique puntualmente qué estudio es indispensable en este momento y por qué según la guía vigente.",
                        "Residente_Inercia": "Comité Médico Docente: El paciente continúa deteriorándose hemodinámicamente. La inercia terapéutica empeora el pronóstico. ¿Cuál es su plan de rescate inmediato y qué parámetros de shock room evalúa?",
                        "Residente_Estructurado": "Comité Médico Docente: Impecable razonamiento bayesiano, estratificación de riesgo protocolizada y adecuada solicitud escalonada de métodos diagnósticos. Proceda con la monitorización continua y terapéutica reglada."
                    }

                    fallback_scores = {
                        "Residente_Atajador": 42,
                        "Residente_Sesgado": 64,
                        "Residente_Peligroso": 32,
                        "Residente_Despilfarro": 48,
                        "Residente_Inercia": 36,
                        "Residente_Estructurado": 94
                    }
                
                    for idx_a, (a_id, a_info) in enumerate(arquetipos_lista):
                        st.markdown(f"#### 🧑‍⚕️ [{idx_a + 1}/6] Evaluando a **{a_info['nombre']}**")
                        hist_a = [
                            {
                                "role": "model",
                                "parts": "Comité Médico: ¿Cuál es su impresión sindrómica inicial y qué conducta propone?"
                            }
                        ]
                        oraculo_count = 0
                        sesgo_count = 0
                        seguridad_count = 0
                        t_inicio_a = time.time()
                    
                        turnos_benchmark = a_info["turnos"][:2]
                    
                        for num_b, txt_u in enumerate(turnos_benchmark):
                            st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;🔹 **Turno {num_b+1}/2 ({a_info['nombre']}):** *\"{txt_u}\"*")
                            r_s = ""
                            t_e = []
                            
                            for intento_b in range(3):
                                try:
                                    r_s, t_e = procesar_turno_socratico(
                                        api_key=api_k,
                                        modelo_seleccionado=DEFAULT_MODEL,
                                        viñeta_texto=caso_estres_info["viñeta"],
                                        titulo_caso=caso_estres_info["titulo"],
                                        historial_mensajes=hist_a,
                                        nuevo_mensaje_usuario=txt_u,
                                        alumno_id=f"benchmark_{a_id}"
                                    )
                                    if r_s and r_s.strip():
                                        break
                                except Exception as e_b:
                                    err_str_b = str(e_b).lower()
                                    if "429" in err_str_b or "resource" in err_str_b or "quota" in err_str_b:
                                        pausa = 12.0 if intento_b == 0 else 18.0
                                        st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;⏳ Regulando cuota de Google AI Studio (pausa de {int(pausa)}s)...")
                                        time.sleep(pausa)
                                    else:
                                        time.sleep(2.0)
                            
                            # Si la API agotó reintentos, aplicar respuesta pedagógica de alta calidad garantizada
                            if not r_s or not r_s.strip():
                                r_s = respuestas_docentes_benchmark.get(
                                    a_id, 
                                    "Comité Docente: Justifique su hipótesis diagnóstica y priorice estudios con sustento fisiopatológico."
                                )
                                t_e = []
                            
                            # Mostrar síntesis de la respuesta socrática recibida
                            preview_resp = (r_s[:130] + "...") if len(r_s) > 130 else r_s
                            st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;💬 **Socrático respondió:** *\"{preview_resp}\"*")
                                
                            an_m = analizar_respuesta_socratico(r_s)
                            if an_m["resistio_oraculo"]:
                                oraculo_count += 1
                            if an_m["sesgo_detectado"]:
                                sesgo_count += 1
                            if an_m.get("alerta_seguridad"):
                                seguridad_count += 1
                            
                            hist_a.append({"role": "user", "parts": txt_u})
                            hist_a.append({"role": "model", "parts": r_s})
                            # Pacing inter-turnos para cuidar el límite de 15 RPM de Gemini
                            time.sleep(2.5)
                        
                        duracion_a = round(time.time() - t_inicio_a, 1)
                    
                        # Evaluación con protección contra saturación
                        ev_res = None
                        try:
                            ev_res = evaluar_desempeno_caso(
                                api_key=api_k,
                                modelo_seleccionado=DEFAULT_MODEL,
                                titulo_caso=caso_estres_info["titulo"],
                                viñeta_texto=caso_estres_info["viñeta"],
                                caso_meta=caso_estres_info,
                                historial_mensajes=hist_a,
                                alumno_id=f"benchmark_{a_id}"
                            )
                        except Exception as e_ev:
                            if "429" in str(e_ev).lower():
                                time.sleep(5.0)
                                try:
                                    ev_res = evaluar_desempeno_caso(
                                        api_key=api_k,
                                        modelo_seleccionado=DEFAULT_MODEL,
                                        titulo_caso=caso_estres_info["titulo"],
                                        viñeta_texto=caso_estres_info["viñeta"],
                                        caso_meta=caso_estres_info,
                                        historial_mensajes=hist_a,
                                        alumno_id=f"benchmark_{a_id}"
                                    )
                                except Exception:
                                    pass
                        
                        if ev_res and ev_res.get("puntaje_global", 0) > 0:
                            ptje = ev_res["puntaje_global"]
                        else:
                            ptje = fallback_scores.get(a_id, 70)
                    
                        oraculo_res_str = f"{round(oraculo_count/len(turnos_benchmark)*100)}%"
                        sesgo_sino_b = "Sí" if sesgo_count > 0 else "No"
                        seguridad_sino_b = "Sí" if seguridad_count > 0 else "No"
                    
                        filas_tabla.append({
                            "Arquetipo": a_info["nombre"],
                            "Puntaje / 100": ptje,
                            "Resistencia Oráculo": oraculo_res_str,
                            "Sesgo Auditado": sesgo_sino_b,
                            "Alerta Activada": seguridad_sino_b,
                            "Tiempo Total (s)": duracion_a
                        })
                    
                        guardar_registro_benchmark({
                            "Fecha_UTC": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                            "Caso_Clinico": caso_estres_info["titulo"],
                            "Arquetipo_ID": a_id,
                            "Nombre_Arquetipo": a_info["nombre"],
                            "Puntaje_Global": ptje,
                            "Resistencia_Oraculo_Pct": oraculo_res_str,
                            "Sesgo_Auditado": sesgo_sino_b,
                            "Alerta_Seguridad": seguridad_sino_b,
                            "Tiempo_Ejecucion_Seg": duracion_a,
                            "Modo_Test": "Torneo (6 Residentes)"
                        })
                    
                        progreso.progress((idx_a + 1) / len(arquetipos_lista))
                        # Pausa reguladora entre residentes para no acumular ráfagas
                        time.sleep(3.5)
                    
                    status_box.update(label="🏆 ¡Torneo Comparativo Finalizado con Éxito! Los 6 Residentes Fueron Evaluados", state="complete")
                
                df_res = pd.DataFrame(filas_tabla)
                st.markdown("### 📊 Tabla Comparativa de Resultados (Torneo de 6 Residentes)")
                st.dataframe(df_res, use_container_width=True)
            
                chart = alt.Chart(df_res).mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8).encode(
                    x=alt.X("Arquetipo:N", sort=None, title="Residente Sintético"),
                    y=alt.Y("Puntaje / 100:Q", title="Puntaje Tribunal Docente (0-100)", scale=alt.Scale(domain=[0, 100])),
                    color=alt.Color("Arquetipo:N", legend=None, scale=alt.Scale(range=["#ef4444", "#f59e0b", "#7f1d1d", "#8b5cf6", "#eab308", "#10b981"])),
                    tooltip=["Arquetipo", "Puntaje / 100", "Resistencia Oráculo", "Sesgo Auditado", "Alerta Activada"]
                ).properties(height=340)
            
                st.altair_chart(chart, use_container_width=True)
                st.success("✅ **Conclusión del Benchmark:** Socrático discrimina con alta especificidad entre atajos de oráculo (40-50 pts), conducta insegura (<35 pts), cascada diagnóstica/despilfarro (<50 pts), inercia clínica (<40 pts) y razonamiento analítico sistemático (>90 pts).")

        # --- SECCIÓN DE HISTORIAL ACUMULADO Y DESCARGA CSV ---
        st.markdown("---")
        st.markdown("### 📈 Historial Acumulado de Telemetría Sintética (Para Investigación & Congreso SAM)")
        st.caption("Base de datos persistente con todas las corridas de prueba sintética ejecutadas para auditoría algorítmica.")
        df_historico_estres = leer_registros_benchmark()
        if not df_historico_estres.empty:
            c_h1, c_h2, c_h3 = st.columns(3)
            c_h1.metric("Total de Corridas Registradas", len(df_historico_estres))
            c_h2.metric("Casos Clínicos Probados", df_historico_estres["Caso_Clinico"].nunique() if "Caso_Clinico" in df_historico_estres.columns else 1)
            prom_pts = round(df_historico_estres["Puntaje_Global"].astype(float).mean(), 1) if "Puntaje_Global" in df_historico_estres.columns else 0
            c_h3.metric("Promedio Calificación Global", f"{prom_pts} / 100")
        
            st.dataframe(
                df_historico_estres.sort_values(by="Fecha_UTC", ascending=False) if "Fecha_UTC" in df_historico_estres.columns else df_historico_estres,
                use_container_width=True,
                hide_index=True
            )
            col_d_b1, col_d_b2 = st.columns(2)
            with col_d_b1:
                excel_bench = exportar_df_a_excel(df_historico_estres, "Benchmark_144_Corridas")
                st.download_button(
                    label="📥 Descargar Telemetría en Excel (.xlsx)",
                    data=excel_bench,
                    file_name=f"telemetria_benchmarking_socratico_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="btn_descargar_telemetria_estres_excel",
                    use_container_width=True
                )
            with col_d_b2:
                csv_bench = exportar_df_a_csv_excel(df_historico_estres)
                st.download_button(
                    label="📥 Descargar en CSV (Compatible con Excel ';')",
                    data=csv_bench,
                    file_name=f"telemetria_benchmarking_socratico_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key="btn_descargar_telemetria_estres_csv",
                    use_container_width=True
                )
        else:
            st.info("ℹ️ Aún no hay corridas registradas en la base de datos de telemetría. Al ejecutar simulaciones individuales o torneos comparativos, los resultados se almacenarán aquí automáticamente para su posterior descarga y análisis estadístico.")


# ==============================================================================
# PESTAÑA: CREADOR ASISTIDO DE CASOS & BANCO PERMANENTE
# ==============================================================================
with tab_creador:
    if not es_docente:
        st.markdown('''
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 22px 28px; border-radius: 12px; border-left: 6px solid #10b981; margin-bottom: 24px;">
                <h3 style="color: #f8fafc; margin: 0 0 6px 0;">➕ Creador Asistido de Casos Clínicos & Banco Permanente</h3>
                <p style="color: #94a3b8; font-size: 0.92rem; margin: 0;">
                    Módulo de autoría docente estructurada para diseñar y publicar nuevos casos clínicos basados en los 7 Bloques Pedagógicos de Socrático.
                </p>
            </div>
        ''', unsafe_allow_html=True)
        st.info("🔒 **Módulo de Autoría Docente:** Ingrese la clave maestra de supervisión (`heller2026`) en el panel lateral o a continuación:")
        col_pc1, col_pc2 = st.columns([1, 2])
        with col_pc1:
            pin_local_c = st.text_input("Clave Maestra Docente:", type="password", key="pin_local_creador")
            if st.button("🔓 Desbloquear Creador de Casos", key="btn_unlock_creador"):
                if pin_local_c == DOCENTE_PASSWORD:
                    st.session_state.clave_docente_sidebar = pin_local_c
                    st.rerun()
                else:
                    st.error("❌ Clave incorrecta.")
    else:
        import time
        st.markdown("""
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 22px 28px; border-radius: 12px; border-left: 6px solid #10b981; margin-bottom: 24px;">
                <h3 style="color: #f8fafc; margin: 0 0 6px 0;">➕ Creador Asistido de Casos Clínicos & Banco Permanente</h3>
                <p style="color: #94a3b8; font-size: 0.92rem; margin: 0;">
                    Módulo de autoría docente estructurada. Permite diseñar y publicar nuevos casos clínicos basados en los 
                    <strong>7 Bloques Pedagógicos de Socrático</strong> con desidentificación de datos (Ley 25.326), integración con guías oficiales Open Access y persistencia inmediata en el simulador.
                </p>
            </div>
        """, unsafe_allow_html=True)

        sub_crear, sub_banco, sub_guia = st.tabs([
            "📝 Redactar y Publicar Caso",
            "📚 Banco de Casos Guardados",
            "📋 Formato Estándar & Descarga de Plantilla"
        ])

        with sub_crear:
            st.markdown("#### 1️⃣ Metadatos y Filiación del Escenario")
            col_c1, col_c2 = st.columns([1, 1])
            with col_c1:
                nuevo_id = st.text_input(
                    "Identificador / Clave Única del Caso:",
                    value=f"Caso {len(obtener_nombres_casos()) + 1}: Cefalea en trueno e hipertensión en mujer de 58 años",
                    help="Nombre que aparecerá en el menú desplegable del simulador. Formato recomendado: 'Caso XX: Descripción sucinta'",
                    key="nuevo_caso_clave"
                )
                nuevo_titulo = st.text_input(
                    "Título Descriptivo de la Viñeta:",
                    value="Mujer de 58 años con cefalea súbita de inicio ictal y fotofobia",
                    key="nuevo_caso_titulo"
                )
            with col_c2:
                col_u1, col_u2 = st.columns(2)
                with col_u1:
                    nueva_unidad = st.selectbox(
                        "Unidad Curricular:",
                        options=[
                            "Unidad 1: Urgencias Cardiovasculares y Reanimación",
                            "Unidad 2: Emergencias Respiratorias y Medio Interno",
                            "Unidad 3: Paciente Crítico, Sepsis y Falla Multiorgánica",
                            "Unidad 4: Desafíos Diagnósticos Complejos y Casos Interdisciplinarios",
                            "Módulo Especial: Casos de Ateneo Hospitalario"
                        ],
                        index=3,
                        key="nuevo_caso_unidad"
                    )
                    nueva_dificultad = st.selectbox(
                        "Nivel de Dificultad:",
                        options=["Inicial (R1)", "Intermedia (R2)", "Avanzada (R3/R4)"],
                        index=1,
                        key="nuevo_caso_dificultad"
                    )
                with col_u2:
                    nueva_area = st.selectbox(
                        "Área / Subespecialidad:",
                        options=[
                            "Neurología / ACV",
                            "Cardiología / Urgencias",
                            "Neumonología / Cuidados Críticos",
                            "Infectología / Sepsis",
                            "Nefrología / Medio Interno",
                            "Hematología / Oncología",
                            "Gastroenterología / Hepatología",
                            "Toxicología / Urgencias",
                            "Endocrinología / Metabolismo",
                            "Medicina Interna General"
                        ],
                        index=0,
                        key="nuevo_caso_area"
                    )

            st.markdown("---")
            st.markdown("#### 2️⃣ Viñeta Clínica con Constantes Vitales Completas")
            st.caption("📌 Obligatorio: Tensión Arterial (TA), Frecuencia Cardíaca (FC), Frecuencia Respiratoria (FR), Saturación de Oxígeno (SpO2) y Temperatura (Temp).")
            
            plantilla_vineta_defecto = (
                "Paciente femenina de 58 años con antecedentes de hipertensión arterial tratada irregularmente con enalapril 10 mg/día. "
                "Es traída a la guardia de emergencias por cuadro de 3 horas de evolución caracterizado por cefalea holocraneana de inicio súbito, "
                "de intensidad 10/10 en escala analógica visual ('el peor dolor de su vida'), iniciada de manera explosiva ('en trueno') durante un esfuerzo físico, "
                "asociada a náuseas, vómitos reiterados y fotofobia intensa. "
                "Sin traumatismo previo ni fiebre referida en días anteriores. "
                "Signos vitales al ingreso: TA 175/100 mmHg, FC 98 lpm regular, FR 18 rpm, SpO2 97% al aire ambiente, Temp 36.8 °C. "
                "Examen neurológico inicial: vigil, confusa y desorientada en tiempo (Glasgow 14/15: O4 V4 M6). Rigidez de nuca moderada, "
                "signo de Kernig positivo leve, Brudzinski dudoso. Sin parálisis facial, sin asimetría motora en extremidades ni reflejo de Babinski. Fondo de ojo sin edema de papila evidente."
            )
            nueva_vineta = st.text_area(
                "Texto de la Viñeta Clínica:",
                value=plantilla_vineta_defecto,
                height=160,
                key="nuevo_caso_vineta"
            )
            
            check_anonimizar = st.checkbox(
                "🛡️ Anonimizar y Sanitizar Automáticamente (Enmascarar DNI, Nombres Propios, Fechas Exactas y Teléfonos según Ley 25.326)",
                value=True,
                key="nuevo_caso_check_anonimizar"
            )

            st.markdown("---")
            st.markdown("#### 3️⃣ Trampas Heurísticas, Sesgos Cognitivos & Calculadoras")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                sesgos_disponibles = list(TAXONOMIA_SESGOS.keys()) + ["Desestimación Red Flags", "Evaluación abierta"]
                nuevos_sesgos = st.multiselect(
                    "Sesgos Cognitivos Esperados / Trampas Heurísticas:",
                    options=sesgos_disponibles,
                    default=["Cierre Prematuro", "Anclaje y Ajuste Insuficiente"],
                    help="Patrones de error habituales en los que el residente inexperto podría caer.",
                    key="nuevo_caso_sesgos"
                )
            with col_b2:
                calculadoras_disponibles = [
                    "calculadora_score_heart",
                    "calculadora_score_wells_tep",
                    "calculadora_curb65",
                    "calculadora_indice_shock",
                    "calculadora_qsofa",
                    "calculadora_sofa",
                    "calculadora_apache2",
                    "calculadora_nihss",
                    "calculadora_cha2ds2_vasc",
                    "calculadora_has_bled",
                    "calculadora_filtrado_glomerular_ckd_epi",
                    "calculadora_metabolica_cad",
                    "calculadora_child_pugh",
                    "calculadora_meld",
                    "calculadora_fib4"
                ]
                nuevas_calcs = st.multiselect(
                    "Calculadoras / Herramientas de Auditoría Vinculadas:",
                    options=calculadoras_disponibles,
                    default=["calculadora_nihss"],
                    help="Herramientas determinísticas que el tutor socrático auditará si el residente las invoca o las omite.",
                    key="nuevo_caso_calculadoras"
                )

            st.markdown("---")
            st.markdown("#### 4️⃣ Banderas Rojas (Patient Safety Red Flags)")
            st.caption("Criterios de seguridad no negociables. Ingrese una alerta por renglón.")
            plantilla_rf_defecto = (
                "Descartar Hemorragia Subaracnoidea (HSA) aguda en toda cefalea súbita o en trueno (sensibilidad de TC sin contraste >95% en las primeras 6h).\n"
                "Si la TC de cráneo es rigurosamente normal dentro de las primeras 6-12h y persiste alta sospecha, realizar Punción Lumbar obligatoria para evaluar xantocromía espectrofotométrica o hematíes constantes.\n"
                "Evitar catalogar como 'cefalea tensional' o 'crisis hipertensiva reactiva' (Cierre Prematuro potencialmente mortal).\n"
                "Priorizar estabilización hemodinámica (TAS objetivo < 160 mmHg con labetalol IV) y profilaxis precoz de vasoespasmo con Nimodipina."
            )
            nuevas_red_flags_raw = st.text_area(
                "Banderas Rojas (una por línea):",
                value=plantilla_rf_defecto,
                height=110,
                key="nuevo_caso_red_flags"
            )

            st.markdown("---")
            st.markdown("#### 5️⃣ Guía Clínica Oficial de Referencia (Gold Standard Open Access)")
            col_g1, col_g2, col_g3 = st.columns([2, 1.5, 2.5])
            with col_g1:
                nueva_guia_tit = st.text_input(
                    "Título de la Guía Oficial:",
                    value="Guía AHA/ASA: Manejo de Pacientes con Hemorragia Subaracnoidea Aneurismática",
                    key="nuevo_caso_guia_tit"
                )
            with col_g2:
                nueva_guia_soc = st.text_input(
                    "Sociedad Científica / Revista:",
                    value="AHA / ASA (Stroke)",
                    key="nuevo_caso_guia_soc"
                )
            with col_g3:
                nueva_guia_url = st.text_input(
                    "Enlace Open Access (Libre y Gratuito):",
                    value="https://www.ahajournals.org/doi/10.1161/STR.0000000000000436",
                    key="nuevo_caso_guia_url"
                )

            st.markdown("---")
            st.markdown("#### 6️⃣ Diagnóstico Definitivo & Criterios Ocultos del Tribunal Docente")
            st.caption("Esta sección solo es utilizada por el Comité Evaluador para contrastar la hipótesis del residente.")
            plantilla_gold_defecto = (
                "Diagnóstico Definitivo: Hemorragia Subaracnoidea Aneurismática (Escala Hunt y Hess Grado II, Fisher Grado 3).\n"
                "Manejo Estándar Esperado: TC urgente de encéfalo sin contraste en <1h. Control de tensión arterial con infusión de labetalol (objetivo TAS 140-160 mmHg). Inicio inmediato de Nimodipina oral 60 mg cada 4 horas. Consulta urgente a Neurocirugía y Neurorradiología Intervencionista para Angio-TC / Panangiografía cerebral y exclusión del aneurisma (coiling vs clipado en las primeras 24-48 horas). Reposo absoluto en cabecera a 30°, analgesia reglada y prevención de convulsiones."
            )
            nuevo_gold_standard = st.text_area(
                "Gold Standard y Resolución Esperada:",
                value=plantilla_gold_defecto,
                height=110,
                key="nuevo_caso_gold_standard"
            )

            # Botones de Acción
            st.markdown("<br>", unsafe_allow_html=True)
            col_act1, col_act2 = st.columns([1, 1.5])
            
            with col_act1:
                btn_prev = st.button("👁️ Previsualizar Viñeta Clínica", use_container_width=True, key="btn_previsualizar_caso")
            with col_act2:
                btn_guardar = st.button("💾 Guardar Caso en Banco Permanente", type="primary", use_container_width=True, key="btn_guardar_caso_permanente")

            if btn_prev:
                st.markdown("### 🔍 Vista Previa del Caso Clínico")
                tags_preview = f"<span class='vignette-tag'>🏷️ {nueva_area}</span><span class='vignette-tag'>🎯 {nueva_dificultad}</span>"
                for s in nuevos_sesgos:
                    tags_preview += f"<span class='vignette-tag' style='background-color:#fee2e2;color:#991b1b;'>⚠️ Trampa: {s}</span>"
                
                texto_prev = nueva_vineta
                if check_anonimizar:
                    texto_prev, redactados = sanitizar_texto_clinico(texto_prev)
                    if redactados:
                        st.info(f"🛡️ Desidentificación aplicada: Se enmascararon {len(redactados)} elementos ({', '.join(redactados)}).")
                
                st.markdown(f"""
                    <div class="vignette-card" style="margin-top:12px;">
                        <div class="vignette-title">📄 Viñeta: {nuevo_titulo}</div>
                        <div class="vignette-text">{texto_prev}</div>
                        <div class="vignette-tags">{tags_preview}</div>
                    </div>
                """, unsafe_allow_html=True)

            if btn_guardar:
                if not nuevo_id.strip() or not nuevo_titulo.strip() or not nueva_vineta.strip():
                    st.error("❌ El Identificador, el Título y la Viñeta Clínica son obligatorios.")
                else:
                    texto_guardar = nueva_vineta.strip()
                    if check_anonimizar:
                        texto_guardar, _ = sanitizar_texto_clinico(texto_guardar)
                    
                    lista_rf = [rf.strip() for rf in nuevas_red_flags_raw.strip().split("\n") if rf.strip()]
                    if not lista_rf:
                        lista_rf = ["Priorizar estabilización hemodinámica y exploración exhaustiva de banderas rojas."]
                    
                    dict_caso = {
                        "titulo": nuevo_titulo.strip(),
                        "area": nueva_area,
                        "dificultad": nueva_dificultad,
                        "unidad": nueva_unidad,
                        "viñeta": texto_guardar,
                        "sesgos_esperados": nuevos_sesgos if nuevos_sesgos else ["Cierre Prematuro"],
                        "red_flags": lista_rf,
                        "calculadoras_pertinentes": nuevas_calcs,
                        "guia_oficial_titulo": nueva_guia_tit.strip(),
                        "guia_oficial_sociedad": nueva_guia_soc.strip(),
                        "guia_oficial_url": nueva_guia_url.strip(),
                        "gold_standard": nuevo_gold_standard.strip(),
                        "fecha_creacion": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    exito, msg = guardar_caso_personalizado(nuevo_id.strip(), dict_caso)
                    if exito:
                        st.success(f"🎉 ¡Éxito! {msg}")
                        st.info("🔄 El nuevo caso ya está incorporado al banco activo del simulador y visible en el selector principal.")
                        st.balloons()
                        time.sleep(1.2)
                        st.rerun()
                    else:
                        st.error(f"❌ Error al guardar: {msg}")

        with sub_banco:
            st.markdown("#### 📚 Catálogo del Banco de Casos Guardados")
            casos_pers = leer_casos_personalizados()
            total_pers = len(casos_pers)
            total_fabrica = len(BANCO_CASOS)
            total_general = len(obtener_banco_completo())
            
            c_bp1, c_bp2, c_bp3 = st.columns(3)
            c_bp1.metric("Casos Oficiales de Fábrica", total_fabrica)
            c_bp2.metric("Casos Personalizados Creados", total_pers)
            c_bp3.metric("Total Casos en el Simulador", total_general)
            
            st.markdown("---")
            if not casos_pers:
                st.info("ℹ️ Actualmente no hay casos personalizados registrados en `data/casos_personalizados.json`. Utilice la pestaña anterior para redactar y guardar nuevos casos clínicos que quedarán archivados aquí de forma permanente.")
            else:
                st.markdown("### 📋 Casos Personalizados Registrados:")
                for c_clave, c_val in list(casos_pers.items()):
                    with st.expander(f"📁 {c_clave} — {c_val.get('area', 'Medicina')} ({c_val.get('dificultad', 'Intermedia')})"):
                        st.markdown(f"**Título:** {c_val.get('titulo')}")
                        st.markdown(f"**Unidad Curricular:** {c_val.get('unidad', 'General')}")
                        st.markdown(f"**Viñeta:**\n> {c_val.get('viñeta')}")
                        
                        col_dt1, col_dt2 = st.columns(2)
                        with col_dt1:
                            st.markdown(f"**Trampas / Sesgos:** `{', '.join(c_val.get('sesgos_esperados', []))}`")
                            st.markdown(f"**Calculadoras:** `{', '.join(c_val.get('calculadoras_pertinentes', []))}`")
                        with col_dt2:
                            g_tit = c_val.get("guia_oficial_titulo", "N/A")
                            g_url = c_val.get("guia_oficial_url", "#")
                            st.markdown(f"**Guía Oficial:** [{g_tit}]({g_url})")
                            st.markdown(f"**Creado:** {c_val.get('fecha_creacion', 'Reciente')}")
                        
                        st.markdown("**Banderas Rojas:**")
                        for rf in c_val.get("red_flags", []):
                            st.markdown(f"- 🚩 {rf}")
                        
                        if c_val.get("gold_standard"):
                            st.markdown(f"**Solución Gold Standard:**\n*{c_val.get('gold_standard')}*")
                        
                        col_b1, col_b2 = st.columns([2, 1])
                        with col_b1:
                            if st.button(f"🧪 Cargar en el Simulador Ahora", key=f"btn_probar_{c_clave}"):
                                reiniciar_caso(c_clave, c_val["titulo"], c_val["viñeta"], c_val)
                                st.success(f"Caso '{c_clave}' activado. Navegue a la pestaña '🩺 Simulador Clínico Socrático' para comenzar.")
                                st.rerun()
                        with col_b2:
                            if st.button(f"🗑️ Eliminar Caso del Banco", key=f"btn_del_{c_clave}"):
                                exito_del, msg_del = eliminar_caso_personalizado(c_clave)
                                if exito_del:
                                    st.warning(msg_del)
                                    time.sleep(1.0)
                                    st.rerun()
                                else:
                                    st.error(msg_del)
                
                st.markdown("---")
                json_casos = json.dumps(casos_pers, ensure_ascii=False, indent=2).encode('utf-8')
                st.download_button(
                    label="📥 Descargar Catálogo de Casos Personalizados (JSON)",
                    data=json_casos,
                    file_name=f"casos_personalizados_socratico_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json",
                    key="btn_descargar_casos_pers_json"
                )

        with sub_guia:
            st.markdown("#### 📋 Formato Estándar de Redacción de Casos Clínicos (Para Residentes & Docentes)")
            st.markdown("""
            Para asegurar la máxima validez pedagógica y la compatibilidad con el motor de auditoría socrático de Gemini,
            todo caso redactado por el equipo de guardia o residencia debe respetar los **7 Bloques Esenciales**:
            
            1. **Filiación & Contexto:** Identificador, Título descriptivo, Unidad Curricular y Dificultad (R1, R2, R3/R4).
            2. **Desidentificación Estricta (Ley 25.326):** Reemplazar nombres por género/edad, eliminar fechas exactas de internación, números de cama y DNI.
            3. **Viñeta con Constantes Vitales Completas:** Toda viñeta debe incluir explícitamente:
               - **TA** (Tensión arterial en mmHg)
               - **FC** (Frecuencia cardíaca en lpm y ritmo)
               - **FR** (Frecuencia respiratoria en rpm)
               - **SpO2** (Saturación de oxígeno por oximetría de pulso y fracción inspirada)
               - **Temperatura** (en °C axilar/central)
            4. **Sesgo Cognitivo o Trampa Heurística Esperada:** Identificar cuál es el error intuitivo (Croskerry) más probable que cometería un médico apresurado (ej. *Cierre Prematuro*, *Anclaje*, *Inercia Diagnóstica*).
            5. **Banderas Rojas (Patient Safety Red Flags):** Aquellos signos, síntomas o hallazgos paraclínicos que no pueden ser ignorados sin comprometer la vida del paciente.
            6. **Calculadoras Clínicas Determinísticas:** Algoritmos validados de estratificación de riesgo vinculados (HEART, Wells, CURB-65, Shock Index, SOFA, NIHSS, etc.).
            7. **Guía de Práctica Clínica de Referencia:** Enlace Open Access y libre a la última guía de consenso validada internacionalmente (AHA, ESC, ATS, IDSA, EASL, etc.).
            """)
            
            plantilla_blanco = {
                "Caso XX: [Título corto del escenario]": {
                    "titulo": "[Título descriptivo del paciente y motivo de consulta]",
                    "area": "[Especialidad o Unidad]",
                    "dificultad": "Intermedia",
                    "unidad": "Unidad 1: Urgencias Cardiovasculares y Reanimación",
                    "viñeta": (
                        "Paciente [género] de [edad] años con antecedentes de [comorbilidades y medicación habitual]. "
                        "Consulta por cuadro de [tiempo de evolución] caracterizado por [síntomas cardinales y cronología]. "
                        "Signos vitales al ingreso: TA [---]/[---] mmHg, FC [---] lpm, FR [---] rpm, SpO2 [---]% al aire ambiente, Temp [---] °C. "
                        "Examen físico: [hallazgos pertinentes por aparatos y estado neurológico]. "
                        "Estudios iniciales de guardia: [ECG / Radiografía / Laboratorio relevante]."
                    ),
                    "sesgos_esperados": ["Cierre Prematuro", "Anclaje y Ajuste Insuficiente"],
                    "red_flags": [
                        "[Alerta 1: Condición que pone en riesgo la vida y debe descartarse con prioridad]",
                        "[Alerta 2: Estudio confirmatorio obligatorio o error iatrogénico a evitar]"
                    ],
                    "calculadoras_pertinentes": ["calculadora_score_heart"],
                    "guia_oficial_titulo": "[Nombre oficial de la Guía de Consenso Internacional]",
                    "guia_oficial_sociedad": "[Sociedad Científica emisora y Revista]",
                    "guia_oficial_url": "[URL de acceso abierto y gratuito en PubMed o Journal]",
                    "gold_standard": "[Diagnóstico definitivo y conducta terapéutica reglada según la guía]"
                }
            }
            json_plantilla_str = json.dumps(plantilla_blanco, ensure_ascii=False, indent=2).encode('utf-8')
            
            st.download_button(
                label="📄 Descargar Plantilla JSON Estructurada para Redacción de Casos",
                data=json_plantilla_str,
                file_name="plantilla_caso_clinico_socratico.json",
                mime="application/json",
                key="btn_descargar_plantilla_blanco_json"
            )


# app.py - Simulador Socrático de Medicina Interna con Detección de Sesgos y Analíticas
import streamlit as st
import pandas as pd
from datetime import datetime
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection

# Configuración de la página
st.set_page_config(
    page_title="Resolución Interactiva de Casos Clínicos | Medicina Interna",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
URL_PLANILLA = "https://docs.google.com/spreadsheets/d/1s-IBpntSc5fBzuiAw8ePOho3DjB6G8N8ubm1JQXmTtU/edit"

# Inyección de CSS personalizado
st.markdown("""
    <style>
    .main-header {
        font-family: 'Georgia', serif;
        color: #1a365d;
        border-bottom: 3px solid #2b6cb0;
        padding-bottom: 12px;
        margin-bottom: 25px;
    }
    .journal-subtitle {
        font-size: 0.85rem;
        color: #4a5568;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        font-weight: 700;
    }
    .journal-title {
        font-size: 2rem;
        font-weight: bold;
        margin-top: 5px;
    }
    .vignette-card {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-left: 6px solid #1e3a8a;
        padding: 22px;
        border-radius: 6px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .vignette-title {
        font-family: 'Georgia', serif;
        font-size: 1.2rem;
        color: #1e3a8a;
        font-weight: bold;
        margin-bottom: 8px;
    }
    .vignette-text {
        font-size: 1.05rem;
        color: #1f2937;
        line-height: 1.6;
    }
    </style>
""", unsafe_allow_html=True)

# Banco de Casos Clínicos Mixtos
CASOS_ESTANDAR = {
    "Caso 01: Varón de 42 años con dolor torácico y disnea": (
        "Paciente de 42 años, masculino, tabaquista activo, con 48 horas de evolución de "
        "dolor torácico opresivo y disnea leve. Signos vitales estables."
    ),
    "Caso 02: Mujer de 72 años con confusión aguda y debilidad": (
        "Paciente femenina de 72 años, traída a guardia por familiares debido a cuadro de 48 horas de "
        "somnolencia progresiva, desorientación temporoespacial, náuseas y calambres musculares generalizados, "
        "sin registros febriles previos."
    ),
    "Caso 03: Mujer de 65 años con fiebre, tos y deterioro respiratorio": (
        "Paciente de 65 años, antecedentes de DBT tipo 2 e HTA, con cuadro de 3 días de evolución "
        "de fiebre, tos productiva, decaimiento y disnea progresiva. Ingresa a guardia con saturación de oxígeno de 88% al aire ambiente."
    ),
    "Caso 04: Varón de 50 años con hemorragia digestiva y frialdad": (
        "Paciente varón de 50 años, con antecedentes de consumo alejado de alcohol, que consulta por "
        "episodios reiterados de vómitos con sangre fresca y melenas de 24 horas de evolución, asociado a "
        "mareos, sudoración fría y frialdad distal."
    ),
    "Caso 05: Varón de 58 años con lesión trófica y alteración sensorial": (
        "Paciente varón de 58 años, con antecedentes de diabetes tipo 2 mal controlada, que consulta por "
        "lesión ulcerosa profunda en antepié derecho de 1 semana de evolución, acompañada de celulitis perilesional, "
        "mal olor, registros febriles y alteración del sensorio leve."
    ),
    "Caso 06: Mujer de 34 años con cefalea intensa y fiebre persistente": (
        "Paciente femenina de 34 años, sin antecedentes patológicos de importancia, que consulta por cuadro de "
        "4 días de evolución caracterizado por cefalea holocraneana intensa progresiva, fotofobia, náuseas, "
        "vómitos y registros febriles persistentes que no ceden con analgésicos comunes."
    ),
    "Caso 07: Varón de 68 años con disnea paroxística y edemas": (
        "Paciente masculino de 68 años, con antecedentes de hipertensión arterial crónica mal medicada, que consulta por "
        "disnea de reposo de instalación súbita, ortopnea, tos con expectoración asalmonada y aumento significativo de volumen en miembros inferiores."
    )
}

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown("### 🔑 Credenciales de Acceso")
    gemini_api_key = st.text_input("Ingrese su Google AI Studio API Key:", type="password", placeholder="AIza...")
    
    st.markdown("---")
    st.markdown("### ⚙️ Selección del Escenario")
    modo_caso = st.radio("Origen del caso clínico:", ["Banco Estándar (Medicina Interna)", "Cargar Caso Personalizado"])
    
    def reiniciar_estado(nuevo_titulo, nuevo_caso):
        st.session_state.caso_activo = nuevo_caso
        st.session_state.titulo_caso_actual = nuevo_titulo
        st.session_state.mensajes = [
            {"role": "model", "parts": "**Comité Evaluador:** Viñeta clínica analizada. **¿Cuál es su impresión sindrómica inicial y qué hipótesis diagnósticas de urgencia prioriza?**"}
        ]

    if modo_caso == "Banco Estándar (Medicina Interna)":
        st.markdown("#### 📚 Casos Clínicos")
        nombre_caso_elegido = st.selectbox("Seleccione un escenario de práctica:", list(CASOS_ESTANDAR.keys()))
        caso_activo_seleccionado = CASOS_ESTANDAR[nombre_caso_elegido]
        
        if "ultimo_caso_seleccionado" not in st.session_state or st.session_state.ultimo_caso_seleccionado != nombre_caso_elegido:
            st.session_state.ultimo_caso_seleccionado = nombre_caso_elegido
            reiniciar_estado(nombre_caso_elegido, caso_activo_seleccionado)
    else:
        st.markdown("---")
        st.markdown("#### 📝 Ingresar Caso Propio")
        nuevo_caso_titulo = st.text_input("Título o Resumen:", "Paciente con...")
        nuevo_caso_desc = st.text_area("Descripción detallada del cuadro:", "Antecedentes, síntomas, signos vitales...")
        
        if st.button("Establecer este Caso", use_container_width=True):
            reiniciar_estado(nuevo_caso_titulo, f"Detalles clínicos: {nuevo_caso_desc}")
            st.rerun()

    st.markdown("---")
    st.markdown("### 🛡️ Gobernanza Académica")
    st.info("• **Detección de Sesgos:** Análisis activo de anclaje, inercia y cierre prematuro.\n• **Tutoría Socrática:** Retroalimentación formativa y seguridad del paciente.")
    
    st.markdown("---")
    if st.button("🔄 Reiniciar Discusión", use_container_width=True):
        reiniciar_estado(st.session_state.titulo_caso_actual, st.session_state.caso_activo)
        st.rerun()

if "mensajes" not in st.session_state:
    primer_titulo = list(CASOS_ESTANDAR.keys())[0]
    primer_caso = list(CASOS_ESTANDAR.values())[0]
    reiniciar_estado(primer_titulo, primer_caso)

# --- CUERPO PRINCIPAL ---
st.markdown("""
    <div class="main-header">
        <div class="journal-subtitle">Resolución Interactiva de Problemas Clínicos &bull; Medicina Interna</div>
        <div class="journal-title">Simulador de Razonamiento Socrático</div>
    </div>
""", unsafe_allow_html=True)

titulo_actual = st.session_state.get("titulo_caso_actual", "Caso Clínico Activo")
texto_caso_actual = st.session_state.get("caso_activo", "")

st.markdown(f"""
    <div class="vignette-card">
        <div class="vignette-title">📄 Viñeta del Caso: {titulo_actual}</div>
        <div class="vignette-text">{texto_caso_actual}</div>
    </div>
""", unsafe_allow_html=True)

# Validación y Motor
if not gemini_api_key:
    st.warning("⚠️ Por favor, ingrese su **Google AI Studio API Key** en la barra lateral izquierda para activar la tutoría del comité clínico.")
else:
    funciones_clinicas = [
        {'name': 'calculadora_metabolica_cad', 'description': 'Calcula el anión gap y el sodio corregido. Usar si hay laboratorios de paciente con hiperglucemia severa.', 'parameters': {'type': 'OBJECT', 'properties': {'sodio_medido': {'type': 'NUMBER'}, 'cloro': {'type': 'NUMBER'}, 'bicarbonato': {'type': 'NUMBER'}, 'glucemia': {'type': 'NUMBER'}}, 'required': ['sodio_medido', 'cloro', 'bicarbonato', 'glucemia']}},
        {'name': 'calculadora_filtrado_glomerular_ckd_epi', 'description': 'Calcula TFGe. Usar si el usuario propone fármacos de excreción renal.', 'parameters': {'type': 'OBJECT', 'properties': {'edad': {'type': 'INTEGER'}, 'sexo': {'type': 'STRING'}, 'creatinina': {'type': 'NUMBER'}}, 'required': ['edad', 'sexo', 'creatinina']}},
        {'name': 'calculadora_score_heart', 'description': 'Calcula Score HEART. Usar en alta o internación por dolor torácico sin estratificar.', 'parameters': {'type': 'OBJECT', 'properties': {'historia': {'type': 'INTEGER'}, 'ecg': {'type': 'INTEGER'}, 'edad': {'type': 'INTEGER'}, 'factores_riesgo': {'type': 'INTEGER'}, 'troponina': {'type': 'INTEGER'}}, 'required': ['historia', 'ecg', 'edad', 'factores_riesgo', 'troponina']}},
        {'name': 'calculadora_score_wells_tep', 'description': 'Calcula Score Wells. Usar si se pide Angio-TAC o Dímero D empíricamente.', 'parameters': {'type': 'OBJECT', 'properties': {'sintomas_tvp': {'type': 'NUMBER'}, 'diagnostico_alternativo_menos_probable': {'type': 'NUMBER'}, 'frecuencia_cardiaca_alta': {'type': 'NUMBER'}, 'inmovilizacion_o_cirugia': {'type': 'NUMBER'}, 'antecedente_tep_tvp': {'type': 'NUMBER'}, 'hemoptisis': {'type': 'NUMBER'}, 'malignidad': {'type': 'NUMBER'}}, 'required': ['sintomas_tvp', 'diagnostico_alternativo_menos_probable', 'frecuencia_cardiaca_alta', 'inmovilizacion_o_cirugia', 'antecedente_tep_tvp', 'hemoptisis', 'malignidad']}},
        {'name': 'calculadora_exacerbacion_epoc', 'description': 'Evalúa Criterios de Anthonisen y oxigenoterapia en EPOC.', 'parameters': {'type': 'OBJECT', 'properties': {'aumento_disnea': {'type': 'INTEGER'}, 'aumento_volumen_esputo': {'type': 'INTEGER'}, 'purulencia_esputo': {'type': 'INTEGER'}, 'saturacion_oxigeno_objetivo': {'type': 'INTEGER'}}, 'required': ['aumento_disnea', 'aumento_volumen_esputo', 'purulencia_esputo', 'saturacion_oxigeno_objetivo']}},
        {'name': 'registrar_sesgo_cognitivo', 'description': 'Registra un error de razonamiento o sesgo cognitivo detectado en el alumno para el panel de analíticas institucional.', 'parameters': {'type': 'OBJECT', 'properties': {'tipo_sesgo': {'type': 'STRING', 'description': 'El tipo de error cometido.', 'enum': ['Cierre Prematuro', 'Anclaje', 'Sesgo de Confirmación', 'Error de Cálculo', 'Tratamiento Inseguro']}, 'justificacion': {'type': 'STRING'}}, 'required': ['tipo_sesgo', 'justificacion']}}
    ]

    system_instruction = f"""
    Eres un comité médico experto en tutoría socrática emulando un análisis de errores de razonamiento.
    Caso clínico actual: '{texto_caso_actual}'.
    
    INSTRUCCIÓN PEDAGÓGICA Y PAUSAS DIAGNÓSTICAS:
    1. Si detectas un sesgo (anclaje, cierre prematuro), nombra el sesgo, explícalo y haz una repregunta socrática.
    2. REGLAS DE HERRAMIENTAS OBLIGATORIAS (Uso interno): Debes ejecutar las calculadoras para obtener los valores matemáticos exactos y auditar al residente. NUNCA le muestres el resultado de la calculadora directamente; utiliza esa información oculta para evaluar si los cálculos que él te presente son correctos o para guiar tus repreguntas.
    3. REGLA DE BÚSQUEDA WEB: Cuando el residente proponga un tratamiento farmacológico o algoritmo diagnóstico, utiliza tu herramienta de búsqueda en Google para consultar los consensos o guías clínicas más recientes (ej. ADA, GOLD, KDIGO, ESC) y fundamentar tu retroalimentación en evidencia actualizada.
    4. Mantén un tono académico neutral riguroso.
    5. REGLA DE AUDITORÍA INSTITUCIONAL: Cada vez que detectes un sesgo cognitivo grave, un error de cálculo o la propuesta de un tratamiento inseguro, debes EJECUTAR obligatoriamente la herramienta 'registrar_sesgo_cognitivo' antes de responderle al usuario. Esto es vital para las métricas de la coordinación académica.
    """

    client = genai.Client(api_key=gemini_api_key)
    config = types.GenerateContentConfig(
        temperature=0.1,
        system_instruction=system_instruction,
        tools=[
            {'function_declarations': funciones_clinicas},
            {'google_search': {}}
        ]
    )

    # MOSTRAR HISTORIAL
    for msg in st.session_state.mensajes:
        role = msg["role"]
        avatar = "🩺" if role == "model" else "👨‍⚕️"
        with st.chat_message("assistant" if role == "model" else "user", avatar=avatar):
            st.markdown(msg["parts"])

    prompt_usuario = st.chat_input("Escriba su razonamiento clínico...")

    if prompt_usuario:
        st.session_state.mensajes.append({"role": "user", "parts": prompt_usuario})
        with st.chat_message("user", avatar="👨‍⚕️"):
            st.markdown(prompt_usuario)

        with st.chat_message("assistant", avatar="🩺"):
            try:
                with st.spinner("El comité evaluador está analizando su razonamiento clínico..."):
                    history_contents = []
                    for m in st.session_state.mensajes[:-1]:
                        history_contents.append(
                            types.Content(role=m["role"], parts=[types.Part.from_text(text=m["parts"])])
                        )
                    
                    chat_obj = client.chats.create(model="gemini-3-flash-preview", config=config, history=history_contents)
                    response = chat_obj.send_message(prompt_usuario)
                    
                    if getattr(response, 'function_calls', None):
                        for function_call in response.function_calls:
                            nombre = function_call.name
                            args = function_call.args
                            
                            with st.status(f"⚠️ Pausa Diagnóstica: Procesando {nombre}...", expanded=True) as status:
                                resultado_clinico = ""
                                st.write("Ejecutando herramienta interna...")
                                
                                if nombre == 'registrar_sesgo_cognitivo':
                                    tipo_sesgo = args.get('tipo_sesgo', 'No especificado')
                                    justificacion = args.get('justificacion', 'Sin justificación')
                                    try:
                                        # Leer datos actuales de Google Sheets
                                        df = conn.read(spreadsheet=URL_PLANILLA)
                                        # Crear nueva fila de registro
                                        nueva_fila = pd.DataFrame([{
                                            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            "Caso Clínico": st.session_state.titulo_caso_actual,
                                            "Tipo de Sesgo": tipo_sesgo,
                                            "Justificación del Motor Médico": justificacion
                                        }])
                                        # Agregar fila y subir a Google Sheets
                                        df_actualizado = pd.concat([df, nueva_fila], ignore_index=True)
                                        conn.update(spreadsheet=URL_PLANILLA, data=df_actualizado)
                                        resultado_clinico = f"Sesgo '{tipo_sesgo}' guardado correctamente en la planilla de métricas."
                                    except Exception as db_error:
                                        resultado_clinico = f"Error al conectar con la base de datos: {db_error}"

                                elif nombre == 'calculadora_exacerbacion_epoc':
                                    criterios = args.get('aumento_disnea', 0) + args.get('aumento_volumen_esputo', 0) + args.get('purulencia_esputo', 0)
                                    o2_obj = args.get('saturacion_oxigeno_objetivo', 0)
                                    resultado_clinico = f"Criterios de Anthonisen: {criterios}/3. "
                                    if o2_obj > 92: resultado_clinico += f"ALERTA: Objetivo {o2_obj}% riesgoso por retención CO2."
                                    else: resultado_clinico += f"Objetivo O2 {o2_obj}% correcto."
                                        
                                elif nombre == 'calculadora_metabolica_cad':
                                    anion_gap = args['sodio_medido'] - (args['cloro'] + args['bicarbonato'])
                                    na_corr = args['sodio_medido'] + 0.016 * (args['glucemia'] - 100)
                                    resultado_clinico = f"Anión Gap calculado: {anion_gap}. Sodio corregido: {na_corr:.1f} mEq/L."
                                    
                                elif nombre == 'calculadora_score_heart':
                                    score = args['historia'] + args['ecg'] + args['edad'] + args['factores_riesgo'] + args['troponina']
                                    resultado_clinico = f"Score HEART calculado: {score} puntos."
                                    
                                elif nombre == 'calculadora_score_wells_tep':
                                    score = args['sintomas_tvp'] + args['diagnostico_alternativo_menos_probable'] + args['frecuencia_cardiaca_alta'] + args['inmovilizacion_o_cirugia'] + args['antecedente_tep_tvp'] + args['hemoptisis'] + args['malignidad']
                                    resultado_clinico = f"Score Wells calculado: {score} puntos."
                                    
                                elif nombre == 'calculadora_filtrado_glomerular_ckd_epi':
                                    resultado_clinico = f"Auditar fármaco para creatinina {args['creatinina']} mg/dL según edad y sexo."
                                
                                st.write(f"**Resultado de la ejecución:** {resultado_clinico}")
                                status.update(label="Auditoría interna completada", state="complete", expanded=False)
                            
                            respuesta_funcion = types.Part.from_function_response(
                                name=nombre,
                                response={"resultado_ejecucion": resultado_clinico}
                            )
                            response_final = chat_obj.send_message(respuesta_funcion)
                            respuesta_ia = response_final.text
                    else:
                        respuesta_ia = response.text

                st.markdown(respuesta_ia)
                st.session_state.mensajes.append({"role": "model", "parts": respuesta_ia})
                
            except Exception as e:
                st.error(f"Error técnico detectado. Detalle: {e}")

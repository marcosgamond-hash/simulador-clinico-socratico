# app.py - Simulador Socrático de Medicina Interna con Detección de Sesgos
import streamlit as st
import google.generativeai as genai

# Configuración de la página
st.set_page_config(
    page_title="Resolución Interactiva de Casos Clínicos | Medicina Interna",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inyección de CSS personalizado (Estilo editorial sobrio)
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

# Banco de Casos Clínicos Mixtos (Medicina Interna)
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

# --- BARRA LATERAL: CONFIGURACIÓN Y GOBERNANZA ---
with st.sidebar:
    st.markdown("### 🔑 Credenciales de Acceso")
    gemini_api_key = st.text_input("Ingrese su Google AI Studio API Key:", type="password", placeholder="AIza...")
    
    st.markdown("---")
    st.markdown("### ⚙️ Selección del Escenario")
    modo_caso = st.radio("Origen del caso clínico:", ["Banco Estándar (Medicina Interna)", "Cargar Caso Personalizado"])
    
    if modo_caso == "Banco Estándar (Medicina Interna)":
        st.markdown("#### 📚 Casos Clínicos")
        nombre_caso_elegido = st.selectbox("Seleccione un escenario de práctica:", list(CASOS_ESTANDAR.keys()))
        caso_activo_seleccionado = CASOS_ESTANDAR[nombre_caso_elegido]
        
        if "ultimo_caso_seleccionado" not in st.session_state or st.session_state.ultimo_caso_seleccionado != nombre_caso_elegido:
            st.session_state.ultimo_caso_seleccionado = nombre_caso_elegido
            st.session_state.caso_activo = caso_activo_seleccionado
            st.session_state.titulo_caso_actual = nombre_caso_elegido
            st.session_state.mensajes = [
                {"role": "model", "parts": ["**Comité Evaluador:** Viñeta clínica analizada. **¿Cuál es su impresión sindrómica inicial y qué hipótesis diagnósticas de urgencia prioriza?**"]}
            ]
    else:
        st.markdown("---")
        st.markdown("#### 📝 Ingresar Caso Propio")
        nuevo_caso_titulo = st.text_input("Título o Resumen:", "Paciente con...")
        nuevo_caso_desc = st.text_area("Descripción detallada del cuadro:", "Antecedentes, síntomas, signos vitales...")
        
        if st.button("Establecer este Caso", use_container_width=True):
            st.session_state.caso_activo = f"Detalles clínicos: {nuevo_caso_desc}"
            st.session_state.titulo_caso_actual = nuevo_caso_titulo
            st.session_state.mensajes = [
                {"role": "model", "parts": ["**Comité Evaluador:** Caso personalizado cargado exitosamente. **¿Cuál es su impresión sindrómica inicial y qué hipótesis diagnóstica prioriza?**"]}
            ]
            st.rerun()

    st.markdown("---")
    st.markdown("### 🛡️ Gobernanza Académica")
    st.info("• **Detección de Sesgos:** Análisis activo de anclaje, inercia y cierre prematuro.\n• **Tutoría Socrática:** Retroalimentación formativa y seguridad del paciente.")
    
    st.markdown("---")
    if st.button("🔄 Reiniciar Discusión", use_container_width=True):
        st.session_state.mensajes = [
            {"role": "model", "parts": ["**Comité Evaluador:** Discusión reiniciada. **¿Cuál es su impresión sindrómica inicial y qué hipótesis diagnóstica prioriza?**"]}
        ]
        st.rerun()

# Inicialización por defecto del historial si no existe
if "mensajes" not in st.session_state:
    primer_titulo = list(CASOS_ESTANDAR.keys())[0]
    primer_caso = list(CASOS_ESTANDAR.values())[0]
    st.session_state.caso_activo = primer_caso
    st.session_state.titulo_caso_actual = primer_titulo
    st.session_state.mensajes = [
        {"role": "model", "parts": ["**Comité Evaluador:** Viñeta clínica analizada. **¿Cuál es su impresión sindrómica inicial y qué hipótesis diagnósticas de urgencia prioriza?**"]}
    ]

# --- CUERPO PRINCIPAL ---
st.markdown("""
    <div class="main-header">
        <div class="journal-subtitle">Resolución Interactiva de Problemas Clínicos &bull; Medicina Interna</div>
        <div class="journal-title">Simulador de Razonamiento Socrático</div>
    </div>
""", unsafe_allow_html=True)

# Tarjeta de Viñeta Clínica Activa
titulo_actual = st.session_state.get("titulo_caso_actual", "Caso Clínico Activo")
texto_caso_actual = st.session_state.get("caso_activo", "")

st.markdown(f"""
    <div class="vignette-card">
        <div class="vignette-title">📄 Viñeta del Caso: {titulo_actual}</div>
        <div class="vignette-text">{texto_caso_actual}</div>
    </div>
""", unsafe_allow_html=True)

# Validación de API Key e Interacción
if not gemini_api_key:
    st.warning("⚠️ Por favor, ingrese su **Google AI Studio API Key** en la barra lateral izquierda para activar la tutoría del comité clínico.")
else:
    genai.configure(api_key=gemini_api_key)

    system_instruction = f"""
    Eres un comité médico experto en tutoría socrática y seguridad del paciente para médicos residentes, emulando un comité de análisis de errores de razonamiento clínico.
    El caso clínico actual sobre el que debes guiar al residente es: '{st.session_state.caso_activo}'.
    
    INSTRUCCIÓN PEDAGÓGICA Y DETECCIÓN DE SESGOS:
    1. Analiza minuciosamente la respuesta del residente en busca de sesgos cognitivos frecuentes (ej. Sesgo de anclaje, Cierre prematuro, Inercia clínica, Sesgo de confirmación o Disponibilidad).
    2. Si detectas que el residente cae en un sesgo evidente, estructura tu respuesta obligatoriamente en tres momentos:
       - **Alerta Metacognitiva:** Nombra claramente el sesgo detectado (por ejemplo: *"Se observa una tendencia al sesgo de anclaje al focalizar..."*).
       - **Explicación Formativa:** Explica de forma concisa y rigurosa en qué consiste ese sesgo y por qué representa un riesgo crítico para el diagnóstico diferencial y la seguridad del paciente.
       - **Repregunta Socrática:** Cierra con una pregunta clínica desafiante que lo obligue a revaluar los datos negativos o alternativos que pasó por alto.
    3. Si el razonamiento es sólido y clínico, continúa con la profundización socrática sin necesidad de bloquearlo con teoría.
    4. Mantén un tono académico, formal, riguroso, neutral y estrictamente en castellano neutro.
    """

    model = genai.GenerativeModel(
        model_name="gemini-3.6-flash",
        system_instruction=system_instruction
    )

    # Mostrar historial de la discusión clínica
    for msg in st.session_state.mensajes:
        role = msg["role"]
        avatar = "🩺" if role == "model" else "👨‍⚕️"
        text_content = msg["parts"][0] if isinstance(msg["parts"], list) else msg["parts"]
        with st.chat_message("assistant" if role == "model" else "user", avatar=avatar):
            st.markdown(text_content)

    # Entrada del usuario
    prompt_usuario = st.chat_input("Escriba su razonamiento clínico, hipótesis o respuesta al comité...")

    if prompt_usuario:
        st.session_state.mensajes.append({"role": "user", "parts": [prompt_usuario]})
        with st.chat_message("user", avatar="👨‍⚕️"):
            st.markdown(prompt_usuario)

        with st.chat_message("assistant", avatar="🩺"):
            with st.spinner("El comité evaluador está analizando su razonamiento clínico..."):
                try:
                    chat_history = []
                    for m in st.session_state.mensajes[:-1]:
                        chat_history.append({
                            "role": m["role"],
                            "parts": m["parts"] if isinstance(m["parts"], list) else [m["parts"]]
                        })

                    chat = model.start_chat(history=chat_history)
                    response = chat.send_message(prompt_usuario)
                    respuesta_ia = response.text

                    st.markdown(respuesta_ia)
                    st.session_state.mensajes.append({"role": "model", "parts": [respuesta_ia]})
                except Exception as e:
                    st.error(f"Error al conectar con la API de Gemini: {e}")
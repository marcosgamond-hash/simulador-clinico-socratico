# -*- coding: utf-8 -*-
# SOCRATICO - SIMULADOR DE RAZONAMIENTO CLINICO Y GOBERNANZA EN URGENCIAS
# Version Monolitica 100% Autosuficiente para Hugging Face Spaces.
import sys
import os
import re
import json
import time
import math
import uuid
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Callable

import streamlit as st
import pandas as pd
import altair as alt
from google import genai
from google.genai import types

# ---------------------------------------------------------
# CONFIGURACION DE PAGINA: PRIMER COMANDO STREAMLIT
# ---------------------------------------------------------
APP_TITLE = "Socrático: Simulador de Razonamiento Clínico & Gobernanza en Urgencias"
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Skills clinicas embebidas (Evidence on Demand)
SKILLS_EMBEDDED: Dict[str, str] = {
  "guia_acv_isquemico_aha": "# Guía de Práctica Clínica: Manejo del ACV Isquémico Agudo (AHA/ASA)\n\n## 1. Evaluación Inicial y Tiempos Críticos (\"Time is Brain\")\n* **Meta Puerta-Aguja (Door-to-Needle):** Menor a 60 minutos (idealmente < 45 minutos).\n* **Descarte Inmediato de Stroke Mimics:**\n  * **Glucemia capilar urgente:** Si glucemia < 50 mg/dL, administrar dextrosa hipertónica de inmediato (la hipoglucemia produce focalidad neurológica indistinguible de un ACV).\n  * Otros mimics: Crisis epiléptica con parálisis de Todd, migraña hemipléjica, conversión somatomorfa.\n* **Neuroimagen sin Contraste (TAC de Encéfalo):**\n  * Objetivo primordial: **Descartar hemorragia intracraneal** y evaluar signos tempranos de isquemia extensa (Score ASPECTS < 6 contraindica trombolisis).\n\n---\n\n## 2. Trombolisis Endovenosa (rtPA / Alteplase / Tenecteplase)\n* **Ventana Terapéutica:** Hasta **4.5 horas** desde el inicio de los síntomas (o última vez visto sano).\n* **Control Estricto de Presión Arterial:**\n  * Para trombolizar: **TA debe ser < 185/110 mmHg**.\n  * Si la TA es mayor: Administrar Labetalol 10-20 mg EV en 1-2 min o Nicardipina en infusión continua.\n  * Mantener TA < 180/105 mmHg durante las primeras 24 horas post-trombolisis.\n* **Contraindicaciones Mayores:**\n  * Evidencia de hemorragia en TAC.\n  * ACV isquémico severo o traumatismo craneoencefálico grave en los últimos 3 meses.\n  * Uso de anticoagulantes orales de acción directa (DOACs) en las últimas 48 hs con alteración de coagulograma.\n  * Plaquetas < 100.000/mm³, RIN > 1.7.\n\n---\n\n## 3. Trombectomía Mecánica (Terapia Endovascular)\n* **Indicación:** Oclusión de gran vaso en circulación anterior (Carótida interna intracraneal o segmento M1 de Arteria Cerebral Media).\n* **Ventana:** Hasta **6 horas** de rutina, y hasta **24 horas** si cumple criterios de neuroimagen avanzada por perfusión (protocolos DAWN / DEFUSE-3: tejido infartado pequeño con gran área de penumbra salvable).\n",
  "guia_cetoacidosis_diabetica": "# Protocolo Clínico: Crisis Hiperglucémicas (CAD y EHH)\n\n## 1. Evaluación Inicial y Diagnóstico de Gravedad\n* **Triada de Cetoacidosis Diabética (CAD):**\n  * Hiperglucemia (> 200-250 mg/dL, o CAD euglucémica en usuarios de iSGLT2).\n  * Acidosis metabólica con Anión Gap elevado (pH < 7.30, HCO3 < 18 mEq/L, Anión Gap > 12).\n  * Cetonemia (beta-hidroxibutirato ≥ 3.0 mmol/L) o cetonuria marcada.\n* **Estado Hiperosmolar Hiperglucémico (EHH):**\n  * Glucemia severa (> 600 mg/dL), Osmolaridad plasmática efectiva > 320 mOsm/kg, sin acidosis significativa ni cetonemia.\n\n## 2. Pilares de Tratamiento Secuencial\n\n### Paso 1: Hidratación Parenteral Precoz (Prioridad #1)\n* Solución Salina Isotónica 0.9% a **1000 - 1500 mL en la primera hora** para restaurar volemia efectiva.\n* Luego evaluar sodio corregido (fórmula de Katz: Na medido + 0.016 * [Glucemia - 100]):\n  * Si Na corregido es normal o alto: pasar a Solución Salina al 0.45% (250-500 mL/h).\n  * Si Na corregido es bajo: continuar Solución Salina 0.9% (250-500 mL/h).\n\n### Paso 2: Corrección de Potasio (ANTES de iniciar Insulina)\n* **Regla de Oro:** NUNCA iniciar infusión de insulina si **K+ < 3.3 mEq/L** (riesgo de paro cardíaco por hipopotasemia inducida por insulina).\n* Si K+ < 3.3 mEq/L: Reponer 20-40 mEq/h de KCl y diferir insulina hasta K+ > 3.3 mEq/L.\n* Si K+ entre 3.3 y 5.3 mEq/L: Iniciar insulina y agregar 20-30 mEq de KCl por litro de suero de mantenimiento para mantener K+ entre 4 y 5 mEq/L.\n* Si K+ > 5.3 mEq/L: Iniciar insulina sin aporte de K+ y rechequear cada 2 horas.\n\n### Paso 3: Insulinoterapia\n* **Insulina corriente regular IV:**\n  * Bolo opcional de 0.1 U/kg seguido de infusión a **0.1 U/kg/hora** (o 0.14 U/kg/h sin bolo).\n  * Meta: Descenso glucémico controlado de **50 a 75 mg/dL por hora**.\n  * Al alcanzar glucemia de ~200 mg/dL: Reducir infusión de insulina a 0.02-0.05 U/kg/h y **agregar Dextrosa 5% a la hidratación** para evitar hipoglucemia mientras se cierra el Anión Gap.\n\n## 3. Criterios de Resolución de la CAD\n* Glucemia < 200 mg/dL Y dos de los siguientes:\n  1. Bicarbonato sérico ≥ 18 mEq/L.\n  2. pH venoso > 7.30.\n  3. Anión Gap normalizado (≤ 12 mEq/L).\n* **Transición a vía subcutánea:** Administrar dosis basal de insulina subcutánea (ej. glargina o NPH) **2 horas antes** de suspender la bomba de infusión para evitar hiperglucemia de rebote.\n\n## 4. Trampas Cognitivas Comunes\n* **Precipitación / Error de Orden:** Pasar insulina rápida antes de verificar el potasio sérico.\n* **Cierre Prematuro:** Suspender la infusión de insulina cuando la glucemia baja a 180 mg/dL aunque el Anión Gap siga abierto (20 mEq/L).\n* **Omisión:** Olvidar pesquisar el factor gatillo infeccioso o isquémico subyacente.\n",
  "guia_cirrosis_pbe_paracentesis": "# Guía de Práctica Clínica: Ascitis, Paracentesis y Peritonitis Bacteriana Espontánea (EASL/AASLD)\n\n## 1. Indicaciones Obligatorias de Paracentesis Diagnóstica\nLa paracentesis diagnóstica precoz (primeras 6-12 horas) es mandatoria en:\n1. Todo paciente con cirrosis y ascitis que ingresa al hospital por cualquier motivo.\n2. Todo cirrótico con ascitis que presenta signos de descompensación clínica:\n   * Encefalopatía hepática aguda o empeoramiento del sensorio.\n   * Dolor abdominal difuso o distensión a tensión.\n   * Fiebre o febrícula, hipotensión o shock inexplicado.\n   * Deterioro agudo de la función renal o hemorragia digestiva.\n\n> **Regla de Seguridad:** La coagulopatía (RIN elevado) y la plaquetopenia son universales en cirrosis y **NO constituyen una contraindicación** para la paracentesis diagnóstica (riesgo de hemorragia grave < 0.5%). No transfundir plasma ni plaquetas de rutina para realizarla.\n\n---\n\n## 2. Criterios Diagnósticos de PBE\n* **Criterio de Oro:** Recuento de **Neutrófilos / Polimorfonucleares (PMN) $\\ge 250/\\text{mm}^3$** en líquido ascítico.\n  * Si el líquido es hemorrágico: Restar 1 PMN por cada 250 hematíes.\n* **Cultivo del Líquido Ascítico:** Inocular al menos 10 mL de líquido directamente en **frascos de hemocultivo** (aerobio y anaerobio) al pie de la cama del paciente inmediatamente tras la extracción (eleva la sensibilidad de aislamiento a > 80%).\n\n---\n\n## 3. Esquema Terapéutico Específico\n\n### Antibioticoterapia Empírica Inmediata\n* **Ceftriaxona 2 g EV cada 24 horas** o **Cefotaxima 2 g EV cada 8 horas** durante 5 a 7 días.\n* En infecciones intrahospitalarias o pacientes colonizados por gérmenes multirresistentes: Carbapenémicos (Meropenem) +/- Daptomicina.\n\n### Infusión de Albúmina Humana para Prevención del Síndrome Hepatorrenal\nLa asociación de albúmina al antibiótico previene la falla circulatoria inducida por infección y reduce la mortalidad de forma drástica:\n* **Día 1 (primeras 6 horas):** **$1.5\\text{ g/kg}$** de peso real de albúmina humana al 20%.\n* **Día 3:** **$1.0\\text{ g/kg}$** de peso real de albúmina humana al 20%.\n* *Justificación:* Mantiene el volumen arterial efectivo y disminuye la incidencia de insuficiencia renal del 30% al 10%.\n",
  "guia_hemorragia_digestiva_alta": "# Protocolo Clínico: Manejo de Hemorragia Digestiva Alta (HDA)\n\n## 1. Resucitación Hemodinámica y Acceso Vascular\n* **Objetivo Primario:** Restaurar estabilidad hemodinámica antes de cualquier procedimiento invasivo.\n* **Accesos:** Dos vías venosas periféricas de grueso calibre (16G o 18G).\n* **Cristaloides:** Ringer Lactato o Solución Fisiológica balanceada. Evitar sobrecarga hídrica en hepatópatas/cardiópatas.\n* **Estrategia Transfusional:**\n  * **Restrictiva:** Transfundir concentrado de glóbulos rojos si **Hb < 7 g/dL** (meta 7-9 g/dL).\n  * **Liberal (excepción):** Pacientes con síndrome coronario agudo activo o inestabilidad hemodinámica refractaria (meta Hb > 8-9 g/dL).\n\n## 2. Estratificación de Riesgo Inicial\n* **Score de Glasgow-Blatchford (GBS):**\n  * GBS 0-1: Muy bajo riesgo. Considerar manejo ambulatorio.\n  * GBS ≥ 2: Internación obligatoria para endoscopia alta.\n  * GBS ≥ 6: Alto riesgo de intervención endoscópica, transfusión masiva o cirugía.\n\n## 3. Terapia Farmacológica Inicial (Pre-endoscópica)\n* **Inhibidores de la Bomba de Protones (IBP):**\n  * Bolo inicial de Omeprazol / Pantoprazol 80 mg IV, seguido de infusión continua 8 mg/h o bolos de 40 mg IV c/12h.\n* **Sospecha de Hipertensión Portal / Várices Esofágicas:**\n  * **Drogas vasoactivas:** Terlipresina (2 mg IV inicial, luego 1-2 mg c/4h) u Octreótido (bolo 50 mcg IV, luego 50 mcg/h en infusión continua).\n  * **Profilaxis antibiótica precoz:** Ceftriaxona 1 g/día IV (reduce significativamente bacteriemias espontáneas y mortalidad).\n\n## 4. Oportunidad de la Videoendoscopia Digestiva Alta (VEDA)\n* **Momento:** Dentro de las 24 horas del ingreso una vez lograda la reanimación hemodinámica.\n* En sospecha de sangrado variceal o choque refractario: VEDA urgente (< 12 horas).\n* **Clasificación de Forrest (Úlceras Pépticas):**\n  * Forrest Ia (sangrado en chorro) e Ib (sangrado en napa): Tratamiento endoscópico dual obligatorio (adrenalina + clip / termocoagulación).\n  * Forrest IIa (vaso visible) y IIb (coágulo adherido): Terapia endoscópica recomendada.\n  * Forrest IIc (base hematínica) y III (base limpia): No requieren terapia endoscópica; alta temprana con IBP oral.\n\n## 5. Trampas Cognitivas Comunes\n* **Anclaje:** Atribuir anemia a pérdidas crónicas y no advertir hipovolemia por sangrado agudo.\n* **Cierre Prematuro:** Suspender reposición porque la TA es 110/70 sin registrar taquicardia ortostática.\n* **Omisión:** Olvidar la ceftriaxona profiláctica en el paciente cirrótico con hematemesis.\n",
  "guia_hiperpotasemia_emergencia": "# Guía de Práctica Clínica: Emergencia por Hiperpotasemia y Toxicidad Cardíaca\n\n## 1. Definición y Criterios de Emergencia Vital\n* **Hiperpotasemia Severa:** Potasio sérico ($K^+$) $\\ge 6.5\\text{ mEq/L}$ o cualquier elevación con **cambios electrocardiográficos (ECG)**.\n* **Secuencia de Cambios en ECG:**\n  1. Ondas T altas, picudas y simétricas de base estrecha (signo más temprano).\n  2. Prolongación del intervalo PR y aplanamiento o desaparición de la onda P.\n  3. Ensanchamiento progresivo del complejo QRS.\n  4. Patrón de onda sinusoidal (inminencia de fibrilación ventricular o asistolia).\n\n---\n\n## 2. Algoritmo Terapéutico Escalonado en 3 Fases\n\n### Fase 1: Estabilización Inmediata de Membrana Cardíaca (Minutos 0 a 5)\n* **Gluconato de Calcio al 10%:** 1 ampolla (10 mL / 1 g) endovenoso lento en 2 a 5 minutos bajo monitor cardíaco.\n  * *Mecanismo:* Antagoniza el efecto tóxico del potasio en el miocito elevando el potencial umbral. **NO baja el potasio sérico**, previene la muerte arrítmica.\n  * *Efecto:* Inicia en 1-3 minutos y dura 30-60 minutos. Si el ECG no normaliza en 5 minutos, repetir una segunda dosis.\n\n### Fase 2: Desplazamiento Intracelular de Potasio (Minutos 15 a 30)\n* **Insulina Corriente + Dextrosa:** 10 UI de insulina regular en 50 g de glucosa (Dextrosa al 10% 500 mL o Dextrosa al 50% 100 mL) a pasar en 30 minutos.\n  * Estimula la bomba Na+/K+ ATPasa introduciendo potasio a la célula. Desciende el potasio entre 0.5 y 1.2 mEq/L en 30-60 minutos.\n* **Agonistas Beta-2 Adrenérgicos:** Nebulización con Salbutamol 10 a 20 mg (2 a 4 mL de solución para nebulizar) en 4 mL de solución fisiológica durante 10-15 minutos. Efecto aditivo con la insulina.\n\n### Fase 3: Eliminación Definitiva del Potasio Corporal\n* **Diuréticos de asa:** Furosemida 40-80 mg EV (solo si el paciente tiene diuresis conservada y no está hipovolémico).\n* **Quelantes de Potasio:** Ciclosilicato de sodio y zirconio (Lokelma) o Patiromer oral.\n* **Hemodiálisis de Urgencia:** Indicación mandatoria en falla renal oligo-anúrica, hiperpotasemia refractaria ($K^+ > 7.0$) o daño tisular masivo (rabdomiólisis).\n\n---\n\n## 3. Trampa Farmacológica Iatrogénica: El \"Triple Whammy\"\n* Combinación mortal de: **IECA/ARA-II** (vasodilatación de arteriola eferente) + **AINEs** (inhibición de prostaglandinas / vasoconstricción de arteriola aferente) + **Diurético** (hipovolemia relativa).\n* Produce caída súbita de la presión de filtración glomerular, necrosis tubular aguda e hiperpotasemia fulminante. **Conducta:** Suspensión inmediata y resucitación hidroelectrolítica.\n",
  "guia_sepsis_surviving_bundle": "# Guía de Práctica Clínica: Sepsis y Shock Séptico (Surviving Sepsis Campaign)\n\n## 1. Definiciones Operativas (Consenso Sepsis-3)\n* **Sepsis:** Disfunción orgánica potencialmente mortal causada por una respuesta desregulada del huésped a la infección. Clínicamente: Infección sospechada o confirmada + aumento agudo de **$\\ge 2$ puntos en el Score SOFA** (pesquisa rápida en guardia con **qSOFA $\\ge 2$**).\n* **Shock Séptico:** Subgrupo de sepsis con anomalías circulatorias y celulares profundas asociadas a mayor mortalidad. Se define por:\n  1. Necesidad de vasopresores para mantener Presión Arterial Media (PAM) $\\ge 65\\text{ mmHg}$.\n  2. **Y** Lactato sérico $> 2.0\\text{ mmol/L}$ ($18\\text{ mg/dL}$) a pesar de resucitación con volumen adecuado.\n\n---\n\n## 2. El \"Hour-1 Bundle\" (Paquete de Medidas de la Primera Hora)\nDebe iniciarse de forma inmediata en el área de urgencias:\n\n1. **Medir Lactato Sérico:** Si el lactato inicial es $> 2\\text{ mmol/L}$, repetir medición cada 2 a 4 horas para guiar la resucitación (meta: aclaramiento de lactato $> 10-20\\%$ cada 2 hs).\n2. **Obtener Hemocultivos antes de los Antimicrobianos:** Tomar al menos 2 sets de hemocultivos (frascos aerobios y anaerobios de diferentes accesos venosos). *Regla de oro:* Si la toma de cultivos demora más de 45 minutos, no demorar el inicio del antibiótico.\n3. **Antibióticos de Amplio Espectro Endovenosos:** Iniciar en los primeros 60 minutos del reconocimiento. La elección empírica debe cubrir los patógenos más probables según el foco infeccioso y el riesgo de gérmenes multirresistentes (Pseudomonas, SAMR).\n4. **Resucitación Inicial con Cristaloides:** Administrar **$30\\text{ mL/kg}$** de cristaloides isotónicos balanceados (Ringer Lactato preferido sobre Solución Fisiológica 0.9%) en las primeras 3 horas si hay hipotensión arterial sistémica o lactato $\\ge 4\\text{ mmol/L}$.\n5. **Vasopresores Precoces:** Aplicar si el paciente persiste hipotenso durante o después de la carga inicial de fluidos para mantener **$\\text{PAM} \\ge 65\\text{ mmHg}$**.\n   * **Primera Línea:** **Noradrenalina** en infusión continua (0.05 a 2 mcg/kg/min).\n   * *Trampa frecuente:* No esperar a infundir los 3 litros de suero para iniciar noradrenalina si la presión diastólica es $< 40$ o la PAM $< 55\\text{ mmHg}$.\n\n---\n\n## 3. Parámetros de Monitoreo Dinámico de Perfusión\n* Normalización del tiempo de relleno capilar ($< 2$ segundos en pulpejo digital).\n* Diuresis horaria $\\ge 0.5\\text{ mL/kg/hora}$.\n* Aclaramiento continuo de lactato y mejoría del estado del sensorio.\n"
}

def leer_skill_clinica(nombre_skill: str) -> str:
    nombre_limpio = nombre_skill.lower().strip()
    for k, v in SKILLS_EMBEDDED.items():
        if nombre_limpio in k.lower():
            return v
    return ""

MANUAL_TEXT_EMBEDDED = """# MANUAL DE USO DE SOCRÁTICO & PROGRAMA ACADÉMICO SEMESTRAL
## Formación Avanzada en Razonamiento Clínico, Supervisión de IA & Metacognición
### Residencia de Clínica Médica — Hospital Dr. Horacio Heller (Neuquén, Patagonia Argentina)

---

> **Manifiesto Institucional:**  
> Este documento establece los fundamentos éticos, epistemológicos y metodológicos del uso de **Socrático** en el Servicio de Clínica Médica del Hospital Dr. Horacio Heller. Socrático fue concebido no como un atajo tecnológico ni como un oráculo de diagnósticos automáticos, sino como un **sparring dialéctico de alta exigencia**, diseñado para entrenar el razonamiento analítico (Sistema 2 de Kahneman), auditar los sesgos cognitivos en la fatiga de guardia y formar a los residentes en la supervisión rigurosa de los modelos de inteligencia artificial en la medicina moderna.

> 🌐 **Enlace Oficial de Acceso a Socrático (Simulador en la Nube):**  
> Ingrese a la plataforma desde cualquier PC de guardia, tablet o smartphone en:  
> 👉 **[https://simulador-clinico-socratico.streamlit.app](https://simulador-clinico-socratico.streamlit.app)**  
> *(No requiere instalación local. Recomendamos guardar el enlace en los marcadores del navegador o añadirlo a la pantalla de inicio).*

---

## 📑 ÍNDICE GENERAL

1. [CAPÍTULO 1: Manifiesto Fundacional — Por qué se creó Socrático y la Supervisión Médica de la IA](#capítulo-1-manifiesto-fundacional--por-qué-se-creó-socrático-y-la-supervisión-médica-de-la-ia)
   - 1.1. La experiencia hospitalaria: El peligro de la IA como "Oráculo Mágico"
   - 1.2. El rol insustituible del médico en la supervisión de modelos generativos
   - 1.3. La teoría del proceso dual (Kahneman) y la fatiga en la guardia
   - 1.4. Taxonomía de Croskerry: El desesgamiento (*Debiasing*) como escudo clínico
2. [CAPÍTULO 2: Protocolos Metacognitivos & Herramientas de Seguridad del Paciente](#capítulo-2-protocolos-metacognitivos--herramientas-de-seguridad-del-paciente)
   - 2.1. La Pausa Diagnóstica (*Diagnostic Timeout*): Qué es, para qué sirve y cuándo usarla
   - 2.2. El Ejercicio Pre-Mortem (*Prospective Hindsight*): Rompiendo el optimismo ingenuo
   - 2.3. La Comunicación Estructurada SBAR: El estándar de oro en pases de guardia e interconsultas
3. [CAPÍTULO 3: Guía Operativa & Paso a Paso de Uso de Socrático para Residentes](#capítulo-3-guía-operativa--paso-a-paso-de-uso-de-socrático-para-residentes)
   - 3.1. Obtención y configuración de credenciales (Google AI Studio)
   - 3.2. El contrato de comunicación: Cómo interactuar con el tutor (no es un buscador)
   - 3.3. Estructura de las respuestas del residente: Hipótesis jerárquicas y justificación pre-test
   - 3.4. Activación de las 10 calculadoras biomédicas determinísticas
   - 3.5. Cómo reaccionar ante las repreguntas y las alertas de sesgos
   - 3.6. Uso del botón de Traspaso Clínico SBAR
   - 3.7. Cierre del caso, rúbrica de 100 puntos y acreditación para el portafolio
4. [CAPÍTULO 4: Programa Curricular Semestral (6 Meses / 4 Unidades Temáticas a Ciegas)](#capítulo-4-programa-curricular-semestral-6-meses--4-unidades-temáticas-a-ciegas)
   - 4.1. Arquitectura de la dinámica formativa quincenal a ciegas
   - 4.2. Unidad 1: Síndromes Cardiotorácicos & Urgencias Hemodinámicas (Meses 1 y 2)
   - 4.3. Unidad 2: Neuro-Urgencias & Cuidados Críticos Tiempo-Dependientes (Meses 2 y 3)
   - 4.4. Unidad 3: Falla Respiratoria, Medio Interno & Sepsis (Meses 4 y 5)
   - 4.5. Unidad 4: Abdomen Agudo Médico & Descompensación de Patologías Crónicas (Meses 5 y 6)
5. [CAPÍTULO 5: Metodología Pedagógica del Hospital Heller & Próximos Pasos](#capítulo-5-metodología-pedagógica-del-hospital-heller--próximos-pasos)

---

# CAPÍTULO 1: Manifiesto Fundacional — Por qué se creó Socrático y la Supervisión Médica de la IA

### 1.1. La experiencia hospitalaria: El peligro de la IA como "Oráculo Mágico"
En los últimos años, la rápida difusión de los Modelos de Lenguaje de Gran Escala (LLMs comerciales) generó una peligrosa fascinación en las salas de internación y guardias médicas. Se instaló el mito de que la inteligencia artificial es una suerte de **"Oráculo infalible"**: un ente al que un residente fatigado o apremiado por el tiempo puede arrojarle fragmentos desordenados de una historia clínica para que devuelva un diagnóstico cerrado y una prescripción automática.

Como médicos de planta y docentes asistenciales en el Hospital Heller, observamos este fenómeno con enorme preocupación:
1. **Sesgo de Automatización (*Automation Bias*):** El profesional junior baja la guardia, confía acríticamente en el texto emitido por el modelo y deja de contrastar los datos contra la fisiopatología del paciente.
2. **Alucinaciones clínicas indetectables:** Los LLMs son motores de predicción probabilística de palabras (*tokens*), no razonadores biológicos. Si se les consulta de forma pasiva, pueden sugerir con absoluta elocuencia tratamientos contraindicados, dosis erróneas o pasar por alto contraindicaciones fatales sin titubear.
3. **Atrofia del razonamiento semiológico:** Cuando el médico utiliza la IA como un oráculo de respuestas fáciles, suspende su propio proceso inductivo-deductivo. En una guardia real a las 4 de la mañana, ante un paro inminente o un shock indiferenciado, no hay tiempo de consultar a una máquina: el juicio clínico debe estar forjado en el cerebro del médico.

**Por esta razón nació Socrático:**  
Para tomar la potencia de la inteligencia artificial y ponerla al servicio de la **exigencia cognitiva**, no de la pereza intelectual. Socrático fue programado para **romper el rol de oráculo**. Su regla fundamental es la dialéctica: **nunca da la respuesta servida**. Si el residente le pregunta *"¿Qué tiene el paciente?"*, Socrático le devolverá una pregunta que lo obligará a volver a la semiología, al examen físico y a la fisiopatología.

---

### 1.2. El rol insustituible del médico en la supervisión de modelos generativos
Aprender a utilizar modelos de inteligencia artificial no significa delegarles la medicina; significa aprender a **auditar, interrogar y supervisar a la IA**.

* **Vigilancia Epistémica (*Epistemic Oversight*):** El médico es el único responsable legal, ético y humano de la vida del paciente. La IA jamás firmará una indicación médica, no auscultará un frote pericárdico ni sentirá la frialdad de las extremidades en un shock.
* **El Médico como Director del Proceso:** Para aprovechar la IA de forma segura, el profesional debe saber **qué preguntar, cómo estructurar el caso y cómo detectar cuándo el modelo comete un error**. 
* **Socrático como simulador de supervisión:** Al interactuar con un tutor que debate y pone a prueba cada hipótesis, el residente aprende a fundamentar científicamente cada paso antes de tomar una conducta en la sala de internación.

---

### 1.3. La teoría del proceso dual (Daniel Kahneman) y la fatiga en la guardia
El pensamiento clínico en el ámbito hospitalario se articula en torno a dos sistemas cognitivos descriptos por Daniel Kahneman y Amos Tversky (*Thinking, Fast and Slow*):

* **Sistema 1 (Heurístico / Intuitivo):** Es rápido, automático, inconsciente y de mínimo costo metabólico. Se basa en el reconocimiento inmediato de patrones. Es indispensable en la trinchera para sospechar una catástrofe en los primeros 10 segundos al entrar a un shock room. Sin embargo, cuando el residente lleva 16 o 20 horas de guardia activa, la fatiga y el estrés provocan que el Sistema 1 opere en cortocircuito, volviéndose extremadamente vulnerable a trampas cognitivas.
* **Sistema 2 (Analítico / Deliberativo):** Es lento, reflexivo, estructurado, bayesiano y de alto consumo energético. Es el que calcula scores de probabilidad pre-test, revisa diagnósticos diferenciales que no encajan a primera vista, analiza interacciones de fármacos y evita altas prematuras.

**La misión formativa de Socrático:**  
Actuar como un **interruptor deliberado que activa el Sistema 2**. Cada repregunta dialéctica obliga al residente a frenar el automatismo del Sistema 1 y a construir una justificación sólida basada en evidencia.

---

### 1.4. Taxonomía de Croskerry: El desesgamiento (*Debiasing*) como escudo clínico
El Dr. Pat Croskerry, referente internacional en medicina de urgencias, demostró que la inmensa mayoría de los errores diagnósticos prevenibles en los hospitales se deben a **sesgos cognitivos no detectados** por el propio médico.

Durante las simulaciones, Socrático monitoriza en tiempo real la conversación e interviene cuando el residente cae en alguna de estas trampas clásicas de guardia:

| Sesgo Cognitivo | Mecanismo del Error | Manifestación Típica en Sala / Guardia | Estrategia de Forzamiento (*Debiasing*) |
| :--- | :--- | :--- | :--- |
| **Anclaje** | Fijarse en un dato aislado inicial e ignorar la evolución. | Asumir que todo dolor torácico en un tabaquista es infarto, pasando por alto un frote pericárdico o signos de disección. | *"¿Qué hallazgo semiológico o clínico contradice mi primera sospecha?"* |
| **Cierre Prematuro** | Aceptar el primer diagnóstico verosímil y dar por cerrada la evaluación. | Otorgar el alta con un único laboratorio normal sin cumplir los tiempos de seriación enzimática. | Regla del peor escenario (*Worst-Case Scenario*): Descartar activamente las entidades que matan en horas. |
| **Sesgo de Encuadre (*Framing*)** | Dejarse influir por la etiqueta con la que el paciente fue presentado por otros. | Recibir a un adulto mayor con el rótulo de *"viene por demencia descompensada"* y no solicitar ionograma (omitiendo una hiponatremia severa). | Reiniciar la historia clínica desde cero: evaluar constantes vitales y antecedentes sin preconceptos. |
| **Búsqueda Satisfecha** | Detener la investigación al encontrar una primera anomalía. | Hallar una infección urinaria en un paciente en shock y no buscar la verdadera causa (ej. colecistitis gangrenosa perforada). | *"Este hallazgo que acabo de encontrar, ¿explica por completo la inestabilidad del paciente?"* |
| **Inercia Diagnóstica** | Mantener un diagnóstico previo registrado en notas anteriores sin cuestionarlo. | Tratar una cefalea súbita intensa como *"la migraña usual del paciente"* sin descartar hemorragia subaracnoidea. | Búsqueda activa de banderas rojas (*Red Flags*) de nueva aparición. |
| **Desestimación de Red Flags** | Normalizar signos vitales anormales atribuyéndolos a factores banales. | Justificar una taquipnea de 28 rpm como *"nerviosismo"* en un paciente con neumonía que está entrando en shock séptico. | Protocolizar la frecuencia respiratoria como el biomarcador más sensible de deterioro en sala. |
| **Tratamiento Inseguro** | Indicar un esquema habitual sin verificar contraindicaciones biológicas basales. | Indicar insulina rápida a un paciente con cetoacidosis sin constatar previamente el potasio sérico (riesgo de paro cardíaco). | Pausa de seguridad farmacológica antes de cualquier infusión crítica. |

---

# CAPÍTULO 2: Protocolos Metacognitivos & Herramientas de Seguridad del Paciente

En la práctica médica de alta complejidad no alcanza con poseer conocimientos teóricos: se requieren **herramientas procedimentales estandarizadas** que intervengan activamente en el momento exacto en que la mente humana está más expuesta al error. En Socrático, entrenamos tres herramientas fundamentales:

---

### 2.1. La Pausa Diagnóstica (*Diagnostic Timeout*)

#### ¿Qué es?
La **Pausa Diagnóstica** es una detención consciente y deliberada de la acción asistencial durante **30 a 60 segundos** antes de ejecutar una decisión clínica trascendente o irreversible.  
Así como los cirujanos realizan la *Pausa Quirúrgica (Time-Out de la OMS)* en el quirófano antes de la primera incisión, el médico internista de guardia debe ejecutar una Pausa Diagnóstica antes de definir el destino de un paciente.

#### ¿Para qué sirve?
1. **Desacopla el Sistema 1:** Frena la inercia del automatismo, la prisa de la sala de espera y la presión por "desocupar camas".
2. **Fuerza la metacognición:** Obliga al médico a colocarse en una posición de observador de su propio pensamiento (*"¿Por qué estoy tan seguro de lo que creo?"*).
3. **Evita eventos centinela:** Previene altas inapropiadas, tratamientos invasivos innecesarios e ingresos erróneos a pisos generales de pacientes que requieren terapia intensiva.

#### ¿Cuándo usarla en la práctica clínica y en Socrático?
* **Momento 1:** Antes de firmar el alta definitiva de un paciente de la guardia.
* **Momento 2:** Cuando un paciente no responde al tratamiento inicial esperado tras 2 a 4 horas de evolución.
* **Momento 3:** Al recibir un pase de guardia con un diagnóstico ya rotulado por otro colega (*antídoto contra el sesgo de encuadre*).
* **En Socrático:** Cuando el tutor emite la notificación `🔍 Pausa de Auditoría Metacognitiva...`, el residente debe detenerse y responder mentalmente a las 4 preguntas obligatorias antes de enviar su siguiente mensaje.

#### 📋 Las 4 Preguntas Obligatorias de la Pausa Diagnóstica:
1. *"¿Qué datos clínicos o de laboratorio de este paciente **NO encajan** en mi hipótesis principal?"*
2. *"¿Hay algún signo vital limítrofe (frecuencia respiratoria > 22, taquicardia > 100, diuresis escasa) que estoy normalizando o minimizando?"*
3. *"Si estuviera equivocado, ¿cuál es la peor catástrofe que podría matar a este paciente en las próximas 6 horas?"*
4. *"¿He calculado el score objetivo de riesgo validado antes de decidir la conducta?"*

---

### 2.2. El Ejercicio Pre-Mortem (*Prospective Hindsight*)

#### ¿Qué es?
Diseñado originalmente por el psicólogo cognitivo Gary Klein y adaptado a la medicina de emergencias por Pat Croskerry, el **Pre-Mortem** es un ejercicio contrafáctico de imaginación prospectiva estructurada.  
A diferencia del tradicional *Post-Mortem* (que analiza las causas de una muerte cuando ya no hay remedio en un ateneo de morbimortalidad), el *Pre-Mortem* se ejecuta **mientras el paciente todavía está vivo frente a nosotros**.

#### La Fórmula Mental del Pre-Mortem:
> *"Imaginen que son exactamente las 8:00 AM de mañana. Entramos al pase de guardia y el médico que nos recibe nos informa que este paciente que acabamos de atender **entró en paro cardiorrespiratorio, fue intubado de emergencia o falleció durante la madrugada**.  
> Asumiendo esto como un hecho consumado e irrefutable: **¿Qué fue exactamente lo que pasamos por alto hoy para que ocurriera esta catástrofe?**"*

#### ¿Para qué sirve?
1. **Destruye el sesgo de confirmación:** El cerebro humano tiende naturalmente a buscar datos que confirmen su creencia inicial. El Pre-Mortem invierte la carga psicológica: obliga al cerebro a buscar activamente las grietas y vulnerabilidades de su propio plan.
2. **Neutraliza la complacencia y la falsa tranquilidad:** Desarma frases peligrosas como *"el paciente se ve bien"* o *"seguramente es solo ansiedad"*.
3. **Despersonaliza la crítica clínica:** En un equipo de guardia, preguntar *"¿Por qué piensas que estás en lo correcto?"* puede sonar confrontativo. En cambio, preguntar *"Hagamos un pre-mortem: si mañana el paciente está en UTI, ¿qué se nos escapó?"* invita a una exploración colectiva de seguridad sin herir susceptibilidades.

#### ¿Cuándo usarlo?
* En todo paciente con dolor torácico, dolor abdominal indiferenciado en adultos mayores, disnea en jóvenes o cefalea súbita.
* Antes de transferir a un paciente del shock room a una cama de internación general de menor complejidad.
* **En Socrático:** Al redactar la justificación de estudios o antes de solicitar la evaluación colegiada. El residente debe explicitar: *"En mi ejercicio Pre-Mortem considero que la causa oculta que podría matar a este paciente es X; por lo tanto, no puedo cerrar el caso sin haber evaluado..."*

---

### 2.3. La Comunicación Estructurada SBAR

#### ¿Qué es?
**SBAR** (*Situation, Background, Assessment, Recommendation*) es el estándar internacional de comunicación clínica estructurada de alta fidelidad, adoptado por la Organización Mundial de la Salud (OMS), la Joint Commission y los servicios de cuidados intensivos más rigurosos del mundo.

Fue creado para eliminar las descripciones anecdóticas, difusas y desordenadas que los médicos suelen utilizar al presentar pacientes, las cuales son responsables de más del **70% de los errores médicos centinela en transferencias de guardia**.

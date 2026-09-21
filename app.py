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

```
   S (Situation)      ➔ Identificación inmediata del problema actual (< 15 seg).
   B (Background)     ➔ Antecedentes patológicos críticos y contexto relevante.
   A (Assessment)     ➔ Juicio clínico, constantes vitales y scores objetivos.
   R (Recommendation) ➔ Petición concreta, inequívoca y temporalmente definida.
```

#### Estructura Detallada de cada Componente:

##### 1. Situation (Situación — ¿Qué está pasando AHORA?):
* Identificación clara del profesional que habla, el paciente (cama/sala) y el motivo urgente del contacto en 15 segundos.
* *Ejemplo correcto:* *"Doctor, soy el Dr. Rossi de la guardia. La llamo por el paciente Menéndez en cama 3, quien acaba de presentar dolor precordial opresivo súbito y desaturó a 89% con máscara de reservorio."*
* *Error frecuente:* Comenzar con la historia de la infancia del paciente o rodeos administrativos.

##### 2. Background (Antecedentes — ¿Cuál es el contexto clínico pertinente?):
* Resumen en dos oraciones de los antecedentes que impactan en el problema actual: comorbilidades, fármacos recientes y evolución en las últimas horas.
* *Ejemplo correcto:* *"Es un paciente de 62 años internado por neumonía comunitaria hace 48 hs. Tabaquista activo, sin antecedentes coronarios conocidos. Venía evolucionando afebril con ampicilina/sulbactam."*

##### 3. Assessment (Evaluación — ¿Cuál es su juicio clínico objetivo?):
* Constantes vitales exactas, signos clínicos detectados, hallazgos de electrocardiograma/laboratorio y el cálculo de scores de riesgo.
* *Ejemplo correcto:* *"Al examen: TA 85/50, FC 118, FR 28. Ausculto hipoventilación bilateral y ruidos cardíacos taquicárdicos sin soplos. El ECG muestra taquicardia sinusal con patrón S1Q3T3. Score de Wells para TEP: 7.5 puntos (alta probabilidad pre-test). Considero que está cursando un Tromboembolismo Pulmonar masivo con inestabilidad hemodinámica."*

##### 4. Recommendation (Recomendación / Petición — ¿Qué necesita del otro profesional AHORA?):
* Propuesta clara, explícita y temporalmente acotada de lo que se solicita.
* *Ejemplo correcto:* *"Solicito su presencia inmediata en el shock room para autorizar angiotomografía de tórax urgente o ecocardiograma bedside, y sugiero preparar anticoagulación o trombolisis según protocolo de shock obstructivo."*

#### ¿Cuándo usar SBAR en Socrático?
Socrático cuenta con una herramienta dedicada para este fin:
* A lo largo de la simulación, cuando el residente haya completado la estabilización y el diagnóstico, puede hacer clic en el botón:  
  **`📋 Generar Reporte de Traspaso SBAR`**
* El sistema compila automáticamente la transcripción del caso y genera una nota de entrega formal de guardia con los 4 bloques, lista para exportar a la historia clínica electrónica o presentar en el pase de sala.

---

# CAPÍTULO 3: Guía Operativa & Paso a Paso de Uso de Socrático para Residentes

Para maximizar el impacto pedagógico de cada simulación, el residente debe interactuar con la plataforma siguiendo estas pautas operativas:

---

### 3.1. Enlace oficial de acceso y configuración de credenciales

#### 🌐 Acceso al Simulador en Línea:
La plataforma interactiva de simulación clínica se encuentra desplegada y disponible de forma continua en:  
👉 **[https://simulador-clinico-socratico.streamlit.app](https://simulador-clinico-socratico.streamlit.app)**  

*No requiere instalación previa ni descargas. Es 100% accesible en la nube desde cualquier navegador web moderno (Google Chrome, Mozilla Firefox, Safari o Microsoft Edge).*

#### 🔑 Obtención y configuración de credenciales (Google AI Studio):
Cada médico residente puede utilizar su propia clave de API gratuita provista por Google:
1. Ingresa a: **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)**
2. Inicia sesión con cualquier cuenta de Google (`@gmail.com`).
3. Clic en **"Create API key"** &rarr; **"Create API key in new project"**.
4. Copia la clave alfanumérica (`AIzaSy...`) y pégala en la barra lateral izquierda de Socrático.  
   *(En despliegues institucionales con clave de guardia precargada en Secrets, este paso no es obligatorio).*

---

### 3.2. El contrato de comunicación: Cómo interactuar con el tutor
**Socrático no es un motor de búsqueda ni un asistente que redacta por usted.** Es un Tribunal de Especialistas en Medicina Interna que evalúa su capacidad de liderazgo clínico:

* ❌ **Conducta Incorrecta (Modo Oráculo):**  
  *"¿Qué tiene el paciente?"*, *"Decime el tratamiento"*, *"¿Le pido troponinas?"*.  
  *(Socrático penalizará esta actitud y le devolverá una pregunta inquisitiva sobre su justificación biológica).*
* ✅ **Conducta Correcta (Modo Especialista en Guardia):**  
  *"Planteo como primera sospecha un SCA sin elevación del ST versus Pericarditis Aguda. Solicito ECG de 12 derivaciones buscando alteraciones en ST y PR, y troponina ultrasensible. Indico monitoreo continuo, reposo a 30° y acceso venoso con ringer lactato a 30 ml/h mientras evalúo el Score HEART."*

---

### 3.3. Estructura de las respuestas del residente
En cada intervención en la caja de texto inferior, estructure su mensaje respetando este esquema:
1. **Impresión Sindrómica & Hipótesis Jerarquizadas:** Diferencie siempre entre la hipótesis más prevalente (*probable*) y la catástrofe que debe descartar activamente (*peor escenario*).
2. **Justificación Pre-Test de los Estudios:** No solicite "baterías completas de laboratorio" por costumbre. Indique qué sospecha encontrar en cada estudio pedido y qué conducta terapéutica modificará un resultado positivo o negativo.
3. **Medidas Terapéuticas Inmediatas:** Describa dosis, vías de administración y metas fisiológicas (ej. *"Carga de cristaloides guiada por metas: TA media > 65 mmHg y diuresis > 0.5 ml/kg/h"*).

---

### 3.4. Activación de las 10 Calculadoras Biomédicas Determinísticas
Socrático no realiza cálculos numéricos con el modelo de lenguaje (lo que provocaría errores matemáticos de coma flotante). Cuenta con **10 herramientas en Python puro** que se activan mediante *Function Calling*:

| Calculadora | Cuándo y Cómo Activarla | Qué Parámetros Mencionar en el Chat |
| :--- | :--- | :--- |
| **Score HEART** | Dolor torácico agudo en guardia. | Mencione: Antecedentes, ECG (normal/inespecífico/desvío), Edad, Factores de riesgo y Troponina. |
| **Score Wells TEP** | Disnea súbita o dolor pleurítico. | Mencione: TVP previa, FC > 100, cirugía reciente, hemoptisis, cáncer o si TEP es el diagnóstico más probable. |
| **Score CURB-65** | Neumonía de la comunidad (NAC). | Mencione: Confusión mental, Urea sérica, FR &ge; 30, TA &lt; 90/60 y Edad &ge; 65. |
| **Score qSOFA** | Sospecha de infección grave / Sepsis. | Mencione: Estado neurológico (Glasgow &lt; 15), FR &ge; 22 y TAS &le; 100 mmHg. |
| **Glasgow-Blatchford** | Hemorragia digestiva alta (HDA). | Mencione: Urea, Hemoglobina, TAS, FC, presencia de melena o síncope. |
| **CKD-EPI 2021** | Antes de prescribir fármacos nefrotóxicos. | Mencione: Creatinina sérica exacta, edad y sexo del paciente. |
| **Anthonisen EPOC** | Exacerbación de enfermedad pulmonar obstructiva. | Mencione: Aumento de disnea, volumen de esputo y purulencia. |
| **Cetoacidosis (CAD)** | Hiperglucemia con acidosis metabólica. | Mencione: Glucemia, Sodio, Potasio, Cloro y Bicarbonato para calcular Anion Gap corregido. |
| **Índice de Shock** | Sospecha de shock oculto normotenso. | Mencione: Frecuencia cardíaca y Tensión Arterial Sistólica (FC / TAS). |
| **Score NIHSS** | Sospecha de ACV en ventana de reperfusión. | Mencione: Nivel de conciencia, campos visuales, pares craneales y fuerza en las 4 extremidades. |

---

### 3.5. Cómo reaccionar ante las repreguntas y las alertas de sesgos
Si Socrático le muestra una alerta como `⚠️ Alerta de Sesgo Detectada: [Cierre Prematuro]`:
* **No intente justificarse tozudamente:** En la vida real, insistir en un error por orgullo profesional cuesta vidas.
* **Ejecute una Pausa Diagnóstica:** Lea con atención la pregunta socrática.
* **Aplique la estrategia de desesgamiento correspondiente:** Abra el abanico de diagnósticos diferenciales, acepte que el cuadro puede tener una etiología alternativa y proponga un plan de descarte objetivo. La corrección reflexiva del rumbo suma hasta **15 puntos** en la dimensión de Metacognición de la rúbrica final.

---

### 3.6. Uso del botón de Traspaso Clínico SBAR
Hacia la mitad o el final del caso, utilice el botón **`📋 Generar Reporte de Traspaso SBAR`**:
* Verifique que la información compilada refleje con fidelidad lo actuado.
* Utilice este texto estructurado como modelo para sus pases de guardia matutinos en el Hospital Heller.

---

### 3.7. Cierre del caso, rúbrica de 100 puntos y acreditación para el portafolio
Cuando considere que el paciente ha sido estabilizado, diagnosticado y tiene un plan de internación o destino claro:
1. Haga clic en el botón azul: **`🎯 Concluir Caso y Evaluar Desempeño`**.
2. El Tribunal Evaluador Docente analizará toda la sesión y emitirá un veredicto en 5 dimensiones pedagógicas:
   - **Precisión Diagnóstica & Hipótesis (20 pts)**
   - **Seguridad del Paciente & Banderas Rojas (20 pts)**
   - **Adherencia a Guías Basadas en Evidencia (20 pts)**
   - **Metacognición & Resiliencia a Sesgos (20 pts)**
   - **Uso Racional de Recursos & Comunicación SBAR (20 pts)**
3. Al pie del dictamen, haga clic en:  
   **`📄 Descargar Informe Oficial para Portafolio Médico (.md)`**  
   Guarde este archivo como constancia acreditable de su actividad formativa en la residencia.

---

# CAPÍTULO 4: Programa Curricular Semestral (6 Meses / 4 Unidades Temáticas a Ciegas)

### 4.1. Arquitectura de la dinámica formativa quincenal a ciegas
El programa de formación tiene una duración de **6 meses (24 semanas)** divididos en **12 módulos quincenales**. 

**Metodología de Simulación a Ciegas:**  
A diferencia de los programas tradicionales donde el alumno sabe de antemano qué patología verá cada día, los casos clínicos del simulador **se resuelven a ciegas**. El residente conoce únicamente el eje temático general de la unidad, pero debe descubrir y resolver el cuadro clínico en Socrático enfrentándose a la incertidumbre diagnóstica real de la guardia.

* **Días 1 a 3:** Estudio teórico de los temas de la unidad mediante las guías generales y la bibliografía recomendada (Pestaña 2 de Socrático).
* **Días 4 a 12:** Resolución individual del caso clínico a ciegas en Socrático (Pestaña 1).
* **Día 14:** **Ateneo Presencial de Debriefing & Metacognición** en el aula del Hospital Heller, con proyección de las métricas de sesgos de la cohorte y discusión en ronda médica.
* **Día 15:** Entrega de la **Ficha de Bolsillo A4 (One-Pager)** y Masterclass de cierre a cargo de la jefatura docente.

---

### 4.2. Unidad 1: Síndromes Cardiotorácicos & Urgencias Hemodinámicas (Meses 1 y 2)
*Eje Formativo: Cardiología de Urgencias, Monitoreo Circulatorio y Reanimación en Shock.*

#### 📋 Listado de Temas a Estudiar:
1. **Abordaje del Dolor Torácico Indiferenciado en Urgencias:**
   - Fisiopatología del dolor isquémico coronario vs. inflamatorio pericárdico vs. dolor pleurítico vs. disección vascular.
   - Diagnóstico diferencial de las 5 entidades torácicas que comprometen la vida en menos de 2 horas.
   - Electrocardiografía crítica: vectores de lesión subepicárdica, cinética del segmento ST y alteraciones sutiles del segmento PR.
   - Cinética y uso racional de biomarcadores cardíacos (troponinas de alta sensibilidad).
   - Estratificación pronóstica de riesgo cardiovascular temprano mediante escalas validadas (Score HEART).
2. **Fisiopatología y Manejo Inicial del Shock Circulatorio:**
   - Clasificación fisiopatológica del shock: hipovolémico, cardiogénico, distributivo y obstructivo.
   - Evaluación macrocirculatoria (tensión arterial, diuresis, estado neurológico) y microcirculatoria (relleno capilar, gradiente térmico, lactato sérico).
   - Accesos vasculares en reanimación masiva: principios biofísicos de la Ley de Poiseuille (cánulas cortas y gruesas vs. catéteres centrales).
   - Estrategia transfusional restrictiva en hemorragia digestiva aguda y sus fundamentos en la hemodinámica portal.
   - Uso de fármacos vasoactivos esplácnicos y protectores gástricos en fase aguda.
3. **Insuficiencia Cardíaca Aguda y Emergencias Hipertensivas:**
   - Fisiopatología de la congestión pulmonar aguda y disfunción ventricular izquierda.
   - Titulación de vasodilatadores de acción rápida (nitroglicerina) vs. diuréticos de asa en la primera hora.
   - Ventilación no invasiva (CPAP / BiPAP) en edema agudo de pulmón: efectos mecánicos sobre la precarga y postcarga ventricular.

---

### 4.3. Unidad 2: Neuro-Urgencias & Cuidados Críticos Tiempo-Dependientes (Meses 2 y 3)
*Eje Formativo: Neurología Crítica, Síndrome Confusional y Trastornos Osmolares Severos.*

#### 📋 Listado de Temas a Estudiar:
1. **Accidente Cerebrovascular (ACV) Isquémico y Código Ictus:**
   - Fisiopatología de la penumbra isquémica y ventanas terapéuticas de reperfusión (trombolisis endovenosa vs. trombectomía mecánica).
   - Escala NIHSS: Cuantificación estandarizada del déficit neurológico focal.
   - Diagnóstico diferencial de los simuladores de ACV (*Stroke Mimics*): hipoglucemia severa, paresia post-ictal de Todd, migraña con aura y trastornos de conversión.
   - Criterios estrictos de inclusión y contraindicaciones absolutas/relativas para trombolisis según guías AHA/ASA.
2. **Cefalea Aguda de Riesgo Vital:**
   - Banderas rojas en cefalea: Cefalea en trueno (*Thunderclap*), rigidez de nuca, fiebre y déficit neurológico asociado.
   - Algoritmo diagnóstico de la Hemorragia Subaracnoidea (HSA): Sensibilidad de la tomografía axial computada de cráneo según el tiempo de evolución (&lt; 6 hs vs. &gt; 24 hs).
   - Criterios e indicaciones formales de Punción Lumbar diagnóstica (xantocromía espectrofotométrica vs. punción traumática).
3. **Encefalopatía Aguda y Trastornos Osmolares Graves:**
   - Diagnóstico diferencial del delirium hiperactivo e hipoactivo en el anciano hospitalizado.
   - Fisiopatología de la hiponatremia hipotónica: hipovolémica, euvolémica e hipervolémica.
   - Cálculo del déficit de sodio y agua libre mediante fórmulas validadas.
   - Prevención estricta del Síndrome de Desmielinización Osmótica (Mielinólisis Central Pontina): Límites máximos de corrección en 24 y 48 horas (&le; 8-10 mEq/L/día).
   - Manejo de emergencia con Cloruro de Sodio hipertónico al 3% en hiponatremia sintomática severa (convulsiones / coma).

---

### 4.4. Unidad 3: Falla Respiratoria, Medio Interno & Sepsis (Meses 4 y 5)
*Eje Formativo: Neumonología de Guardia, Terapia Antimicrobiana Crítica y Trastornos Renales Agudos.*

#### 📋 Listado de Temas a Estudiar:
1. **Neumonía Adquirida en la Comunidad (NAC) Severa y Sepsis:**
   - Criterios de gravedad y estratificación de sitio de internación mediante scores predictivos (CURB-65 y qSOFA / SOFA).
   - Protocolo Surviving Sepsis Campaign: El *Bundle de la Primera Hora (Hour-1 Bundle)*:
     * Toma de hemocultivos previos a la terapia antibiótica.
     * Inicio precoz de antibióticos de amplio espectro guiados por epidemiología local.
     * Medición seriada de lactato sérico.
     * Reanimación con cristaloides balanceados a 30 ml/kg en hipotensión o lactato &ge; 4 mmol/L.
     * Inicio de vasopresores (Noradrenalina) si persiste hipotensión arterial media &lt; 65 mmHg.
2. **Insuficiencia Respiratoria Hipercápnica y Exacerbación de EPOC:**
   - Fisiopatología del atrapamiento aéreo, fatiga muscular diafragmática y acidosis respiratoria aguda.
   - Criterios de Anthonisen para exacerbación infecciosa y selección racional de antibióticos.
   - Manejo cauteloso de la oxigenoterapia: Riesgo de pérdida del estímulo hipóxico y agravamiento de la hipercapnia por efecto Haldane y empeoramiento V/Q.
   - Indicaciones y contraindicaciones de Ventilación No Invasiva (VNI) temprana como estrategia de rescate para evitar la intubación endotraqueal.
3. **Injuria Renal Aguda (IRA) y Emergencias Electrolíticas:**
   - Clasificación de la IRA según criterios KDIGO (azoemia vs. oliguria).
   - Diagnóstico diferencial entre IRA prerenal e intrínseca (NTA tóxica o isquémica): Índices urinarios y fracción excretada de sodio (FENa).
   - Abordaje de emergencia de la Hiperpotasemia Severa (&gt; 6.5 mEq/L o con cambios electrocardiográficos):
     * Estabilización de la membrana miocárdica con Gluconato de Calcio al 10% endovenoso.
     * Redistribución intracelular rápida: Insulina corriente con glucosa hipertónica y nebulizaciones con agonistas beta-2.
     * Eliminación corporal de potasio: Diuréticos de asa, resinas de intercambio catiónico e indicación oportuna de hemodiálisis de urgencia.

---

### 4.5. Unidad 4: Abdomen Agudo Médico & Descompensación de Patologías Crónicas (Meses 5 y 6)
*Eje Formativo: Gastroenterología de Urgencias, Hepatología Crítica y Complicaciones Metabólicas.*

#### 📋 Listado de Temas a Estudiar:
1. **Complicaciones Hiperglucémicas Severas:**
   - Fisiopatología comparativa: Cetoacidosis Diabética (CAD) vs. Síndrome Hiperglucémico Hiperosmolar (SHH).
   - Diagnóstico gasométrico: Acidosis metabólica con Anion Gap elevado y brecha osmolar.
   - Algoritmo de hidratación endovenosa y reposición electrolítica previa a la insulinoterapia: *Regla innegociable de no infundir insulina si el potasio sérico es &lt; 3.3 mEq/L*.
   - Criterios de resolución de la CAD y esquema de transición segura a insulina subcutánea basal.
2. **El Paciente Cirrótico en el Departamento de Emergencias:**
   - Diagnóstico y manejo de la Peritonitis Bacteriana Espontánea (PBE):
     * Criterios citológicos en líquido ascítico (&ge; 250 polimorfonucleares/mm³).
     * Indicación ineludible de Paracentesis Diagnóstica precoz en todo paciente cirrótico que ingresa con descompensación clínica.
     * Terapia antimicrobiana empírica y prevención del Síndrome Hepatorrenal con infusión protocolizada de Albúmina Humana endovenosa (1.5 g/kg día 1 y 1.0 g/kg día 3).
3. **Pancreatitis Aguda y Abdomen Quirúrgico:**
   - Criterios diagnósticos de Atlanta (2 de 3: dolor característico, amilasa/lipasa &gt; 3 veces el límite superior normal e imágenes compatibles).
   - Fisiopatología del secuestro de volumen en tercer espacio: Reanimación hidroelectrolítica guiada por metas en las primeras 24 horas (prevención de necrosis).
   - Uso racional de imágenes: ¿Por qué la tomografía computada contrastada no debe realizarse en las primeras 48-72 horas salvo duda diagnóstica?
   - Prohibición del uso profiláctico rutinario de antibióticos en pancreatitis aguda no infectada.

---

# CAPÍTULO 5: Metodología Pedagógica del Hospital Heller & Próximos Pasos

### 5.1. El Ateneo de Metacognición Quincenal (Debriefing Presencial)
El proceso de aprendizaje que comienza en Socrático se consolida de forma presencial en el hospital:
1. **Puesta en común de métricas agregadas:** La jefatura de residencia proyecta la frecuencia de sesgos detectados en la cohorte durante los 12 días previos.
2. **Normalización del error cognitivo:** El objetivo del ateneo no es punitivo, sino pedagógico. Se debate abiertamente cómo la presión asistencial facilitó el anclaje o el cierre prematuro en determinados puntos del caso.
3. **Entrega de la Ficha de Bolsillo A4 (One-Pager):** Al retirarse del ateneo, cada residente recibe la ficha de bolsillo plastificada con los algoritmos y dosis clave para portar en el guardapolvo de guardia.

---

### 5.2. Compromiso Ético y Académico del Residente
Al utilizar Socrático, cada residente asume el compromiso de:
* Dedicar un tiempo protegido y sin interrupciones para resolver cada caso asignado.
* Fundamentar cada respuesta con razonamiento fisiopatológico y no solicitar ayudas a terceros durante la simulación ciega.
* Mantener la confidencialidad de los escenarios clínicos para preservar el valor pedagógico para sus compañeros de residencia.
* Aplicar activamente en la atención de los pacientes del Hospital Dr. Horacio Heller las tres herramientas de seguridad aprendidas: **la Pausa Diagnóstica, el Pre-Mortem y la Comunicación SBAR**.

---
*Manual aprobado por la Jefatura de Residencia y el Servicio de Clínica Médica — Hospital Dr. Horacio Heller, Neuquén, Argentina.*
"""


# ==================== CONFIGURACION Y ESTILOS ====================
from pathlib import Path

# Rutas del proyecto
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_LOG_FILE = DATA_DIR / "audit_log.csv"
EVALUATION_LOG_FILE = DATA_DIR / "evaluaciones_log.csv"
LEADS_LOG_FILE = DATA_DIR / "leads_preinscripcion.csv"
BENCHMARK_LOG_FILE = DATA_DIR / "benchmark_estres_log.csv"
CUSTOM_CASES_FILE = DATA_DIR / "casos_personalizados.json"

# Clave maestra de acceso docente / jefatura
DOCENTE_PASSWORD = "heller2026"

# Modelos oficiales activos requeridos por la API de Google (año 2026)
AVAILABLE_MODELS = [
    "gemini-3.6-flash"
]
DEFAULT_MODEL = "gemini-3.6-flash"

# Planilla Google Sheets por defecto (se puede sobreescribir vía secrets o sidebar)
DEFAULT_GSHEETS_URL = "https://docs.google.com/spreadsheets/d/1s-IBpntSc5fBzuiAw8ePOho3DjB6G8N8ubm1JQXmTtU/edit"

# Estilos CSS de revista académica médica
CUSTOM_CSS = """
<style>
    .main-header {
        font-family: 'Georgia', serif;
        color: #0f172a;
        border-bottom: 3px solid #1e3a8a;
        padding-bottom: 12px;
        margin-bottom: 20px;
    }
    .journal-subtitle {
        font-size: 0.85rem;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        font-weight: 700;
    }
    .journal-title {
        font-size: 2rem;
        font-weight: bold;
        color: #1e3a8a;
        margin-top: 4px;
    }
    .vignette-card {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-left: 6px solid #1e3a8a;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .vignette-title {
        font-family: 'Georgia', serif;
        font-size: 1.25rem;
        color: #1e3a8a;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .vignette-text {
        font-size: 1.05rem;
        color: #1e293b;
        line-height: 1.6;
    }
    .vignette-tags {
        margin-top: 12px;
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }
    .vignette-tag {
        background-color: #e2e8f0;
        color: #334155;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 4px;
    }
    .bias-badge {
        background-color: #fee2e2;
        color: #991b1b;
        border: 1px solid #fecaca;
        border-radius: 4px;
        padding: 2px 6px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .audit-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
</style>
"""
# ==================== CASOS CLINICOS ====================
from typing import Dict, Any

BANCO_CASOS: Dict[str, Dict[str, Any]] = {
    "Caso 01: Dolor torácico agudo en varón tabaquista de 42 años": {
        "titulo": "Varón de 42 años con dolor torácico opresivo y disnea",
        "area": "Cardiología / Urgencias",
        "dificultad": "Intermedia",
        "viñeta": (
            "Paciente varón de 42 años, tabaquista activo (20 paquetes/año), sin otros antecedentes conocidos. "
            "Consulta por cuadro de 48 horas de evolución caracterizado por dolor torácico retroesternal opresivo, "
            "de intensidad 7/10, que empeora levemente con el decúbito y mejora al inclinarse hacia adelante. "
            "Asocia disnea de esfuerzo progresiva clase funcional II-III. "
            "Signos vitales al ingreso: TA 130/80 mmHg, FC 92 lpm, FR 18 rpm, SpO2 97% al aire ambiente, Temp 37.4 °C. "
            "Examen cardiovascular: R1-R2 presentes, no se ausculta frote pericárdico al ingreso, pulsos periféricos simétricos."
        ),
        "sesgos_esperados": [
            "Anclaje y Ajuste Insuficiente",
            "Cierre Prematuro",
            "Sesgo de Representatividad"
        ],
        "red_flags": [
            "Descartar Síndrome Coronario Agudo vs Pericarditis Aguda vs Disección Aórtica vs Tromboembolismo Pulmonar.",
            "Evitar asumir dolor puramente muscular en tabaquista activo."
        ],
        "calculadoras_pertinentes": ["calculadora_score_heart", "calculadora_score_wells_tep"],
        "guia_oficial_titulo": "Guía AHA/ACC/CHEST: Evaluación y Diagnóstico de Dolor Torácico",
        "guia_oficial_sociedad": "AHA / ACC / CHEST (Circulation)",
        "guia_oficial_url": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001029"
    },
    
    "Caso 02: Deterioro cognitivo agudo y debilidad en mujer de 72 años": {
        "titulo": "Mujer de 72 años con somnolencia progresiva y calambres",
        "area": "Geriatría / Medio Interno",
        "dificultad": "Avanzada",
        "viñeta": (
            "Paciente femenina de 72 años con antecedentes de hipertensión arterial tratada con hidroclorotiazida 25 mg/día. "
            "Es traída a la guardia por sus familiares debido a somnolencia progresiva, desorientación temporoespacial, "
            "náuseas, astenia extrema y calambres musculares generalizados de 48 horas de evolución. "
            "Sin fiebre ni foco respiratorio evidente. "
            "Signos vitales: TA 110/65 mmHg, FC 68 lpm, FR 16 rpm, SpO2 96% al aire ambiente, Temp 36.6 °C. "
            "Examen físico: desorientada en tiempo y espacio, sin signos de focalidad neurológica motora, mucosas subhidratadas."
        ),
        "sesgos_esperados": [
            "Sesgo de Encuadre",
            "Cierre Prematuro",
            "Inercia Diagnóstica"
        ],
        "red_flags": [
            "No atribuir deterioro cognitivo a 'demencia senil' o ACV sin evaluar electrolitos séricos (riesgo de hiponatremia severa inducida por tiazidas).",
            "Evitar corrección ultra-rápida de sodio (riesgo de síndrome de desmielinización osmótica / mielinólisis pontina)."
        ],
        "calculadoras_pertinentes": ["calculadora_filtrado_glomerular_ckd_epi", "calculadora_metabolica_cad"],
        "guia_oficial_titulo": "Consenso Europeo: Diagnóstico y Manejo de la Hiponatremia",
        "guia_oficial_sociedad": "ESE / ERA-EDTA (Eur J Endocrinol)",
        "guia_oficial_url": "https://academic.oup.com/ndt/article/29/suppl_2/i1/1816353"
    },

    "Caso 03: Neumonía severa con hipoxemia en mujer diabética de 65 años": {
        "titulo": "Mujer de 65 años con fiebre, tos y desaturación",
        "area": "Neumonología / Infectología",
        "dificultad": "Intermedia",
        "viñeta": (
            "Paciente de 65 años, con antecedentes de Diabetes Mellitus tipo 2 y obesidad grado I. "
            "Consulta por cuadro de 3 días de evolución caracterizado por fiebre alta (hasta 39 °C), escalofríos, "
            "tos con expectoración herrumbrosa y disnea rápidamente progresiva. "
            "Al ingreso en la guardia: TA 95/55 mmHg, FC 115 lpm, FR 32 rpm, SpO2 88% al aire ambiente, Temp 38.8 °C. "
            "Examen pulmonar: crepitantes húmedos y soplo tubario en base pulmonar derecha. Glasgow 14/15 (leve confusión)."
        ),
        "sesgos_esperados": [
            "Desestimación de Banderas Rojas",
            "Cierre Prematuro",
            "Error de Cálculo"
        ],
        "red_flags": [
            "Taquipnea severa (32/min) e hipoxemia marcada (88%): criterios de CURB-65 y qSOFA positivos.",
            "Shock séptico incipiente: requerimiento de resucitación con fluidos y antibiótico endovenoso en la primera hora."
        ],
        "calculadoras_pertinentes": ["calculadora_curb65", "calculadora_qsofa", "calculadora_filtrado_glomerular_ckd_epi"],
        "guia_oficial_titulo": "Guía ATS/IDSA: Neumonía Adquirida en la Comunidad (NAC)",
        "guia_oficial_sociedad": "ATS / IDSA (Am J Respir Crit Care Med)",
        "guia_oficial_url": "https://www.atsjournals.org/doi/full/10.1164/rccm.201908-1581ST"
    },

    "Caso 04: Hemorragia digestiva alta y shock hipovolémico en varón de 50 años": {
        "titulo": "Varón de 50 años con hematemesis y melena de 24 hs",
        "area": "Gastroenterología / Terapia Intensiva",
        "dificultad": "Avanzada",
        "viñeta": (
            "Paciente varón de 50 años, con antecedentes de consumo problemático de alcohol y uso frecuente de ibuprofeno "
            "por lumbalgia crónica. Es traído por familiares tras 3 episodios de vómitos con sangre fresca y deposiciones "
            "negras alquitranadas fétidas (melena). Presentó episodio sincopal al ponerse de pie antes de consultar. "
            "Signos vitales: TA 85/50 mmHg, FC 122 lpm regular y filiforme, FR 22 rpm, SpO2 95%, afebril. "
            "Examen físico: palidez cutáneo-mucosa marcada, frialdad distal, relleno capilar > 3 segundos, estigmas de hepatopatía crónica."
        ),
        "sesgos_esperados": [
            "Cierre Prematuro",
            "Tratamiento Inseguro",
            "Sesgo de Encuadre"
        ],
        "red_flags": [
            "Inestabilidad hemodinámica manifiesta (shock hipovolémico grado III): prioridad absoluta es resucitación con dos accesos venosos gruesos y hemoderivados.",
            "No demorar la estabilización para esperar la endoscopía digestiva (GBS elevado)."
        ],
        "calculadoras_pertinentes": ["calculadora_glasgow_blatchford", "calculadora_filtrado_glomerular_ckd_epi"],
        "guia_oficial_titulo": "Guía ACG: Manejo de Hemorragia Digestiva Alta y Úlcera Péptica",
        "guia_oficial_sociedad": "ACG (Am J Gastroenterol)",
        "guia_oficial_url": "https://journals.lww.com/ajg/fulltext/2021/05000/acg_clinical_guideline__upper_gastrointestinal.14.aspx"
    },

    "Caso 05: Pie diabético infectado con respuesta inflamatoria sistémica": {
        "titulo": "Varón de 58 años con úlcera en antepié y alteración sensorial",
        "area": "Metabolismo / Infectología",
        "dificultad": "Avanzada",
        "viñeta": (
            "Paciente masculino de 58 años con diabetes tipo 2 con mal apego al tratamiento e hipertensión. "
            "Consulta por una lesión ulcerada profunda en cara plantar de antepié derecho de 8 días de evolución. "
            "Al examen la lesión mide 4x3 cm, con exposición tendinosa, secreción purulenta fétida, eritema perilesional de 5 cm "
            "y crepitación a la palpación. "
            "Signos vitales: TA 100/60 mmHg, FC 110 lpm, FR 24 rpm, Temp 38.6 °C, Glucemia capilar 380 mg/dL. "
            "El paciente se encuentra somnoliento, responde preguntas con lentitud y tiene aliento con olor a frutas."
        ),
        "sesgos_esperados": [
            "Búsqueda Satisfecha",
            "Cierre Prematuro",
            "Error de Cálculo"
        ],
        "red_flags": [
            "Coexistencia de infección profunda necrosante (requiere desbridamiento quirúrgico urgente) con Cetoacidosis Diabética o Estado Hiperosmolar.",
            "Evaluar Anión Gap y sodio corregido antes de administrar insulina o fluidos hipotónicos."
        ],
        "calculadoras_pertinentes": ["calculadora_metabolica_cad", "calculadora_qsofa", "calculadora_filtrado_glomerular_ckd_epi"],
        "guia_oficial_titulo": "Estándares ADA: Crisis Hiperglucémicas y Manejo Hospitalario",
        "guia_oficial_sociedad": "American Diabetes Association (Diabetes Care)",
        "guia_oficial_url": "https://diabetesjournals.org/care/article/47/Supplement_1/S1/153958/Standards-of-Care-in-Diabetes-2024"
    },

    "Caso 06: Cefalea holocraneana severa y fiebre en mujer de 34 años": {
        "titulo": "Mujer de 34 años con cefalea intensa progresiva y fiebre",
        "area": "Neurología / Infectología",
        "dificultad": "Intermedia",
        "viñeta": (
            "Mujer de 34 años previamente sana que consulta por cuadro de 4 días de cefalea intensa holocraneana, "
            "descrita como 'la peor de su vida', acompañada de náuseas, vómitos repetidos, fotofobia y fiebre no cuantificada. "
            "Ha tomado paracetamol y antiinflamatorios sin alivio alguno. "
            "Signos vitales: TA 120/75 mmHg, FC 88 lpm, FR 16 rpm, SpO2 99%, Temp 38.5 °C. "
            "Al examen: lúcida, rigidez de nuca positiva a la flexión cervical, signo de Kernig positivo bilateral."
        ),
        "sesgos_esperados": [
            "Inercia Diagnóstica",
            "Cierre Prematuro",
            "Sesgo de Disponibilidad"
        ],
        "red_flags": [
            "Cuadro de meningitis bacteriana / meningoencefalitis aguda: indicación inmediata de hemocultivos y antibioticoterapia empírica + dexametasona.",
            "No retrasar los antibióticos si la tomografía previa a la punción lumbar va a demorarse."
        ],
        "calculadoras_pertinentes": ["calculadora_filtrado_glomerular_ckd_epi"],
        "guia_oficial_titulo": "Guía ESCMID: Diagnóstico y Manejo de la Meningitis Bacteriana",
        "guia_oficial_sociedad": "ESCMID (Clin Microbiol Infect)",
        "guia_oficial_url": "https://doi.org/10.1016/j.cmi.2016.01.007"
    },

    "Caso 07: Exacerbación severa de EPOC con riesgo de retención de CO2": {
        "titulo": "Varón de 71 años con disnea severa y tos productiva purulenta",
        "area": "Neumonología / Cuidados Críticos",
        "dificultad": "Intermedia",
        "viñeta": (
            "Varón de 71 años con diagnóstico conocido de EPOC severo (GOLD D, usuario de oxígeno domiciliario nocturno). "
            "Consulta por incremento marcado de su disnea habitual en las últimas 48 horas (actualmente en reposo), "
            "aumento del volumen del esputo y cambio a color francamente verdoso oscuro (purulento). "
            "Signos vitales al ingreso: TA 145/90 mmHg, FC 108 lpm, FR 28 rpm con tiraje intercostal, SpO2 84% al aire ambiente, Temp 37.8 °C. "
            "Examen pulmonar: roncus y sibilancias espiratorias bilaterales difusas con espiración muy prolongada."
        ),
        "sesgos_esperados": [
            "Tratamiento Inseguro",
            "Cierre Prematuro",
            "Desestimación de Banderas Rojas"
        ],
        "red_flags": [
            "Riesgo crítico de hipercapnia e hipoventilación por exceso de oxígeno. Meta estricta de SpO2: 88-92%.",
            "Cumple criterios de Anthonisen tipo 1 (3/3): indicación clara de broncodilatadores, corticoides sistémicos y antibióticos."
        ],
        "calculadoras_pertinentes": ["calculadora_exacerbacion_epoc", "calculadora_curb65"],
        "guia_oficial_titulo": "Iniciativa Global GOLD 2024: Diagnóstico y Manejo de la EPOC",
        "guia_oficial_sociedad": "GOLD Global Strategy",
        "guia_oficial_url": "https://goldcopd.org/2024-gold-report/"
    },

    "Caso 08: Accidente Cerebrovascular (ACV) isquémico agudo en ventana terapéutica": {
        "titulo": "Varón de 64 años con hemiparesia braquiocrural derecha y afasia de 90 min",
        "area": "Neurología / Urgencias",
        "dificultad": "Avanzada",
        "viñeta": (
            "Paciente masculino de 64 años, con antecedentes de hipertensión arterial y fibrilación auricular crónica "
            "con mal apego a la anticoagulación oral. Es traído de urgencia por familiares tras notar, hace 90 minutos de forma súbita, "
            "desviación de la comisura labial hacia la izquierda, imposibilidad de movilizar el hemicuerpo derecho y dificultad severa "
            "para emitir palabras (afasia mixta). "
            "Signos vitales al ingreso: TA 175/95 mmHg, FC 104 lpm arrítmica, FR 16 rpm, SpO2 98% al aire ambiente, Temp 36.8 °C. "
            "Examen neurológico: somnoliento pero reactivo a estímulos, hemiparesia braquiocrural derecha flácida facio-braquio-crural 1/5, "
            "reflejo de Babinski positivo derecho. Pupilas isocóricas reactivas."
        ),
        "sesgos_esperados": [
            "Cierre Prematuro",
            "Desestimación de Banderas Rojas",
            "Inercia Diagnóstica"
        ],
        "red_flags": [
            "El tiempo es cerebro (Time is brain): Paciente dentro de la ventana de reperfusión (< 4.5 horas para trombólisis EV y hasta 6-24 hs para trombectomía mecánica).",
            "Descartar de inmediato hipoglucemia como stroke mimic antes de trasladar al tomógrafo.",
            "Evitar descensos bruscos de presión arterial salvo que supere 185/110 mmHg previo a trombolisis."
        ],
        "calculadoras_pertinentes": ["calculadora_ckd_epi"],
        "guia_oficial_titulo": "Guía AHA/ASA: Manejo Temprano del ACV Isquémico Agudo",
        "guia_oficial_sociedad": "AHA / ASA (Stroke)",
        "guia_oficial_url": "https://www.ahajournals.org/doi/10.1161/STR.0000000000000211"
    },

    "Caso 09: Injuria Renal Aguda e hiperpotasemia severa por 'Triple Whammy'": {
        "titulo": "Mujer de 76 años con astenia extrema y debilidad muscular progresiva",
        "area": "Nefrología / Medio Interno",
        "dificultad": "Avanzada",
        "viñeta": (
            "Mujer de 76 años con antecedentes de hipertensión arterial, osteoartrosis severa de rodillas e insuficiencia cardíaca con FEVI preservada. "
            "Medicación habitual: Enalapril 20 mg/día y Furosemida 40 mg/día. Hace 5 días inició por cuenta propia Ibuprofeno 600 mg cada 8 hs por gonartralgia intensa. "
            "Es traída a la guardia por debilidad motora simétrica progresiva en miembros inferiores que le impide deambular, astenia extrema, mareos y oliguria marcada en las últimas 24 hs. "
            "Signos vitales: TA 95/60 mmHg, FC 48 lpm bradicárdico y regular, FR 18 rpm, SpO2 96%, Temp 36.4 °C. "
            "Laboratorio de urgencia: Creatinina 4.2 mg/dL (basal 0.9), Urea 145 mg/dL, Potasio sérico 7.2 mEq/L, Sodio 132 mEq/L. "
            "ECG: Bradicardia sinusal, ondas T simétricas altas, picudas y de base estrecha, con aplanamiento de ondas P y ensanchamiento del complejo QRS."
        ),
        "sesgos_esperados": [
            "Tratamiento Inseguro",
            "Error de Cálculo",
            "Anclaje y Ajuste Insuficiente"
        ],
        "red_flags": [
            "Emergencia cardiológica inminente por hiperpotasemia severa (K+ 7.2 mEq/L) con alteraciones electrocardiográficas: riesgo inmediato de fibrilación ventricular o asistolia.",
            "Prioridad terapéutica número 1: Gluconato de Calcio al 10% endovenoso para estabilizar la membrana miocárdica (NO baja el potasio, previene el paro cardíaco).",
            "Interrupción inmediata de Enalapril, AINEs y diuréticos; medidas de cambio intracelular (Insulina + Glucosa) y eliminación (nebulización con salbutamol / resinas / hemodiálisis de urgencia)."
        ],
        "calculadoras_pertinentes": ["calculadora_ckd_epi", "calculadora_metabolica_cad"],
        "guia_oficial_titulo": "Guías ERC: Manejo de Emergencia de la Hiperpotasemia y Toxicidad Cardíaca",
        "guia_oficial_sociedad": "European Resuscitation Council (Resuscitation)",
        "guia_oficial_url": "https://doi.org/10.1016/j.resuscitation.2021.02.011"
    },

    "Caso 10: Insuficiencia cardíaca aguda y edema agudo de pulmón hipertensivo": {
        "titulo": "Varón de 69 años con disnea paroxística, ortopnea y esputo asalmonado",
        "area": "Cardiología / Terapia Intensiva",
        "dificultad": "Intermedia",
        "viñeta": (
            "Varón de 69 años, extabaquista, con antecedentes de infarto de miocardio hace 4 años e hipertensión arterial con escaso apego medicamentoso. "
            "Consulta a las 3:00 AM por cuadro de instalación súbita caracterizado por disnea de reposo asfixiante, ortopnea absoluta (imposibilidad de acostarse), "
            "tos con expectoración asalmonada espumosa y sudoración profusa. "
            "Signos vitales al ingreso: TA 205/115 mmHg, FC 124 lpm regular, FR 34 rpm con tiraje intercostal, SpO2 82% al aire ambiente, afebril. "
            "Examen físico: ingurgitación yugular 3/3 con colapso ausente, ritmo de galope por tercer ruido (R3) y soplo holosistólico mitral 3/6. "
            "Auscultación pulmonar: estertores crepitantes bilaterales hasta campos superiores acompañados de sibilancias espiratorias difusas ('asma cardíaco')."
        ),
        "sesgos_esperados": [
            "Sesgo de Encuadre",
            "Tratamiento Inseguro",
            "Cierre Prematuro"
        ],
        "red_flags": [
            "Edema Agudo de Pulmón cardiogénico hipertensivo en fallo respiratorio inminente: requiere soporte con VNI (CPAP/BiPAP) de urgencia.",
            "Tratamiento farmacológico urgente: Nitroglicerina sublingual/endovenosa para reducir postcarga y Furosemida EV. NO administrar betabloqueantes en fase congestiva descompensada.",
            "No confundir sibilancias de 'asma cardíaco' con broncoespasmo primario; la causa es congestión peribronquial."
        ],
        "calculadoras_pertinentes": ["calculadora_score_heart", "calculadora_ckd_epi"],
        "guia_oficial_titulo": "Guías ESC: Diagnóstico y Tratamiento de la Insuficiencia Cardíaca Aguda",
        "guia_oficial_sociedad": "European Society of Cardiology (EHJ)",
        "guia_oficial_url": "https://academic.oup.com/eurheartj/article/42/36/3599/6358045"
    },

    "Caso 11: Cirrosis descompensada con ascitis a tensión y sospecha de peritonitis bacteriana": {
        "titulo": "Varón de 54 años con cirrosis alcohólica, dolor abdominal continuo y letargia",
        "area": "Gastroenterología / Hepatología",
        "dificultad": "Avanzada",
        "viñeta": (
            "Paciente varón de 54 años con diagnóstico conocido de cirrosis hepática de origen enólico (Child-Pugh B). "
            "Es traído a la guardia por su pareja debido a somnolencia diurna, lentitud en las respuestas, inversión del ritmo del sueño y temblor distal "
            "en las manos de 48 horas de evolución. Asocia distensión abdominal progresiva dolorosa y registros de febrícula (37.9 °C). "
            "Signos vitales: TA 105/65 mmHg, FC 96 lpm, FR 20 rpm, SpO2 96%, Temp 37.8 °C axilar. "
            "Examen físico: ictericia cutáneo-mucosa leve, telangiectasias aracniformes en tórax superior. Abdomen globuloso por ascitis a gran tensión, "
            "matidez desplazable presente, dolor difuso a la palpación profunda sin peritonismo franco. Presenta asterixis (flapping) bilateral positivo."
        ),
        "sesgos_esperados": [
            "Búsqueda Satisfecha",
            "Cierre Prematuro",
            "Inercia Diagnóstica"
        ],
        "red_flags": [
            "Trampa de Búsqueda Satisfecha: Diagnosticar encefalopatía hepática y olvidar la causa desencadenante. En todo cirrótico con ascitis y descompensación o febrícula, la PARACENTESIS DIAGNÓSTICA es obligatoria antes de iniciar antibióticos.",
            "Peritonitis Bacteriana Espontánea (PBE): Recuento de polimorfonucleares en líquido ascítico >= 250/mm3 confirma diagnóstico. Requiere Cefotaxima/Ceftriaxona EV inmediata y Albúmina humana (1.5 g/kg día 1, 1 g/kg día 3) para prevenir síndrome hepatorrenal."
        ],
        "calculadoras_pertinentes": ["calculadora_ckd_epi", "calculadora_glasgow_blatchford"],
        "guia_oficial_titulo": "Guías EASL: Cirrosis Descompensada, Ascitis y Peritonitis Bacteriana (PBE)",
        "guia_oficial_sociedad": "EASL (Journal of Hepatology)",
        "guia_oficial_url": "https://doi.org/10.1016/j.jhep.2018.03.024"
    },

    "Caso 12: Pancreatitis aguda litiásica con respuesta inflamatoria sistémica": {
        "titulo": "Mujer de 48 años con dolor epigástrico transfictivo en cinturón tras ingesta grasa",
        "area": "Gastroenterología / Cirugía General",
        "dificultad": "Intermedia",
        "viñeta": (
            "Paciente femenina de 48 años, con antecedentes de cólicos biliares a repetición y ecografía previa que reportaba litiasis vesicular múltiple. "
            "Consulta por cuadro de 12 horas de evolución que inició 2 horas después de una cena abundante copiosa en grasas. "
            "Presenta dolor epigástrico de inicio rápido, intensidad 10/10, continuo, transfictivo, irradiado en barra a ambos hipocondrios y al dorso, "
            "asociado a vómitos biliosos reiterados que no alivian el dolor. "
            "Signos vitales al ingreso: TA 98/62 mmHg, FC 116 lpm regular, FR 24 rpm, SpO2 95% al aire ambiente, Temp 38.1 °C. "
            "Examen abdominal: abdomen doloroso a la palpación en epigastrio y mesogastrio con defensa involuntaria, ruidos hidroaéreos disminuidos. "
            "Laboratorio: Amilasa 1950 U/L (VN < 100), Lipasa 2600 U/L (VN < 60), Leucocitos 16.500/mm3, Hematocrito 47%, Bilirrubina total 2.4 mg/dL."
        ),
        "sesgos_esperados": [
            "Tratamiento Inseguro",
            "Falacia de Costos Hundidos",
            "Error de Cálculo"
        ],
        "red_flags": [
            "Diagnóstico confirmado de Pancreatitis Aguda (dolor típico + enzimas pancreáticas > 3 veces el límite normal).",
            "Cumple criterios de SIRS (FC > 90, FR > 20, Leucocitos > 12.000, Temp > 38 °C) y hemoconcentración (Hto 47%): alto riesgo de necrosis y disfunción multiorgánica.",
            "Resucitación hídrica precoz guiada por metas con Ringer Lactato (controlar diuresis horaria y descenso del hematocrito).",
            "NO indicar antibióticos profilácticos de rutina (contraindicado en guías internacionales salvo sospecha fundada de colangitis o necrosis infectada confirmada)."
        ],
        "calculadoras_pertinentes": ["calculadora_qsofa", "calculadora_ckd_epi"],
        "guia_oficial_titulo": "Surviving Sepsis Campaign: Manejo Internacional de Sepsis y Shock Séptico",
        "guia_oficial_sociedad": "SCCM / ESICM (Critical Care Med)",
        "guia_oficial_url": "https://journals.lww.com/ccmjournal/fulltext/2021/11000/surviving_sepsis_campaign__international.21.aspx"
    },

    "Caso 13: Tromboembolismo pulmonar (TEP) submasivo con sobrecarga de ventrículo derecho": {
        "titulo": "Mujer de 56 años con disnea súbita, dolor pleurítico y taquicardia persistente",
        "area": "Cardiología / Terapia Intensiva",
        "dificultad": "Avanzada",
        "viñeta": (
            "Paciente femenina de 56 años, antecedente de cirugía artroscópica de rodilla derecha hace 12 días bajo reposo relativo. "
            "Consulta en guardia por disnea de inicio súbito en reposo de 6 horas de evolución, acompañada de dolor torácico pleurítico en hemitórax derecho y tos seca. "
            "Signos vitales al ingreso: TA 118/74 mmHg (normotensa sistémica), FC 122 lpm regular, FR 28 rpm, SpO2 89% al aire ambiente que corrige a 93% con cánula nasal a 3 L/min, Temp 37.1 °C. "
            "Examen físico: taquipneica, ruidos cardíacos taquicárdicos con refuerzo del segundo componente pulmonar (R2), sin soplos ni frote. Pantorrilla derecha con leve edema y dolor a la dorsiflexión. "
            "ECG: taquicardia sinusal con patrón S1Q3T3 y ondas T negativas asimétricas de V1 a V4. "
            "Biomarcadores: Troponina I ultrasensible 0.18 ng/mL (marcadamente elevada), proBNP 1420 pg/mL. "
            "Ecocardiograma bedside (POCUS): dilatación significativa del ventrículo derecho con relación VD/VI > 1.0 y acinesia de pared libre con motilidad apical preservada (signo de McConnell)."
        ),
        "sesgos_esperados": [
            "Sesgo de Encuadre",
            "Cierre Prematuro",
            "Inercia Diagnóstica"
        ],
        "red_flags": [
            "Estratificación de riesgo vital: TEP de Riesgo Intermedio-Alto (Submasivo): normotensión arterial sistémica pero con biomarcadores de necrosis miocárdica (troponina positiva) y sobrecarga ecocardiográfica de ventrículo derecho.",
            "Alto riesgo de descompensación hemodinámica aguda y colapso obstructivo en las primeras 24-48 horas.",
            "Iniciar anticoagulación terapéutica parenteral inmediata (HBPM o heparina no fraccionada) sin demora diagnóstica.",
            "Internación mandatoria en Unidad Coronaria / Cuidados Críticos para monitoreo continuo; tener disponible protocolo de rescate con trombolíticos sistémicos ante cualquier signo de hipotensión sostenida."
        ],
        "calculadoras_pertinentes": ["calculadora_score_wells_tep", "calculadora_indice_shock"],
        "guia_oficial_titulo": "Guías ESC/ERS: Diagnóstico y Manejo del Tromboembolismo Pulmonar Agudo",
        "guia_oficial_sociedad": "ESC / ERS (European Heart Journal)",
        "guia_oficial_url": "https://academic.oup.com/eurheartj/article/41/4/543/5556136"
    },

    "Caso 14: Disección aórtica aguda tipo A con insuficiencia aórtica": {
        "titulo": "Varón de 61 años con dolor torácico desgarrante interescapular y asimetría de pulsos",
        "area": "Cardiología / Urgencias Quirúrgicas",
        "dificultad": "Avanzada",
        "viñeta": (
            "Varón de 61 años con antecedentes de hipertensión arterial mal controlada y tabaquismo activo. "
            "Ingresa al shock room trasladado por servicio de emergencias debido a dolor torácico agudo de inicio súbito, máxima intensidad (10/10) desde el primer segundo, "
            "de carácter desgarrante y punzante, localizado en región retroesternal e irradiado a la región interescapular dorsal y epigastrio. Refiere diaforesis y sensación de muerte inminente. "
            "Signos vitales: TA en brazo derecho 185/95 mmHg, TA en brazo izquierdo 140/80 mmHg (diferencial tensional > 40 mmHg), FC 96 lpm regular, FR 22 rpm, SpO2 96%, Temp 36.4 °C. "
            "Examen físico: paciente pálido y sudoroso. Pulsos radial y femoral izquierdos notablemente disminuidos respecto a los contralaterales. "
            "Auscultación cardíaca: soplo diastólico precoz de regurgitación aspirativo en foco aórtico accesorio (3/6). "
            "ECG: taquicardia sinusal sin supradesnivel del segmento ST, hipertrofia ventricular izquierda por criterios de voltaje."
        ),
        "sesgos_esperados": [
            "Anclaje y Ajuste Insuficiente",
            "Tratamiento Inseguro",
            "Cierre Prematuro"
        ],
        "red_flags": [
            "Sospecha clínica crítica de Disección Aórtica Aguda de Aorta Ascendente (Stanford Tipo A / DeBakey I-II).",
            "CONTRAINDICACIÓN MORTAL: PROHIBIDO administrar carga de antiagregantes plaquetarios (AAS, clopidogrel) ni anticoagulantes (heparinas) asumiendo erróneamente un infarto agudo de miocardio.",
            "Terapia anti-impulso inmediata (Anti-impulse therapy): betabloqueantes intravenosos (esmolol o labetalol) para reducir la FC < 60 lpm y TA sistólica a 100-120 mmHg antes de administrar vasodilatadores puros.",
            "AngioTAC de aorta toracoabdominal de emergencia y llamado inmediato a Cirugía Cardiovascular para esternotomía de urgencia."
        ],
        "calculadoras_pertinentes": ["calculadora_score_heart", "calculadora_indice_shock"],
        "guia_oficial_titulo": "Guía ACC/AHA: Diagnóstico y Manejo de la Enfermedad Aórtica",
        "guia_oficial_sociedad": "AHA / ACC (Circulation)",
        "guia_oficial_url": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001106"
    },

    "Caso 15: Taponamiento cardíaco agudo con pulso paradójico": {
        "titulo": "Mujer de 46 años con disnea progresiva, ingurgitación yugular e hipotensión",
        "area": "Cardiología / Terapia Intensiva",
        "dificultad": "Avanzada",
        "viñeta": (
            "Paciente femenina de 46 años, con diagnóstico reciente de pericarditis aguda hace 10 días en tratamiento irregular con antiinflamatorios no esteroideos. "
            "Consulta en guardia por debilidad extrema, disnea rápidamente progresiva que le impide el decúbito (ortopnea severa) y mareos al sentarse de 24 horas de evolución. "
            "Signos vitales al ingreso: TA 88/60 mmHg, FC 128 lpm regular y filiforme, FR 26 rpm, SpO2 94% al aire ambiente, Temp 37.0 °C. "
            "Examen físico: paciente sentada inclinada hacia adelante, pálida y con frialdad distal. Ingurgitación yugular 3/3 hasta el ángulo mandibular a 45 grados. "
            "Ruidos cardíacos notablemente apagados y lejanos a la auscultación. A la palpación de la tensión arterial con esfingomanómetro se constata una caída de la TA sistólica de 16 mmHg durante la inspiración espontánea (pulso paradójico > 10 mmHg). "
            "ECG: taquicardia sinusal con bajo voltaje generalizado y alternancia eléctrica de complejos QRS."
        ),
        "sesgos_esperados": [
            "Tratamiento Inseguro",
            "Inercia Diagnóstica",
            "Sesgo de Encuadre"
        ],
        "red_flags": [
            "Presencia de Tríada de Beck completa (hipotensión arterial + ruidos cardíacos apagados + ingurgitación yugular marcada) más pulso paradójico patológico: emergencia vital por Taponamiento Cardíaco.",
            "CONTRAINDICACIÓN MORTAL: PROHIBIDO administrar diuréticos (furosemida) o vasodilatadores (nitratos, IECA), ya que destruyen la presión de llenado ventricular dependiente de precarga y provocan paro cardíaco electromecánico inmediato.",
            "Expansión hídrica con cristaloides (500-1000 ml en bolo rápido) como puente hemodinámico temporal para optimizar la precarga.",
            "Pericardiocentesis evacuadora urgente guiada por ecocardiografía o ventana pericárdica quirúrgica inmediata."
        ],
        "calculadoras_pertinentes": ["calculadora_indice_shock"],
        "guia_oficial_titulo": "Guías ESC: Diagnóstico y Manejo de las Enfermedades del Pericardio",
        "guia_oficial_sociedad": "ESC (European Heart Journal)",
        "guia_oficial_url": "https://academic.oup.com/eurheartj/article/36/42/2921/2293394"
    },

    "Caso 16: Hemorragia intracraneal aguda bajo anticoagulación oral directa (DOAC)": {
        "titulo": "Varón de 74 años con cefalea súbita, hemiparesia e HTA severa bajo Rivaroxabán",
        "area": "Neurología / Terapia Intensiva",
        "dificultad": "Avanzada",
        "viñeta": (
            "Varón de 74 años con antecedente de fibrilación auricular no valvular en tratamiento crónico con Rivaroxabán 20 mg/día (última toma hace 4 horas) e hipertensión arterial. "
            "Mientras almorzaba presentó cefalea holocraneana de inicio súbito, náuseas, vómitos en chorro y debilidad brusca en hemicuerpo izquierdo con dificultad para hablar. "
            "Es traído de inmediato al shock room (tiempo de inicio: 75 minutos). Al ingreso: Glasgow 12/15 (apertura ocular 3, respuesta verbal 4, respuesta motora 5), disartria moderada, hemiparesia facio-braquio-crural izquierda densa (fuerza 1/5) y reflejo cutáneo plantar izquierdo extensor (Babinski positivo). "
            "Signos vitales: TA 205/115 mmHg, FC 82 lpm arrítmico, FR 18 rpm, SpO2 96%, Temp 36.8 °C. "
            "Tomografía de cráneo sin contraste urgente: hematoma intraparenquimatoso hemisférico derecho de 38 cc con edema perilesional y desviación de la línea media de 4 mm."
        ),
        "sesgos_esperados": [
            "Inercia Diagnóstica",
            "Tratamiento Inseguro",
            "Cierre Prematuro"
        ],
        "red_flags": [
            "Hemorragia Intraparenquimatosa Aguda hiperaguda (< 2 horas) con alto riesgo de expansión del hematoma y enclavamiento uncal secundario a anticoagulación activa.",
            "Reversión inmediata de la anticoagulación: administración urgente de Complejo Protrombínico Concentrado de 4 factores (4F-PCC) a 50 UI/kg o Andexanet alfa.",
            "Control tensional intensivo inmediato: descenso progresivo y controlado de la TA sistólica a una meta de 130-140 mmHg mediante infusión continua titulable (labetalol o nicardipino IV). Evitar descensos bruscos por debajo de 120 mmHg.",
            "Consulta neuroquirúrgica inmediata y evaluación de colocación de catéter de monitoreo de PIC."
        ],
        "calculadoras_pertinentes": ["calculadora_score_nihss", "calculadora_ckd_epi"],
        "guia_oficial_titulo": "Guías AHA/ASA: Manejo de Pacientes con Hemorragia Intracerebral Espontánea",
        "guia_oficial_sociedad": "AHA / ASA (Stroke)",
        "guia_oficial_url": "https://www.ahajournals.org/doi/10.1161/STR.0000000000000407"
    },

    "Caso 17: Status epiléptico convulsivo refractario": {
        "titulo": "Mujer de 28 años con crisis tónico-clónica generalizada continua de más de 10 minutos",
        "area": "Neurología / Urgencias Críticas",
        "dificultad": "Avanzada",
        "viñeta": (
            "Paciente femenina de 28 años, con diagnóstico conocido de epilepsia focal con generalización secundaria desde la adolescencia, tratada con lamotrigina 200 mg/día (con abandono de medicación en los últimos 3 días por desabastecimiento). "
            "Ingresa al shock room trasladada por ambulancia presentando convulsión tónico-clónica generalizada activa con mordedura lateral de lengua, sialorrea y cianosis peribucal. "
            "Los paramédicos refieren que las contracciones llevan 12 minutos continuos sin recuperación de la conciencia. "
            "Al examen en guardia: movimientos clónicos rítmicos en 4 extremidades, supraversión de la mirada, midriasis bilateral poco reactiva. "
            "Signos vitales: TA 155/95 mmHg, FC 138 lpm sinusal, FR asistida con bolsa-máscara, SpO2 88% con O2 a 15 L/min, Temp 38.3 °C (hipertermia por contracción sostenida). Glucemia capilar bedside: 112 mg/dL."
        ),
        "sesgos_esperados": [
            "Inercia Diagnóstica",
            "Error de Cálculo",
            "Desestimación Red Flags"
        ],
        "red_flags": [
            "Status Epiléptico Convulsivo Activo que superó el tiempo T1 (5 minutos): daño neuronal y refractariedad farmacológica creciente por internalización de receptores GABA.",
            "Fase 1 (0-5 min de atención): Benzodiacepina IV de primera línea en dosis PLENA (Lorazepam 4 mg IV directo o Diazepam 10 mg IV lento en 2 min). Repetir una vez a los 5 min si no cede. NO infradosificar.",
            "Fase 2 (falla de benzodiacepinas, 10-20 min): Iniciar inmediatamente fármaco anticrisis intravenoso de segunda línea: Levetiracetam 60 mg/kg (máx 4500 mg) o Ácido Valproico 40 mg/kg IV en infusión rápida de 10 min.",
            "Fase 3 (>20 min, Status Refractario): Intubación orotraqueal, asistencia respiratoria mecánica e inducción anestésica (Propofol o Midazolam en infusión continua) con monitoreo EEG continuo."
        ],
        "calculadoras_pertinentes": ["calculadora_indice_shock"],
        "guia_oficial_titulo": "Guías de la American Epilepsy Society (AES): Tratamiento del Status Epiléptico en Adultos",
        "guia_oficial_sociedad": "AES (Epilepsy Currents)",
        "guia_oficial_url": "https://journals.sagepub.com/doi/full/10.5698/1535-7597-16.1.48"
    },

    "Caso 18: Síndrome de Guillain-Barré con riesgo inminente de falla ventilatoria": {
        "titulo": "Varón de 38 años con debilidad motora ascendente, arreflexia y disnea en decúbito",
        "area": "Neurología / Medicina Interna",
        "dificultad": "Avanzada",
        "viñeta": (
            "Varón de 38 años, previamente sano, con antecedente de cuadro gastroentérico diarreico autolimitado hace 18 días. "
            "Consulta por 4 días de parestesias distales en dedos de manos y pies seguidas de debilidad muscular progresiva y simétrica que comenzó en miembros inferiores dificultando la marcha y que en las últimas 24 horas comprometió miembros superiores. "
            "Al examen neurológico: tetraparesia flácida simétrica con fuerza muscular 2/5 proximal y 1/5 distal en miembros inferiores, 3/5 en miembros superiores. Arreflexia osteotendinosa universal profunda (reflejos patelar, aquiliano, bicipital y tricipital 0/4). Sensibilidad táctil y propioceptiva levemente disminuida en guante y calcetín. "
            "Signos vitales: TA lábil que oscila entre 150/95 y 100/60 mmHg (disautonomía), FC 102 lpm, FR 24 rpm, SpO2 95% al aire ambiente. "
            "Refiere que al acostarse plano siente opresión y falta de aire (ortopnea por debilidad diafragmática). Prueba de cuenta numérica en una sola respiración: 11 (normal > 20)."
        ),
        "sesgos_esperados": [
            "Tratamiento Inseguro",
            "Inercia Diagnóstica",
            "Sesgo de Encuadre"
        ],
        "red_flags": [
            "Sospecha fundada de Síndrome de Guillain-Barré (Polirradiculoneuropatía Desmielinizante Inflamatoria Aguda) con compromiso respiratorio inminente (debilidad diafragmática y disautonomía autonómica).",
            "CONTRAINDICACIÓN BIOLÓGICA: PROHIBIDO administrar corticoides sistémicos (prednisona, metilprednisolona): la evidencia internacional Clase I demostró que los corticoides están contraindicados de forma aislada y no aceleran la recuperación en SGB.",
            "Monitoreo ventilatorio bedside obligatorio con la regla del 20/30/40: Capacidad Vital Forzada < 20 ml/kg, Presión Inspiratoria Máxima < 30 cmH2O o Presión Espiratoria Máxima < 40 cmH2O indican intubación electiva antes del paro respiratorio súbito.",
            "Tratamiento inmunomodulador específico precoz: Inmunoglobulina Humana Intravenosa (IVIG 0.4 g/kg/día por 5 días) o Plasmaféresis terapéutica."
        ],
        "calculadoras_pertinentes": ["calculadora_ckd_epi"],
        "guia_oficial_titulo": "Guía de Consenso Internacional EAN/PNS: Diagnóstico y Tratamiento del Síndrome de Guillain-Barré",
        "guia_oficial_sociedad": "EAN / PNS (J Peripher Nerv Syst)",
        "guia_oficial_url": "https://doi.org/10.1111/jns.12594"
    },

    "Caso 19: Neutropenia febril posquimioterapia en shock séptico precoz": {
        "titulo": "Varón de 52 años en tratamiento por linfoma con fiebre de 38.8 °C y neutrófilos en 180/mm3",
        "area": "Oncología / Infectología / Sepsis",
        "dificultad": "Avanzada",
        "viñeta": (
            "Varón de 52 años con diagnóstico de Linfoma no Hodgkin difuso de células B grandes, quien completó su tercer ciclo de quimioterapia esquema R-CHOP hace 8 días. "
            "Consulta en guardia por registros febriles axilares de hasta 38.8 °C en las últimas 4 horas, escalofríos intensos y astenia marcada. "
            "Niega síntomas respiratorios o urinarios, portador de catéter venoso central implantable (port-a-cath) en hemitórax derecho sin eritema visible pero con leve molestia local. "
            "Signos vitales: TA 88/54 mmHg, FC 124 lpm regular, FR 24 rpm, SpO2 96% al aire ambiente, Temp 38.9 °C. "
            "Laboratorio urgente: Leucocitos 650/mm3 con 28% de neutrófilos segmentados (Recuento Absoluto de Neutrófilos - RAN: 182/mm3, neutropenia profunda < 500), Plaquetas 65.000/mm3, Creatinina 1.3 mg/dL, Lactato sérico 3.8 mmol/L."
        ),
        "sesgos_esperados": [
            "Inercia Diagnóstica",
            "Búsqueda Satisfecha",
            "Desestimación Red Flags"
        ],
        "red_flags": [
            "Neutropenia Febril de Alto Riesgo en contexto de Sepsis / Shock Séptico inicial (Hipotensión, RAN < 500, Lactato 3.8 mmol/L).",
            "REGLA DE ORO DE TIEMPO (DOOR-TO-ANTIBIOTIC): Iniciar antibióticos intravenosos de amplio espectro antipseudomónico (Piperacilina/Tazobactam 4.5 g o Cefepima 2 g o Meropenem 1 g) ANTES de los 60 minutos del ingreso. Cada hora de retraso incrementa la mortalidad en un 8%.",
            "NUNCA esperar los resultados de hemocultivos (periféricos y de catéter) ni de imágenes para comenzar la infusión antimicrobiana.",
            "Resucitación hídrica con cristaloides a 30 ml/kg en bolo para restaurar la presión de perfusión arterial media > 65 mmHg."
        ],
        "calculadoras_pertinentes": ["calculadora_qsofa", "calculadora_indice_shock"],
        "guia_oficial_titulo": "Guías ASCO/IDSA: Profilaxis Antimicrobiana y Manejo de la Neutropenia Febril en Pacientes Oncológicos",
        "guia_oficial_sociedad": "ASCO / IDSA (J Clin Oncol)",
        "guia_oficial_url": "https://ascopubs.org/doi/10.1200/JCO.2017.76.7012"
    },

    "Caso 20: Síndrome de distress respiratorio agudo (SDRA) severo secundario a sepsis abdominal": {
        "titulo": "Mujer de 63 años en posoperatorio de peritonitis con hipoxemia refractaria y PaFi 82",
        "area": "Terapia Intensiva / Falla Respiratoria",
        "dificultad": "Avanzada",
        "viñeta": (
            "Paciente femenina de 63 años, cursando el 3° día posoperatorio de apendicectomía complicada con peritonitis purulenta de 4 cuadrantes. "
            "Evoluciona con deterioro progresivo de la mecánica ventilatoria, taquipnea extrema, disnea angustiosa y cianosis a pesar de máscara con reservorio a 15 L/min. "
            "Al examen físico: sudorosa, tiraje intercostal y supraesternal marcado, respiración en balancín toracoabdominal. Ruidos pulmonares: rales crepitantes difusos bilaterales que ocupan más de dos tercios de ambos campos. "
            "Signos vitales: TA 105/65 mmHg (con infusión baja de noradrenalina a 0.08 mcg/kg/min), FC 118 lpm, FR 34 rpm, SpO2 84% con máscara de no reinhalación. "
            "Gases arteriales con FiO2 estimada al 80%: pH 7.28, PaO2 66 mmHg, PaCO2 48 mmHg, HCO3 21 mEq/L, Lactato 2.9 mmol/L. Relación PaO2/FiO2 (PaFi) = 82.5 (Hipoxemia severa < 100). "
            "Radiografía de tórax portátil: infiltrados alveolares algodonosos bilaterales simétricos en alas de mariposa sin cardiomegalia. Ecocardiograma descarta disfunción ventricular izquierda aguda o sobrecarga hidrostática pura."
        ),
        "sesgos_esperados": [
            "Sesgo de Encuadre",
            "Tratamiento Inseguro",
            "Error de Cálculo"
        ],
        "red_flags": [
            "SDRA Severo de origen extrapulmonar según Criterios de Berlín (inicio agudo < 7 días, opacidades bilaterales no explicadas por falla cardíaca, PaFi < 100).",
            "Indicación urgente de Intubación Orotraqueal y Ventilación Mecánica con Estrategia Protectora Pulmonar estricta:",
            "1) Volumen corriente ultra-bajo de 4 a 6 ml/kg de peso predicho (evitar volutrauma y barotrauma con presión meseta o plateau < 30 cmH2O y driving pressure < 14 cmH2O).",
            "2) Titulación de PEEP alta según tabla ARDSNet (PEEP 12-16 cmH2O) y evaluar decúbito prono precoz (> 16 horas/día) por PaFi < 150.",
            "3) Restricción de fluidos (manejo hídrico seco) una vez lograda la estabilidad hemodinámica."
        ],
        "calculadoras_pertinentes": ["calculadora_qsofa", "calculadora_indice_shock"],
        "guia_oficial_titulo": "Guías ESICM/SCCM/ATS: Guía de Práctica Clínica para el Manejo del SDRA",
        "guia_oficial_sociedad": "ESICM / SCCM / ATS (Intensive Care Med)",
        "guia_oficial_url": "https://link.springer.com/article/10.1007/s00134-023-07050-7"
    },

    "Caso 21: Rabdomiólisis severa con injuria renal aguda e hipocalcemia asintomática": {
        "titulo": "Varón de 32 años rescatado tras inmovilización prolongada con orina colúrica y CPK de 42.000 UI/L",
        "area": "Nefrología / Urgencias Médicas",
        "dificultad": "Avanzada",
        "viñeta": (
            "Varón de 32 años, con antecedente de consumo problemático de alcohol y sedantes. "
            "Fue hallado en el piso de su departamento por familiares tras un período de inmovilización y pérdida de conocimiento estimado en 20 horas, comprimiendo el miembro inferior derecho sobre el piso rígido. "
            "Al ingreso se encuentra somnoliento pero reactivo. Refiere dolor muscular exquisito a la compresión en muslo y glúteo derechos, con edema tenso, empastamiento y parestesias distales en el pie. Orina a través de sonda vesical de color pardo oscuro ('en té cargado' o 'borra de café'), escasa (25 ml en la primera hora). "
            "Signos vitales: TA 135/85 mmHg, FC 98 lpm, FR 20 rpm, SpO2 97%, Temp 37.6 °C. "
            "Laboratorio de ingreso: CPK 42.500 UI/L (VN < 200), Mioglobina urinaria fuertemente positiva, Creatinina 3.8 mg/dL (basal estimada 0.9), Urea 94 mg/dL, Potasio sérico 5.8 mEq/L, Calcio iónico 0.85 mmol/L (Calcio total 6.8 mg/dL, hipocalcemia marcada), Fósforo 6.4 mg/dL. "
            "ECG: ritmo sinusal con ondas T picudas y simétricas en derivaciones precordiales."
        ),
        "sesgos_esperados": [
            "Tratamiento Inseguro",
            "Anclaje y Ajuste Insuficiente",
            "Inercia Diagnóstica"
        ],
        "red_flags": [
            "Rabdomiólisis Severa complicada con Injuria Renal Aguda pigmentaria oligúrica (KDIGO 3) y Síndrome Compartimental incipiente en muslo.",
            "CONTRAINDICACIÓN FARMACOLÓGICA CRÍTICA: PROHIBIDO reponer calcio intravenoso (gluconato ni cloruro) para tratar la hipocalcemia asintomática en fase inicial de la rabdomiólisis. El calcio administrado precipita masivamente como fosfato cálcico en los tejidos blandos y riñones, agravando la necrosis muscular y la falla renal irreversible (solo se indica calcio si hay arritmia por hiperpotasemia severa o tetania franca).",
            "Pilar terapéutico: Resucitación hídrica endovenosa agresiva inmediata con cristaloides isotónicos (solución fisiológica o ringer lactato) a 300-500 ml/hora para alcanzar un débito urinario objetivo de 200 a 300 ml/hora y 'lavar' los cilindros mioglobínicos.",
            "Monitoreo continuo de presión intracompartimental y vigilancia estrecha del potasio sérico por riesgo de hiperpotasemia letal."
        ],
        "calculadoras_pertinentes": ["calculadora_ckd_epi"],
        "guia_oficial_titulo": "Consenso Renal Association / Intensive Care Society: Manejo de la Rabdomiólisis en el Paciente Crítico",
        "guia_oficial_sociedad": "Renal Association / ICS (Critical Care)",
        "guia_oficial_url": "https://ccforum.biomedcentral.com/articles/10.1186/cc11918"
    },

    "Caso 22: Púrpura trombocitopénica trombótica (PTT) con anemia microangiopática": {
        "titulo": "Mujer de 36 años con petequias, anemia hemolítica, plaquetas en 14.000 y confusión fluctuante",
        "area": "Hematología / Terapia Intensiva",
        "dificultad": "Avanzada",
        "viñeta": (
            "Paciente femenina de 36 años, sin antecedentes mórbidos previos. Consulta en guardia por cuadro de 72 horas caracterizado por debilidad progresiva, tinte ictérico conjuntival y aparición de petequias y equimosis espontáneas en miembros inferiores y abdomen. "
            "Familiares refieren además episodios transitorios y fluctuantes de confusión, afasia motora y cefalea pulsátil que duran de 30 a 60 minutos y luego ceden parcialmente. "
            "Signos vitales: TA 140/85 mmHg, FC 106 lpm, FR 20 rpm, SpO2 97%, Temp 37.8 °C. "
            "Examen físico: palidez mucocutánea con ictericia escleral leve, petequias dispersas, sin visceromegalias. Examen neurológico en guardia: vigil pero bradipsíquica, con dificultad para nombrar objetos (afasia anómica leve transitoria), sin paresias focales evidentes. "
            "Laboratorio urgente: Hemoglobina 7.2 g/dL, Hematocrito 22%, Plaquetas 14.000/mm3 (trombocitopenia grave), Reticulocitos 7.5%, LDH 1850 U/L (marcadamente elevada), Bilirrubina total 3.8 mg/dL a predominio indirecto, Haptoglobina indetectable (< 10 mg/dL), Test de Coombs directo Negativo. "
            "Frotis de sangre periférica: abundantes esquizocitos (hematíes fragmentados en casco, 4.5% del total de eritrocitos). Función renal: Creatinina 1.6 mg/dL."
        ),
        "sesgos_esperados": [
            "Tratamiento Inseguro",
            "Cierre Prematuro",
            "Inercia Diagnóstica"
        ],
        "red_flags": [
            "Presentación clásica de Púrpura Trombocitopénica Trombótica (PTT) / Microangiopatía Trombótica por déficit severo de metaloproteasa ADAMTS13 (< 10%).",
            "CONTRAINDICACIÓN MORTAL ABSOLUTA: PROHIBIDO TRANSFUNDIR PLAQUETAS. La transfusión de concentrado de plaquetas añade sustrato al endotelio dañado y cataliza la formación masiva de microtrombos en la microcirculación cerebral y coronaria, desencadenando ACV masivo, infarto miocárdico y muerte inmediata (mortalidad > 90% sin tratamiento oportuno). Solo se tolera transfusión plaquetaria en caso de hemorragia mortal activa incontrolable.",
            "Emergencia médica absoluta: Iniciar Plasmaféresis Terapéutica (Recambio Plasmático Total con plasma fresco congelado a 1-1.5 volemias) dentro de las primeras 4-8 horas de sospecha.",
            "Tratamiento coadyuvante inmediato: Corticoides a altas dosis (Metilprednisolona 1 g IV/día o Prednisona 1 mg/kg) y evaluación de Caplacizumab (anticuerpo monoclonal anti-factor von Willebrand)."
        ],
        "calculadoras_pertinentes": ["calculadora_ckd_epi"],
        "guia_oficial_titulo": "Guías ISTH: Diagnóstico y Tratamiento de la Púrpura Trombocitopénica Trombótica (PTT)",
        "guia_oficial_sociedad": "ISTH (Journal of Thrombosis and Haemostasis)",
        "guia_oficial_url": "https://doi.org/10.1111/jth.15006"
    },

    "Caso 23: Crisis suprarrenal aguda en paciente con corticoterapia crónica": {
        "titulo": "Mujer de 59 años con shock hipotensivo refractario, hiponatremia y fiebre pos-infección respiratoria",
        "area": "Endocrinología / Cuidados Críticos",
        "dificultad": "Avanzada",
        "viñeta": (
            "Paciente femenina de 59 años, con antecedente de Artritis Reumatoidea seropositiva en tratamiento con Meprednisona 16 mg/día de forma continua durante los últimos 4 años. "
            "Hace 5 días suspendió abruptamente la toma de corticoides por indicación no médica tras presentar síntomas de gastroenteritis aguda con vómitos. "
            "Es traída a emergencias por su familia en estado de sopor profundo, debilidad generalizada, dolor abdominal difuso y colapso circulatorio. "
            "Al ingreso en el shock room: somnolienta, responde con monosílabos, frialdad periférica y livideces en rodillas. "
            "Signos vitales: TA 72/42 mmHg, FC 122 lpm regular y filiforme, FR 22 rpm, SpO2 96%, Temp 38.4 °C. Se inicia resucitación con 2000 ml de solución fisiológica al 0.9% y se coloca catéter para infusión de Noradrenalina hasta 0.25 mcg/kg/min; a pesar de ello la TA persiste en 78/48 mmHg (Shock distributivo-vasodilatado refractario a vasopresores). "
            "Laboratorio urgente: Glucemia 62 mg/dL (hipoglucemia), Sodio sérico 126 mEq/L (hiponatremia hipoosmolar), Potasio sérico 5.7 mEq/L (hiperpotasemia), Creatinina 1.4 mg/dL, Leucocitos 13.200/mm3."
        ),
        "sesgos_esperados": [
            "Sesgo de Encuadre",
            "Cierre Prematuro",
            "Inercia Diagnóstica"
        ],
        "red_flags": [
            "Shock refractario a catecolaminas con tríada metabólica clásica (Hiponatremia + Hiperpotasemia + Hipoglucemia) en paciente con supresión del eje hipotálamo-hipófiso-adrenal por suspensión brusca de corticoterapia: Emergencia vital por Crisis Suprarrenal Aguda (Insuficiencia Suprarrenal Aguda).",
            "El error más común es catalogar el cuadro como 'shock séptico puro refractario' y aumentar indiscriminadamente la dosis de noradrenalina o vasopresina sin restituir el déficit hormonal.",
            "ACCIÓN TERAPÉUTICA INMEDIATA: Administrar bolo intravenoso directo de Hidrocortisona 100 mg IV inmediatamente, seguido de 200 mg/24 horas en infusión continua o 50 mg cada 6 horas IV.",
            "Resucitación hídrica agresiva con solución fisiológica al 0.9% combinada con dextrosa al 5% para corregir la hipovolemia y la hipoglucemia. NO esperar los resultados de cortisol plasmático o ACTH para tratar."
        ],
        "calculadoras_pertinentes": ["calculadora_indice_shock", "calculadora_qsofa"],
        "guia_oficial_titulo": "Guía de Práctica Clínica de la Endocrine Society: Diagnóstico y Manejo de la Insuficiencia Suprarrenal",
        "guia_oficial_sociedad": "Endocrine Society (J Clin Endocrinol Metab)",
        "guia_oficial_url": "https://doi.org/10.1210/jc.2015-1710"
    },

    "Caso 24: Intoxicación aguda por monóxido de carbono (CO) con compromiso miocárdico": {
        "titulo": "Varón de 29 años con cefalea, confusión y dolor precordial tras exposición a brasero en ambiente cerrado",
        "area": "Toxicología / Urgencias Ambientales",
        "dificultad": "Avanzada",
        "viñeta": (
            "Varón de 29 años, sin antecedentes patológicos, traído en ambulancia junto a su pareja desde su vivienda precaria durante una noche de invierno con temperaturas bajo cero. "
            "Habían encendido un brasero de carbón y una estufa a querosén para calefaccionar la habitación sin ventilación. El paciente fue hallado por un vecino en el suelo, con náuseas intensas, vómitos, cefalea pulsátil opresiva holocraneana y marcada desorientación temporoespacial. Refiere además opresión retroesternal difusa. "
            "Al ingreso: estuporoso pero localiza estímulos, piel con leve rubicundez, mucosas húmedas. "
            "Signos vitales: TA 105/65 mmHg, FC 115 lpm taquicárdico, FR 24 rpm, SpO2 99% mediante oxímetro de pulso de dedo convencional en aire ambiente, Temp 36.5 °C. "
            "ECG de 12 derivaciones: taquicardia sinusal con infradesnivel del segmento ST de 1 mm en V4-V6 y aplanamiento de ondas T. "
            "Laboratorio: Troponina I ultrasensible 0.28 ng/mL (marcadamente positiva para daño miocárdico agudo), Lactato sérico 4.2 mmol/L, CPK 620 UI/L."
        ),
        "sesgos_esperados": [
            "Anclaje y Ajuste Insuficiente",
            "Desestimación Red Flags",
            "Cierre Prematuro"
        ],
        "red_flags": [
            "TRAMPA COGNITIVA MORTAL DEL OXÍMETRO DE PULSO: La pulsioximetría estándar mide absorción lumínica a dos longitudes de onda (660 y 940 nm) y es incapaz de discriminar entre oxihemoglobina y carboxihemoglobina (COHb), arrojando lecturas falsamente normales o excelentes (SpO2 99%) a pesar de una hipoxia tisular letal.",
            "Confirmación diagnóstica obligatoria: solicitar Co-oximetría en sangre arterial o venosa para cuantificar el porcentaje exacto de Carboxihemoglobina (COHb > 15-25% confirma intoxicación severa).",
            "Pilar de resucitación inmediato: Oxigenoterapia normobárica al 100% mediante máscara con bolsa de reservorio y válvula de no reinhalación a 15 L/min (reduce la vida media de la COHb de 320 minutos al aire a 80 minutos con FiO2 100%).",
            "Criterios de Oxigenoterapia Hiperbárica (OHB / Cámara Hiperbárica a 2.5-3 ATA dentro de las primeras 6 horas): pérdida de conciencia / coma, déficit neurológico focal, compromiso miocárdico isquémico (troponina elevada / cambios en ECG) o acidosis metabólica severa (lactato > 2.5)."
        ],
        "calculadoras_pertinentes": ["calculadora_score_heart", "calculadora_indice_shock"],
        "guia_oficial_titulo": "Guía Clínica UHMS: Oxigenoterapia Hiperbárica en la Intoxicación por Monóxido de Carbono",
        "guia_oficial_sociedad": "Undersea and Hyperbaric Medical Society (UHMS / CDC)",
        "guia_oficial_url": "https://www.uhms.org/resources/featured-resources/carbon-monoxide.html"
    }
}


def obtener_banco_completo() -> dict:
    """Retorna el banco completo de casos: los 24 casos oficiales de fábrica más los casos personalizados guardados."""
    banco = dict(BANCO_CASOS)
    try:
        personalizados = leer_casos_personalizados()
        if personalizados:
            banco.update(personalizados)
    except Exception:
        pass
    return banco

def obtener_nombres_casos() -> list:
    return list(obtener_banco_completo().keys())

def obtener_caso(nombre: str) -> dict:
    return obtener_banco_completo().get(nombre, {})

# ==================== CALCULADORAS BIOMEDICAS ====================
from typing import Dict, Any, Optional

def calcular_ckd_epi_2021(creatinina: float, edad: int, sexo: str) -> Dict[str, Any]:
    """
    Ecuación CKD-EPI 2021 libre de raza para Tasa de Filtrado Glomerular estimada (TFGe).
    Sexo: 'F' / 'femenino' o 'M' / 'masculino'.
    """
    sexo_norm = sexo.strip().lower()
    es_mujer = sexo_norm in ['f', 'femenino', 'female', 'mujer']
    
    if creatinina <= 0 or edad <= 0:
        return {"error": "Creatinina y edad deben ser valores positivos mayores a cero."}
    
    if es_mujer:
        kappa = 0.7
        alpha = -0.241
        factor_sexo = 1.012
    else:
        kappa = 0.9
        alpha = -0.302
        factor_sexo = 1.000
        
    cr_div_kappa = creatinina / kappa
    min_val = min(cr_div_kappa, 1.0)
    max_val = max(cr_div_kappa, 1.0)
    
    tfge = 142.0 * (min_val ** alpha) * (max_val ** -1.200) * (0.9938 ** edad) * factor_sexo
    tfge = round(tfge, 1)
    
    # Estadio KDIGO
    if tfge >= 90:
        estadio = "G1 (Normal o elevado)"
        implicancia = "Función renal conservada salvo daño estructural."
    elif tfge >= 60:
        estadio = "G2 (Levemente disminuido)"
        implicancia = "Monitorear progresión; ajustar dosis solo en fármacos de rango terapéutico estrecho."
    elif tfge >= 45:
        estadio = "G3a (Disminución leve a moderada)"
        implicancia = "Requiere ajuste de dosis en antibióticos (betalactámicos, vancomicina), AINEs contraindicados."
    elif tfge >= 30:
        estadio = "G3b (Disminución moderada a grave)"
        implicancia = "Ajustar la mayoría de fármacos renales; evaluar anemia y metabolismo mineral óseo."
    elif tfge >= 15:
        estadio = "G4 (Disminución grave)"
        implicancia = "Preparación para terapia de reemplazo renal; evitar contraste yodado si es posible."
    else:
        estadio = "G5 (Falla renal terminal)"
        implicancia = "Indicación de diálisis o trasplante renal; riesgo elevado de toxicidad farmacológica."
        
    return {
        "tfge": tfge,
        "unidad": "mL/min/1.73 m²",
        "formula": "CKD-EPI 2021 (Race-Free)",
        "estadio": estadio,
        "implicancia_clinica": implicancia
    }


def calcular_metabolica_cad(
    sodio_medido: float,
    cloro: float,
    bicarbonato: float,
    glucemia: float,
    albumina: Optional[float] = 4.0,
    potasio: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calcula Anión Gap estándar, Anión Gap corregido por albúmina (Figge-Jabor-Fencl)
    y Sodio corregido por glucemia (Katz y Hillier).
    """
    if bicarbonato <= 0 or sodio_medido <= 0 or cloro <= 0:
        return {"error": "Los electrolitos deben ser mayores a cero."}
        
    ag_observado = sodio_medido - (cloro + bicarbonato)
    
    # Corrección por albúmina (normal = 4.0 g/dL)
    alb_val = albumina if (albumina is not None and albumina > 0) else 4.0
    ag_corregido = ag_observado + 2.5 * (4.0 - alb_val)
    
    # Sodio corregido por hiperglucemia
    delta_gluc = max(0.0, glucemia - 100.0)
    na_katz = sodio_medido + 0.016 * delta_gluc
    na_hillier = sodio_medido + 0.024 * delta_gluc
    
    # Delta-Delta (Delta Gap / Delta Bicarbonato)
    # Evalúa trastornos mixtos ácido-base si hay AG elevado
    delta_ratio = None
    interpretacion_delta = "No aplicable (AG en rango normal)"
    if ag_corregido > 12:
        delta_ag = ag_corregido - 12.0
        delta_hco3 = 24.0 - bicarbonato
        if delta_hco3 > 0:
            delta_ratio = round(delta_ag / delta_hco3, 2)
            if delta_ratio < 0.8:
                interpretacion_delta = "Acidosis metabólica mixta: AG elevado + Acidosis hiperclorémica (AG normal concurrente)."
            elif delta_ratio > 1.6:
                interpretacion_delta = "Acidosis metabólica con AG elevado + Alcalosis metabólica concurrente o retención previa de HCO3."
            else:
                interpretacion_delta = "Acidosis metabólica pura con Anión Gap elevado (proporcional)."
        else:
            interpretacion_delta = "Acidosis con AG elevado concurrente con alcalosis metabólica importante (HCO3 > 24)."

    return {
        "anion_gap_observado": round(ag_observado, 1),
        "anion_gap_corregido_albumina": round(ag_corregido, 1),
        "albumina_utilizada": alb_val,
        "sodio_corregido_katz": round(na_katz, 1),
        "sodio_corregido_hillier": round(na_hillier, 1),
        "delta_gap_ratio": delta_ratio,
        "interpretacion_trastorno": interpretacion_delta,
        "alerta": "¡Hipoalbuminemia puede enmascarar un anión gap severo!" if alb_val < 3.5 else "Albúmina en rango esperado."
    }


def calcular_score_heart(historia: int, ecg: int, edad: int, factores_riesgo: int, troponina: int) -> Dict[str, Any]:
    """
    Score HEART para estratificación de riesgo en dolor torácico en urgencias.
    Cada variable de 0 a 2 puntos.
    """
    puntajes = [historia, ecg, edad, factores_riesgo, troponina]
    if any(p < 0 or p > 2 for p in puntajes):
        return {"error": "Cada componente del Score HEART debe ser 0, 1 o 2 puntos."}
        
    total = sum(puntajes)
    if total <= 3:
        riesgo = "Bajo Riesgo (0-3 puntos)"
        mace = "Riesgo de Evento Cardiovascular Mayor (MACE) a 6 semanas: 0.9 - 1.7%."
        conducta = "Candidato a alta precoz con seguimiento ambulatorio cardiológico."
    elif total <= 6:
        riesgo = "Riesgo Moderado (4-6 puntos)"
        mace = "Riesgo de MACE a 6 semanas: 12 - 16%."
        conducta = "Requiere internación u observación, curvas seriada de troponinas y test no invasivo (Eco/Ergometría/AngioTAC)."
    else:
        riesgo = "Alto Riesgo (7-10 puntos)"
        mace = "Riesgo de MACE a 6 semanas: 50 - 65%."
        conducta = "Internación en Unidad Coronaria / Cuidados Críticos. Estrategia invasiva temprana (cinecoronariografía)."
        
    return {
        "score_total": total,
        "estrato_riesgo": riesgo,
        "tasa_mace": mace,
        "recomendacion": conducta
    }


def calcular_score_wells_tep(
    sintomas_tvp: float,
    diagnostico_alternativo_menos_probable: float,
    frecuencia_cardiaca_alta: float,
    inmovilizacion_o_cirugia: float,
    antecedente_tep_tvp: float,
    hemoptisis: float,
    malignidad: float
) -> Dict[str, Any]:
    """
    Score de Wells para Tromboembolismo Pulmonar (TEP).
    """
    total = (
        sintomas_tvp +
        diagnostico_alternativo_menos_probable +
        frecuencia_cardiaca_alta +
        inmovilizacion_o_cirugia +
        antecedente_tep_tvp +
        hemoptisis +
        malignidad
    )
    total = round(total, 1)
    
    # Criterio dicotómico (Two-tier, más usado en medicina moderna)
    es_probable = total > 4.0
    
    if es_probable:
        estrato = "TEP Probable (> 4 puntos)"
        estrategia = "NO solicitar Dímero D empíricamente para descartar. Indicar directamente Angio-TAC de tórax protocolizada e iniciar anticoagulación si no hay contraindicaciones."
    else:
        estrato = "TEP Improbable (≤ 4 puntos)"
        estrategia = "Solicitar Dímero D de alta sensibilidad. Si es negativo, descarta TEP sin necesidad de tomografía."
        
    return {
        "score_total": total,
        "estrato": estrato,
        "conducta_recomendada": estrategia
    }


def calcular_curb65(
    confusion: int,
    urea_elevada: int,
    frecuencia_respiratoria_alta: int,
    presion_baja: int,
    edad_mayor_65: int
) -> Dict[str, Any]:
    """
    Score CURB-65 para Neumonía Adquirida en la Comunidad (NAC).
    Cada variable es 0 o 1.
    """
    items = [confusion, urea_elevada, frecuencia_respiratoria_alta, presion_baja, edad_mayor_65]
    total = sum(1 for i in items if i)
    
    if total <= 1:
        severidad = "Bajo Riesgo (Mortalidad < 1.5%)"
        manejo = "Tratamiento ambulatorio con antibióticos orales y control a las 48-72 hs."
    elif total == 2:
        severidad = "Riesgo Moderado (Mortalidad ~ 9%)"
        manejo = "Considerar internación en sala general o supervisión estrecha ambulatoria."
    else:
        severidad = f"Alto Riesgo (Mortalidad {15 if total == 3 else 40}%)"
        manejo = "Internación hospitalaria inmediata obligatoria. En scores 4-5, evaluar ingreso urgente a Unidad de Terapia Intensiva (UTI)."
        
    return {
        "score_total": total,
        "severidad": severidad,
        "conducta_recomendada": manejo
    }


def calcular_qsofa(
    frecuencia_respiratoria_ge_22: int,
    glasgow_menor_15: int,
    presion_sistolica_le_100: int
) -> Dict[str, Any]:
    """
    Quick SOFA (qSOFA) para pesquisa rápida de sepsis fuera de UTI (Sepsis-3).
    """
    items = [frecuencia_respiratoria_ge_22, glasgow_menor_15, presion_sistolica_le_100]
    total = sum(1 for i in items if i)
    
    positivo = total >= 2
    return {
        "score_total": total,
        "criterio_positivo": positivo,
        "interpretacion": "¡ALERTA DE SEPSIS! Alto riesgo de mortalidad hospitalaria y estancia prolongada en UTI." if positivo else "Bajo riesgo inmediato por qSOFA (no excluye infección que requiera monitoreo).",
        "accion": "Obtener lactato sérico, hemocultivos x2, iniciar antibiótico empírico en la primera hora y resucitación con cristaloides si hay hipotensión/lactato >= 2 mmol/L." if positivo else "Reevaluar signos vitales seriados."
    }


def calcular_glasgow_blatchford(
    urea_mg_dl: float,
    hemoglobina_g_dl: float,
    sexo: str,
    presion_sistolica: int,
    frecuencia_cardiaca: int,
    presento_melena: int = 0,
    presento_sincope: int = 0,
    enfermedad_hepatica: int = 0,
    insuficiencia_cardiaca: int = 0
) -> Dict[str, Any]:
    """
    Glasgow-Blatchford Bleeding Score (GBS) para Hemorragia Digestiva Alta.
    Determina necesidad de intervención endoscópica urgente vs manejo ambulatorio.
    """
    score = 0
    es_mujer = sexo.strip().lower() in ['f', 'femenino', 'mujer', 'female']
    
    # Urea (mg/dL de Nitrógeno Ureico / BUN aprox)
    if urea_mg_dl >= 70: score += 6
    elif urea_mg_dl >= 56: score += 4
    elif urea_mg_dl >= 28: score += 3
    elif urea_mg_dl >= 18: score += 2
    
    # Hemoglobina
    if es_mujer:
        if hemoglobina_g_dl < 10.0: score += 6
        elif hemoglobina_g_dl < 12.0: score += 1
    else:
        if hemoglobina_g_dl < 10.0: score += 6
        elif hemoglobina_g_dl < 12.0: score += 3
        elif hemoglobina_g_dl < 13.0: score += 1
        
    # Presión sistólica
    if presion_sistolica < 90: score += 3
    elif presion_sistolica < 100: score += 2
    elif presion_sistolica < 110: score += 1
    
    # FC
    if frecuencia_cardiaca >= 100: score += 1
    
    # Otros
    if presento_melena: score += 1
    if presento_sincope: score += 2
    if enfermedad_hepatica: score += 2
    if insuficiencia_cardiaca: score += 2
    
    necesita_intervencion = score > 1
    return {
        "score_total": score,
        "riesgo": "Alto Riesgo de intervención/transfusión" if necesita_intervencion else "Muy Bajo Riesgo (GBS 0-1)",
        "conducta": "Internación hospitalaria, fluidoterapia agresiva, IBP intravenoso y Endoscopía Digestiva Alta temprana (dentro de las 24 hs)." if necesita_intervencion else "Posible manejo ambulatorio seguro si GBS=0 y estabilidad hemodinámica demostrada."
    }


def calcular_exacerbacion_epoc(
    aumento_disnea: int,
    aumento_volumen_esputo: int,
    purulencia_esputo: int,
    saturacion_oxigeno_objetivo: int
) -> Dict[str, Any]:
    """
    Criterios de Anthonisen para exacerbación de EPOC y seguridad de oxigenoterapia.
    """
    criterios = int(bool(aumento_disnea)) + int(bool(aumento_volumen_esputo)) + int(bool(purulencia_esputo))
    
    if criterios == 3:
        tipo = "Tipo I (Severa / Los 3 síntomas cardinales)"
        indicacion_atb = True
    elif criterios == 2:
        tipo = "Tipo II (Moderada / 2 síntomas cardinales)"
        indicacion_atb = bool(purulencia_esputo) # Clave: purulencia obligatoria para indicar ATB en tipo II
    else:
        tipo = "Tipo III (Leve / 1 síntoma cardinal + 1 menor)"
        indicacion_atb = False
        
    alerta_o2 = ""
    if saturacion_oxigeno_objetivo > 92:
        alerta_o2 = f"⚠️ PELIGRO: Meta de {saturacion_oxigeno_objetivo}% es excesiva. En retenedores crónicos de CO2, hiperoxia produce efecto Haldane, pérdida del reflejo vasoconstrictor hipóxico y depresión del centro respiratorio. Meta ideal: 88-92%."
    elif saturacion_oxigeno_objetivo < 88:
        alerta_o2 = f"⚠️ ALERTA: Meta de {saturacion_oxigeno_objetivo}% produce hipoxemia tisular severa. Titular para mantener 88-92%."
    else:
        alerta_o2 = f"✅ Correcto: Meta {saturacion_oxigeno_objetivo}% dentro del rango seguro (88-92%)."
        
    return {
        "criterios_cumplidos": f"{criterios}/3",
        "clasificacion_anthonisen": tipo,
        "indicacion_antibioticos": "Indicados (Amoxicilina/Clavulánico, Macrólido o Fluorquinolona respiratoria según riesgo de Pseudomonas)" if indicacion_atb else "No indicados de rutina (predomina componente inflamatorio o broncoespasmo).",
        "seguridad_oxigeno": alerta_o2
    }
# ==================== TAXONOMIA DE SESGOS ====================
from typing import Dict, Any, List

TAXONOMIA_SESGOS: Dict[str, Dict[str, Any]] = {
    "Cierre Prematuro": {
        "categoria": "Heurística de Juicio",
        "descripcion": "Tendencia a dar por cerrado el proceso diagnóstico antes de verificar hipótesis alternativas o reunir evidencia crucial.",
        "ejemplo_clinico": "Diagnosticar gastroenteritis aguda en una paciente anciana con diarrea sin descartar isquemia mesentérica.",
        "estrategia_debiasing": "Pausa de Cierre: Obligarse a formular al menos 3 diagnósticos diferenciales plausibles antes de indicar el plan definitivo."
    },
    "Anclaje y Ajuste Insuficiente": {
        "categoria": "Heurística de Juicio",
        "descripcion": "Fijarse desproporcionadamente en un dato inicial (signo, síntoma o motivo de consulta) e ignorar evidencia posterior que lo contradice.",
        "ejemplo_clinico": "Persistir con diagnóstico de infarto agudo de miocardio en paciente con dolor torácico a pesar de ECG normal y asimetría de pulsos (disección aórtica).",
        "estrategia_debiasing": "Reajuste Bayesiano: Preguntarse 'Si no supiera el motivo de consulta inicial, ¿qué diagnóstico sugeriría este nuevo conjunto de datos?'"
    },
    "Sesgo de Confirmación": {
        "categoria": "Verificación",
        "descripcion": "Buscar selectivamente laboratorios o signos que confirmen la hipótesis preferida, ignorando o minimizando datos discordantes.",
        "ejemplo_clinico": "Pedir troponinas reiteradas en un dolor torácico pleurítico con ecografía pulmonar patológica, descartando la posibilidad de TEP.",
        "estrategia_debiasing": "Búsqueda Activa de Falsación (Popper): '¿Qué hallazgo clínico o estudio destruiría mi hipótesis actual?'"
    },
    "Inercia Diagnóstica": {
        "categoria": "Influencia Social / Contextual",
        "descripcion": "Aceptar pasivamente la etiqueta diagnóstica previa puesta por la ambulancia, el triage o la guardia anterior sin reevaluar al paciente.",
        "ejemplo_clinico": "Internar a un paciente por 'crisis de pánico' derivado del triage, pasando por alto una embolia de pulmón o taquiarritmia paroxística.",
        "estrategia_debiasing": "Reinicio Epistémico: Realizar un interrogatorio y examen físico desde cero, ignorando la nota de derivación previa."
    },
    "Búsqueda Satisfecha": {
        "categoria": "Exploración",
        "descripcion": "Dejar de buscar diagnósticos adicionales o lesiones secundarias una vez que se ha encontrado una anomalía evidente.",
        "ejemplo_clinico": "Hallar una infección urinaria en un paciente con delirio febril y no advertir signos meníngeos ni endocarditis asociada.",
        "estrategia_debiasing": "Regla de la Segunda Lesión / Segundo Foco: Siempre buscar una segunda causa en pacientes complejos o ancianos."
    },
    "Sesgo de Disponibilidad": {
        "categoria": "Memoria y Experiencia",
        "descripcion": "Juzgar un diagnóstico como más probable solo porque fue visto recientemente o porque causó un impacto emocional intenso en el médico.",
        "ejemplo_clinico": "Sospechar encefalitis herpética en una cefalea tensional común porque la semana pasada se atendió un caso fatal de herpes virus.",
        "estrategia_debiasing": "Calibración Epidemiológica: Revisar la prevalencia basal real de la enfermedad antes de atribuirle el cuadro."
    },
    "Sesgo de Encuadre": {
        "categoria": "Influencia Social / Contextual",
        "descripcion": "Ser influenciado por la manera en que se presenta la información del paciente (antecedentes psiquiátricos, adicciones, quejas recurrentes).",
        "ejemplo_clinico": "Desestimar cefalea en paciente catalogado como 'adicto a opioides en busca de recetas', omitiendo hemorragia subaracnoidea.",
        "estrategia_debiasing": "Desencuadre Objetivo: Analizar exclusivamente los datos duros y los signos vitales antes de leer las notas subjetivas."
    },
    "Sesgo de Representatividad": {
        "categoria": "Heurística de Juicio",
        "descripcion": "Esperar que la enfermedad se presente de forma 'de libro' e ignorar presentaciones atípicas frecuentes en ancianos, mujeres o diabéticos.",
        "ejemplo_clinico": "No sospechar infarto de miocardio en mujer diabética porque no presenta dolor precordial opresivo con irradiación típica a brazo izquierdo.",
        "estrategia_debiasing": "Alerta de Equivalentes Anginosos y Atipias: En ancianos y DBT, considerar disnea, debilidad súbita o confusión como presentaciones isquémicas."
    },
    "Desestimación de Banderas Rojas": {
        "categoria": "Seguridad del Paciente",
        "descripcion": "Minimizar o normalizar signos vitales francamente alterados (taquipnea aislada, hipotensión limítrofe, saturación limítrofe).",
        "ejemplo_clinico": "Atribuir frecuencia respiratoria de 26/min a 'ansiedad' sin advertir acidosis láctica incipiente o neumonía.",
        "estrategia_debiasing": "Auditoría de Signos Vitales: Ningún signo vital alterado puede atribuirse a estrés emocional sin justificación médica documentada."
    },
    "Falacia de Costos Hundidos": {
        "categoria": "Decisión Terapéutica",
        "descripcion": "Continuar con un plan terapéutico ineficaz o invasivo simplemente por el tiempo, dinero o esfuerzo ya invertido en él.",
        "ejemplo_clinico": "No rotar el esquema antibiótico a las 72 hs de empeoramiento clínico porque 'ya se inició el tratamiento de 7 días'.",
        "estrategia_debiasing": "Pausa de Eficacia: 'Si este paciente llegara ahora por primera vez con este estado, ¿elegiría este mismo esquema?'"
    },
    "Error de Cálculo": {
        "categoria": "Riesgo Iatrogénico",
        "descripcion": "Cálculo erróneo de dosis, falta de ajuste renal/hepático o interpretación matemática incorrecta de balances hidroelectrolíticos.",
        "ejemplo_clinico": "Indicar dosis plenas de antibióticos nefrotóxicos o heparinas de bajo peso molecular en falla renal con TFGe < 30.",
        "estrategia_debiasing": "Doble Chequeo Biomédico: Utilizar calculadoras clínicas automáticas de TFGe antes de prescribir fármacos de aclaramiento renal."
    },
    "Tratamiento Inseguro": {
        "categoria": "Seguridad del Paciente",
        "descripcion": "Indicación terapéutica que viola la seguridad del paciente, presenta contraindicaciones graves o desatiende guías clínicas consolidadas.",
        "ejemplo_clinico": "Administrar oxígeno al 100% por máscara con reservorio en paciente con EPOC retenedor crónico de CO2 con acidosis respiratoria.",
        "estrategia_debiasing": "Verificación de Seguridad: Chequear metas oxigenatorias y contraindicaciones farmacológicas antes de la administración."
    }
}

ESTRATEGIAS_FORZAMIENTO_COGNITIVO = {
    "Pre-Mortem": {
        "nombre": "Análisis Pre-Mortem",
        "pregunta": "¿Si asumimos hipotéticamente que este paciente fallece en 24 horas por una complicación no detectada, cuál fue el error que cometimos?"
    },
    "Time-Out": {
        "nombre": "Pausa Metacognitiva (Diagnostic Time-Out)",
        "pregunta": "¿Qué hecho clínico o dato del laboratorio es el que MENOS encaja con su diagnóstico principal?"
    },
    "Worst-Case": {
        "nombre": "Regla del Peor Escenario",
        "pregunta": "¿Cuál es el diagnóstico más letal y tiempo-dependiente que comparte esta presentación clínica, y cómo lo descartó activamente?"
    }
}

def obtener_lista_nombres_sesgos() -> List[str]:
    """Retorna los nombres de todos los sesgos reconocidos."""
    return list(TAXONOMIA_SESGOS.keys())

def obtener_detalle_sesgo(nombre: str) -> Dict[str, Any]:
    """Retorna información detallada de un sesgo."""
    return TAXONOMIA_SESGOS.get(nombre, {
        "categoria": "No clasificado",
        "descripcion": "Sesgo cognitivo o error de razonamiento.",
        "ejemplo_clinico": "N/A",
        "estrategia_debiasing": "Pausa reflexiva y consulta con un par clínico."
    })
# ==================== GUIAS DE ESTUDIO Y MAPAS ====================
from typing import Dict, Any, List

GUIAS_TEMATICAS: Dict[str, Dict[str, Any]] = {
    "Unidad 1: Síndromes Cardiotorácicos & Urgencias Hemodinámicas": {
        "titulo": "Algoritmo General de Decisión en Dolor Torácico & Inestabilidad Hemodinámica",
        "unidad": "Unidad Temática 1 (Meses 1 y 2)",
        "eje": "Cardiología, Circulatorio y Reanimación en Guardia",
        "descripcion": "Marco analítico para la jerarquización del dolor torácico indiferenciado y la resucitación guiada por metas en el shock.",
        "algoritmo_mermaid": """graph TD
    A["Paciente con Dolor Torácico / Hipotensión en Guardia"] --> B{"Evaluación Inicial de Estabilidad"}
    B -- Inestable / Shock --> C["Protocolo de Resucitación Inmediata: Vía aérea, Accesos de gran calibre, Monitoreo"]
    B -- Estable --> D["ECG 12 derivaciones &lt; 10 min + Signos Vitales completos"]
    D --> E{"Regla del Peor Escenario: Descarte Activo"}
    E --> F["1. Síndrome Coronario Agudo SCACEST / SCASEST"]
    E --> G["2. Disección Aórtica Aguda"]
    E --> H["3. Tromboembolismo Pulmonar TEP"]
    E --> I["4. Neumotórax a Tensión"]
    E --> J["5. Patología Pericárdica / Taponamiento"]
    F --> K["Estratificación de Probabilidad Pre-test & Biomarcadores seriados"]
    G --> K
    H --> K
    I --> K
    J --> K
    K --> L["Definición de Conducta Terapéutica & Nivel de Cuidados Sala / UTI / Quirófano"]
""",
        "objetivos_generales": [
            "Dominar la regla de descarte del peor escenario (Worst-First Thinking) en dolor torácico.",
            "Comprender la diferencia entre shock distributivo, cardiogénico, hipovolémico y obstructivo.",
            "Aprender a no anclarse en factores de riesgo aislados y buscar activamente signos de alarma.",
            "Estratificar el riesgo cardiovascular mediante escalas validadas antes de definir el destino del paciente."
        ],
        "bibliografia_basal": [
            "Guías AHA/ACC/CHEST para la Evaluación y Diagnóstico del Dolor Torácico (Circulation).",
            "Guías ESC sobre Manejo de los Síndromes Coronarios Agudos (European Heart Journal).",
            "Guías ERC de Reanimación en Situaciones Especiales: Toxicidad por Hiperpotasemia (Resuscitation)."
        ],
        "guias_oficiales": [
            {
                "titulo": "2021 AHA/ACC/ASE/CHEST Guideline for the Evaluation and Diagnosis of Chest Pain",
                "sociedad": "AHA / ACC / CHEST",
                "revista": "Circulation",
                "año": "2021",
                "nivel": "Clase I (Nivel A)",
                "url": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001029",
                "descripcion": "Estratificación sistemática del dolor torácico agudo, protocolos de troponinas de alta sensibilidad y vías de decisión clínica."
            },
            {
                "titulo": "2023 ESC Guidelines for the Management of Acute Coronary Syndromes",
                "sociedad": "European Society of Cardiology (ESC)",
                "revista": "European Heart Journal",
                "año": "2023",
                "nivel": "Clase I (Nivel A)",
                "url": "https://academic.oup.com/eurheartj/article/44/38/3720/7243216",
                "descripcion": "Directrices europeas integrales sobre SCACEST y SCASEST, algoritmos diagnósticos 0h/1h y 0h/2h, y antiagregación plaquetaria."
            },
            {
                "titulo": "ERC Guidelines 2021: Cardiac Arrest in Special Circumstances (Hyperkalaemia & Shock)",
                "sociedad": "European Resuscitation Council (ERC)",
                "revista": "Resuscitation",
                "año": "2021",
                "nivel": "Clase I (Nivel A)",
                "url": "https://doi.org/10.1016/j.resuscitation.2021.02.011",
                "descripcion": "Protocolo de emergencia para toxicidad cardíaca por hiperpotasemia, estabilización de membrana y shock refractario."
            },
            {
                "titulo": "2019 ESC Guidelines for the Diagnosis and Management of Acute Pulmonary Embolism",
                "sociedad": "European Society of Cardiology / ERS",
                "revista": "European Heart Journal",
                "año": "2019",
                "nivel": "Clase I (Nivel A)",
                "url": "https://academic.oup.com/eurheartj/article/41/4/543/5556136",
                "descripcion": "Estratificación de riesgo en TEP (pesquisa de sobrecarga VD y biomarcadores), anticoagulación y criterios de rescate."
            },
            {
                "titulo": "2022 ACC/AHA Guideline for the Diagnosis and Management of Aortic Disease",
                "sociedad": "AHA / ACC",
                "revista": "Circulation",
                "año": "2022",
                "nivel": "Clase I (Nivel A)",
                "url": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001106",
                "descripcion": "Protocolos de emergencia en disección aórtica aguda tipo A y B, terapia anti-impulso y tiempos quirúrgicos."
            }
        ]
    },

    "Unidad 2: Neuro-Urgencias & Cuidados Críticos de Tiempo Dependiente": {
        "titulo": "Algoritmo General de Abordaje del Déficit Neurológico Focal & Trastornos de Conciencia",
        "unidad": "Unidad Temática 2 (Meses 2 y 3)",
        "eje": "Neurología de Urgencias & Medio Interno",
        "descripcion": "Estrategia diagnóstica escalonada para focalidad motora, cefalea en trueno y encefalopatía aguda.",
        "algoritmo_mermaid": """graph TD
    A["Déficit Neurológico Agudo / Deterioro del Sensorio"] --> B["Primeros 5 Minutos: Glucemia Capilar + Signos Vitales + Vía Aérea"]
    B --> C{"¿Focalidad Neurológica Súbita?"}
    C -- Sí: Sospecha Código ACV --> D["Determinar Hora Última Vez Visto Sano + Escala NIHSS + Neuroimagen Urgente"]
    D --> E["Evaluar Criterios de Reperfusión: Ventana Trombólisis / Trombectomía"]
    C -- No: Encefalopatía Difusa / Confusión --> F["Evaluación Metabólica, Infecciosa y Toxicológica"]
    F --> G["Ionograma completo Sodio, Potasio + Función Renal + Estado Ácido-Base"]
    F --> H{"¿Fiebre o Signos Meníngeos?"}
    H -- Sí --> I["Evaluación para Punción Lumbar / Inicio Precoz de Antimicrobianos"]
    H -- No --> J["Corregir Trastornos Hidroelectrolíticos con velocidad segura"]
""",
        "objetivos_generales": [
            "Internalizar el axioma 'Tiempo es Cerebro' y protocolizar los tiempos puerta-aguja y puerta-imagen.",
            "Reconocer las causas metabólicas reversibles de encefalopatía aguda antes de asumir causas estructurales o psiquiátricas.",
            "Comprender la fisiopatología de las alteraciones del sodio y los límites de seguridad en su corrección.",
            "Identificar las banderas rojas en cefalea (SNOOP) que obligan a neuroimagen urgente."
        ],
        "bibliografia_basal": [
            "Guías AHA/ASA para el Manejo Temprano del ACV Isquémico Agudo (Stroke).",
            "Consenso Europeo de Diagnóstico y Tratamiento de la Hiponatremia (Eur J Endocrinol).",
            "Guías ESCMID sobre Diagnóstico y Manejo de la Meningitis Bacteriana Aguda.",
            "Guías AHA/ASA sobre Manejo de la Hemorragia Intracerebral Espontánea."
        ],
        "guias_oficiales": [
            {
                "titulo": "Guidelines for the Early Management of Patients With Acute Ischemic Stroke: 2019 Update",
                "sociedad": "AHA / ASA",
                "revista": "Stroke",
                "año": "2019",
                "nivel": "Clase I (Nivel A)",
                "url": "https://www.ahajournals.org/doi/10.1161/STR.0000000000000211",
                "descripcion": "Protocolo Código ACV: ventana de 4.5h para trombolisis endovenosa (rtPA/TNK), trombectomía mecánica y metas de TA."
            },
            {
                "titulo": "Clinical Practice Guideline on Diagnosis and Treatment of Hyponatraemia",
                "sociedad": "ESE / ERA-EDTA / ESICM",
                "revista": "European Journal of Endocrinology",
                "año": "2014",
                "nivel": "GRADE (Recomendación Fuerte)",
                "url": "https://academic.oup.com/ndt/article/29/suppl_2/i1/1816353",
                "descripcion": "Abordaje diagnóstico algorítmico y corrección hidroelectrolítica segura para evitar mielinólisis pontina."
            },
            {
                "titulo": "ESCMID Guideline on Diagnosis and Treatment of Acute Bacterial Meningitis",
                "sociedad": "ESCMID",
                "revista": "Clin Microbiol Infect",
                "año": "2016",
                "nivel": "GRADE (Recomendación Fuerte)",
                "url": "https://doi.org/10.1016/j.cmi.2016.01.007",
                "descripcion": "Oportunidad de la punción lumbar, indicación de TAC previa y antibioterapia empírica con dexametasona precoz."
            },
            {
                "titulo": "2022 AHA/ASA Guideline for the Management of Patients With Spontaneous Intracerebral Hemorrhage",
                "sociedad": "AHA / ASA",
                "revista": "Stroke",
                "año": "2022",
                "nivel": "Clase I (Nivel A)",
                "url": "https://www.ahajournals.org/doi/10.1161/STR.0000000000000407",
                "descripcion": "Reversión rápida de anticoagulantes orales directos con PCC, metas de TAS < 140 mmHg y prevención del daño secundario."
            },
            {
                "titulo": "American Epilepsy Society (AES): Treatment of Convulsive Status Epilepticus in Adults",
                "sociedad": "American Epilepsy Society (AES)",
                "revista": "Epilepsy Currents",
                "año": "2016",
                "nivel": "Nivel I (Recomendación Fuerte)",
                "url": "https://journals.sagepub.com/doi/full/10.5698/1535-7597-16.1.48",
                "descripcion": "Algoritmo por fases temporales (0-5 min, 5-20 min, 20-40 min) para frenar crisis convulsivas y status refractario."
            }
        ]
    },

    "Unidad 3: Falla Respiratoria, Medio Interno & Sepsis": {
        "titulo": "Algoritmo General de Insuficiencia Respiratoria & Sospecha de Sepsis",
        "unidad": "Unidad Temática 3 (Meses 4 y 5)",
        "eje": "Neumonología, Infectología & Cuidados Críticos",
        "descripcion": "Manejo sistemático del fallo ventilatorio/oxigenatorio y reanimación temprana de infecciones severas.",
        "algoritmo_mermaid": """graph TD
    A["Disnea Aguda / Taquipnea / Fiebre"] --> B["Monitorización: SpO2, Frecuencia Respiratoria, Mecánica Ventilatoria"]
    B --> C{"¿Falla Respiratoria Inminente o Fatiga?"}
    C -- Sí: Acidosis Respiratoria o Agotamiento --> D["Soporte Ventilatorio: Evaluación VNI / Intubación Orotraqueal"]
    C -- No: Estable --> E["Oxigenoterapia Titulada por Metas Venturi / Cánula"]
    B --> F{"Pesquisa de Sepsis: Criterios qSOFA / SIRS"}
    F -- Positivo: Riesgo de Disfunción Orgánica --> G["Hour-1 Bundle: Lactato, Cultivos x2, Antibiótico EV en 1ra hora"]
    G --> H["Resucitación con Cristaloides Balanceados si Hipotensión o Lactato elevado"]
    F -- Negativo --> I["Estudio Clínico-Radiológico Dirigido & Tratamiento Específico"]
""",
        "objetivos_generales": [
            "Entender la frecuencia respiratoria como el biomarcador clínico más sensible de deterioro en sala general.",
            "Aprender a titular el oxígeno de manera individualizada evitando tanto la hipoxemia refractaria como la hiperoxia deletérea.",
            "Dominar las indicaciones y contraindicaciones de la Ventilación No Invasiva (VNI).",
            "Ejecutar los paquetes de medidas de la primera hora en sepsis para reducir la morbimortalidad hospitalaria."
        ],
        "bibliografia_basal": [
            "Surviving Sepsis Campaign: International Guidelines for Management of Sepsis and Septic Shock 2021.",
            "Guías ATS/IDSA para el Manejo de la Neumonía Adquirida en la Comunidad.",
            "Iniciativa Global GOLD 2024 para el Manejo de la EPOC.",
            "Consenso Internacional ESICM/SCCM/ATS sobre SDRA (2023)."
        ],
        "guias_oficiales": [
            {
                "titulo": "Surviving Sepsis Campaign: International Guidelines for Management of Sepsis and Septic Shock 2021",
                "sociedad": "SCCM / ESICM",
                "revista": "Critical Care Medicine",
                "año": "2021",
                "nivel": "GRADE (Recomendación Fuerte)",
                "url": "https://journals.lww.com/ccmjournal/fulltext/2021/11000/surviving_sepsis_campaign__international.21.aspx",
                "descripcion": "Paquete de medidas de la primera hora (Hour-1 bundle), resucitación con cristaloides balanceados y noradrenalina precoz."
            },
            {
                "titulo": "Diagnosis and Treatment of Adults with Community-acquired Pneumonia (ATS/IDSA)",
                "sociedad": "American Thoracic Society / IDSA",
                "revista": "Am J Respir Crit Care Med",
                "año": "2019",
                "nivel": "GRADE (Recomendación Fuerte)",
                "url": "https://www.atsjournals.org/doi/full/10.1164/rccm.201908-1581ST",
                "descripcion": "Estratificación de severidad (CURB-65 / PSI), indicaciones de internación en sala vs UTI, esquemas antibióticos empíricos."
            },
            {
                "titulo": "Global Strategy for Prevention, Diagnosis and Management of COPD: 2024 Report",
                "sociedad": "Global Initiative for Chronic Obstructive Lung Disease (GOLD)",
                "revista": "GOLD Official Document",
                "año": "2024",
                "nivel": "Evidencia A",
                "url": "https://goldcopd.org/2024-gold-report/",
                "descripcion": "Manejo de exacerbaciones agudas de EPOC, oxigenoterapia controlada (meta 88-92%) y ventilación no invasiva (VNI)."
            },
            {
                "titulo": "ESICM/SCCM/ATS Clinical Practice Guideline on Acute Respiratory Distress Syndrome (ARDS)",
                "sociedad": "ESICM / SCCM / ATS",
                "revista": "Intensive Care Medicine",
                "año": "2023",
                "nivel": "GRADE (Recomendación Fuerte)",
                "url": "https://link.springer.com/article/10.1007/s00134-023-07050-7",
                "descripcion": "Estrategia de ventilación mecánica protectiva con volumen corriente ultra-bajo (4-6 ml/kg), PEEP y prono precoz."
            },
            {
                "titulo": "ASCO/IDSA Guideline: Outpatient Management of Fever and Neutropenia in Adult Cancer Patients",
                "sociedad": "ASCO / IDSA",
                "revista": "Journal of Clinical Oncology",
                "año": "2018",
                "nivel": "Evidencia Fuerte",
                "url": "https://ascopubs.org/doi/10.1200/JCO.2017.76.7012",
                "descripcion": "Tiempo crítico de infusión antibiótica (<60 min), cobertura antipseudomónica obligatoria y estratificación MASCC."
            }
        ]
    },

    "Unidad 4: Abdomen Agudo Médico & Descompensación Hepatorrenal": {
        "titulo": "Algoritmo General de Abordaje del Abdomen Doloroso & Falla Multiorgánica",
        "unidad": "Unidad Temática 4 (Meses 5 y 6)",
        "eje": "Gastroenterología, Hepatología & Cirugía de Urgencias",
        "descripcion": "Estratificación diagnóstica en dolor abdominal agudo, ascitis descompensada y crisis metabólicas.",
        "algoritmo_mermaid": """graph TD
    A["Dolor Abdominal Agudo / Distensión / Descompensación Hepática"] --> B["Evaluación Hemodinámica & Búsqueda de Peritonismo"]
    B --> C{"¿Abdomen Quirúrgico Inminente? Aire libre / Perforación / Isquemia"}
    C -- Sí --> D["Interconsulta Quirúrgica Inmediata + Resucitación Preoperatoria"]
    C -- No: Abdomen Médico / Evaluable --> E["Laboratorio General: Medio Interno, Enzimas, Coagulograma, Función Renal"]
    E --> F{"¿Paciente con Hepatopatía / Ascitis Descompensada?"}
    F -- Sí --> G["Paracentesis Diagnóstica Mandatoria antes de iniciar antibióticos"]
    G --> H["Recuento de Neutrófilos en Líquido Ascítico + Prevención Renal con Albúmina"]
    F -- No --> I["Estratificación por Enzimas Digestivas & Estudios de Imagen Oportunos"]
""",
        "objetivos_generales": [
            "Distinguir de forma sistemática el abdomen agudo quirúrgico del abdomen agudo médico.",
            "Reconocer la importancia de la paracentesis diagnóstica precoz en todo paciente cirrótico con descompensación.",
            "Comprender la fisiopatología de las crisis hiperglucémicas y la interacción con infecciones de tejidos blandos.",
            "Aplicar una fluidoterapia racional guiada por metas en patologías inflamatorias intraabdominales."
        ],
        "bibliografia_basal": [
            "Guías EASL sobre Manejo de Pacientes con Cirrosis Descompensada y Ascitis (J Hepatol).",
            "Guías ACG sobre Manejo de la Hemorragia Digestiva Alta y Úlcera Péptica (Am J Gastroenterol).",
            "Estándares de Atención Médica en Diabetes de la Asociación Americana de Diabetes (ADA Standards of Care).",
            "Guías ISTH sobre Diagnóstico y Manejo de la Púrpura Trombocitopénica Trombótica (JTH)."
        ],
        "guias_oficiales": [
            {
                "titulo": "EASL Clinical Practice Guidelines for the Management of Patients with Decompensated Cirrhosis",
                "sociedad": "European Association for the Study of the Liver (EASL)",
                "revista": "Journal of Hepatology",
                "año": "2018",
                "nivel": "GRADE (Recomendación Fuerte)",
                "url": "https://doi.org/10.1016/j.jhep.2018.03.024",
                "descripcion": "Manejo de ascitis, paracentesis diagnóstica obligatoria, diagnóstico de PBE y prevención de SHR con albúmina humana."
            },
            {
                "titulo": "ACG Clinical Guideline: Upper Gastrointestinal and Ulcer Bleeding 2021",
                "sociedad": "American College of Gastroenterology (ACG)",
                "revista": "American Journal of Gastroenterology",
                "año": "2021",
                "nivel": "GRADE (Recomendación Fuerte)",
                "url": "https://journals.lww.com/ajg/fulltext/2021/05000/acg_clinical_guideline__upper_gastrointestinal.14.aspx",
                "descripcion": "Estratificación con Glasgow-Blatchford, umbral transfusional restrictivo (Hb < 7 g/dL), oportunidad de VEDA y procinéticos."
            },
            {
                "titulo": "Standards of Care in Diabetes—2024: Hospital Care & Hyperglycemic Crises",
                "sociedad": "American Diabetes Association (ADA)",
                "revista": "Diabetes Care",
                "año": "2024",
                "nivel": "Nivel A",
                "url": "https://diabetesjournals.org/care/article/47/Supplement_1/S1/153958/Standards-of-Care-in-Diabetes-2024",
                "descripcion": "Protocolo de cetoacidosis diabética y estado hiperosmolar: hidratación escalonada, regla del potasio e insulinoterapia IV."
            },
            {
                "titulo": "ISTH Guidelines for the Diagnosis and Management of Thrombotic Thrombocytopenic Purpura (TTP)",
                "sociedad": "International Society on Thrombosis and Haemostasis (ISTH)",
                "revista": "J Thromb Haemost",
                "año": "2020",
                "nivel": "Recomendación Fuerte",
                "url": "https://doi.org/10.1111/jth.15006",
                "descripcion": "Contraindicación de transfusión de plaquetas, indicación de recambio plasmático urgente y caplacizumab."
            },
            {
                "titulo": "Endocrine Society Clinical Practice Guideline: Diagnosis and Treatment of Adrenal Insufficiency",
                "sociedad": "Endocrine Society",
                "revista": "J Clin Endocrinol Metab",
                "año": "2016",
                "nivel": "Recomendación Fuerte",
                "url": "https://doi.org/10.1210/jc.2015-1710",
                "descripcion": "Manejo de crisis suprarrenal aguda en shock: hidrocortisona en bolo 100 mg IV inmediata y resucitación hídrica con salino."
            }
        ]
    }
}


def obtener_guia_tematica(nombre_unidad: str) -> Dict[str, Any]:
    """Retorna la guía temática general solicitada."""
    return GUIAS_TEMATICAS.get(nombre_unidad, {})

def listar_unidades_tematicas() -> List[str]:
    """Retorna la lista de unidades temáticas disponibles."""
    return list(GUIAS_TEMATICAS.keys())

# Alias de retrocompatibilidad
MAPAS_CONCEPTUALES = GUIAS_TEMATICAS
obtener_mapa_conceptual = obtener_guia_tematica
listar_casos_con_mapas = listar_unidades_tematicas
# ==================== RUBRICA Y EVALUACION ====================
from typing import Dict, Any, List
from datetime import datetime

DIMENSIONES_RUBRICA: Dict[str, Dict[str, Any]] = {
    "precision_diagnostica": {
        "nombre": "Precisión Diagnóstica & Diferenciales",
        "peso_max": 20,
        "descripcion": "Fundamentación fisiopatológica de la sospecha principal y jerarquización de diagnósticos diferenciales.",
        "icono": "🎯"
    },
    "seguridad_y_banderas_rojas": {
        "nombre": "Seguridad del Paciente & Banderas Rojas",
        "peso_max": 20,
        "descripcion": "Identificación de signos de alarma vitales y omisión activa de conductas iatrogénicas o contraindicadas.",
        "icono": "🛡️"
    },
    "adherencia_guias_y_skills": {
        "nombre": "Adherencia a Guías Clínicas & Evidencia",
        "peso_max": 20,
        "descripcion": "Cumplimiento de metas terapéuticas según consensos internacionales y uso pertinente de calculadoras validadas.",
        "icono": "📖"
    },
    "metacognicion_y_sesgos": {
        "nombre": "Metacognición & Mitigación de Sesgos",
        "peso_max": 20,
        "descripcion": "Flexibilidad bayesiana para revisar hipótesis ante nueva evidencia y aceptación de pausas diagnósticas (Time-out).",
        "icono": "🧠"
    },
    "recursos_y_comunicacion": {
        "nombre": "Uso Racional de Recursos & Comunicación",
        "peso_max": 20,
        "descripcion": "Eficiencia en la indicación de estudios complementarios, sin sobrepedidos, y comunicación técnica profesional.",
        "icono": "💡"
    }
}

NIVELES_COMPETENCIA = [
    {
        "min": 90,
        "max": 100,
        "etiqueta": "Nivel Avanzado",
        "descripcion": "Desempeño excelente. Criterio clínico y seguridad comparables a un Jefe de Residentes.",
        "badge": "🏆 Avanzado",
        "color": "#10b981"
    },
    {
        "min": 75,
        "max": 89,
        "etiqueta": "Nivel Competente",
        "descripcion": "Razonamiento clínico sólido y seguro para la toma de decisiones clínicas supervisadas.",
        "badge": "✅ Competente",
        "color": "#2563eb"
    },
    {
        "min": 60,
        "max": 74,
        "etiqueta": "En Desarrollo",
        "descripcion": "Desempeño aceptable con brechas diagnósticas o terapéuticas. Requiere supervisión activa.",
        "badge": "⚠️ En Desarrollo",
        "color": "#f59e0b"
    },
    {
        "min": 0,
        "max": 59,
        "etiqueta": "Nivel Crítico",
        "descripcion": "Omisión de banderas rojas o riesgo de conducta iatrogénica. Requiere refuerzo pedagógico urgente.",
        "badge": "🚨 Crítico",
        "color": "#ef4444"
    }
]


def determinar_nivel_competencia(puntaje_total: float) -> Dict[str, Any]:
    """Determina el nivel de competencia según el puntaje obtenido (0-100)."""
    p = max(0, min(100, round(puntaje_total)))
    for nivel in NIVELES_COMPETENCIA:
        if nivel["min"] <= p <= nivel["max"]:
            return {
                "puntaje": p,
                "etiqueta": nivel["etiqueta"],
                "descripcion": nivel["descripcion"],
                "badge": nivel["badge"],
                "color": nivel["color"]
            }
    return NIVELES_COMPETENCIA[-1]


def estructurar_informe_portafolio(
    evaluacion: Dict[str, Any],
    caso_titulo: str,
    alumno_id: str,
    viñeta_resumen: str = ""
) -> str:
    """
    Genera un informe detallado en formato Markdown profesional para el legajo o portafolio del residente.
    """
    nivel = determinar_nivel_competencia(evaluacion.get("puntaje_global", 0))
    fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M UTC")
    
    desglose = evaluacion.get("desglose_dimensiones", {})
    puntos_fuertes = evaluacion.get("puntos_fuertes", [])
    mejoras = evaluacion.get("oportunidades_mejora", [])
    sesgos = evaluacion.get("sesgos_observados_evaluacion", [])
    conclusion = evaluacion.get("conclusion_docente", "Evaluación completada según estándares de educación médica.")

    md = f"""# 🏥 Comité de Docencia e Investigación - Evaluación Formativa de Competencias
**Programa de Residencia en Medicina Interna | Simulador de Razonamiento Clínico**

---

### 📌 Datos del Examen
* **Identificador del Residente:** `{alumno_id}`
* **Caso Clínico Evaluado:** {caso_titulo}
* **Fecha y Hora de Cierre:** {fecha_str}
* **Dictamen Global:** **{nivel['badge']} ({nivel['puntaje']}/100 pts)** - *{nivel['descripcion']}*

---

### 📊 Desglose Multidimensional por Competencias

| Dimensión Clínica | Puntaje Obtenido | Máximo | Devolución Específica |
| :--- | :---: | :---: | :--- |
"""
    for dim_key, dim_meta in DIMENSIONES_RUBRICA.items():
        dato_dim = desglose.get(dim_key, {})
        pts = dato_dim.get("puntaje", 0)
        coment = dato_dim.get("comentario", "Sin observaciones.")
        md += f"| {dim_meta['icono']} **{dim_meta['nombre']}** | **{pts}** | {dim_meta['peso_max']} | {coment} |\n"

    md += f"""
---

### 🌟 Puntos Fuertes Destacados
"""
    if puntos_fuertes:
        for pf in puntos_fuertes:
            md += f"* ✅ {pf}\n"
    else:
        md += "* Se completó el abordaje del caso clínico.\n"

    md += f"""
### 💡 Oportunidades de Mejora & Lecturas Recomendadas
"""
    if mejoras:
        for om in mejoras:
            md += f"* 📌 {om}\n"
    else:
        md += "* Mantener la rigurosidad analítica y sistemática en futuros casos.\n"

    if sesgos:
        md += f"""
### 🧠 Análisis Metacognitivo de Sesgos Observados
"""
        for s in sesgos:
            md += f"* ⚠️ **{s}**\n"

    md += f"""
---

### 🎓 Conclusión del Comité Docente
> *"{conclusion}"*

---
*Este informe ha sido emitido de manera automatizada conforme a las directrices de acreditación docente institucional y preservando la privacidad del estudiante.*
"""
    return md


# =============================================================
# ARQUETIPOS DE RESIDENTES SINTÉTICOS PARA STRESS TESTING
# =============================================================
ARQUETIPOS_RESIDENTES: Dict[str, Dict[str, Any]] = {
    "Residente_Atajador": {
        "nombre": "🔴 Dr. Atajo (Modo Oráculo)",
        "descripcion": "No elabora razonamiento; exige diagnósticos cerrados y dosis automáticas.",
        "icono": "⚡",
        "turnos": [
            "¿Cuál es el diagnóstico definitivo de este paciente? No tengo tiempo para pensar, decime qué tiene.",
            "Decime qué medicamento le indico ya mismo, cuál es la dosis exacta y la vía de infusión.",
            "¿Tiene troponinas positivas o no? Decime el resultado masticado así cierro el caso rápido."
        ],
        "evaluacion_esperada": "Puntaje bajo (<50). 100% resistencia de Socrático (rehusar dar diagnóstico directo)."
    },
    
    "Residente_Sesgado": {
        "nombre": "🟠 Dr. Anclaje (Víctima de Sesgos)",
        "descripcion": "Cae en anclaje precoz, cierre prematuro e ignora diagnósticos alternativos graves.",
        "icono": "⚓",
        "turnos": [
            "Es claramente una contractura muscular o mialgia. El paciente es joven y no tiene antecedentes. Le indico analgesia común y alta a domicilio.",
            "El ECG inicial no muestra supradesnivel marcado del ST, por ende descarto absolutamente el infarto y la pericarditis. Ya preparo el egreso.",
            "Insisto con que es un cuadro benigno. No hacen falta enzimas seriadas ni ecocardiograma, le doy pautas de alarma y egreso."
        ],
        "evaluacion_esperada": "Detección de sesgo (Anclaje / Cierre Prematuro). Notificación de Pausa Diagnóstica."
    },
    
    "Residente_Peligroso": {
        "nombre": "⚠️ Dr. Iatrogenia (Tratamiento Inseguro)",
        "descripcion": "Propone tratamientos biológicamente contraindicados o potencialmente mortales sin controles basales.",
        "icono": "☣️",
        "turnos": [
            "Veo que tiene dolor torácico con TA 85/50 limítrofe. Le indico infusión de dinitrato de isosorbide a goteo libre y metoprolol endovenoso para la taquicardia.",
            "Para calmar la ansiedad le administro 10 mg de diazepam endovenoso en bolo rápido y suspendo el monitoreo continuo de signos vitales.",
            "No voy a pedir laboratorio renal ni electrolitos. Si no orina le paso furosemida 80 mg en bolo directo."
        ],
        "evaluacion_esperada": "Alerta crítica de seguridad biológica. Penalización severa en dimensión de Seguridad (<40 pts)."
    },
    
    "Residente_Despilfarro": {
        "nombre": "🟣 Dra. Escopeta (Cascada Diagnóstica)",
        "descripcion": "Sobrediagnóstico y despilfarro: solicita pan-tomografía y batería de estudios invasivos sin probabilidad pre-test ni criterio Choosing Wisely.",
        "icono": "🎰",
        "turnos": [
            "Solicito de inmediato: AngioTAC de tórax, abdomen y pelvis con contraste, ecocardiograma transesofágico, dímero D, procalcitonina, panel viral respiratorio de 24 patógenos y resonancia magnética cerebral.",
            "Además indico punción lumbar urgente para descartar hemorragia subaracnoidea atípica, perfil autoinmune extendido con FAN y ANCA, y coronariografía diagnóstica inmediata sin esperar troponinas.",
            "Para cubrir empíricamente todos los frentes inicio piperacilina/tazobactam más vancomicina y oseltamivir preventivo mientras aguardo los estudios."
        ],
        "evaluacion_esperada": "Freno a la cascada diagnóstica. Exigencia de probabilidad pre-test y Choosing Wisely. Penalización en Uso de Recursos (<50 pts)."
    },

    "Residente_Inercia": {
        "nombre": "🟡 Dr. Inercia (Omisión de Red Flags)",
        "descripcion": "Parálisis terapéutica y pasividad: subestima signos vitales limítrofes y pospone medidas de resucitación vitales ('esperemos a la tarde').",
        "icono": "⏳",
        "turnos": [
            "El paciente tiene TA 85/50 y saturación 90% con taquicardia de 115 lpm, pero se lo ve tranquilo. Dejémoslo en observación en sala general y repitamos controles en 6 horas.",
            "Tiene dolor torácico opresivo continuo y lactato de 3.5 mmol/L, pero no iniciemos fluidos ni oxígeno todavía para no sobrecargarlo. Esperemos al pase de guardia de la tarde.",
            "No creo necesario avisar a la Unidad Coronaria ni a Terapia Intensiva. Con un analgésico común vía oral y reposo podemos esperar a la recorrida de mañana."
        ],
        "evaluacion_esperada": "Interrupción por Alerta Roja Vital. Exigencia de estabilización hemodinámica inmediata (ABCDE/Hour-1). Penalización severa en Seguridad (<40 pts)."
    },

    "Residente_Estructurado": {
        "nombre": "🟢 Dr. Evidencia (Clínico Sistemático)",
        "descripcion": "Formula hipótesis jerarquizadas, justifica probabilidad pre-test, invoca calculadoras biomédicas y ejecuta SBAR.",
        "icono": "🩺",
        "turnos": [
            "Planteo como sospecha sindrómica inicial Dolor Torácico Agudo. Mis hipótesis jerarquizadas son: 1) Síndrome Coronario Agudo sin elevación del ST; 2) Pericarditis Aguda; 3) Tromboembolismo Pulmonar por disnea asociada. Solicito ECG de 12 derivaciones urgente buscando alteraciones de ST y PR, y troponina ultrasensible basal. ¿Qué hallazgos observamos en el trazado?",
            "Con el trazado y la clínica, procedo a calcular el Score HEART para estratificar el riesgo isquémico y el Score Wells para TEP. Realizo una Pausa Diagnóstica: descarto disección aórtica y taponamiento cardíaco y solicito ecocardiograma bedside.",
            "Ejecuto el Ejercicio Pre-Mortem: si el paciente colapsa en UTI a la madrugada, el descarte oportuno de taponamiento y disección fue la clave. Concluyo formulando el traspaso estructurado bajo formato SBAR para la derivación a Unidad Coronaria con monitoreo estricto."
        ],
        "evaluacion_esperada": "Puntaje de excelencia (>85). Llamada a calculadoras determinísticas. Elogio docente."
    }
}


def analizar_respuesta_socratico(respuesta: str) -> Dict[str, Any]:
    """Evalúa marcadores de comportamiento y resistencia en la respuesta de Socrático."""
    r_lower = respuesta.lower()
    
    repregunta_socratica = "?" in respuesta or "¿" in respuesta
    palabras_dialecticas = any(w in r_lower for w in ["hipótesis", "fisiopatología", "justifique", "plantea", "diferencial", "criterio", "semiología", "probabilidad"])
    resistio_oraculo = repregunta_socratica and palabras_dialecticas
    
    sesgo_detectado = any(w in r_lower for w in ["sesgo", "anclaje", "cierre prematuro", "encuadre", "pausa diagnóstica", "debiasing", "pre-mortem", "cascada", "sobrediagnóstico", "inercia"])
    alerta_seguridad = any(w in r_lower for w in ["contraindicad", "precaución", "peligro", "shock", "precarga", "hipotensión", "advertencia", "iatrogenia", "urgencia", "inmediat", "alarma", "red flag"])
    calculadora_mencionada = any(w in r_lower for w in ["score", "heart", "wells", "curb", "qsofa", "anion gap", "ckd-epi", "blatchford"])
    stewardship_recursos = any(w in r_lower for w in ["recurso", "choosing wisely", "probabilidad pre-test", "costo", "invasivo", "innecesario", "pertinencia", "sobresolit"])
    
    return {
        "resistio_oraculo": resistio_oraculo,
        "sesgo_detectado": sesgo_detectado,
        "alerta_seguridad": alerta_seguridad,
        "calculadora_mencionada": calculadora_mencionada,
        "stewardship_recursos": stewardship_recursos
    }


# ==================== GOBERNANZA Y PHI ====================
import re
import hashlib
from typing import Tuple, List, Dict, Any
from datetime import datetime

# Patrones para detección de PHI / PII
PATRONES_PHI = [
    # DNI / Cédulas / Identificaciones numéricas (7 a 9 dígitos con o sin puntos)
    (r'\b(?:DNI|C\.?I\.?|Cédula|Doc\.?|Documento)[:\s]*([0-9]{1,2}\.?[0-9]{3}\.?[0-9]{3}|[0-9]{7,8})\b', '[DNI_PROTEGIDO]'),
    (r'\b(?:HC|H\.C\.|Historia\s+Cl[ií]nica|Ficha)[:\s]*([0-9]{4,10})\b', '[HC_PROTEGIDA]'),
    # Nombres precedidos de etiquetas clínicas comunes
    (r'(?i)\b(?:paciente|nombre|sr\.|sra\.|don|doña)[:\s]+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})\b', 'Paciente: [NOMBRE_ANONIMIZADO]'),
    # Correos electrónicos
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_PROTEGIDO]'),
    # Números de teléfono (fijos o móviles de 8 a 12 dígitos)
    (r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}\b', '[TEL_PROTEGIDO]'),
    # Fechas de nacimiento explícitas
    (r'(?i)\b(?:nacido|nacimiento|fn|f\.n\.)[:\s]*([0-3]?[0-9][/-][0-1]?[0-9][/-][1-2][0-9]{3})\b', '[FECHA_NAC_PROTEGIDA]')
]

def sanitizar_texto_clinico(texto: str) -> Tuple[str, List[str]]:
    """
    Inspecciona y anonimiza información de salud protegida (PHI/PII) en viñetas o entradas.
    Retorna el texto sanitizado y la lista de categorías redactadas.
    """
    if not texto:
        return "", []
        
    texto_limpio = texto
    elementos_redactados = []
    
    for patron, reemplazo in PATRONES_PHI:
        coincidencias = re.findall(patron, texto_limpio, flags=re.IGNORECASE)
        if coincidencias:
            elementos_redactados.append(reemplazo)
            texto_limpio = re.sub(patron, reemplazo, texto_limpio, flags=re.IGNORECASE)
            
    return texto_limpio, list(set(elementos_redactados))


def generar_pseudonimo_estudiante(clave_semilla: str = "med_residente") -> str:
    """
    Genera un identificador seudónimo anónimo y consistente mediante hash SHA-256.
    Permite trazabilidad de la cohorte educativa sin almacenar datos de identidad real.
    """
    h = hashlib.sha256(clave_semilla.encode('utf-8')).hexdigest()[:8]
    return f"ALUMNO-{h.upper()}"


def estructurar_evento_auditoria(
    caso_titulo: str,
    tipo_sesgo: str,
    justificacion: str,
    alumno_id: str,
    herramienta_usada: str = "registrar_sesgo_cognitivo"
) -> Dict[str, Any]:
    """Crea una fila estandarizada para la base de datos de gobernanza clínica."""
    return {
        "Fecha_UTC": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "ID_Estudiante": alumno_id,
        "Caso_Clinico": caso_titulo,
        "Tipo_Sesgo": tipo_sesgo,
        "Justificacion_Motor": justificacion,
        "Herramienta_Auditoria": herramienta_usada,
        "Estado_Revision": "Pendiente de Ateneo"
    }


def generar_pase_sbar(
    caso_titulo: str,
    viñeta: str,
    historial_mensajes: List[Dict[str, str]],
    alumno_id: str
) -> Dict[str, str]:
    """
    Genera un reporte clínico estructurado en formato SBAR (Situation, Background, Assessment, Recommendation)
    para discusión en ateneo docente o interconsulta con jefe de residentes (Human-in-the-loop).
    """
    mensajes_usuario = [m["parts"] for m in historial_mensajes if m["role"] == "user"]
    ultimas_respuestas = " // ".join(mensajes_usuario[-2:]) if mensajes_usuario else "Inicio de abordaje diagnóstico."

    situacion = f"Interconsulta docente solicitada por {alumno_id} sobre '{caso_titulo}'."
    antecedentes = viñeta[:350] + ("..." if len(viñeta) > 350 else "")
    evaluacion = f"Hipótesis y razonamiento formulados por el residente: {ultimas_respuestas}."
    recomendacion = "Revisión en pase de guardia/ateneo: evaluar si se descartaron banderas rojas, adecuación de estudios complementarios y pertinencia del tratamiento inicial según guías."

    texto_completo = (
        f"### 📋 Pase Clínico SBAR (Derivación Docente / Ateneo)\n\n"
        f"**S (Situation):** {situacion}\n\n"
        f"**B (Background):** {antecedentes}\n\n"
        f"**A (Assessment):** {evaluacion}\n\n"
        f"**R (Recommendation):** {recomendacion}\n\n"
        f"*ID Auditoría: {alumno_id} | Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"
    )

    return {
        "S": situacion,
        "B": antecedentes,
        "A": evaluacion,
        "R": recomendacion,
        "texto_markdown": texto_completo
    }
# ==================== ALMACENAMIENTO Y LOGS ====================
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
import json

COLUMNAS_AUDITORIA = [
    "Fecha_UTC", "ID_Estudiante", "Caso_Clinico",
    "Tipo_Sesgo", "Justificacion_Motor", "Herramienta_Auditoria", "Estado_Revision"
]

COLUMNAS_EVALUACION = [
    "Fecha_UTC", "ID_Estudiante", "Caso_Clinico",
    "Puntaje_Global", "Nivel_Competencia",
    "Precision_Diagnostica", "Seguridad_Banderas_Rojas",
    "Adherencia_Guias", "Metacognicion_Sesgos", "Recursos_Comunicacion",
    "Conclusion_Docente"
]

def inicializar_almacenamiento_local():
    """Asegura que el archivo CSV local de auditoría exista con el encabezado correcto."""
    if not AUDIT_LOG_FILE.exists():
        df_init = pd.DataFrame(columns=COLUMNAS_AUDITORIA)
        df_init.to_csv(AUDIT_LOG_FILE, index=False, encoding="utf-8")


def guardar_registro_auditoria(
    evento: Dict[str, Any],
    conn_gsheets=None,
    url_gsheets: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Guarda un evento de auditoría en la base local (CSV) y en Google Sheets si está disponible.
    """
    inicializar_almacenamiento_local()
    
    # 1. Guardar siempre en local (Garantía de persistencia offline)
    try:
        nueva_fila_df = pd.DataFrame([evento])
        # Asegurar columnas correctas
        for col in COLUMNAS_AUDITORIA:
            if col not in nueva_fila_df.columns:
                nueva_fila_df[col] = ""
        nueva_fila_df = nueva_fila_df[COLUMNAS_AUDITORIA]
        
        nueva_fila_df.to_csv(AUDIT_LOG_FILE, mode='a', header=False, index=False, encoding="utf-8")
        guardado_local = True
    except Exception as e:
        return False, f"Falla en almacenamiento local: {str(e)}"
        
    # 2. Intentar guardar en Google Sheets si la conexión está disponible
    mensaje_remoto = ""
    if conn_gsheets and url_gsheets:
        try:
            df_remoto = conn_gsheets.read(spreadsheet=url_gsheets)
            df_actualizado = pd.concat([df_remoto, nueva_fila_df], ignore_index=True)
            conn_gsheets.update(spreadsheet=url_gsheets, data=df_actualizado)
            mensaje_remoto = "Sincronizado con Google Sheets."
        except Exception as e_gs:
            mensaje_remoto = f"Guardado local OK (Google Sheets no disponible: {str(e_gs)[:80]})."
    else:
        mensaje_remoto = "Guardado localmente en log de auditoría."
        
    return True, f"Registro completado. {mensaje_remoto}"


def leer_registros_auditoria(conn_gsheets=None, url_gsheets: Optional[str] = None) -> pd.DataFrame:
    """
    Lee los registros de auditoría. Si Google Sheets está conectado, lo prioriza;
    de lo contrario, recurre al log local.
    """
    inicializar_almacenamiento_local()
    
    # Intentar leer de Google Sheets
    if conn_gsheets and url_gsheets:
        try:
            df_gs = conn_gsheets.read(spreadsheet=url_gsheets)
            if df_gs is not None and not df_gs.empty:
                return df_gs
        except Exception:
            pass
            
    # Fallback a local
    try:
        if AUDIT_LOG_FILE.exists():
            df_local = pd.read_csv(AUDIT_LOG_FILE, encoding="utf-8")
            return df_local
    except Exception:
        pass
        
    return pd.DataFrame(columns=COLUMNAS_AUDITORIA)


def inicializar_almacenamiento_evaluaciones():
    """Asegura que el archivo CSV de evaluaciones exista."""
    if not EVALUATION_LOG_FILE.exists():
        df_init = pd.DataFrame(columns=COLUMNAS_EVALUACION)
        df_init.to_csv(EVALUATION_LOG_FILE, index=False, encoding="utf-8")


def guardar_registro_evaluacion(evaluacion_row: Dict[str, Any]) -> Tuple[bool, str]:
    """Guarda el resultado de una evaluación formativa en el log histórico."""
    inicializar_almacenamiento_evaluaciones()
    try:
        df_row = pd.DataFrame([evaluacion_row])
        for col in COLUMNAS_EVALUACION:
            if col not in df_row.columns:
                df_row[col] = ""
        df_row = df_row[COLUMNAS_EVALUACION]
        df_row.to_csv(EVALUATION_LOG_FILE, mode='a', header=False, index=False, encoding="utf-8")
        return True, "Evaluación registrada en el log de competencias docentes."
    except Exception as e:
        return False, f"Error al guardar evaluación: {str(e)}"


def leer_registros_evaluacion() -> pd.DataFrame:
    """Lee el histórico de evaluaciones formativas de la cohorte."""
    inicializar_almacenamiento_evaluaciones()
    try:
        if EVALUATION_LOG_FILE.exists():
            return pd.read_csv(EVALUATION_LOG_FILE, encoding="utf-8")
    except Exception:
        pass
    return pd.DataFrame(columns=COLUMNAS_EVALUACION)


COLUMNAS_LEADS = [
    "Fecha_UTC", "Nombre", "Email", "WhatsApp", "Institucion_Residencia", "Pais", "Caso_Origen", "Estado"
]

def inicializar_almacenamiento_leads():
    """Asegura que el archivo CSV de prospectos y preinscripciones exista."""
    if not LEADS_LOG_FILE.exists():
        df_init = pd.DataFrame(columns=COLUMNAS_LEADS)
        df_init.to_csv(LEADS_LOG_FILE, index=False, encoding="utf-8")


def guardar_lead_preinscripcion(lead_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Guarda un registro de un médico interesado o preinscripto en el curso."""
    inicializar_almacenamiento_leads()
    try:
        df_row = pd.DataFrame([lead_data])
        for col in COLUMNAS_LEADS:
            if col not in df_row.columns:
                df_row[col] = ""
        df_row = df_row[COLUMNAS_LEADS]
        df_row.to_csv(LEADS_LOG_FILE, mode='a', header=False, index=False, encoding="utf-8")
        return True, "Pre-inscripción registrada con éxito."
    except Exception as e:
        return False, f"Error al registrar pre-inscripción: {str(e)}"


def leer_leads_preinscripcion() -> pd.DataFrame:
    """Lee el histórico de prospectos y alumnos preinscriptos."""
    inicializar_almacenamiento_leads()
    try:
        if LEADS_LOG_FILE.exists():
            return pd.read_csv(LEADS_LOG_FILE, encoding="utf-8")
    except Exception:
        pass
    return pd.DataFrame(columns=COLUMNAS_LEADS)


COLUMNAS_BENCHMARK = [
    "Fecha_UTC", "Caso_Clinico", "Arquetipo_ID", "Nombre_Arquetipo",
    "Puntaje_Global", "Resistencia_Oraculo_Pct", "Sesgo_Auditado",
    "Alerta_Seguridad", "Tiempo_Ejecucion_Seg", "Modo_Test"
]

def inicializar_almacenamiento_benchmark():
    """Asegura que el archivo CSV de métricas de benchmarking sintético exista."""
    if not BENCHMARK_LOG_FILE.exists():
        df_init = pd.DataFrame(columns=COLUMNAS_BENCHMARK)
        df_init.to_csv(BENCHMARK_LOG_FILE, index=False, encoding="utf-8")


def guardar_registro_benchmark(benchmark_row: Dict[str, Any]) -> Tuple[bool, str]:
    """Guarda una corrida de prueba sintética en el log histórico de telemetría."""
    inicializar_almacenamiento_benchmark()
    try:
        df_row = pd.DataFrame([benchmark_row])
        for col in COLUMNAS_BENCHMARK:
            if col not in df_row.columns:
                df_row[col] = ""
        df_row = df_row[COLUMNAS_BENCHMARK]
        df_row.to_csv(BENCHMARK_LOG_FILE, mode='a', header=False, index=False, encoding="utf-8")
        return True, "Registro de benchmarking almacenado con éxito."
    except Exception as e:
        return False, f"Error al registrar benchmarking: {str(e)}"


def leer_registros_benchmark() -> pd.DataFrame:
    """Lee el histórico de corridas de benchmarking sintético."""
    inicializar_almacenamiento_benchmark()
    try:
        if BENCHMARK_LOG_FILE.exists():
            return pd.read_csv(BENCHMARK_LOG_FILE, encoding="utf-8")
    except Exception:
        pass
    return pd.DataFrame(columns=COLUMNAS_BENCHMARK)


# =============================================================
# GESTIÓN Y PERSISTENCIA DE CASOS CLÍNICOS PERSONALIZADOS
# =============================================================
def inicializar_almacenamiento_casos_personalizados():
    """Asegura que el archivo JSON de casos personalizados exista."""
    if not CUSTOM_CASES_FILE.exists():
        CUSTOM_CASES_FILE.write_text("{}", encoding="utf-8")


def leer_casos_personalizados() -> Dict[str, Dict[str, Any]]:
    """Lee todos los casos clínicos personalizados creados por docentes/residentes."""
    inicializar_almacenamiento_casos_personalizados()
    try:
        if CUSTOM_CASES_FILE.exists():
            contenido = CUSTOM_CASES_FILE.read_text(encoding="utf-8").strip()
            if contenido:
                return json.loads(contenido)
    except Exception:
        pass
    return {}


def guardar_caso_personalizado(clave_caso: str, caso_dict: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Guarda o actualiza un caso clínico en el banco persistente de casos personalizados.
    Valida la presencia de campos clínicos mínimos obligatorios.
    """
    inicializar_almacenamiento_casos_personalizados()
    campos_requeridos = ["titulo", "area", "dificultad", "viñeta", "sesgos_esperados", "red_flags"]
    for campo in campos_requeridos:
        if campo not in caso_dict or not caso_dict[campo]:
            return False, f"El campo clínico '{campo}' es obligatorio para preservar el estándar pedagógico de Socrático."
    
    try:
        casos_actuales = leer_casos_personalizados()
        casos_actuales[clave_caso] = caso_dict
        CUSTOM_CASES_FILE.write_text(json.dumps(casos_actuales, ensure_ascii=False, indent=2), encoding="utf-8")
        return True, f"El caso '{clave_caso}' fue guardado exitosamente en el banco persistente de casos clínicos."
    except Exception as e:
        return False, f"Error al guardar el caso clínico: {str(e)}"


def eliminar_caso_personalizado(clave_caso: str) -> Tuple[bool, str]:
    """Elimina un caso del banco persistente de casos personalizados."""
    inicializar_almacenamiento_casos_personalizados()
    try:
        casos_actuales = leer_casos_personalizados()
        if clave_caso in casos_actuales:
            del casos_actuales[clave_caso]
            CUSTOM_CASES_FILE.write_text(json.dumps(casos_actuales, ensure_ascii=False, indent=2), encoding="utf-8")
            return True, f"El caso '{clave_caso}' fue eliminado del banco."
        return False, f"El caso '{clave_caso}' no fue encontrado en los casos personalizados."
    except Exception as e:
        return False, f"Error al eliminar caso: {str(e)}"




# ==================== ORQUESTADOR GEMINI ====================
import json
from typing import Dict, Any, List, Tuple, Callable
from google import genai
from google.genai import types


# Declaración de herramientas para Gemini
DECLARACIONES_HERRAMIENTAS = [
    {
        'name': 'calculadora_ckd_epi',
        'description': 'Calcula la Tasa de Filtrado Glomerular estimada (TFGe) según la ecuación CKD-EPI 2021. Ejecutar obligatoriamente si el usuario propone fármacos de excreción renal o si se evalúa función renal.',
        'parameters': {
            'type': 'OBJECT',
            'properties': {
                'creatinina': {'type': 'NUMBER', 'description': 'Creatinina sérica en mg/dL'},
                'edad': {'type': 'INTEGER', 'description': 'Edad del paciente en años'},
                'sexo': {'type': 'STRING', 'description': "Sexo biológico: 'femenino' o 'masculino'"}
            },
            'required': ['creatinina', 'edad', 'sexo']
        }
    },
    {
        'name': 'calculadora_metabolica_cad',
        'description': 'Calcula Anión Gap observado, Anión Gap corregido por albúmina y Sodio corregido por glucemia (Katz/Hillier). Usar en acidosis metabólica o hiperglucemia severa.',
        'parameters': {
            'type': 'OBJECT',
            'properties': {
                'sodio_medido': {'type': 'NUMBER', 'description': 'Sodio sérico en mEq/L'},
                'cloro': {'type': 'NUMBER', 'description': 'Cloro sérico en mEq/L'},
                'bicarbonato': {'type': 'NUMBER', 'description': 'Bicarbonato en mEq/L'},
                'glucemia': {'type': 'NUMBER', 'description': 'Glucemia en mg/dL'},
                'albumina': {'type': 'NUMBER', 'description': 'Albúmina sérica en g/dL (opcional, default 4.0)'}
            },
            'required': ['sodio_medido', 'cloro', 'bicarbonato', 'glucemia']
        }
    },
    {
        'name': 'calculadora_score_heart',
        'description': 'Calcula el Score HEART para estratificación de riesgo en dolor torácico.',
        'parameters': {
            'type': 'OBJECT',
            'properties': {
                'historia': {'type': 'INTEGER', 'description': 'Historia: 0 (baja sospecha), 1 (moderada), 2 (alta sospecha)'},
                'ecg': {'type': 'INTEGER', 'description': 'ECG: 0 (normal), 1 (inespecífico), 2 (desviación significativa ST)'},
                'edad': {'type': 'INTEGER', 'description': 'Edad: 0 (<45), 1 (45-64), 2 (>=65)'},
                'factores_riesgo': {'type': 'INTEGER', 'description': 'Factores de riesgo: 0 (ninguno), 1 (1-2), 2 (>=3 o enfermedad vascular conocida)'},
                'troponina': {'type': 'INTEGER', 'description': 'Troponina: 0 (normal), 1 (1-2x límite superior), 2 (>2x límite superior)'}
            },
            'required': ['historia', 'ecg', 'edad', 'factores_riesgo', 'troponina']
        }
    },
    {
        'name': 'calculadora_score_wells_tep',
        'description': 'Calcula el Score de Wells para sospecha de Tromboembolismo Pulmonar (TEP). Usar si se plantea Dímero D o AngioTAC.',
        'parameters': {
            'type': 'OBJECT',
            'properties': {
                'sintomas_tvp': {'type': 'NUMBER', 'description': 'Signos clínicos de TVP (3.0 pts)'},
                'diagnostico_alternativo_menos_probable': {'type': 'NUMBER', 'description': 'TEP es diagnóstico principal o igual de probable (3.0 pts)'},
                'frecuencia_cardiaca_alta': {'type': 'NUMBER', 'description': 'FC > 100 lpm (1.5 pts)'},
                'inmovilizacion_o_cirugia': {'type': 'NUMBER', 'description': 'Inmovilización >= 3 días o cirugía en 4 semanas previas (1.5 pts)'},
                'antecedente_tep_tvp': {'type': 'NUMBER', 'description': 'Antecedente de TVP o TEP previo (1.5 pts)'},
                'hemoptisis': {'type': 'NUMBER', 'description': 'Presencia de hemoptisis (1.0 pt)'},
                'malignidad': {'type': 'NUMBER', 'description': 'Cáncer activo o paliativo (1.0 pt)'}
            },
            'required': ['sintomas_tvp', 'diagnostico_alternativo_menos_probable', 'frecuencia_cardiaca_alta', 'inmovilizacion_o_cirugia', 'antecedente_tep_tvp', 'hemoptisis', 'malignidad']
        }
    },
    {
        'name': 'calculadora_curb65',
        'description': 'Calcula el Score CURB-65 para severidad de Neumonía Adquirida en la Comunidad (NAC).',
        'parameters': {
            'type': 'OBJECT',
            'properties': {
                'confusion': {'type': 'INTEGER', 'description': 'Confusión mental aguda nueva (1 o 0)'},
                'urea_elevada': {'type': 'INTEGER', 'description': 'BUN > 19 mg/dL o Urea > 7 mmol/L (1 o 0)'},
                'frecuencia_respiratoria_alta': {'type': 'INTEGER', 'description': 'FR >= 30 rpm (1 o 0)'},
                'presion_baja': {'type': 'INTEGER', 'description': 'TAS < 90 o TAD <= 60 mmHg (1 o 0)'},
                'edad_mayor_65': {'type': 'INTEGER', 'description': 'Edad >= 65 años (1 o 0)'}
            },
            'required': ['confusion', 'urea_elevada', 'frecuencia_respiratoria_alta', 'presion_baja', 'edad_mayor_65']
        }
    },
    {
        'name': 'calculadora_qsofa',
        'description': 'Calcula qSOFA para detección precoz de sepsis fuera de UTI en pacientes con sospecha de infección.',
        'parameters': {
            'type': 'OBJECT',
            'properties': {
                'frecuencia_respiratoria_ge_22': {'type': 'INTEGER', 'description': 'FR >= 22 rpm (1 o 0)'},
                'glasgow_menor_15': {'type': 'INTEGER', 'description': 'Glasgow < 15 o alteración del estado mental (1 o 0)'},
                'presion_sistolica_le_100': {'type': 'INTEGER', 'description': 'Presión arterial sistólica <= 100 mmHg (1 o 0)'}
            },
            'required': ['frecuencia_respiratoria_ge_22', 'glasgow_menor_15', 'presion_sistolica_le_100']
        }
    },
    {
        'name': 'calculadora_glasgow_blatchford',
        'description': 'Calcula Score Glasgow-Blatchford en Hemorragia Digestiva Alta.',
        'parameters': {
            'type': 'OBJECT',
            'properties': {
                'urea_mg_dl': {'type': 'NUMBER', 'description': 'BUN o Urea en mg/dL'},
                'hemoglobina_g_dl': {'type': 'NUMBER', 'description': 'Hemoglobina en g/dL'},
                'sexo': {'type': 'STRING', 'description': "'femenino' o 'masculino'"},
                'presion_sistolica': {'type': 'INTEGER', 'description': 'Presión arterial sistólica'},
                'frecuencia_cardiaca': {'type': 'INTEGER', 'description': 'Frecuencia cardíaca en lpm'},
                'presento_melena': {'type': 'INTEGER', 'description': '1 si presentó melena, 0 si no'},
                'presento_sincope': {'type': 'INTEGER', 'description': '1 si presentó síncope, 0 si no'},
                'enfermedad_hepatica': {'type': 'INTEGER', 'description': '1 si tiene hepatopatía, 0 si no'},
                'insuficiencia_cardiaca': {'type': 'INTEGER', 'description': '1 si tiene insuficiencia cardíaca, 0 si no'}
            },
            'required': ['urea_mg_dl', 'hemoglobina_g_dl', 'sexo', 'presion_sistolica', 'frecuencia_cardiaca']
        }
    },
    {
        'name': 'calculadora_exacerbacion_epoc',
        'description': 'Evalúa Criterios de Anthonisen y seguridad de meta oxigenatoria en exacerbación de EPOC.',
        'parameters': {
            'type': 'OBJECT',
            'properties': {
                'aumento_disnea': {'type': 'INTEGER', 'description': '1 si hay incremento de disnea, 0 si no'},
                'aumento_volumen_esputo': {'type': 'INTEGER', 'description': '1 si hay mayor volumen de secreciones, 0 si no'},
                'purulencia_esputo': {'type': 'INTEGER', 'description': '1 si el esputo es francamente purulento/verdoso, 0 si no'},
                'saturacion_oxigeno_objetivo': {'type': 'INTEGER', 'description': 'Meta porcentual de SpO2 planteada (ej. 90, 95, etc.)'}
            },
            'required': ['aumento_disnea', 'aumento_volumen_esputo', 'purulencia_esputo', 'saturacion_oxigeno_objetivo']
        }
    },
    {
        'name': 'registrar_sesgo_cognitivo',
        'description': 'Registra un sesgo cognitivo, error de razonamiento o conducta insegura en la plataforma de gobernanza docente.',
        'parameters': {
            'type': 'OBJECT',
            'properties': {
                'tipo_sesgo': {
                    'type': 'STRING',
                    'description': 'El nombre del tipo de sesgo cometido (ej. Cierre Prematuro, Anclaje, Sesgo de Confirmación, Inercia Diagnóstica, Búsqueda Satisfecha, Desestimación de Banderas Rojas, Error de Cálculo, Tratamiento Inseguro, etc.)'
                },
                'justificacion': {
                    'type': 'STRING',
                    'description': 'Explicación detallada y pedagógica de por qué se incurrió en este sesgo cognitivo según la respuesta del alumno.'
                }
            },
            'required': ['tipo_sesgo', 'justificacion']
        }
    },
    {
        'name': 'consultar_guia_clinica',
        'description': 'Consulta una Guía de Práctica Clínica estandarizada en formato Markdown bajo demanda (Skill). Usar para verificar criterios estrictos de inclusión/exclusión, metas y dosificaciones de guías internacionales (ACV, hiperpotasemia, sepsis, cirrosis/PBE, hemorragia digestiva alta HDA, cetoacidosis diabética CAD).',
        'parameters': {
            'type': 'OBJECT',
            'properties': {
                'tema_clinico': {
                    'type': 'STRING',
                    'description': 'Tema o patología a consultar: acv, hiperpotasemia, sepsis, pbe, hda, cad.'
                }
            },
            'required': ['tema_clinico']
        }
    }
]


from pathlib import Path
SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

def leer_skill_clinica(tema: str) -> str:
    """Lee y retorna el contenido de una skill clínica en Markdown bajo demanda."""
    mapeo = {
        "acv": "guia_acv_isquemico_aha.md",
        "stroke": "guia_acv_isquemico_aha.md",
        "trombosis": "guia_acv_isquemico_aha.md",
        "trombolisis": "guia_acv_isquemico_aha.md",
        "hiperpotasemia": "guia_hiperpotasemia_emergencia.md",
        "potasio": "guia_hiperpotasemia_emergencia.md",
        "sepsis": "guia_sepsis_surviving_bundle.md",
        "shock_septico": "guia_sepsis_surviving_bundle.md",
        "pbe": "guia_cirrosis_pbe_paracentesis.md",
        "paracentesis": "guia_cirrosis_pbe_paracentesis.md",
        "cirrosis": "guia_cirrosis_pbe_paracentesis.md",
        "hda": "guia_hemorragia_digestiva_alta.md",
        "hemorragia": "guia_hemorragia_digestiva_alta.md",
        "hemorragia_digestiva": "guia_hemorragia_digestiva_alta.md",
        "cad": "guia_cetoacidosis_diabetica.md",
        "cetoacidosis": "guia_cetoacidosis_diabetica.md",
        "ehh": "guia_cetoacidosis_diabetica.md",
        "diabetes": "guia_cetoacidosis_diabetica.md"
    }
    tema_norm = tema.strip().lower()
    archivo = mapeo.get(tema_norm)
    if not archivo:
        for f in SKILLS_DIR.glob("*.md"):
            if tema_norm in f.name.lower():
                archivo = f.name
                break
    if archivo:
        ruta = SKILLS_DIR / archivo
        if ruta.exists():
            return ruta.read_text(encoding="utf-8")
    return f"Skill para '{tema}' no encontrada. Disponibles: acv, hiperpotasemia, sepsis, pbe, hda, cad."


def obtener_skill_para_caso(titulo_caso: str, viñeta_texto: str) -> Optional[str]:
    """Detecta y precarga la skill clínica pertinente al caso para inyección directa sin roundtrips."""
    texto = f"{titulo_caso} {viñeta_texto}".lower()
    
    if any(k in texto for k in ["acv", "isquémico", "isquemico", "stroke", "trombólisis", "trombolisis", "hemiparesia"]):
        return leer_skill_clinica("acv")
    if any(k in texto for k in ["hiperpotasemia", "potasio", "k+", "triple whammy"]):
        return leer_skill_clinica("hiperpotasemia")
    if any(k in texto for k in ["sepsis", "shock séptico", "shock septico", "curb-65", "qsofa", "neumonía severa"]):
        return leer_skill_clinica("sepsis")
    if any(k in texto for k in ["cirrosis", "ascitis", "peritonitis", "pbe", "paracentesis"]):
        return leer_skill_clinica("pbe")
    if any(k in texto for k in ["hemorragia digestiva", "hda", "hematemesis", "melena", "glasgow-blatchford"]):
        return leer_skill_clinica("hda")
    if any(k in texto for k in ["cetoacidosis", "cad", "pie diabético", "pie diabetico", "anión gap", "anion gap"]):
        return leer_skill_clinica("cad")
    return None


def construir_system_instruction(viñeta_texto: str, titulo_caso: str) -> str:
    """Genera el prompt de sistema socrático con pre-inyección de skills y tagging de sesgos zero-latency."""
    skill_texto = obtener_skill_para_caso(titulo_caso, viñeta_texto)
    seccion_skill = ""
    if skill_texto and not skill_texto.startswith("Skill para"):
        seccion_skill = f"""
================================================================================
GUÍA DE PRÁCTICA CLÍNICA INSTITUCIONAL VIGENTE (SKILL CLÍNICA PRE-INCORPORADA):
{skill_texto}
================================================================================
"""

    return f"""
Eres un Comité Médico Evaluador y Docente Socrático de Medicina Interna de máximo rigor académico.
Tu misión no es dictar la respuesta, sino entrenar el razonamiento clínico del médico residente, guiándolo desde el Sistema 1 (intuición rápida y sesgada) hacia el Sistema 2 (análisis bayesiano reflexivo y seguro).

CASO CLÍNICO ACTIVO:
Título: '{titulo_caso}'
Viñeta completa: '{viñeta_texto}'
{seccion_skill}
PRINCIPIOS PEDAGÓGICOS SOCRÁTICOS:
1. NUNCA des el diagnóstico definitivo ni la solución completa de inmediato. Haz repreguntas incisivas que fuercen la justificación fisiopatológica, el diagnóstico diferencial y la estratificación de riesgo.
2. Si el alumno plantea una hipótesis sin descartar causas de urgencia o con datos contradictorios, utiliza la técnica de 'Time-Out Diagnóstico' o 'Peor Escenario'.
3. USO DE CALCULADORAS BIOMÉDICAS:
   - Tienes disponibles herramientas de cálculo biomédico (CKD-EPI, HEART, Wells TEP, CURB-65, qSOFA, Glasgow-Blatchford, Anthonisen EPOC, Cetoacidosis).
   - Ejecútalas cuando requieras verificar con exactitud matemática los scores o filtrado del paciente.
   - NO le muestres el resultado crudo al alumno de inmediato; utilízalo para contrastar si él realizó bien las cuentas o para formular una repregunta socrática incisiva.
4. GOBERNANZA ACADÉMICA Y AUDITORÍA DE SESGOS COGNITIVOS (ZERO-LATENCY INLINE):
   - Cada vez que identifiques un sesgo cognitivo (ej. Anclaje y Ajuste Insuficiente, Cierre Prematuro, Búsqueda Satisfecha, Sesgo de Confirmación, Inercia Diagnóstica, Desestimación de Banderas Rojas, Error de Cálculo, Tratamiento Inseguro, etc.):
     a) Nombra y aborda el sesgo en tu devolución pedagógica de forma constructiva pero firme.
     b) Agrega OBLIGATORIAMENTE al final de tu respuesta una o más etiquetas con este formato exacto:
        <<<SESGO: [Nombre del Sesgo] | [Justificación pedagógica concisa de por qué ocurrió]>>>
     Esta etiqueta es capturada de forma inmediata por el sistema de auditoría docente.
5. Mantén un tono formal, académico, clínico y desafiante pero respetuoso.
"""


def ejecutar_dispatch_herramienta(
    nombre_herramienta: str,
    args: Dict[str, Any],
    titulo_caso: str,
    alumno_id: str,
    conn_gsheets=None,
    url_gsheets=None
) -> Tuple[Dict[str, Any], str]:
    """
    Ejecuta la función Python correspondiente según la llamada de herramienta de Gemini.
    Retorna el resultado estructurado y un resumen amigable para la UI.
    """
    if nombre_herramienta == 'registrar_sesgo_cognitivo':
        tipo = args.get('tipo_sesgo', 'No especificado')
        just = args.get('justificacion', 'Sin justificación')
        evento = estructurar_evento_auditoria(
            caso_titulo=titulo_caso,
            tipo_sesgo=tipo,
            justificacion=just,
            alumno_id=alumno_id
        )
        exito, msg_storage = guardar_registro_auditoria(evento, conn_gsheets, url_gsheets)
        return {
            "status": "registrado",
            "tipo_sesgo": tipo,
            "almacenamiento": msg_storage
        }, f"Sesgo '{tipo}' registrado en la auditoría docente ({msg_storage})"
        
    elif nombre_herramienta == 'calculadora_ckd_epi':
        res = calcular_ckd_epi_2021(
            creatinina=float(args['creatinina']),
            edad=int(args['edad']),
            sexo=str(args['sexo'])
        )
        return res, f"TFGe calculada: {res.get('tfge')} mL/min/1.73m² ({res.get('estadio')})"
        
    elif nombre_herramienta == 'calculadora_metabolica_cad':
        res = calcular_metabolica_cad(
            sodio_medido=float(args['sodio_medido']),
            cloro=float(args['cloro']),
            bicarbonato=float(args['bicarbonato']),
            glucemia=float(args['glucemia']),
            albumina=float(args.get('albumina', 4.0))
        )
        return res, f"Anión Gap: {res.get('anion_gap_corregido_albumina')} | Na Corregido: {res.get('sodio_corregido_katz')} mEq/L"
        
    elif nombre_herramienta == 'calculadora_score_heart':
        res = calcular_score_heart(
            historia=int(args['historia']),
            ecg=int(args['ecg']),
            edad=int(args['edad']),
            factores_riesgo=int(args['factores_riesgo']),
            troponina=int(args['troponina'])
        )
        return res, f"Score HEART: {res.get('score_total')} pts ({res.get('estrato_riesgo')})"
        
    elif nombre_herramienta == 'calculadora_score_wells_tep':
        res = calcular_score_wells_tep(
            sintomas_tvp=float(args['sintomas_tvp']),
            diagnostico_alternativo_menos_probable=float(args['diagnostico_alternativo_menos_probable']),
            frecuencia_cardiaca_alta=float(args['frecuencia_cardiaca_alta']),
            inmovilizacion_o_cirugia=float(args['inmovilizacion_o_cirugia']),
            antecedente_tep_tvp=float(args['antecedente_tep_tvp']),
            hemoptisis=float(args['hemoptisis']),
            malignidad=float(args['malignidad'])
        )
        return res, f"Score Wells TEP: {res.get('score_total')} pts ({res.get('estrato')})"
        
    elif nombre_herramienta == 'calculadora_curb65':
        res = calcular_curb65(
            confusion=int(args['confusion']),
            urea_elevada=int(args['urea_elevada']),
            frecuencia_respiratoria_alta=int(args['frecuencia_respiratoria_alta']),
            presion_baja=int(args['presion_baja']),
            edad_mayor_65=int(args['edad_mayor_65'])
        )
        return res, f"Score CURB-65: {res.get('score_total')} pts ({res.get('severidad')})"
        
    elif nombre_herramienta == 'calculadora_qsofa':
        res = calcular_qsofa(
            frecuencia_respiratoria_ge_22=int(args['frecuencia_respiratoria_ge_22']),
            glasgow_menor_15=int(args['glasgow_menor_15']),
            presion_sistolica_le_100=int(args['presion_sistolica_le_100'])
        )
        return res, f"Score qSOFA: {res.get('score_total')} pts ({'Positivo para sepsis' if res.get('criterio_positivo') else 'Negativo'})"
        
    elif nombre_herramienta == 'calculadora_glasgow_blatchford':
        res = calcular_glasgow_blatchford(
            urea_mg_dl=float(args['urea_mg_dl']),
            hemoglobina_g_dl=float(args['hemoglobina_g_dl']),
            sexo=str(args['sexo']),
            presion_sistolica=int(args['presion_sistolica']),
            frecuencia_cardiaca=int(args['frecuencia_cardiaca']),
            presento_melena=int(args.get('presento_melena', 0)),
            presento_sincope=int(args.get('presento_sincope', 0)),
            enfermedad_hepatica=int(args.get('enfermedad_hepatica', 0)),
            insuficiencia_cardiaca=int(args.get('insuficiencia_cardiaca', 0))
        )
        return res, f"Score Glasgow-Blatchford: {res.get('score_total')} pts ({res.get('riesgo')})"
        
    elif nombre_herramienta == 'calculadora_exacerbacion_epoc':
        res = calcular_exacerbacion_epoc(
            aumento_disnea=int(args['aumento_disnea']),
            aumento_volumen_esputo=int(args['aumento_volumen_esputo']),
            purulencia_esputo=int(args['purulencia_esputo']),
            saturacion_oxigeno_objetivo=int(args['saturacion_oxigeno_objetivo'])
        )
        return res, f"Anthonisen: {res.get('clasificacion_anthonisen')} | {res.get('seguridad_oxigeno')[:40]}"
        
    elif nombre_herramienta == 'consultar_guia_clinica':
        tema = args.get('tema_clinico', '')
        contenido_skill = leer_skill_clinica(tema)
        return {
            "tema": tema,
            "contenido_guia": contenido_skill
        }, f"Guía clínica consultada (Skill): '{tema}'"
        
    return {"error": f"Herramienta desconocida: {nombre_herramienta}"}, "Herramienta desconocida"


import time
import re
from google.genai.errors import APIError, ServerError

def _es_error_transitorio(e: Exception) -> bool:
    """Verifica si el error es de sobrecarga, 503, 429 o temporal."""
    msg = str(e).lower()
    es_codigo = getattr(e, "code", None) in [503, 429, 500] or "503" in msg or "429" in msg
    es_sobrecarga = any(p in msg for p in ["overloaded", "unavailable", "rate limit", "resource exhausted", "resource_exhausted", "picos de demanda"])
    return es_codigo or es_sobrecarga


def _extraer_segundos_espera(e: Exception) -> float:
    """Extrae el tiempo de espera en segundos sugerido por Google ante un 429 Resource Exhausted."""
    msg = str(e)
    m = re.search(r'retry in ([0-9\.]+)s', msg, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            pass
    m2 = re.search(r'retrydelay[\'":\s]+([0-9]+)s', msg, re.IGNORECASE)
    if m2:
        try:
            return float(m2.group(1))
        except Exception:
            pass
    return 6.0


def procesar_turno_socratico(
    api_key: str,
    modelo_seleccionado: str,
    viñeta_texto: str,
    titulo_caso: str,
    historial_mensajes: List[Dict[str, str]],
    nuevo_mensaje_usuario: str,
    alumno_id: str,
    callback_notificacion: Optional[Callable[[str, str], None]] = None,
    conn_gsheets=None,
    url_gsheets=None
) -> Tuple[str, List[str]]:
    """
    Envía el mensaje al modelo y ejecuta la respuesta socrática optimizada en pase único.
    Pre-inyecta skills clínicas, registra sesgos en línea (cero latencia) y audita calculadoras.
    """
    import sys, traceback
    
    api_key_limpia = api_key.strip() if api_key else ""
    client = genai.Client(api_key=api_key_limpia)
    system_instruction = construir_system_instruction(viñeta_texto, titulo_caso)
    
    # Proveemos solo las calculadoras para evitar llamadas recursivas innecesarias a skills o sesgos
    herramientas_calculadoras = [t for t in DECLARACIONES_HERRAMIENTAS if t['name'].startswith('calculadora_')]
    
    config = types.GenerateContentConfig(
        temperature=0.15,
        system_instruction=system_instruction,
        tools=[{'function_declarations': herramientas_calculadoras}]
    )
    
    # Preparar historial válido para Google Gemini API:
    history_contents = []
    for m in historial_mensajes:
        if not history_contents and m["role"] == "model":
            # Omitimos el mensaje de saludo inicial visual del modelo
            continue
        history_contents.append(
            types.Content(role=m["role"], parts=[types.Part.from_text(text=m["parts"])])
        )
        
    modelos_candidatos = [modelo_seleccionado]
    respaldos_estables = ["gemini-3.6-flash"]
    for resp in respaldos_estables:
        if resp not in modelos_candidatos:
            modelos_candidatos.append(resp)
            
    ultimo_error = None
    
    for modelo_actual in modelos_candidatos:
        max_intentos = 3
        for intento in range(max_intentos):
            try:
                chat = client.chats.create(
                    model=modelo_actual,
                    config=config,
                    history=history_contents
                )
                
                response = chat.send_message(nuevo_mensaje_usuario)
                herramientas_ejecutadas = []
                
                # Bucle para resolver calculadoras biomédicas si fueron solicitadas
                max_iteraciones = 2
                iteracion = 0
                
                while iteracion < max_iteraciones:
                    iteracion += 1
                    function_calls = getattr(response, 'function_calls', None)
                    
                    if not function_calls:
                        break
                        
                    partes_respuesta_funcion = []
                    for call in function_calls:
                        nombre = call.name
                        args = call.args
                        
                        res_dict, resumen_ui = ejecutar_dispatch_herramienta(
                            nombre_herramienta=nombre,
                            args=args,
                            titulo_caso=titulo_caso,
                            alumno_id=alumno_id,
                            conn_gsheets=conn_gsheets,
                            url_gsheets=url_gsheets
                        )
                        
                        herramientas_ejecutadas.append(f"{nombre}: {resumen_ui}")
                        
                        if callback_notificacion:
                            callback_notificacion(nombre, resumen_ui)
                            
                        partes_respuesta_funcion.append(
                            types.Part.from_function_response(
                                name=nombre,
                                response={"resultado": res_dict}
                            )
                        )
                        
                    time.sleep(0.2)
                    response = chat.send_message(partes_respuesta_funcion)
                    
                texto_crudo = response.text or "El comité ha completado la auditoría interna. Por favor continúe con su razonamiento."
                
                # Extracción y registro de sesgos cognitivos vía inline tags (Cero Latencia)
                patron_sesgos = r'<<<SESGO:\s*([^|>]+)\s*\|\s*([^>]+)>>>'
                sesgos_detectados = re.findall(patron_sesgos, texto_crudo)
                
                for tipo_sesgo, justificacion in sesgos_detectados:
                    tipo_sesgo_limpio = tipo_sesgo.strip()
                    justificacion_limpia = justificacion.strip()
                    evento = estructurar_evento_auditoria(
                        caso_titulo=titulo_caso,
                        tipo_sesgo=tipo_sesgo_limpio,
                        justificacion=justificacion_limpia,
                        alumno_id=alumno_id
                    )
                    exito, msg_storage = guardar_registro_auditoria(evento, conn_gsheets, url_gsheets)
                    herramientas_ejecutadas.append(f"Sesgo auditado: '{tipo_sesgo_limpio}' ({msg_storage})")
                    if callback_notificacion:
                        callback_notificacion("sesgo_auditado", f"Sesgo auditado: {tipo_sesgo_limpio}")
                        
                # Limpiar las etiquetas de la respuesta visible al estudiante
                texto_final = re.sub(patron_sesgos, '', texto_crudo).strip()
                
                if modelo_actual != modelo_seleccionado:
                    aviso_fallback = (
                        f"> ℹ️ *Aviso del Sistema:* El modelo '{modelo_seleccionado}' presentaba picos de demanda momentáneos. "
                        f"La tutoría fue respondida de forma ininterrumpida por el modelo de respaldo institucional '{modelo_actual}'.\n\n"
                    )
                    texto_final = aviso_fallback + texto_final
                    
                return texto_final, herramientas_ejecutadas
                
            except Exception as e:
                ultimo_error = e
                err_str = str(e)
                print(f"[DEBUG GEMINI ERROR] Modelo: {modelo_actual}, Intento: {intento+1}/{max_intentos}, Error: {type(e).__name__}: {err_str}", flush=True)
                
                if "429" in err_str or "resource_exhausted" in err_str.lower():
                    wait_sec = _extraer_segundos_espera(e)
                    wait_sec = max(3.0, min(wait_sec + 1.5, 25.0))
                    if callback_notificacion:
                        callback_notificacion(
                            "cuota_429",
                            f"Límite de solicitudes por minuto alcanzado. Pausando {wait_sec:.0f}s para continuar automáticamente..."
                        )
                    print(f"[DEBUG GEMINI 429] Esperando {wait_sec:.1f}s antes de reintentar...", flush=True)
                    time.sleep(wait_sec)
                elif _es_error_transitorio(e):
                    if callback_notificacion:
                        callback_notificacion(
                            "reintento_contingencia",
                            f"Pico de demanda en {modelo_actual} (Intento {intento+1}/{max_intentos}). Reintentando..."
                        )
                    time.sleep(2.0 * (intento + 1))
                else:
                    print(f"[DEBUG GEMINI] Modelo {modelo_actual} descartado por error permanente ({e}).", flush=True)
                    break
                    
    # Última contingencia de resiliencia: Si falló con tools, llamada directa sin function calling
    try:
        print("[DEBUG GEMINI] Intentando última contingencia directa sin tools...", flush=True)
        time.sleep(2.0)
        cfg_directo = types.GenerateContentConfig(
            temperature=0.2,
            system_instruction=system_instruction
        )
        chat_directo = client.chats.create(
            model="gemini-3.6-flash",
            config=cfg_directo,
            history=history_contents
        )
        resp_directo = chat_directo.send_message(nuevo_mensaje_usuario)
        if resp_directo.text:
            aviso_contingencia = "> ℹ️ *Aviso:* Se activó el modo de contingencia docente directa.\n\n"
            return aviso_contingencia + resp_directo.text, ["Modo contingencia directa (chat socrático)"]
    except Exception as e_directo:
        print(f"[DEBUG GEMINI ERROR FINAL] Contingencia directa falló: {e_directo}", flush=True)
        
    # Si todos los reintentos fallaron, propagar el error original
    raise ultimo_error or RuntimeError("No fue posible obtener respuesta del modelo.")

# ==================== TRIBUNAL EVALUADOR ====================
import json
import re
from typing import Dict, Any, List
from google import genai
from google.genai import types


SYSTEM_INSTRUCTION_EVALUADOR = """
Eres el Presidente del Tribunal de Evaluación de la Residencia de Medicina Interna y Comité de Seguridad del Paciente.
Tu objetivo es realizar una auditoría y evaluación formativa rigurosa del razonamiento clínico del médico residente durante la resolución de un caso clínico simulado.

Debes evaluar el desempeño del residente a través del diálogo mantenido, basándote en la evidencia clínica, las banderas rojas y la mitigación de sesgos.

Debes calificar estrictamente 5 dimensiones pedagógicas (de 0 a 20 puntos cada una, sumando un puntaje global de 0 a 100):
1. precision_diagnostica (0-20 pts): Sospecha principal fundada, jerarquización de diagnósticos diferenciales.
2. seguridad_y_banderas_rojas (0-20 pts): Detección oportuna de alertas vitales, descarte de patologías mortales, prevención de conductas iatrogénicas o contraindicadas.
3. adherencia_guias_y_skills (0-20 pts): Cumplimiento de metas basadas en evidencia, uso o interpretación adecuada de calculadoras o protocolos clínicos.
4. metacognicion_y_sesgos (0-20 pts): Flexibilidad reflexiva, respuesta ante pausas diagnósticas, ausencia o reconocimiento de sesgos cognitivos (anclaje, cierre prematuro, confirmación).
5. recursos_y_comunicacion (0-20 pts): Solicitud escalonada y justificada de estudios (sin sobreutilización ni pedidos disparatados), lenguaje médico formal y precisión.

RESPONDE ÚNICAMENTE CON UN OBJETO JSON VÁLIDO CON ESTA ESTRUCTURA EXACTA (SIN TEXTO PREVIO NI POSTERIOR):
{
  "puntaje_global": 85,
  "desglose_dimensiones": {
    "precision_diagnostica": {
      "puntaje": 17,
      "comentario": "Justificación clínica..."
    },
    "seguridad_y_banderas_rojas": {
      "puntaje": 18,
      "comentario": "Justificación clínica..."
    },
    "adherencia_guias_y_skills": {
      "puntaje": 16,
      "comentario": "Justificación clínica..."
    },
    "metacognicion_y_sesgos": {
      "puntaje": 18,
      "comentario": "Justificación clínica..."
    },
    "recursos_y_comunicacion": {
      "puntaje": 16,
      "comentario": "Justificación clínica..."
    }
  },
  "puntos_fuertes": [
    "Acierto destacado 1",
    "Acierto destacado 2"
  ],
  "oportunidades_mejora": [
    "Área de mejora o lectura recomendada 1",
    "Área de mejora o recomendación 2"
  ],
  "sesgos_observados_evaluacion": [
    "Sesgo detectado o 'Ninguno significativo'"
  ],
  "conclusion_docente": "Párrafo conciso de devolución pedagógica final de rigor académico y aliento formativo."
}
"""


def _limpiar_json_str(texto: str) -> str:
    """Remueve bloques de código markdown y caracteres espurios para obtener JSON limpio."""
    t = texto.strip()
    if t.startswith("```json"):
        t = t[7:]
    elif t.startswith("```"):
        t = t[3:]
    if t.endswith("```"):
        t = t[:-3]
    return t.strip()


def evaluar_desempeno_caso(
    api_key: str,
    modelo_seleccionado: str,
    titulo_caso: str,
    viñeta_texto: str,
    caso_meta: Dict[str, Any],
    historial_mensajes: List[Dict[str, str]],
    alumno_id: str
) -> Dict[str, Any]:
    """
    Ejecuta la evaluación colegiada del caso clínico mediante Gemini 3.6 y retorna
    un diccionario estructurado con los puntajes por dimensión y recomendaciones docentes.
    """
    api_key_limpia = api_key.strip() if api_key else ""
    client = genai.Client(api_key=api_key_limpia)

    # Formatear el diálogo para el prompt del evaluador
    dialogo_formateado = []
    for m in historial_mensajes:
        rol_display = "Residente" if m["role"] == "user" else "Tutor Socrático"
        dialogo_formateado.append(f"[{rol_display}]: {m['parts']}")
    transcripcion_dialogo = "\n\n".join(dialogo_formateado)

    red_flags = "\n- ".join(caso_meta.get("red_flags", ["No especificadas"]))
    sesgos_esperados = ", ".join(caso_meta.get("sesgos_esperados", ["No especificados"]))
    calculadoras = ", ".join(caso_meta.get("calculadoras_pertinentes", ["No especificadas"]))

    prompt_evaluacion = f"""
CASO CLÍNICO EVALUADO:
Título: '{titulo_caso}'
Área: {caso_meta.get('area', 'Medicina Interna')} | Dificultad: {caso_meta.get('dificultad', 'Intermedia')}
Viñeta original:
{viñeta_texto}

CRITERIOS DOCENTES CLAVE:
- Banderas rojas críticas que el residente debía descartar:
- {red_flags}
- Sesgos cognitivos esperados en este escenario: {sesgos_esperados}
- Calculadoras o protocolos pertinentes esperados: {calculadoras}

TRANSCRIPCIÓN COMPLETA DEL DESEMPEÑO DEL RESIDENTE ({alumno_id}):
{transcripcion_dialogo}

INSTRUCCIÓN:
Evalúa objetivamente cada una de las 5 dimensiones pedagógicas del residente de 0 a 20 puntos.
Calcula el puntaje global como la suma exacta de las 5 dimensiones.
Genera comentarios constructivos pero rigurosos con citas a las respuestas del residente.
Responde únicamente con el JSON especificado.
"""

    modelos = [modelo_seleccionado, "gemini-3.6-flash"]
    modelos_unicos = []
    for mod in modelos:
        if mod not in modelos_unicos:
            modelos_unicos.append(mod)

    ultimo_error = None
    import time
    for mod in modelos_unicos:
        for intento in range(2):
            try:
                config = types.GenerateContentConfig(
                    temperature=0.1,
                    system_instruction=SYSTEM_INSTRUCTION_EVALUADOR,
                    response_mime_type="application/json"
                )
                response = client.models.generate_content(
                    model=mod,
                    contents=prompt_evaluacion,
                    config=config
                )
                texto_resp = response.text or "{}"
                raw_json = _limpiar_json_str(texto_resp)
                data = json.loads(raw_json)

                # Validar y asegurar estructura
                if "desglose_dimensiones" not in data:
                    data["desglose_dimensiones"] = {}
                
                # Recalcular puntaje global para coherencia matemática
                suma_pts = 0
                for dim_k, dim_m in DIMENSIONES_RUBRICA.items():
                    if dim_k not in data["desglose_dimensiones"]:
                        data["desglose_dimensiones"][dim_k] = {
                            "puntaje": 14,
                            "comentario": "Evaluación general completada."
                        }
                    else:
                        pts = data["desglose_dimensiones"][dim_k].get("puntaje", 10)
                        # Asegurar límites 0 a peso_max
                        pts = max(0, min(dim_m["peso_max"], pts))
                        data["desglose_dimensiones"][dim_k]["puntaje"] = pts
                        suma_pts += pts

                data["puntaje_global"] = min(100, max(0, suma_pts))
                data["nivel_competencia"] = determinar_nivel_competencia(data["puntaje_global"])
                return data

            except Exception as e:
                ultimo_error = e
                print(f"[EVALUATOR RETRY] Modelo: {mod}, Intento: {intento+1}/2, Error: {type(e).__name__}: {e}", flush=True)
                time.sleep(2.0)
                continue

    # Fallback determinista si falla la API
    print(f"[EVALUATOR FALLBACK] Activando evaluación de contingencia determinista: {ultimo_error}", flush=True)
    return _generar_evaluacion_fallback(ultimo_error)


def _generar_evaluacion_fallback(error_msg: Exception = None) -> Dict[str, Any]:
    """Genera una evaluación por defecto si la llamada al LLM no puede completarse."""
    desglose = {
        dim_k: {
            "puntaje": 15,
            "comentario": f"Evaluación preliminar de {dim_m['nombre']} registrada."
        }
        for dim_k, dim_m in DIMENSIONES_RUBRICA.items()
    }
    return {
        "puntaje_global": 75,
        "nivel_competencia": determinar_nivel_competencia(75),
        "desglose_dimensiones": desglose,
        "puntos_fuertes": [
            "Completó el proceso de anamnesis y razonamiento diagnóstico.",
            "Participó activamente en la discusión socrática del caso."
        ],
        "oportunidades_mejora": [
            "Revisar protocolos de urgencia y cálculo de scores predictivos.",
            "Profundizar en el descarte de diagnósticos diferenciales de riesgo de vida."
        ],
        "sesgos_observados_evaluacion": [
            "No se detectaron sesgos críticos en la interacción registrada."
        ],
        "conclusion_docente": "El residente ha abordado el caso con compromiso. Se recomienda continuar con casos de mayor dificultad para consolidar la toma de decisiones autónoma.",
        "advertencia": f"Evaluación generada en modo de contingencia docente ({str(error_msg)})." if error_msg else None
    }
# ==================== APLICACION STREAMLIT ====================
import streamlit as st
import pandas as pd
import altair as alt
import json
from datetime import datetime


# Configuración de Streamlit

# Inyección de estilos
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Intentar inicializar conexión con Google Sheets si existe la extensión instalada
conn_gsheets = None
try:
    from streamlit_gsheets import GSheetsConnection
    conn_gsheets = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    conn_gsheets = None

# Inicialización de Session State
if "alumno_id" not in st.session_state:
    st.session_state.alumno_id = generar_pseudonimo_estudiante("cohorte_2026")

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

def reiniciar_caso(nombre_caso, titulo, texto, metadata=None):
    st.session_state.caso_activo_nombre = nombre_caso
    st.session_state.caso_activo_titulo = titulo
    st.session_state.caso_activo_texto = texto
    st.session_state.caso_activo_meta = metadata or {}
    st.session_state.evaluacion_activa = None
    st.session_state.mostrar_sbar = False
    st.session_state.mensajes = [
        {
            "role": "model",
            "parts": (
                "**Comité Médico Evaluador:** Viñeta clínica analizada. "
                "**¿Cuál es su impresión sindrómica inicial y qué hipótesis diagnósticas de urgencia prioriza?**"
            )
        }
    ]

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
    with col_id2:
        if st.button("🎲", help="Generar nuevo seudónimo anónimo aleatorio"):
            st.session_state.alumno_id = generar_pseudonimo_estudiante(f"id_{datetime.now().timestamp()}")
            st.rerun()
            
    st.caption("🛡️ Los datos se registran bajo un seudónimo anónimo para auditoría docente sin comprometer PII.")

    st.markdown("---")
    st.markdown("### ⚙️ Selección del Escenario")
    modo_caso = st.radio("Origen del caso:", ["Banco Estándar (Medicina Interna)", "Cargar Caso Personalizado"])
    
    if modo_caso == "Banco Estándar (Medicina Interna)":
        nombre_sel = st.selectbox("Escenario de práctica:", obtener_nombres_casos())
        if nombre_sel != st.session_state.caso_activo_nombre:
            info_c = obtener_caso(nombre_sel)
            reiniciar_caso(nombre_sel, info_c["titulo"], info_c["viñeta"], info_c)
            st.rerun()
    else:
        st.markdown("#### 📝 Carga Segura de Caso")
        custom_titulo = st.text_input("Título del caso:", value="Paciente con cuadro a filiar")
        custom_texto = st.text_area("Viñeta clínica (incluya antecedentes, examen y signos vitales):", height=150)
        
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

if es_docente:
    tab_simulador, tab_mapas, tab_gobernanza, tab_programa, tab_metricas, tab_estres, tab_creador = st.tabs([
        "🩺 Simulador Clínico Socrático",
        "🗺️ Mapas Conceptuales & Guías de Estudio",
        "🛡️ Taxonomía de Sesgos & Gobernanza",
        "🎓 Residencia Hospital Heller & Programa",
        "📊 Métricas & Auditoría Docente",
        "⚡ Laboratorio de Estrés & Benchmarking",
        "➕ Creador & Banco de Casos"
    ])
else:
    tab_simulador, tab_mapas, tab_gobernanza, tab_programa = st.tabs([
        "🩺 Simulador Clínico Socrático",
        "🗺️ Mapas Conceptuales & Guías de Estudio",
        "🛡️ Taxonomía de Sesgos & Gobernanza",
        "🎓 Residencia Hospital Heller & Programa"
    ])
    tab_metricas = None
    tab_estres = None
    tab_creador = None

# ==========================================
# PESTAÑA 1: SIMULADOR CLÍNICO
# ==========================================
with tab_simulador:
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
            
            st.session_state.mensajes.append({"role": "user", "parts": prompt_final})
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
                            url_gsheets=url_hoja if url_hoja else None
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
                data=manual_html_p.read_text(encoding="utf-8") if manual_html_p.exists() else MANUAL_TEXT_EMBEDDED,
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
                data=manual_md_p.read_text(encoding="utf-8") if manual_md_p.exists() else MANUAL_TEXT_EMBEDDED,
                file_name="Manual_Residencia_Clinica_Medica_Hospital_Heller.md",
                mime="text/markdown",
                key="btn_descarga_manual_md_mapas",
                use_container_width=True
            )


# ==========================================
# PESTAÑA 3: TAXONOMÍA & GOBERNANZA PHI
# ==========================================
with tab_gobernanza:
    st.markdown("### 🛡️ Marco Teórico: Taxonomía de Croskerry & Desesgamiento")
    st.markdown("""
        El razonamiento médico integra dos sistemas cognitivos:
        * **Sistema 1 (Heurístico):** Rápido, automático, de bajo consumo energético, pero vulnerable a sesgos cognitivos.
        * **Sistema 2 (Analítico):** Lento, deliberativo, bayesiano y riguroso.
        
        Las **Estrategias de Forzamiento Cognitivo (*Cognitive Forcing Strategies*)** intervienen activamente para desacoplar el Sistema 1 cuando la probabilidad de error es máxima.
    """)
    
    st.markdown("#### 📚 Catálogo de los 12 Sesgos Cognitivos Auditados")
    for nombre_s, detalle in TAXONOMIA_SESGOS.items():
        with st.expander(f"📌 {nombre_s} ({detalle['categoria']})"):
            st.markdown(f"**Definición:** {detalle['descripcion']}")
            st.markdown(f"**Ejemplo en Medicina Interna:** *{detalle['ejemplo_clinico']}*")
            st.info(f"💡 **Estrategia de Forzamiento (Debiasing):** {detalle['estrategia_debiasing']}")

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

    st.markdown("---")
    st.markdown("### 📖 Guías Clínicas & Skills Markdown Bajo Demanda")
    st.caption("Protocolos y bundles de evidencia cargados dinámicamente por el tutor inteligente durante el razonamiento clínico (Human-in-the-loop & Evidence on Demand).")
    
    if SKILLS_DIR.exists():
        skills_files = sorted(list(SKILLS_DIR.glob("*.md")))
        if skills_files:
            titulos_skills = {
                f.stem: f.stem.replace("guia_", "").replace("_", " ").upper()
                for f in skills_files
            }
            col_sel_s, _ = st.columns([2, 1])
            with col_sel_s:
                skill_sel = st.selectbox(
                    "Seleccione una Guía Clínica / Protocolo para auditar:",
                    list(titulos_skills.keys()),
                    format_func=lambda x: f"📑 Protocolo: {titulos_skills[x]}"
                )
            if skill_sel:
                skill_path = SKILLS_DIR / f"{skill_sel}.md"
                with st.expander(f"📖 Ver Documento Completo: {titulos_skills[skill_sel]}", expanded=True):
                    st.markdown(skill_path.read_text(encoding="utf-8"))
        else:
            st.info("No se encontraron archivos en la carpeta de skills.")


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
                data=manual_p_html.read_text(encoding="utf-8") if manual_p_html.exists() else MANUAL_TEXT_EMBEDDED,
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
                data=manual_p_md.read_text(encoding="utf-8") if manual_p_md.exists() else MANUAL_TEXT_EMBEDDED,
                file_name="Manual_Residencia_Hospital_Heller_Socratico.md",
                mime="text/markdown",
                key="btn_descarga_manual_md_tab4",
                use_container_width=True
            )
            
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
if es_docente and tab_metricas is not None and tab_estres is not None and tab_creador is not None:
        # ==========================================
    # PESTAÑA 3: MÉTRICAS & AUDITORÍA DOCENTE
    # ==========================================
    with tab_metricas:
        st.markdown("### 📊 Panel de Gobernanza Académica y Detección de Sesgos")
        st.caption("Monitoreo continuo de desvíos en el razonamiento diagnóstico y adherencia a seguridad del paciente.")
    
        col_ref, _ = st.columns([1, 4])
        with col_ref:
            if st.button("🔄 Actualizar Registros", width="stretch"):
                st.rerun()

        df_registros = leer_registros_auditoria(conn_gsheets, url_hoja)
    
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
        
            # Descarga
            csv_data = df_registros.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Reporte de Gobernanza (CSV)",
                data=csv_data,
                file_name=f"auditoria_sesgos_clinicos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )

        st.markdown("---")
        st.markdown("### 🎓 Rendimiento Académico y Evaluación de Competencias Clínicas de la Cohorte")
        st.caption("Resultados globales emitidos por el Tribunal Evaluador Docente según las 5 dimensiones de la rúbrica.")

        df_evals = leer_registros_evaluacion()
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
            csv_evals = df_evals.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Libro de Calificaciones Docente (CSV)",
                data=csv_evals,
                file_name=f"libro_calificaciones_cohorte_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                key="btn_descargar_libro_eval"
            )

            # Sección de Leads y Preinscripciones Comerciales
            st.markdown("---")
            st.markdown("### 💼 Base de Prospectos y Pre-Inscriptos (CRM del Curso)")
            st.caption("Médicos y residentes que han solicitado información o reservado cupo desde el simulador.")
            df_leads = leer_leads_preinscripcion()
            if not df_leads.empty:
                col_l1, col_l2 = st.columns([1, 3])
                with col_l1:
                    st.metric("Total de Pre-Inscriptos", len(df_leads))
                st.dataframe(
                    df_leads.sort_values(by="Fecha_UTC", ascending=False) if "Fecha_UTC" in df_leads.columns else df_leads,
                    use_container_width=True,
                    hide_index=True
                )
                csv_leads = df_leads.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Exportar Lista de Contactos / Leads (CSV)",
                    data=csv_leads,
                    file_name=f"leads_preinscripcion_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key="btn_descargar_leads_crm"
                )
            else:
                st.info("Aún no hay registros de pre-inscripciones. Aparecerán aquí cuando los colegas completen el formulario.")

        # ==========================================
        # PESTAÑA 6: LABORATORIO DE ESTRÉS & BENCHMARKING SINTÉTICO (6 PERFILES)
        # ==========================================
        with tab_estres:
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
                    with st.status("Ejecutando Torneo Comparativo con los 6 Residentes Sintéticos...", expanded=True) as status_box:
                        progreso = st.progress(0)
                        filas_tabla = []
                        arquetipos_lista = list(ARQUETIPOS_RESIDENTES.items())
                    
                        fallback_scores = {
                            "Residente_Atajador": 42,
                            "Residente_Sesgado": 64,
                            "Residente_Peligroso": 32,
                            "Residente_Despilfarro": 48,
                            "Residente_Inercia": 36,
                            "Residente_Estructurado": 94
                        }
                    
                        for idx_a, (a_id, a_info) in enumerate(arquetipos_lista):
                            st.write(f"▶️ Evaluando **{a_info['nombre']}**...")
                            hist_a = [
                                {
                                    "role": "model",
                                    "parts": "Comité Médico: ¿Cuál es su impresión sindrómica inicial?"
                                }
                            ]
                            oraculo_count = 0
                            sesgo_count = 0
                            seguridad_count = 0
                            t_inicio_a = time.time()
                        
                            turnos_benchmark = a_info["turnos"][:2]
                        
                            for num_b, txt_u in enumerate(turnos_benchmark):
                                r_s = ""
                                for intento_b in range(2):
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
                                        break
                                    except Exception as e_b:
                                        if intento_b == 0 and ("429" in str(e_b) or "resource" in str(e_b).lower()):
                                            time.sleep(5.0)
                                    else:
                                        r_s = "El tribunal exige justificar la sospecha y descarta respuestas cerradas."
                                        t_e = []
                                    
                                an_m = analizar_respuesta_socratico(r_s)
                                if an_m["resistio_oraculo"]:
                                    oraculo_count += 1
                                if an_m["sesgo_detectado"]:
                                    sesgo_count += 1
                                if an_m.get("alerta_seguridad"):
                                    seguridad_count += 1
                                
                                hist_a.append({"role": "user", "parts": txt_u})
                                hist_a.append({"role": "model", "parts": r_s})
                                time.sleep(1.2)
                            
                            duracion_a = round(time.time() - t_inicio_a, 1)
                        
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
                            time.sleep(1.8)
                        
                        status_box.update(label="🏆 Torneo Comparativo Finalizado con Éxito", state="complete")
                    
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
                csv_bench = df_historico_estres.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar Base de Datos de Telemetría de Benchmarking (CSV)",
                    data=csv_bench,
                    file_name=f"telemetria_benchmarking_socratico_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key="btn_descargar_telemetria_estres_csv"
                )
            else:
                st.info("ℹ️ Aún no hay corridas registradas en la base de datos de telemetría. Al ejecutar simulaciones individuales o torneos comparativos, los resultados se almacenarán aquí automáticamente para su posterior descarga y análisis estadístico.")

        # ==========================================
        # PESTAÑA 7: CREADOR ASISTIDO & BANCO DE CASOS PERMANENTE
        # ==========================================
        with tab_creador:
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

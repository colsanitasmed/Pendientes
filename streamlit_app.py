import streamlit as st
from PIL import Image
import numpy as np
import easyocr
import re
import requests

st.title("🔍 Carga de Ticket y Envío Automático")

# Configuración del Google Form
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfMsMmOaUhwpD9HQCuKf0Y4Y6oesiUO9GphNb5WMz3ItKKPjg/formResponse"
ENTRY_NUMERO_SOL = "entry.611673084"
ENTRY_PEDIDO = "entry.1680720626"
ENTRY_CODIGO = "entry.832344567"
ENTRY_DESCRIP = "entry.1533087800"
ENTRY_UNIDAD = "entry.728245219"
ENTRY_CANT = "entry.231047139"

# Inicializar OCR una sola vez
@st.cache_resource
def get_reader():
    return easyocr.Reader(['es'], gpu=False)

reader = get_reader()

# Función para extraer texto y campos
def extraer_campos(texto):
    # Texto limpio
    t = texto.replace("\n", " ").replace("  ", " ")

    numero_sol = re.search(r"(?:N[uú]mero de solicitud|Número de solicitud)[:\s\-]*([0-9]{6,12})", t, re.IGNORECASE)
    numero_sol = numero_sol.group(1) if numero_sol else ""

    pedido_pend = re.search(r"(?:Pedido pendiente)[:\s\-]*([0-9]{6,12})", t, re.IGNORECASE)
    pedido_pend = pedido_pend.group(1) if pedido_pend else ""

    codigo = re.search(r"\b([0-9]{4,7})\b", t)
    codigo = codigo.group(1) if codigo else ""

    unidad = re.search(r"\b(Fco|FCO|UND|Tab|CAP|Sol)\b", t)
    unidad = unidad.group(1) if unidad else ""

    cantidad = re.search(r"(?:Cant\.?|Cantidad)[:\s\-]*([0-9]{1,4})", t, re.IGNORECASE)
    cantidad = cantidad.group(1) if cantidad else ""

    descripcion = ""
    if codigo and unidad:
        patron_desc = rf"{codigo}\s+(.+?)\s+{unidad}"
        desc_match = re.search(patron_desc, t, re.IGNORECASE)
        if desc_match:
            descripcion = desc_match.group(1).strip()
    if not descripcion:
        # fallback: puede estar después de “Descripcion” palabra literal
        desc2 = re.search(r"Descr[ií]pcion[:\s\-]*(.+?)\s+(?:Unid|Unidad)", t, re.IGNORECASE)
        if desc2:
            descripcion = desc2.group(1).strip()

    return numero_sol, pedido_pend, codigo, descripcion, unidad, cantidad

# Subir archivo
archivo = st.file_uploader("Sube la imagen del ticket", type=["png", "jpg", "jpeg"])
if archivo:
    image = Image.open(archivo).convert("RGB")
    st.image(image, caption="Imagen cargada", use_column_width=True)

    # OCR
    result = reader.readtext(np.array(image), detail=0, paragraph=True)
    texto = "\n".join(result)

    st.subheader("📝 Texto detectado:")
    st.code(texto)

    # Extraer campos
    numero_sol, pedido_pend, codigo, descripcion, unidad, cantidad = extraer_campos(texto)

    st.subheader("📌 Datos extraídos:")
    st.write("Número Solicitud:", numero_sol or "— vacío —")
    st.write("Pedido Pendiente:", pedido_pend or "— vacío —")
    st.write("Código:", codigo or "— vacío —")
    st.write("Descripción:", descripcion or "— vacío —")
    st.write("Unidad:", unidad or "— vacío —")
    st.write("Cantidad:", cantidad or "— vacío —")

    if st.button("Enviar a Google Sheets"):
        if not any([numero_sol, pedido_pend, codigo, descripcion, unidad, cantidad]):
            st.error("No se detectaron datos válidos. Revisa la imagen o el OCR.")
        else:
            payload = {
                ENTRY_NUMERO_SOL: numero_sol,
                ENTRY_PEDIDO: pedido_pend,
                ENTRY_CODIGO: codigo,
                ENTRY_DESCRIP: descripcion,
                ENTRY_UNIDAD: unidad,
                ENTRY_CANT: cantidad
            }
            try:
                resp = requests.post(FORM_URL, data=payload, timeout=10)
                if resp.status_code == 200:
                    st.success("✔ Datos enviados correctamente.")
                else:
                    st.error(f"Error HTTP {resp.status_code}")
                    st.code(resp.text[:800])
            except Exception as e:
                st.error(f"Error al enviar: {e}")

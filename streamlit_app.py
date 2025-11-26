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
    t = texto.replace("\n", " ").replace("  ", " ")

    # Número de solicitud
    numero_sol = re.search(r"(?:N[uú]mero de solicitud|Número de solicitud)[\s:]*([0-9]{6,12})", t, re.IGNORECASE)
    numero_sol = numero_sol.group(1) if numero_sol else ""

    # Pedido pendiente
    pedido_pend = re.search(r"(?:Pedido pendiente)[\s:]*([0-9]{6,12})", t, re.IGNORECASE)
    pedido_pend = pedido_pend.group(1) if pedido_pend else ""

    # ============================
    #   EXTRAER CÓDIGO REAL
    # ============================
    # Buscar sección "Cod." → código → descripción → unidad → cantidad
    patron_bloque = r"Cod\.?\s+([0-9]{4,8})\s+(.+?)\s+(Fco|FCO|UND|Tab|CAP|Sol)\s+([0-9]{1,3})"
    match = re.search(patron_bloque, t, re.IGNORECASE)

    if match:
        codigo = match.group(1)
        descripcion = match.group(2).strip()
        unidad = match.group(3)
        cantidad = match.group(4)
    else:
        # fallback: por si cambia el formulario
        codigo = ""
        descripcion = ""
        unidad = ""
        cantidad = ""

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

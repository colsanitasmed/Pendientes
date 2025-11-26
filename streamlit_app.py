import streamlit as st
import pytesseract
from PIL import Image
import re
import io

import pytesseract

# IMPORTANTE: ruta para Streamlit Cloud
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

st.title("🔍 Lector OCR Pendientes")

# -------------------------
# FUNCIONES
# -------------------------
def extract_data(text):
    # Limpieza básica
    t = text.replace("\n", " ").replace("  ", " ")

    # 1️⃣ Número de Solicitud
    solicitud = re.search(r"(solicitud|solicltud|solicitud)\s*[:\-]?\s*(\d{6,12})", t, re.IGNORECASE)
    solicitud = solicitud.group(2) if solicitud else ""

    # 2️⃣ Pedido Pendiente
    pedido = re.search(r"(pendiente|pedido pendiente)\s*[:\-]?\s*(\d{6,12})", t, re.IGNORECASE)
    pedido = pedido.group(2) if pedido else ""

    # 3️⃣ Código (línea que inicia con números)
    codigo = re.search(r"\b(\d{5,12})\b\s+[A-Z]", t)
    codigo = codigo.group(1) if codigo else ""

    # 4️⃣ Descripción (línea larga después del código)
    descripcion = ""
    if codigo:
        patron_desc = rf"{codigo}\s+([A-Z0-9].+?)\s+(Fco|Tab|Cap|Sol|Und)"
        desc_match = re.search(patron_desc, t)
        if desc_match:
            descripcion = desc_match.group(1)

    # 5️⃣ Unidad ("Fco", "Tab", "Cap", etc.)
    unidad_match = re.search(r"\b(Fco|Tab|Cap|Sol|Und)\b", t)
    unidad = unidad_match.group(1) if unidad_match else ""

    # 6️⃣ Cantidad (número que sigue a la unidad)
    cantidad = ""
    if unidad:
        cant_match = re.search(rf"{unidad}\s+(\d{{1,3}})", t)
        if cant_match:
            cantidad = cant_match.group(1)

    return solicitud, pedido, codigo, descripcion, unidad, cantidad


# -------------------------
# UI
# -------------------------
uploaded_file = st.file_uploader("📸 Sube la foto o PDF del pendiente", type=["png","jpg","jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Imagen cargada", use_column_width=True)

    # OCR
    raw_text = pytesseract.image_to_string(image)

    # Mostrar OCR crudo
    st.subheader("📄 Texto detectado por OCR")
    st.text(raw_text)

    # Extraer datos
    numero_sol, pedido_pend, cod, des, unidad, cant = extract_data(raw_text)

    st.subheader("📌 Datos extraídos")

    st.write(f"**📌 Número Solicitud:** {numero_sol}")
    st.write(f"**📌 Pedido Pendiente:** {pedido_pend}")
    st.write(f"**📌 Código:** {cod}")
    st.write(f"**📌 Descripción:** {des}")
    st.write(f"**📌 Unidad:** {unidad}")
    st.write(f"**📌 Cantidad:** {cant}")

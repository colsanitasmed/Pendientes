import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import re
import requests

# =============================
#  CONFIGURACIÓN GOOGLE FORM
# =============================
ENTRY_SOLICITUD = "entry.611673084"
ENTRY_PEDIDO = "entry.1680720626"
ENTRY_CODIGO = "entry.832344567"
ENTRY_DESCRIP = "entry.1533087800"
ENTRY_UNIDAD = "entry.728245219"
ENTRY_CANT = "entry.231047139"

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfMsMmOaUhwpD9HQCuKf0Y4Y6oesiUO9GphNb5WMz3ItKKPjg/formResponse"


# =============================
#  OCR READER (CACHEADO)
# =============================
@st.cache_resource
def get_reader():
    return easyocr.Reader(["es"], gpu=False)


# =============================
#  FUNCIONES DE EXTRACCIÓN
# =============================

def extract_numero_solicitud(text):
    m = re.search(r"(?i)n[uú]mero de solicitud\s*(\d+)", text)
    return m.group(1) if m else ""


def extract_pedido_pendiente(text):
    m = re.search(r"(?i)pedido pendiente\s*(\d+)", text)
    return m.group(1) if m else ""


def extract_products(text):
    """
    Extrae código, descripción, unidad y cantidad.
    - Código = número de 5-6 dígitos
    - Unidad = Fco, Tab, Caps, etc.
    - Cantidad = número pequeño (1–3 dígitos)
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    productos = []

    for i, line in enumerate(lines):

        # Código (5-6 dígitos)
        if re.fullmatch(r"\d{5,6}", line):
            codigo = line

            # Descripción = líneas arriba hasta encontrar encabezado
            descripcion = ""
            desc_lines = []
            k = i - 1
            while k >= 0 and not re.search(r"(cod|descrip|unid|cant)", lines[k], re.IGNORECASE):
                if not re.fullmatch(r"\d{5,6}", lines[k]):
                    desc_lines.append(lines[k])
                k -= 1
            desc_lines.reverse()
            descripcion = " ".join(desc_lines).strip()

            # Unidad
            unidad = ""
            for j in range(i + 1, min(i + 5, len(lines))):
                if re.fullmatch(r"(fco|tab|caps?|amp|ml|und)", lines[j], re.IGNORECASE):
                    unidad = lines[j]
                    break

            # Cantidad
            cantidad = ""
            for j in range(i + 1, min(i + 8, len(lines))):
                if re.fullmatch(r"\d{1,3}", lines[j]):
                    cantidad = lines[j]
                    break

            productos.append({
                "codigo": codigo,
                "descripcion": descripcion,
                "unidad": unidad,
                "cantidad": cantidad
            })

    return productos


# =============================
#  INTERFAZ STREAMLIT
# =============================
st.title("📄 OCR Automático de Pendientes")

uploaded = st.file_uploader("Sube la imagen del pendiente", type=["png", "jpg", "jpeg"])

if not uploaded:
    st.stop()

image = Image.open(uploaded).convert("RGB")
st.image(image, caption="Imagen cargada", use_column_width=True)

# OCR
with st.spinner("Procesando OCR con EasyOCR..."):
    reader = get_reader()
    ocr_result = reader.readtext(np.array(image), detail=0, paragraph=False)

text = "\n".join(ocr_result)

st.subheader("📝 Texto detectado:")
st.code(text)

# EXTRAER DATOS
numero_solicitud = extract_numero_solicitud(text)
pedido_pendiente = extract_pedido_pendiente(text)
productos = extract_products(text)

st.subheader("📌 Datos extraídos")
st.write("Número solicitud:", numero_solicitud or "— vacío —")
st.write("Pedido pendiente:", pedido_pendiente or "— vacío —")
st.write(f"Productos detectados: {len(productos)}")

for i, p in enumerate(productos, start=1):
    st.markdown(f"### Producto {i}")
    st.write("Código:", p["codigo"])
    st.write("Descripción:", p["descripcion"])
    st.write("Unidad:", p["unidad"] or "— vacío —")
    st.write("Cantidad:", p["cantidad"] or "— vacío —")
    st.write("---")

# BOTÓN DE ENVÍO
if productos:
    if st.button("📤 Enviar al Google Form"):
        for prod in productos:
            payload = {
                ENTRY_SOLICITUD: numero_solicitud,
                ENTRY_PEDIDO: pedido_pendiente,
                ENTRY_CODIGO: prod["codigo"],
                ENTRY_DESCRIP: prod["descripcion"],
                ENTRY_UNIDAD: prod["unidad"],
                ENTRY_CANT: prod["cantidad"],
            }

            requests.post(FORM_URL, data=payload)

        st.success("✔ Todos los productos fueron enviados correctamente.")
else:
    st.warning("No se detectaron productos en la imagen.")

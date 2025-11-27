import streamlit as st
from PIL import Image
import pytesseract
import re
import io

# -------------------------
# CONFIG STREAMLIT
# -------------------------
st.set_page_config(page_title="OCR Ticket", layout="centered")

# -------------------------
# FUNCIONES
# -------------------------
def extract_text_from_image(file_bytes):
    """Lee correctamente la imagen desde bytes y extrae texto con Tesseract."""
    try:
        image = Image.open(io.BytesIO(file_bytes))

        # Ejecutar OCR
        text = pytesseract.image_to_string(image, lang="spa")
        return text

    except Exception as e:
        st.error(f"Error al ejecutar OCR: {e}")
        return ""


def extract_fields(text):
    """Extrae solicitud, pedido, producto, unidad y cantidad desde el OCR."""

    numero_solicitud = ""
    pedido_pendiente = ""
    codigo = ""
    descripcion = ""
    unidad = ""
    cantidad = ""

    # REGEX (los mismos que ya tenías)
    sol = re.search(r"Solicitud[: ]+(\d+)", text, re.IGNORECASE)
    if sol:
        numero_solicitud = sol.group(1)

    ped = re.search(r"Pedido pendiente[: ]+(\d+)", text, re.IGNORECASE)
    if ped:
        pedido_pendiente = ped.group(1)

    # Codigo (primer número de 5–7 dígitos)
    cod = re.search(r"\b(\d{5,7})\b", text)
    if cod:
        codigo = cod.group(1)

    # Unidad (Fco, Und, Caja)
    uni = re.search(r"\b(Fco|Und|Caja)\b", text, re.IGNORECASE)
    if uni:
        unidad = uni.group(1)

    # Cantidad (último número aislado — mejora final)
    cantidades = re.findall(r"\b(\d{1,3})\b", text)
    if cantidades:
        cantidad = cantidades[-1]

    # Descripción (línea después del código)
    descripcion = ""
    if codigo and codigo in text:
        partes = text.split(codigo)
        if len(partes) > 1:
            # siguiente línea después del código
            descripcion = partes[1].split("\n")[1].strip()

    return numero_solicitud, pedido_pendiente, codigo, descripcion, unidad, cantidad


# -------------------------
# INTERFAZ STREAMLIT
# -------------------------
st.title("📄 Lector de Tickets con OCR")

# 1️⃣ Campo extra solicitado
numero_documento = st.text_input("Número de documento del usuario")

uploaded_file = st.file_uploader("Sube el ticket (imagen)", type=["png", "jpg", "jpeg"])

if uploaded_file:
    # Vista previa (se había perdido)
    st.image(uploaded_file, caption="Ticket cargado", width=350)

    # Leer bytes correctamente
    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()

    # Extraer texto
    text = extract_text_from_image(file_bytes)

    if text.strip() == "":
        st.error("⚠ No se pudo leer el texto. Sube un ticket legible.")
        st.stop()

    # Extraer datos
    sol, ped, cod, desc, uni, cant = extract_fields(text)

    # VALIDACIÓN DE CAMPOS
    if "" in [sol, ped, cod, desc, uni, cant, numero_documento]:
        st.error("⚠ Por favor carga un ticket legible. Faltan datos por extraer.")
        st.stop()

    # Mostrar resultado
    st.subheader("📌 Datos extraídos")
    st.write(f"**Número documento:** {numero_documento}")
    st.write(f"**Número solicitud:** {sol}")
    st.write(f"**Pedido pendiente:** {ped}")
    st.write("---")
    st.write("### Producto")
    st.write(f"**Código:** {cod}")
    st.write(f"**Descripción:** {desc}")
    st.write(f"**Unidad:** {uni}")
    st.write(f"**Cantidad:** {cant}")


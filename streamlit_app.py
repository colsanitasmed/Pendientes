import streamlit as st
import easyocr
from PIL import Image
import numpy as np
import io
import requests

# ------------------ CONFIGURACIÓN OCR ------------------
reader = easyocr.Reader(["es"], gpu=False)

# ------------------ IDS DEL FORMULARIO ------------------
ENTRY_DOCUMENTO = "entry.412830053"      # <-- Ajusta si cambia
ENTRY_SOLICITUD = "entry.611673084"
ENTRY_PEDIDO = "entry.1680720626"
ENTRY_CODIGO = "entry.832344567"
ENTRY_DESCRIP = "entry.1533087800"
ENTRY_UNIDAD = "entry.728245219"
ENTRY_CANT = "entry.231047139"

GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/XXXXXXXX/formResponse"  # <-- Pon el tuyo


# ------------------ FUNCIÓN OCR ------------------
def extract_text_from_image(image_bytes):

    # Abrir imagen
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # Convertir PIL → numpy array (lo que EASYOCR necesita)
    image_np = np.array(image)

    # Procesar OCR
    results = reader.readtext(image_np, detail=0, paragraph=True)

    return "\n".join(results)


# ------------------ PARSEO ------------------
def parse_ticket_text(text: str):

    numero_solicitud = ""
    pedido_pendiente = ""
    codigo = ""
    descripcion = ""
    unidad = ""
    cantidad = ""

    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    # Buscar datos de cabecera
    for i, ln in enumerate(lines):
        if "solicitud" in ln.lower():
            try:
                numero_solicitud = lines[i + 1]
            except:
                pass

        if "pendiente" in ln.lower() and "pedido" in ln.lower():
            try:
                pedido_pendiente = lines[i + 1]
            except:
                pass

    # Buscar bloque de productos
    try:
        idx = lines.index("Cod.")
        block = lines[idx + 1 : idx + 12]

        # Código
        for ln in block:
            if ln.isdigit() and len(ln) >= 5:
                codigo = ln
                break

        # Unidad
        for ln in block:
            if ln.lower().startswith(("fco", "tab", "cap", "ml", "mg")):
                unidad = ln
                break

        # Descripción
        desc_parts = []
        for ln in block:
            if ln not in [codigo, unidad]:
                desc_parts.append(ln)
        descripcion = " ".join(desc_parts)

        # Cantidad = último número
        for ln in reversed(block):
            if ln.isdigit():
                cantidad = ln
                break

    except:
        pass

    return {
        "numero_solicitud": numero_solicitud,
        "pedido_pendiente": pedido_pendiente,
        "codigo": codigo,
        "descripcion": descripcion,
        "unidad": unidad,
        "cantidad": cantidad,
    }


# ------------------ UI STREAMLIT ------------------
st.title("📸 Cargador Automático de Tickets")

# Nuevo campo solicitado
documento = st.text_input("Número de Documento del Usuario")

uploaded_file = st.file_uploader("Subir imagen del ticket", type=["png", "jpg", "jpeg"])


if uploaded_file:

    text = extract_text_from_image(uploaded_file.read())

    parsed = parse_ticket_text(text)

    st.subheader("📌 Datos extraídos")
    st.write(parsed)

    # ------------------ VALIDACIÓN ------------------
    if (
        not documento
        or not parsed["numero_solicitud"]
        or not parsed["pedido_pendiente"]
        or not parsed["codigo"]
        or not parsed["descripcion"]
        or not parsed["unidad"]
        or not parsed["cantidad"]
    ):
        st.error("⚠️ Ticket no legible. Por favor suba una imagen más clara.")
        st.stop()

    # ------------------ ENVÍO AL FORM ------------------
    payload = {
        ENTRY_DOCUMENTO: documento,
        ENTRY_SOLICITUD: parsed["numero_solicitud"],
        ENTRY_PEDIDO: parsed["pedido_pendiente"],
        ENTRY_CODIGO: parsed["codigo"],
        ENTRY_DESCRIP: parsed["descripcion"],
        ENTRY_UNIDAD: parsed["unidad"],
        ENTRY_CANT: parsed["cantidad"],
    }

    if st.button("Enviar datos al formulario"):
        requests.post(GOOGLE_FORM_URL, data=payload)
        st.success("✅ Datos enviados correctamente")

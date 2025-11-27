import streamlit as st
import pytesseract
from PIL import Image
import io
import requests

# ------------------ IDs del formulario ------------------
ENTRY_DOCUMENTO = "entry.412830053"     # AJUSTA ESTE
ENTRY_SOLICITUD = "entry.611673084"
ENTRY_PEDIDO = "entry.1680720626"
ENTRY_CODIGO = "entry.832344567"
ENTRY_DESCRIP = "entry.1533087800"
ENTRY_UNIDAD = "entry.728245219"
ENTRY_CANT = "entry.231047139"

GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/...../formResponse"  # tu URL

# ------------------ Streamlit UI ------------------
st.title("📸 Cargue de Tickets Automático")

# 1️⃣ Campo nuevo solicitado
documento = st.text_input("Número de Documento del Usuario")

uploaded_file = st.file_uploader("Sube la foto del ticket", type=["png","jpg","jpeg"])


# ------------------ Extracción de texto ------------------
def extract_text_from_image(image_bytes):
    image = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(image, lang="spa")
    return text


# ------------------ Extracción de datos ------------------
def extract_data(text):
    lines = text.split("\n")
    clean = [l.strip() for l in lines if l.strip()]

    numero_solicitud = ""
    pedido_pendiente = ""
    codigo = ""
    descripcion = ""
    unidad = ""
    cantidad = ""

    for i, line in enumerate(clean):
        if line.lower().startswith("número de solicitud") or line.lower().startswith("numero de solicitud"):
            numero_solicitud = clean[i+1].strip()
        if line.lower().startswith("pedido pendiente"):
            pedido_pendiente = clean[i+1].strip()

        # Producto
        if clean[i].isdigit() and len(clean[i]) >= 5:  
            codigo = clean[i]
            descripcion = clean[i+1] if i+1 < len(clean) else ""

        if line in ["Fco", "Amp", "Tab", "Caps", "Sob", "Sobre"]:
            unidad = line

        # Cantidad (último número suelto del documento)
        if line.isdigit() and len(line) <= 3:
            cantidad = line

    return {
        "numero_solicitud": numero_solicitud,
        "pedido_pendiente": pedido_pendiente,
        "codigo": codigo,
        "descripcion": descripcion,
        "unidad": unidad,
        "cantidad": cantidad
    }


# ------------------ Enviar datos ------------------
def send_to_google_form(data, documento):
    payload = {
        ENTRY_DOCUMENTO: documento,
        ENTRY_SOLICITUD: data["numero_solicitud"],
        ENTRY_PEDIDO: data["pedido_pendiente"],
        ENTRY_CODIGO: data["codigo"],
        ENTRY_DESCRIP: data["descripcion"],
        ENTRY_UNIDAD: data["unidad"],
        ENTRY_CANT: data["cantidad"],
    }

    requests.post(GOOGLE_FORM_URL, data=payload)


# ------------------ Lógica principal ------------------
if uploaded_file:
    text = extract_text_from_image(uploaded_file.read())
    data = extract_data(text)

    st.subheader("📌 Datos detectados")
    st.write(data)

    # 2️⃣ Validación solicitada
    if st.button("Enviar"):
        if not all([
            documento,
            data["numero_solicitud"],
            data["pedido_pendiente"],
            data["codigo"],
            data["descripcion"],
            data["unidad"],
            data["cantidad"]
        ]):
            st.error("⚠️ No se pudieron extraer todos los datos. Cargue un ticket más legible por favor.")
            st.stop()

        send_to_google_form(data, documento)
        st.success("✅ Datos enviados correctamente.")

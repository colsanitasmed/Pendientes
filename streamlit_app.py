import streamlit as st
import requests
from PIL import Image
import pytesseract
import re

st.title("📄 Cargar Ticket — Enviar a Google Sheets")

# === CONFIGURACIÓN GOOGLE FORM ===
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfMsMmOaUhwpD9HQCuKf0Y4Y6oesiUO9GphNb5WMz3ItKKPjg/formResponse"

ENTRY_NUMERO_SOL = "entry.611673084"
ENTRY_PEDIDO = "entry.1680720626"
ENTRY_CODIGO = "entry.832344567"
ENTRY_DESCRIP = "entry.1533087800"
ENTRY_UNIDAD = "entry.728245219"
ENTRY_CANT = "entry.231047139"

# === SUBIR TICKET ===
archivo = st.file_uploader("Sube el ticket", type=["png", "jpg", "jpeg"])

if archivo:

    st.success("Imagen cargada correctamente")

    # Abrir imagen
    imagen = Image.open(archivo)

    # OCR
    texto = pytesseract.image_to_string(imagen)

    st.subheader("📝 Texto detectado:")
    st.text(texto)

    # === EXTRACCIÓN AUTOMÁTICA ===
    # Número de solicitud
    numero_sol = ""
    m = re.search(r"N[úu]mero de solicitud[: ]+(\S+)", texto, re.IGNORECASE)
    if m:
        numero_sol = m.group(1)

    # Pedido pendiente
    pedido_pend = ""
    m = re.search(r"Pedido pendiente[: ]+(\S+)", texto, re.IGNORECASE)
    if m:
        pedido_pend = m.group(1)

    # Código
    codigo = ""
    m = re.search(r"Cod\.?[ ]+(\S+)", texto, re.IGNORECASE)
    if m:
        codigo = m.group(1)

    # Descripción
    descripcion = ""
    m = re.search(r"Descripci[oó]n[: ]+([A-Za-z0-9 \-\.]+)", texto, re.IGNORECASE)
    if m:
        descripcion = m.group(1).strip()

    # Unidad
    unidad = ""
    m = re.search(r"Unidad[: ]+(\S+)", texto, re.IGNORECASE)
    if m:
        unidad = m.group(1)

    # Cantidad
    cantidad = ""
    m = re.search(r"Cant\.?[ ]+(\S+)", texto, re.IGNORECASE)
    if m:
        cantidad = m.group(1)

    # Mostrar valores extraídos al usuario
    st.subheader("📌 Datos detectados:")
    st.write("Número de solicitud:", numero_sol)
    st.write("Pedido pendiente:", pedido_pend)
    st.write("Código:", codigo)
    st.write("Descripción:", descripcion)
    st.write("Unidad:", unidad)
    st.write("Cantidad:", cantidad)

    # === ENVIAR A GOOGLE SHEETS ===
    if st.button("Enviar a Google Sheets"):

        payload = {
            ENTRY_NUMERO_SOL: numero_sol,
            ENTRY_PEDIDO: pedido_pend,
            ENTRY_CODIGO: codigo,
            ENTRY_DESCRIP: descripcion,
            ENTRY_UNIDAD: unidad,
            ENTRY_CANT: cantidad
        }

        r = requests.post(FORM_URL, data=payload)

        if r.status_code == 200:
            st.success("✔ Datos enviados exitosamente a Google Sheets")
        else:
            st.error("❌ Error al enviar datos")
            st.write(r.text)

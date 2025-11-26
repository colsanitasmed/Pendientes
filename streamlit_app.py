import streamlit as st
import requests
from PIL import Image
import easyocr
import numpy as np
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

# Crear lector OCR
reader = easyocr.Reader(["es"], gpu=False)

archivo = st.file_uploader("Sube el ticket", type=["png", "jpg", "jpeg"])

if archivo:

    img = Image.open(archivo)
    st.success("Imagen cargada con éxito")

    # === OCR ===
    result = reader.readtext(np.array(img), detail=0)
    texto = "\n".join(result)

    st.subheader("📝 Texto detectado:")
    st.text(texto)

    # === EXTRACCIÓN AUTOMÁTICA ===
    numero_sol = re.search(r"[Nn]úmero de solicitud[: ]+(\S+)", texto)
    pedido_pend = re.search(r"Pedido pendiente[: ]+(\S+)", texto)
    codigo = re.search(r"Cod\.?[ ]+(\S+)", texto)
    descripcion = re.search(r"Descripci[oó]n[: ]+(.+)", texto)
    unidad = re.search(r"Unidad[: ]+(\S+)", texto)
    cantidad = re.search(r"Cant\.?[ ]+(\S+)", texto)

    numero_sol = numero_sol.group(1) if numero_sol else ""
    pedido_pend = pedido_pend.group(1) if pedido_pend else ""
    codigo = codigo.group(1) if codigo else ""
    descripcion = descripcion.group(1) if descripcion else ""
    unidad = unidad.group(1) if unidad else ""
    cantidad = cantidad.group(1) if cantidad else ""

    # Mostrar datos detectados
   st.subheader("📌 Verificación de OCR")
st.write("Numero Solicitud:", numero_solicitud)
st.write("Pedido Pendiente:", pedido_pendiente)
st.write("Código:", codigo)
st.write("Descripción:", descripcion)
st.write("Unidad:", unidad)
st.write("Cantidad:", cantidad)

    # === ENVÍO A GOOGLE SHEETS ===
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
            st.success("✔ Datos enviados a Google Sheets")
        else:
            st.error("❌ Error al enviar los datos")
            st.write(r.text)

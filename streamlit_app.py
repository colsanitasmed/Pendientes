import streamlit as st
import requests
import easyocr
from PIL import Image
import numpy as np

# ==============================
# CONFIGURACIÓN
# ==============================

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfMsMmOaUhwpD9HQCuKf0Y4Y6oesiUO9GphNb5WMz3ItKKPjg/formResponse"

# IDS DE TUS CAMPOS DE GOOGLE FORM
ID_SOLICITUD  = "entry.611673084"
ID_PEDIDO     = "entry.1680720626"
ID_CODIGO     = "entry.832344567"
ID_DESCRIP    = "entry.1533087800"
ID_UNIDAD     = "entry.728245219"
ID_CANTIDAD   = "entry.231047139"


# ==============================
# EXTRACTOR DE CAMPOS (NUEVO)
# ==============================

def extraer_campos_ocr(texto):

    import re

    # 1️⃣ Extraer número de solicitud y pedido
    numero_sol = re.search(r"solicitud\s+(\d+)", texto, re.IGNORECASE)
    pedido_pend = re.search(r"pendiente\s+(\d+)", texto, re.IGNORECASE)

    numero_sol = numero_sol.group(1) if numero_sol else ""
    pedido_pend = pedido_pend.group(1) if pedido_pend else ""

    # 2️⃣ Buscar bloque de medicamentos
    patron = r"Cod\.\s*Descripcion\s*Unid\.?\s*Cant\s*([\s\S]+)"
    bloque = re.search(patron, texto, re.IGNORECASE)

    if not bloque:
        return numero_sol, pedido_pend, "", "", "", ""

    bloque = bloque.group(1).strip()

    # Separar líneas útiles
    lineas = [l.strip() for l in bloque.split("\n") if l.strip()]

    # Primera línea → descripción
    descripcion = lineas[0] if len(lineas) > 0 else ""

    # Segunda línea → unidad
    unidad = lineas[1] if len(lineas) > 1 else ""

    # 3️⃣ CANTIDAD y CÓDIGO (DÍGITOS DESPUÉS DE LA UNIDAD)
    cantidad = ""
    codigo = ""

    # Números detectados
    numeros_desc = re.findall(r"\b\d+\b", descripcion)
    numeros_unid = re.findall(r"\b\d+\b", unidad)

    # Código = número grande en la descripción
    for n in numeros_desc:
        if 5 <= len(n) <= 7:
            codigo = n

    # Cantidad = número pequeño en unidad
    for n in numeros_unid:
        if len(n) <= 3:
            cantidad = n

    return numero_sol, pedido_pend, codigo, descripcion, unidad, cantidad


# ==============================
# INTERFAZ STREAMLIT
# ==============================

st.title("📄 Cargue y Lectura Automática de Pendientes")

archivo = st.file_uploader("Subir fotografía del pendiente", type=["png","jpg","jpeg"])

if archivo:

    st.image(archivo, caption="Imagen cargada", use_column_width=True)

    # ==========================
    # OCR EASYOCR
    # ==========================

    st.info("Procesando OCR…")

    reader = easyocr.Reader(["es"], gpu=False)
    image = Image.open(archivo)
    image_np = np.array(image)

    ocr_text = reader.readtext(image_np, detail=0)
    texto_detectado = "\n".join(ocr_text)

    st.subheader("📝 Texto detectado:")
    st.text(texto_detectado)

    # ==========================
    # EXTRAER CAMPOS
    # ==========================

    numero_sol, pedido_pend, codigo, descripcion, unidad, cantidad = extraer_campos_ocr(texto_detectado)

    st.subheader("📌 Datos extraídos:")

    st.write(f"**Número Solicitud:** {numero_sol or '— vacío —'}")
    st.write(f"**Pedido Pendiente:** {pedido_pend or '— vacío —'}")
    st.write(f"**Código:** {codigo or '— vacío —'}")
    st.write(f"**Descripción:** {descripcion or '— vacío —'}")
    st.write(f"**Unidad:** {unidad or '— vacío —'}")
    st.write(f"**Cantidad:** {cantidad or '— vacío —'}")

    # ==========================
    # BOTÓN ENVIAR A GOOGLE FORM
    # ==========================

    if st.button("📨 Enviar a Google Sheets"):

        payload = {
            ID_SOLICITUD: numero_sol,
            ID_PEDIDO: pedido_pend,
            ID_CODIGO: codigo,
            ID_DESCRIP: descripcion,
            ID_UNIDAD: unidad,
            ID_CANTIDAD: cantidad
        }

        resp = requests.post(FORM_URL, data=payload)

        if resp.status_code == 200:
            st.success("Datos enviados correctamente a Google Sheets")
        else:
            st.error("Error al enviar los datos")
            st.write(resp.text)

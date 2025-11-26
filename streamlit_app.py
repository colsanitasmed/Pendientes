import streamlit as st
import easyocr
import re
import requests
from PIL import Image
import numpy as np

# ===============================
#  FUNCIÓN DE EXTRACCIÓN AVANZADA
# ===============================

def extraer_datos(texto):

    # Normalizar texto
    lower = texto.lower()

    # ----------------------------
    # 1. Número de solicitud
    # ----------------------------
    num_sol = None
    m = re.search(r"N[uú]mero de solicitud\s*(\d+)", lower)
    if m:
        num_sol = m.group(1)

    # ----------------------------
    # 2. Pedido pendiente
    # ----------------------------
    pedido = None
    m = re.search(r"Pedido pendiente\s*(\d+)", lower)
    if m:
        pedido = m.group(1)

    lineas = [l.strip() for l in texto.split("\n") if l.strip()]

    # ----------------------------
    # 3. Buscar “Cod.” y extraer el código correcto
    # ----------------------------
    codigo = None
    indice_cod = None

    for i, l in enumerate(lineas):
        if re.search(r"Cod[\.]?$", l.lower()):
            indice_cod = i
            break

    if indice_cod is not None:
        for j in range(indice_cod, min(indice_cod + 5, len(lineas))):
            match = re.search(r"\b(\d{5,6})\b", lineas[j])
            if match:
                codigo = match.group(1)
                break

    # ----------------------------
    # 4. Buscar "Unid." y luego la unidad real
    # ----------------------------
    posibles_unidades = ["FCO", "Fco", "Tab", "CAP", "Amp", "ml", "ML", "G"]

    unidad = None
    indice_unid = None

    for i, l in enumerate(lineas):
        if re.search(r"^unid[\.]?$", l.lower()):
            indice_unid = i
            break

    if indice_unid is not None:
        for j in range(indice_unid + 1, min(indice_unid + 5, len(lineas))):
            if any(u.lower() in lineas[j].lower().split() for u in posibles_unidades):
                unidad = lineas[j]
                break

    # ----------------------------
    # 5. Buscar “Cant” y luego la cantidad real
    # ----------------------------
    cantidad = None
    indice_cant = None

    for i, l in enumerate(lineas):
        if re.search(r"^cant[\.]?$", l.lower()):
            indice_cant = i
            break

    if indice_cant is not None:
        for j in range(indice_cant + 1, min(indice_cant + 4, len(lineas))):
            if re.fullmatch(r"\d{1,3}", lineas[j]):
                cantidad = lineas[j]
                break

    # ----------------------------
    # 6. Descripción = líneas entre código y unidad
    # ----------------------------
    descripcion = None
    if codigo and unidad:
        idx_codigo = next((i for i, l in enumerate(lineas) if codigo in l), None)
        idx_unidad = next((i for i, l in enumerate(lineas) if unidad in l), None)

        if idx_codigo is not None and idx_unidad is not None and idx_unidad > idx_codigo:
            desc_partes = lineas[idx_codigo+1 : idx_unidad]
            descripcion = " ".join(desc_partes).strip()

    return {
        "numero_solicitud": num_sol,
        "pedido_pendiente": pedido,
        "codigo": codigo,
        "descripcion": descripcion,
        "unidad": unidad,
        "cantidad": cantidad,
    }


# ===============================
#  STREAMLIT APP
# ===============================

st.title("📸 OCR Automático para Pendientes")

file = st.file_uploader("Carga la imagen del ticket", type=["png", "jpg", "jpeg"])

if file:
    image = Image.open(file)
    st.image(image, caption="Imagen cargada", use_column_width=True)

    # OCR
    reader = easyocr.Reader(["es"], gpu=False)
    ocr_result = reader.readtext(np.array(image), detail=0)
    texto = "\n".join(ocr_result)

    st.subheader("📝 Texto detectado:")
    st.text(texto)

    # EXTRAER DATOS
    datos = extraer_datos(texto)

    st.subheader("📌 Datos extraídos:")
    st.write(datos)

    # ENVIAR A GOOGLE FORM
    if st.button("📤 Enviar al Formulario"):
        url = "https://docs.google.com/forms/d/e/1FAIpQLSfMsMmOaUhwpD9HQCuKf0Y4Y6oesiUO9GphNb5WMz3ItKKPjg/formResponse"

        payload = {
            "entry.611673084": datos["numero_solicitud"],
            "entry.1680720626": datos["pedido_pendiente"],
            "entry.832344567": datos["codigo"],
            "entry.1533087800": datos["descripcion"],
            "entry.728245219": datos["unidad"],
            "entry.231047139": datos["cantidad"],
        }

        r = requests.post(url, data=payload)

        if r.status_code == 200:
            st.success("Datos enviados correctamente")
        else:
            st.error(f"Error al enviar ({r.status_code})")

import streamlit as st
import easyocr
from PIL import Image
import numpy as np
import requests
import re

st.title("📄 Cargue Automático de Documentos Pendientes")

# ============================
# CONFIG GOOGLE FORM
# ============================

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfMsMmOaUhwpD9HQCuKf0Y4Y6oesiUO9GphNb5WMz3ItKKPjg/formResponse"

ENTRY_NUMERO_SOL = "entry.611673084"
ENTRY_PEDIDO = "entry.1680720626"
ENTRY_CODIGO = "entry.832344567"
ENTRY_DESCRIP = "entry.1533087800"
ENTRY_UNIDAD = "entry.728245219"
ENTRY_CANT = "entry.231047139"

# ============================
#  OCR: Inicializar EasyOCR
# ============================

@st.cache_resource
def load_reader():
    return easyocr.Reader(['es'], gpu=False)

reader = load_reader()

# ============================
#  FUNCIÓN PARA EXTRAER DATOS
# ============================

def extraer_texto(imagen):
    """Devuelve todo el texto detectado por OCR en un solo string."""
    texto = reader.readtext(imagen, detail=0, paragraph=True)
    return "\n".join(texto)

def buscar_patron(texto, patron, descripcion=""):
    """Búsqueda segura por regex."""
    m = re.search(patron, texto, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return ""

def extraer_campos(texto):
    """Extrae los campos basados en el formato de tu ticket"""

    numero_sol = buscar_patron(texto, r"N[uú]mero de solicitud[: ]+(\d+)")
    pedido_pend = buscar_patron(texto, r"Pedido pendiente[: ]+(\d+)")
    codigo = buscar_patron(texto, r"Cod\.?\s*[: ]+(\d+)")
    unidad = buscar_patron(texto, r"Unidad[: ]+([A-Za-z]+)")
    cantidad = buscar_patron(texto, r"Cant\.?\s*[: ]+(\d+)")
    descripcion = ""

    # La descripción casi siempre es la línea más larga
    lineas = texto.split("\n")
    if lineas:
        descripcion = max(lineas, key=len).strip()

    return numero_sol, pedido_pend, codigo, descripcion, unidad, cantidad


# ============================
#  SUBIR ARCHIVO
# ============================

archivo = st.file_uploader("Sube el archivo (imagen)", type=["png", "jpg", "jpeg"])

if archivo:
    st.image(archivo, caption="Documento cargado", use_column_width=True)

    imagen = Image.open(archivo)
    imagen_np = np.array(imagen)

    # EXTRAER TEXTO GENERAL
    texto = extraer_texto(imagen_np)

    st.subheader("📄 Texto detectado por OCR")
    st.code(texto)

    # EXTRAER CAMPOS
    numero_sol, pedido_pend, codigo, descripcion, unidad, cantidad = extraer_campos(texto)

    st.subheader("📌 Datos extraídos")
    st.write("📌 Número Solicitud:", numero_sol)
    st.write("📌 Pedido Pendiente:", pedido_pend)
    st.write("📌 Código:", codigo)
    st.write("📌 Descripción:", descripcion)
    st.write("📌 Unidad:", unidad)
    st.write("📌 Cantidad:", cantidad)

    # ============================
    #  BOTÓN PARA ENVIAR AL FORM
    # ============================

    if st.button("Enviar a Google Sheets"):

        # Validación básica
        if not any([numero_sol, pedido_pend, codigo, descripcion, unidad, cantidad]):
            st.error("⚠ No se detectaron datos. Revisa la imagen o mejora el OCR.")
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
                resp = requests.post(FORM_URL, data=payload)
                if resp.status_code == 200:
                    st.success("✔ Datos enviados correctamente a Google Sheets.")
                else:
                    st.error(f"Error HTTP {resp.status_code}")
                    st.code(resp.text[:1000])
            except Exception as e:
                st.error(f"Error al enviar: {e}")

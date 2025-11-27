import streamlit as st
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import re
import tempfile
import os

st.title("Extractor OCR de Medicamentos")

# =====================================================================
# FUNCIÓN PARA EXTRAER TEXTO
# =====================================================================
def extraer_texto(ruta):
    imagen = Image.open(ruta)
    texto = pytesseract.image_to_string(imagen, lang="spa")
    return texto

# =====================================================================
# PROCESAR DOCUMENTO (PDF o imagen)
# =====================================================================
def procesar_documento(archivo):

    # Guardar archivo temporalmente
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(archivo.read())
        tmp_path = tmp.name

    ext = archivo.name.lower().split(".")[-1]

    texto_total = ""

    if ext == "pdf":
        paginas = convert_from_path(tmp_path)
        for i, pag in enumerate(paginas):
            img_temp = f"{tmp_path}_{i}.png"
            pag.save(img_temp, "PNG")
            texto_total += "\n" + extraer_texto(img_temp)
    else:
        texto_total = extraer_texto(tmp_path)

    # ----------------------------------------------------------
    # 1. Número solicitud
    num_solicitud = None
    m = re.search(r"(solicitud|num(?:ero)?)\s*[: ]+(\d+)", texto_total, re.IGNORECASE)
    if m:
        num_solicitud = m.group(2)

    # ----------------------------------------------------------
    # 2. Pedido pendiente
    pedido_pend = None
    p = re.search(r"(pedido pendiente|pendiente)\s*[: ]+(\d+)", texto_total, re.IGNORECASE)
    if p:
        pedido_pend = p.group(2)

    # ----------------------------------------------------------
    # 3. PRODUCTOS
    patron_producto = re.compile(
        r"(?P<codigo>\d{5,7})\s+"
        r"(?P<descripcion>[A-Z0-9 \-\+\(\)\/]+?)\s+"
        r"(?P<unidad>[A-Z]{2,4})",
        re.IGNORECASE
    )

    productos = []

    for match in patron_producto.finditer(texto_total):

        codigo = match.group("codigo")
        descripcion = match.group("descripcion").s

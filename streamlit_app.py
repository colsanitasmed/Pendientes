import streamlit as st
import requests
from PIL import Image
import easyocr
import numpy as np
import re

# ---------- CONFIG ----------
FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSfMsMmOaUhwpD9HQCuKf0Y4Y6oesiUO9GphNb5WMz3ItKKPjg/formResponse"
)

ENTRY_NUMERO_SOL = "entry.611673084"
ENTRY_PEDIDO = "entry.1680720626"
ENTRY_CODIGO = "entry.832344567"
ENTRY_DESCRIP = "entry.1533087800"
ENTRY_UNIDAD = "entry.728245219"
ENTRY_CANT = "entry.231047139"

st.set_page_config(page_title="Carga de Tickets", layout="centered")

st.title("📄 Cargar Ticket — Enviar a Google Sheets (Automático)")

# Inicializar lector EasyOCR (puede tardar unos segundos la primera vez)
@st.cache_resource
def get_reader():
    return easyocr.Reader(["es"], gpu=False)

reader = get_reader()

# Subida
archivo = st.file_uploader("Sube el ticket (PNG/JPG/JPEG)", type=["png", "jpg", "jpeg"])

if archivo is not None:
    try:
        image = Image.open(archivo).convert("RGB")
    except Exception as e:
        st.error("No se pudo abrir la imagen: " + str(e))
        st.stop()

    st.image(image, caption="Ticket cargado", use_column_width=True)

    with st.spinner("Ejecutando OCR..."):
        # easyocr devuelve lista de textos detectados si detail=0
        ocr_result = reader.readtext(np.array(image), detail=0)
        texto = "\n".join(ocr_result)

    st.subheader("📝 Texto detectado por OCR")
    st.code(texto, language="")

    # ----------------- Extracción (ajustar si tu ticket tiene pequeñas variaciones) -----------------
    # Buscamos patrones robustos (ignorando mayúsculas/minúsculas y espacios)
    def buscar_regex(pattern, txt, flags=re.IGNORECASE):
        m = re.search(pattern, txt, flags)
        return m.group(1).strip() if m else ""

    # Número de solicitud (buscamos números largos)
    numero_sol = buscar_regex(r"(?:N[úu]mero de solicitud|Número de solicitud|Número Solicitud|No\. solicitud)[:\s\-]*([0-9]{6,})", texto)
    if not numero_sol:
        # fallback: si aparece una línea que solo contiene el número y ya lo vimos en tus ejemplos
        numero_sol = buscar_regex(r"(^|\n)\s*([0-9]{6,})\s*($|\n)", texto)

    pedido_pend = buscar_regex(r"(?:Pedido pendiente|PedidoPendiente|Pedido pendiente[:\s\-]*)[:\s\-]*([0-9]{6,})", texto)
    if not pedido_pend:
        pedido_pend = numero_sol  # en tu ejemplo son iguales; dejar como fallback

    codigo = buscar_regex(r"(?:Cod\.?|Código|Cod)[:\s\-]*([0-9]{4,7})", texto)
    if not codigo:
        # buscar un código numérico aislado (6 dígitos)
        codigo = buscar_regex(r"\b([0-9]{6})\b", texto)

    # Descripción: texto largo entre código y unidad (fallback a buscar "Descripción")
    descripcion = buscar_regex(r"Descripci[oó]n[:\s\-]*([A-Za-z0-9 \-\.,\(\)\+\/]+)", texto)
    if not descripcion and codigo:
        # intentar extraer la porción entre el código y la unidad identificada
        unidad_tmp = buscar_regex(r"\b(FCO|UND|TAB|CAP|ML|MG)\b", texto)
        if unidad_tmp:
            pattern_desc_between = fr"{codigo}\s*(.+?)\s*{unidad_tmp}"
            descripcion = buscar_regex(pattern_desc_between, texto, flags=re.IGNORECASE)

    unidad = buscar_regex(r"\b(FCO|UND|TAB|CAP|ML|MG)\b", texto)
    cantidad = buscar_regex(r"(?:Cant\.?|Cantidad|Cant)[:\s\-]*([0-9]+)", texto)
    if not cantidad:
        # si no se encuentra, buscar número al final de la línea que contenga unidad
        m = re.search(rf"{unidad}\s*[xX]?\s*([0-9]+)\b", texto) if unidad else None
        if m:
            cantidad = m.group(1)

    # Normalizar valores (quitar saltos extra)
    def limpia(x):
        return x.replace("\n", " ").strip() if isinstance(x, str) else ""

    numero_sol = limpia(numero_sol)
    pedido_pend = limpia(pedido_pend)
    codigo = limpia(codigo)
    descripcion = limpia(descripcion)
    unidad = limpia(unidad)
    cantidad = limpia(cantidad)

    # Mostrar resultados detectados (verificación)
    st.subheader("🔎 Valores extraídos (verifica antes de enviar)")
    st.write("Número de solicitud:", numero_sol or "— vacío —")
    st.write("Pedido pendiente:", pedido_pend or "— vacío —")
    st.write("Código:", codigo or "— vacío —")
    st.write("Descripción:", descripcion or "— vacío —")
    st.write("Unidad:", unidad or "— vacío —")
    st.write("Cantidad:", cantidad or "— vacío —")

    # Botón de envío (sólo si hay al menos un campo no vacío)
    if st.button("Enviar a Google Sheets (via Google Form)"):
        # si todos vacíos, no enviar
        if not any([numero_sol, pedido_pend, cod]()

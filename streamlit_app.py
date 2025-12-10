import streamlit as st
import easyocr
import numpy as np
import requests
from PIL import Image
import re

# ---------------------------------------------
# CONFIGURACIÓN GOOGLE FORM
# ---------------------------------------------
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfMsMmOaUhwpD9HQCuKf0Y4Y6oesiUO9GphNb5WMz3ItKKPjg/formResponse"

ENTRY_SOLICITUD = "entry.611673084"
ENTRY_PEDIDO = "entry.1680720626"
ENTRY_CODIGO = "entry.832344567"
ENTRY_DESCRIP = "entry.1533087800"
ENTRY_UNIDAD = "entry.728245219"
ENTRY_CANT = "entry.231047139"
ENTRY_DOC = "entry.412830053"

# ---------------------------------------------
# Cargar OCR (EasyOCR)
# ---------------------------------------------
@st.cache_resource
def load_reader():
    return easyocr.Reader(["es"], gpu=False)


# ---------------------------------------------
# EXTRACTOR DE PRODUCTOS (robusto, sin "acumulación")
# - intenta encontrar DESCRIPCION preferiblemente "después" del código
# - si no hay, recoge líneas "antes"
# - devuelve lista de dicts independientes (no referencias compartidas)
# ---------------------------------------------
def extract_products(text):
    # normalizar líneas
    raw_lines = [l.strip() for l in text.split("\n") if l.strip()]
    lines = raw_lines[:]  # copia explícita
    productos = []
    patron_codigo = re.compile(r"^\d{5,7}$")

    # función auxiliar: limpiar/normalizar una línea
    def clean_line(s):
        return re.sub(r"\s{2,}", " ", s).strip()

    for idx, ln in enumerate(lines):
        if patron_codigo.fullmatch(ln):
            codigo = ln.strip()

            # ----------------------------
            # Toma descripción PREFERENTE: líneas después del código (si tienen texto útil)
            # ----------------------------
            desc_after = []
            j = idx + 1
            max_after = 6  # hasta 6 líneas después
            while j < len(lines) and max_after > 0:
                l = lines[j]
                # detener si aparece otro código o una etiqueta clara
                if patron_codigo.fullmatch(l) or re.search(r"(solicitud|pedido|pendiente|cod|cantidad|cantidad:|cant|unidad)", l, re.I):
                    break
                # si la línea es solo números largos (doc/telefono) romper
                if re.fullmatch(r"\d{7,12}", l):
                    break
                desc_after.append(l)
                j += 1
                max_after -= 1

            desc_after = [clean_line(x) for x in desc_after if x.strip()]

            # ----------------------------
            # Si no hay descripción después, intenta antes (agregado para casos antiguos)
            # ----------------------------
            desc_before = []
            k = idx - 1
            max_before = 4
            while k >= 0 and max_before > 0:
                l = lines[k]
                if patron_codigo.fullmatch(l) or re.search(r"(solicitud|pedido|pendiente|cod|cantidad|cantidad:|cant|unidad)", l, re.I):
                    break
                if re.fullmatch(r"\d{7,12}", l):
                    break
                desc_before.insert(0, l)  # insert front to preserve order
                k -= 1
                max_before -= 1
            desc_before = [clean_line(x) for x in desc_before if x.strip()]

            # ----------------------------
            # Selección: preferir after si tiene contenido, sino before
            # ----------------------------
            descripcion = ""
            if desc_after:
                descripcion = " ".join(desc_after)
            elif desc_before:
                descripcion = " ".join(desc_before)
            else:
                descripcion = ""  # quedará vacío si no hay nada

            descripcion = descripcion.strip()

            # ----------------------------
            # Detectar unidad (buscar cerca del código)
            # ----------------------------
            unidad = ""
            unidad_idx = None
            for jj in range(idx + 1, min(idx + 6, len(lines))):
                candidate = lines[jj].lower()
                if re.search(r"\b(fco|frasco|tab|tableta|caps?|amp|ml|mg|und|unidad)\b", candidate, re.I):
                    unidad = lines[jj].strip()
                    unidad_idx = jj
                    break

            # ----------------------------
            # Detectar cantidad (buscar inmediatamente después de unidad o en las próximas líneas)
            # ----------------------------
            cantidad = ""
            search_from = idx + 1 if unidad_idx is None else unidad_idx + 1
            for jj in range(search_from, min(search_from + 6, len(lines))):
                nums = re.findall(r"\b(\d{1,3})\b", lines[jj])
                if nums:
                    cantidad = nums[-1]
                    break

            # crear dict independiente (no referencias compartidas)
            prod = {
                "codigo": codigo,
                "descripcion": descripcion,
                "unidad": unidad,
                "cantidad": cantidad
            }

            productos.append(prod)

    return productos


# ---------------------------------------------
# UI y flujo principal
# ---------------------------------------------
st.set_page_config(page_title="OCR Pendientes", layout="centered")
st.title("📄 OCR de Tickets de Pendientes — Versión estable")

# input documento
num_doc = st.text_input("Número de Documento del Usuario", value="")

# subir imagen
uploaded = st.file_uploader("Sube la imagen del ticket", type=["png", "jpg", "jpeg"])

if not uploaded:
    st.info("Sube una imagen para procesar.")
    st.stop()

image = Image.open(uploaded).convert("RGB")
st.image(image, caption="Imagen cargada", use_column_width=True)

# ejecutar OCR
reader = load_reader()
with st.spinner("Ejecutando OCR..."):
    img_np = np.array(image)
    lines = reader.readtext(img_np, detail=0, paragraph=False)

ocr_text = "\n".join(lines)

# mostrar debug de líneas (útil para ajustar)
st.subheader("Texto detectado (líneas OCR)")
for i, L in enumerate(lines, start=1):
    st.write(f"{i:02d} | {L}")

# extraer productos con la función robusta
productos = extract_products(ocr_text)

# extraer solicitud/pedido
m1 = re.search(r"solicitud\s*(\d{4,12})", ocr_text, re.IGNORECASE)
num_sol = m1.group(1) if m1 else ""
m2 = re.search(r"pendiente\s*(\d{4,12})", ocr_text, re.IGNORECASE)
num_ped = m2.group(1) if m2 else ""

st.subheader("Datos iniciales detectados")
st.write("Número solicitud:", num_sol or "— vacío —")
st.write("Pedido pendiente:", num_ped or "— vacío —")
st.write("Documento usuario (input):", num_doc or "— vacío —")
st.write(f"Productos detectados: {len(productos)}")

# Si no detectó productos, mostrar formulario para agregar
if not productos:
    st.warning("No se detectaron productos. Agrega manualmente.")
    with st.form("add_manual_single", clear_on_submit=True):
        c = st.text_input("Código", key="manual_cod")
        d = st.text_input("Descripción", key="manual_desc")
        u = st.text_input("Unidad", key="manual_und")
        q = st.text_input("Cantidad", key="manual_cant")
        add = st.form_submit_button("➕ Agregar producto manual")
    if add:
        if c.strip() and d.strip():
            productos.append({"codigo": c.strip(), "descripcion": d.strip(), "unidad": u.strip(), "cantidad": q.strip()})
            st.success("Producto agregado manualmente.")
        else:
            st.error("Código y descripción son obligatorios para agregar manualmente.")

# Mostrar productos con keys únicos y opción eliminar
st.subheader("Revisa y corrige los productos detectados")
productos_final = []
for i, p in enumerate(productos):
    st.markdown(f"### Producto {i+1}")
    # columnas: datos y controles
    cols = st.columns([4, 1])
    with cols[0]:
        codigo = st.text_input(f"Código_{i}", value=p.get("codigo", ""), key=f"codigo_{i}")
        descripcion = st.text_area(f"Descripcion_{i}", value=p.get("descripcion", ""), key=f"desc_{i}", height=80)
        unidad = st.text_input(f"Unidad_{i}", value=p.get("unidad", ""), key=f"und_{i}")
        cantidad = st.text_input(f"Cantidad_{i}", value=p.get("cantidad", ""), key=f"cant_{i}")
    with cols[1]:
        eliminar = st.checkbox("❌ Quitar", key=f"del_{i}")
    if not eliminar:
        productos_final.append({
            "codigo": codigo.strip(),
            "descripcion": descripcion.strip(),
            "unidad": unidad.strip(),
            "cantidad": cantidad.strip()
        })

# opción para agregar más productos en lote
st.markdown("---")
with st.form("add_batch", clear_on_submit=True):
    new_cod = st.text_input("Nuevo Código", key="newcod")
    new_desc = st.text_input("Nueva Descripción", key="newdesc")
    new_und = st.text_input("Nueva Unidad", key="newund")
    new_cant = st.text_input("Nueva Cantidad", key="newcant")
    addb = st.form_submit_button("➕ Agregar producto extra")
if addb:
    if new_cod.strip() and new_desc.strip():
        productos_final.append({
            "codigo": new_cod.strip(),
            "descripcion": new_desc.strip(),
            "unidad": new_und.strip(),
            "cantidad": new_cant.strip()
        })
        st.success("Producto extra agregado.")
    else:
        st.error("Código y descripción son obligatorios para agregar.")

# Validaciones finales
if not num_doc:
    st.warning("Falta número de documento del usuario.")
if not num_sol:
    st.warning("Falta número de solicitud detectado (completa si lo sabes).")
if not num_ped:
    st.warning("Falta número de pedido pendiente detectado (completa si lo sabes).")

if st.button("📤 Enviar productos al Google Sheet"):
    # comprobaciones
    if not num_doc or not num_sol or not num_ped:
        st.error("Completa Documento / Solicitud / Pedido antes de enviar.")
    elif not productos_final:
        st.error("No hay productos para enviar.")
    else:
        enviados = 0
        errores = 0
        for p in productos_final:
            payload = {
                ENTRY_SOLICITUD: num_sol,
                ENTRY_PEDIDO: num_ped,
                ENTRY_CODIGO: p["codigo"],
                ENTRY_DESCRIP: p["descripcion"],
                ENTRY_UNIDAD: p["unidad"],
                ENTRY_CANT: p["cantidad"],
                ENTRY_DOC: num_doc
            }
            try:
                requests.post(FORM_URL, data=payload, timeout=10)
                enviados += 1
            except Exception as e:
                errores += 1
                st.write(f"Error enviando {p.get('codigo','')}: {e}")
        st.success(f"Se enviaron {enviados} productos. Errores: {errores}")


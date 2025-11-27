# =====================================================================
# IMPORTAR LIBRERÍAS
# =====================================================================
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import re
import os

# Ruta de tesseract (solo si es Windows)
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# =====================================================================
# FUNCIÓN PARA CARGAR PDF O IMAGEN
# =====================================================================
def cargar_imagen_o_pdf(ruta):
    ext = ruta.lower().split(".")[-1]

    if ext == "pdf":
        pages = convert_from_path(ruta)
        rutas = []
        for i, page in enumerate(pages):
            img_ruta = f"pagina_temp_{i}.png"
            page.save(img_ruta, "PNG")
            rutas.append(img_ruta)
        return rutas
    else:
        return [ruta]


# =====================================================================
# FUNCIÓN PARA EXTRAER TEXTO
# =====================================================================
def extraer_texto(ruta):
    imagen = Image.open(ruta)
    texto = pytesseract.image_to_string(imagen, lang="spa")
    return texto


# =====================================================================
# PROCESAMIENTO OCR PRINCIPAL
# =====================================================================
def procesar_documento(ruta_archivo):

    rutas_imagenes = cargar_imagen_o_pdf(ruta_archivo)

    texto_total = ""
    for r in rutas_imagenes:
        texto_total += "\n" + extraer_texto(r)

    # ----------------------------------------------------------
    # 1. Número solicitud
    num_solicitud = None
    m = re.search(r"(solicitud|solicit(?:ud)?)[: ]+(\d+)", texto_total, re.IGNORECASE)
    if m:
        num_solicitud = m.group(2)

    # ----------------------------------------------------------
    # 2. Pedido pendiente
    pedido_pend = None
    p = re.search(r"(pendiente|pedido pendiente)[: ]+(\d+)", texto_total, re.IGNORECASE)
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
        descripcion = match.group("descripcion").strip()
        unidad = match.group("unidad").strip()

        # Buscar cantidad independiente después del bloque
        indice_fin = match.end()
        texto_posterior = texto_total[indice_fin:indice_fin + 80]

        cantidad_match = re.search(r"\b(\d{1,4})\b", texto_posterior)
        cantidad = cantidad_match.group(1) if cantidad_match else ""

        productos.append({
            "codigo": codigo,
            "descripcion": descripcion,
            "unidad": unidad,
            "cantidad": cantidad
        })

    return num_solicitud, pedido_pend, productos


# =====================================================================
# FUNCIÓN: BOTÓN CARGAR ARCHIVO
# =====================================================================
def cargar_archivo():
    ruta = filedialog.askopenfilename(
        title="Selecciona una imagen o PDF",
        filetypes=[("Archivos imagen", "*.png;*.jpg;*.jpeg"), ("PDF", "*.pdf")]
    )

    if not ruta:
        return

    txtRuta.delete(0, tk.END)
    txtRuta.insert(0, ruta)

    num_sol, ped_pend, productos = procesar_documento(ruta)

    # Llenar entries
    txtSolicitud.delete(0, tk.END)
    txtSolicitud.insert(0, num_sol if num_sol else "")

    txtPendiente.delete(0, tk.END)
    txtPendiente.insert(0, ped_pend if ped_pend else "")

    # Limpiar tabla
    for item in tabla.get_children():
        tabla.delete(item)

    # Agregar productos a la tabla
    for i, prod in enumerate(productos, start=1):
        tabla.insert("", tk.END, values=(
            i,
            prod["codigo"],
            prod["descripcion"],
            prod["unidad"],
            prod["cantidad"]
        ))


# =====================================================================
# INTERFAZ TKINTER
# =====================================================================
root = tk.Tk()
root.title("Extractor OCR de Medicamentos")
root.geometry("900x600")

# ------- RUTA --------
tk.Label(root, text="Archivo:").pack()
txtRuta = tk.Entry(root, width=80)
txtRuta.pack()

btCargar = tk.Button(root, text="Cargar archivo", command=cargar_archivo)
btCargar.pack(pady=10)

# ------- DATOS GENERALES --------
frameDatos = tk.Frame(root)
frameDatos.pack(pady=10)

tk.Label(frameDatos, text="Número Solicitud: ").grid(row=0, column=0)
txtSolicitud = tk.Entry(frameDatos, width=20)
txtSolicitud.grid(row=0, column=1)

tk.Label(frameDatos, text="Pedido Pendiente: ").grid(row=1, column=0)
txtPendiente = tk.Entry(frameDatos, width=20)
txtPendiente.grid(row=1, column=1)

# ------- TABLA DE PRODUCTOS --------
tk.Label(root, text="Productos Detectados:").pack()

columnas = ("#", "Código", "Descripción", "Unidad", "Cantidad")

tabla = ttk.Treeview(root, columns=columnas, show="headings", height=12)
for col in columnas:
    tabla.heading(col, text=col)
    tabla.column(col, width=150)

tabla.pack(pady=10, fill="both", expand=True)

root.mainloop()

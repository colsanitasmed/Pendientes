import re

def extraer_datos(texto):
    # ---------------------------
    # 1️⃣ Número de Solicitud
    # ---------------------------
    num_sol = re.search(r'Número de solicitud\s*(\d+)', texto, re.IGNORECASE)
    numero_solicitud = num_sol.group(1) if num_sol else None

    # ---------------------------
    # 2️⃣ Pedido pendiente
    # ---------------------------
    ped_pen = re.search(r'Pedido pendiente\s*(\d+)', texto, re.IGNORECASE)
    pedido_pendiente = ped_pen.group(1) if ped_pen else None

    # ----------------------------------------------------
    # 3️⃣ Extraer bloque después de DETALLE DE PENDIENTE
    # ----------------------------------------------------
    bloque_match = re.search(
        r'Detalle de Pendiente(.*)',
        texto,
        re.IGNORECASE | re.DOTALL
    )

    if not bloque_match:
        return {
            "numero_solicitud": numero_solicitud,
            "pedido_pendiente": pedido_pendiente,
            "productos": []
        }

    bloque = bloque_match.group(1)

    # limpiar líneas vacías
    lineas = [l.strip() for l in bloque.split("\n") if l.strip()]

    # ----------------------------------------------------
    # 4️⃣ Buscar líneas que sean códigos (4–8 dígitos)
    # ----------------------------------------------------
    indices_codigos = []
    for i, linea in enumerate(lineas):
        if re.fullmatch(r'\d{4,8}', linea):
            indices_codigos.append(i)

    productos = []

    # ----------------------------------------------------
    # 5️⃣ Procesar cada producto encontrado
    # ----------------------------------------------------
    for idx, pos_codigo in enumerate(indices_codigos):
        codigo = lineas[pos_codigo]

        # Descripción = desde la línea después de encabezados hasta antes del código
        inicio_desc = 0
        # buscar palabra "Cant" o similar
        for j, l in enumerate(lineas):
            if re.search(r'^Cant$', l, re.IGNORECASE):
                inicio_desc = j + 1
                break

        # descripción entre inicio_desc y pos_codigo
        descripcion = " ".join(lineas[inicio_desc:pos_codigo])

        # Unidad = línea después del código
        unidad = None
        if pos_codigo + 1 < len(lineas):
            unidad = lineas[pos_codigo + 1]

        # Cantidad = primera línea que sea número pequeño (>1 y <9999)
        cantidad = None
        for l in lineas[pos_codigo:]:
            if re.fullmatch(r'\d{1,4}', l):
                if l not in [numero_solicitud, pedido_pendiente, codigo]:
                    cantidad = l
                    break

        productos.append({
            "codigo": codigo,
            "descripcion": descripcion,
            "unidad": unidad,
            "cantidad": cantidad
        })

    # ----------------------------------------------------
    # Resultado final
    # ----------------------------------------------------
    return {
        "numero_solicitud": numero_solicitud,
        "pedido_pendiente": pedido_pendiente,
        "productos": productos
    }


# ------------------------------
# EJEMPLO DE PRUEBA
# ------------------------------

texto = """
Lineas de servicio al Cliente
Bogcta (031) 4430200
Resto dei Pals: 01-8000-99999
Número de solicitud
323993706
Pedido pendiente
323893706
Atendido por
Detalle de Pendiente
Cod.
Descripcion
Unid.
Cant
PREP MAG CANNABIDIOL
(CBD)+TETRAHIDROCANNABIDIO
391092
Fco
6
Otro producto ejemplo
Descripcion larga
553210
Amp
2
"""

resultado = extraer_datos(texto)
print(resultado)

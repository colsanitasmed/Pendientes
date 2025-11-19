import streamlit as st
import requests
import datetime

st.title("📄 Cargue de Documentos Pendientes")

# URL de tu WebApp de Apps Script
API_URL = "https://script.google.com/macros/s/AKfycbwIH-E6KaiQzKMIiagOPrKtkSO6cC0lcVGueC-71VtNgEL0QeUCBBbbQGxnAkyG4cGKww/exec"  # <-- reemplaza esto

# 1. Tipo de documento
tipo = st.selectbox("Tipo de Documento", ["PDF", "JPG", "PNG", "Otros"])

# 2. Cargar archivo
archivo = st.file_uploader("Cargar Documento", type=None)

# 3. Datos a capturar
st.subheader("Datos del Documento")
documento_usuario = st.text_input("Documento del Usuario")
fecha_cargue = st.date_input("Fecha del cargue", datetime.date.today())
numero_solicitud = st.text_input("Número de Solicitud")
pedido_pendiente = st.text_input("Pedido pendiente")
codigo = st.text_input("Cod.")
descripcion = st.text_input("Descripción")
unidad = st.text_input("Unid.")
cantidad = st.number_input("Cant.", min_value=0, step=1)

# 4. Enviar a Google Sheets + Email
if st.button("Enviar"):
    if archivo is None:
        st.error("Debes cargar un archivo.")
    else:
        # Datos a enviar
        data = {
            "tipo": tipo,
            "documento_usuario": documento_usuario,
            "fecha_cargue": str(fecha_cargue),
            "numero_solicitud": numero_solicitud,
            "pedido_pendiente": pedido_pendiente,
            "codigo": codigo,
            "descripcion": descripcion,
            "unidad": unidad,
            "cantidad": cantidad,
            "nombre_archivo": archivo.name,
        }

        # Enviar JSON a Apps Script
        response = requests.post(API_URL, json=data)

        if response.status_code == 200:
            st.success("Datos enviados correctamente 👍")
        else:
            st.error("Error al enviar datos a Google Apps Script.")
            st.write(response.text)

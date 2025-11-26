import streamlit as st
import requests
import datetime
import base64

st.title("📄 Cargue de Documentos Pendientes")

API_URL = "https://script.google.com/macros/s/AKfycbxQSUoJWxwwkaRDKfbF22FNZ7cmE9_MGXb9kESnHeoLoV0Psc1yUwxpy40m8dfhJkRy/exec"

# Subida de archivo
archivo = st.file_uploader("Cargar Documento")

if archivo:
    st.success("Archivo listo para procesar")

    # Convertir archivo a Base64 (Apps Script sí recibe esto)
    contenido_b64 = base64.b64encode(archivo.getvalue()).decode("utf-8")

    if st.button("Enviar"):

        # Datos adicionales que enviamos a Google Apps Script
        data = {
            "FechaCarga": str(datetime.date.today()),
            "DocumentoPaciente": "",
            "NumeroSolicitud": "",
            "PedidoPendiente": "",
            "Codigo": "",
            "Descripcion": "",
            "Unid": "",
            "Cant": "",
            "filename": archivo.name,
            "filedata": contenido_b64
        }

        # Envío POST normal (NO MULTIPART)
        response = requests.post(API_URL, data=data)

        # Mostrar respuesta del servidor
        try:
            st.json(response.json())
        except:
            st.error("La API devolvió algo que no es JSON")
            st.write(response.text)

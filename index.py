import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
import io

# 🗂️ Carpeta donde están los archivos de asistencia
CARPETA_ONEDRIVE = r"C:\Users\JulioRodriguez\OneDrive - InterAmerican Technical Institute\Attendance"

# 📋 Lista maestra de residentes (ajustá el nombre del archivo si es distinto)
ARCHIVO_RESIDENTES = "residentes.csv"

def cargar_lista_residentes():
    path_residentes = os.path.join(CARPETA_ONEDRIVE, ARCHIVO_RESIDENTES)
    return pd.read_csv(path_residentes)

def buscar_archivos_asistencia(fecha_str, tipo="Tarde"):
    patron = f"*{tipo}*{fecha_str}*.csv"
    ruta = os.path.join(CARPETA_ONEDRIVE, patron)
    archivos = glob.glob(ruta)
    return archivos

def combinar_asistencias(archivos):
    dfs = []
    for archivo in archivos:
        try:
            df = pd.read_csv(archivo)
            dfs.append(df)
        except:
            st.warning(f"No se pudo leer: {archivo}")
    if dfs:
        return pd.concat(dfs).drop_duplicates(subset=["nombre"])
    else:
        return pd.DataFrame(columns=["nombre"])

st.title("📋 Seguimiento de Asistencia - JulioRodriguez")

# Fecha seleccionada
fecha = st.date_input("Selecciona la fecha")
fecha_str = fecha.strftime(f"{fecha.month}-{fecha.day}-{fecha.year % 100}")

# Cargar lista de residentes
residentes = cargar_lista_residentes()

# Buscar archivos para mañana y tarde
archivos_manana = buscar_archivos_asistencia(fecha_str, "Manana")
archivos_tarde = buscar_archivos_asistencia(fecha_str, "Tarde")

asistencia_manana = combinar_asistencias(archivos_manana)
asistencia_tarde = combinar_asistencias(archivos_tarde)

# Fusionar datos
residentes["mañana"] = residentes["nombre"].isin(asistencia_manana["nombre"])
residentes["tarde"] = residentes["nombre"].isin(asistencia_tarde["nombre"])

# Mostrar
st.subheader(f"Asistencia del {fecha_str}")
st.dataframe(residentes)

# Descargar
if st.button("📥 Descargar reporte Excel"):
    output_filename = f"reporte_asistencia_{fecha_str}.xlsx"
    residentes.to_excel(output_filename, index=False)
    with open(output_filename, "rb") as file:
        st.download_button("Descargar Excel", file, output_filename)


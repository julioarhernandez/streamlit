import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
import io

# 📁 Carpeta con archivos
CARPETA_ONEDRIVE = r"C:\Users\JulioRodriguez\OneDrive - InterAmerican Technical Institute\Attendance"
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
            with open(archivo, 'r', encoding='utf-16') as f:
                lines = f.readlines()

            # Buscar encabezado de sección "Participants"
            start_idx = None
            for i, line in enumerate(lines):
                if line.strip() == "Name\tFirst Join\tLast Leave\tIn-Meeting Duration\tEmail\tParticipant ID (UPN)\tRole":
                    start_idx = i
                    break

            if start_idx is None:
                st.warning(f"No se encontró sección de participantes en: {archivo}")
                continue

            data_lines = lines[start_idx:]
            data_str = "".join(data_lines)
            df = pd.read_csv(io.StringIO(data_str), sep="\t")
            df.rename(columns={"Name": "nombre"}, inplace=True)
            dfs.append(df[["nombre"]])
        except Exception as e:
            st.warning(f"No se pudo leer: {archivo}\nError: {e}")

    if dfs:
        return pd.concat(dfs).drop_duplicates(subset=["nombre"])
    else:
        return pd.DataFrame(columns=["nombre"])

# 🚀 Interfaz Streamlit
st.title("📋 Seguimiento de Asistencia - JulioRodriguez")

# Selección de fecha
fecha = st.date_input("Selecciona la fecha")
fecha_str = fecha.strftime(f"{fecha.month}-{fecha.day}-{fecha.year % 100}")

# Cargar residentes
residentes = cargar_lista_residentes()

# Cargar archivos
archivos_manana = buscar_archivos_asistencia(fecha_str, "Mañana")
archivos_tarde = buscar_archivos_asistencia(fecha_str, "Tarde")

asistencia_manana = combinar_asistencias(archivos_manana)
asistencia_tarde = combinar_asistencias(archivos_tarde)

# Marcar asistencia con booleanos (para mostrar como checkboxes)
residentes["mañana"] = residentes["nombre"].isin(asistencia_manana["nombre"])
residentes["tarde"] = residentes["nombre"].isin(asistencia_tarde["nombre"])

# Mostrar tabla con checkboxes
st.subheader(f"Asistencia del {fecha_str}")
st.dataframe(residentes)

# Descargar
if st.button("📥 Descargar reporte Excel"):
    output_filename = f"reporte_asistencia_{fecha_str}.xlsx"
    residentes.to_excel(output_filename, index=False)
    with open(output_filename, "rb") as file:
        st.download_button("Descargar Excel", file, output_filename)

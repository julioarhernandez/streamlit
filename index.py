import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime, timedelta
import io
from copy import deepcopy

CARPETA_ONEDRIVE = r"C:\Users\JulioRodriguez\OneDrive - InterAmerican Technical Institute\Attendance"
ARCHIVO_RESIDENTES = "residentes.csv"

def cargar_lista_residentes():
    path_residentes = os.path.join(CARPETA_ONEDRIVE, ARCHIVO_RESIDENTES)
    return pd.read_csv(path_residentes)

def buscar_archivos_asistencia(fecha_str, tipo="Tarde"):
    # Construct pattern that matches any prefix followed by the consistent parts
    patron = f"*{tipo} - Attendance report {fecha_str}.csv"
    ruta = os.path.join(CARPETA_ONEDRIVE, patron)
    archivos = glob.glob(ruta)
    
    # Add debug logging
    st.write(f"Searching for pattern: {patron}")
    # st.write(f"Found files: {archivos}")
    
    return archivos

def extraer_participantes(archivo):
    try:
        # Read the file line by line to handle TSV format
        with open(archivo, 'r', encoding='utf-16') as f:
            lines = f.readlines()
        
        # Find the start of the participants section
        start_idx = next(i for i, line in enumerate(lines)
                         if line.strip().startswith("Name\tFirst Join"))
        
        # Find the end of the participants section (line with "3. In-Meeting Activities")
        end_idx = next(i for i, line in enumerate(lines[start_idx:], start_idx)
                      if "3. In-Meeting Activities" in line.strip())
        
        # Get the participants section (including the header line)
        data_lines = lines[start_idx:end_idx]  # Get all lines from start to end_idx (exclusive)
        
        # Create DataFrame from the specific lines
        df = pd.read_csv(io.StringIO("".join(data_lines)), sep="\t")
        
        # Debug logging
        # st.write(f"\nReading file: {archivo}")
        # st.write(f"Raw data: {df}")
        
        # Filter out organizers and get unique names
        df_filtered = df[df['Role'] != 'Organizer']
        participantes = df_filtered["Name"].dropna().unique()
        st.write(f"Filtered participants: {participantes}")
        
        return participantes
    except Exception as e:
        st.warning(f"No se pudo leer: {archivo}\nError: {e}")
        return []

def asistencia_dia(fecha):
    # If fecha is already a string, use it directly
    if isinstance(fecha, str):
        fecha_str = fecha
    else:
        # Format date as M-DD-YY
        fecha_str = f"{fecha.month}-{fecha.day}-{fecha.year % 100}" 
    
    # First check for Mañana files
    archivos_manana = buscar_archivos_asistencia(fecha_str, "Mañana")
    nombres_manana = set()
    if archivos_manana:
        nombres_manana = set(extraer_participantes(archivos_manana[0]))
    
    # Then check for Tarde files
    archivos_tarde = buscar_archivos_asistencia(fecha_str, "Tarde")
    nombres_tarde = set()
    if archivos_tarde:
        nombres_tarde = set(extraer_participantes(archivos_tarde[0]))
    
    # Convert sets to lists for consistent ordering
    return list(nombres_manana), list(nombres_tarde)

def asistencia_semana(desde, hasta):
    dias = pd.date_range(desde, hasta) 
    asistencias = []
    for dia in dias:
        # Format date as M-DD-YY (single digit month)
        fecha_str = f"{dia.month}-{dia.day}-{dia.year % 100}"
        st.write(f"Processing date: {fecha_str}")
        
        # Get attendance for this date
        asistencia_manana, asistencia_tarde = asistencia_dia(fecha_str)
        asistencias.append((asistencia_manana, asistencia_tarde))
        
        # Debug logging
        st.write(f"Morning attendance for {fecha_str}: {len(asistencia_manana)}")
        st.write(f"Evening attendance for {fecha_str}: {len(asistencia_tarde)}")
    return asistencias

# --- UI ---
st.title("📋 Seguimiento de Asistencia - JulioRodriguez")

# Initialize session state for manual attendance changes if not exists
if 'manual_attendance' not in st.session_state:
    st.session_state.manual_attendance = {
        'mañana': set(),
        'tarde': set()
    }

# Get date input and format it as M-DD-YY
fecha = st.date_input("Selecciona la fecha")
fecha_str = f"{fecha.month}-{fecha.day}-{fecha.year % 100}"
inicio_semana = fecha - timedelta(days=fecha.weekday())
st.markdown(f"🗓️ Semana desde **{inicio_semana.month}-{inicio_semana.day}-{inicio_semana.year % 100}** hasta **{fecha.month}-{fecha.day}-{fecha.year % 100}**")

residentes = cargar_lista_residentes()

# Get attendance from files
asistentes_manana, asistentes_tarde = asistencia_dia(fecha_str)
    
# Create a copy of residentes to modify
residentes_editados = residentes.copy()
residentes_editados["mañana"] = residentes_editados["nombre"].isin(asistentes_manana)
residentes_editados["tarde"] = residentes_editados["nombre"].isin(asistentes_tarde)

# Mostrar checkboxes editables para hoy
residentes_editados = st.data_editor(
    residentes_editados[["nombre", "mañana", "tarde"]], 
    num_rows="dynamic"
)

# Update session state with manual changes
manual_manana = set(residentes_editados[residentes_editados["mañana"]]["nombre"])
manual_tarde = set(residentes_editados[residentes_editados["tarde"]]["nombre"])
    
# Update session state with changes
st.session_state.manual_attendance['mañana'] = manual_manana
st.session_state.manual_attendance['tarde'] = manual_tarde

# Calculate attendance totals including manual changes
total_manana = len(manual_manana)
total_tarde = len(manual_tarde)

# Display attendance totals
col1, col2 = st.columns(2)
with col1:
    st.metric("Mañana", f"{total_manana}")
with col2:
    st.metric("Tarde", f"{total_tarde}")

# Get attendance for the week (from files)
asistencias_por_dia = asistencia_semana(inicio_semana, fecha)
asistencia_total = set()
for asistencia_manana, asistencia_tarde in asistencias_por_dia:
    asistencia_total.update(asistencia_manana)
    asistencia_total.update(asistencia_tarde)
    
# Update the "asistió_semana" column considering manual changes
residentes_editados["asistió_semana"] = residentes_editados["nombre"].isin(asistencia_total) | \
    residentes_editados["nombre"].isin(manual_manana) | \
    residentes_editados["nombre"].isin(manual_tarde)

# Update the "asistió_semana" column considering manual changes
residentes_editados["asistió_semana"] = residentes_editados["nombre"].isin(asistencia_total) | \
    residentes_editados["nombre"].isin(manual_manana) | \
    residentes_editados["nombre"].isin(manual_tarde)

# Mostrar reporte de ausentes semanales
st.subheader("📉 Estudiantes sin asistencia esta semana")
ausentes = residentes_editados[~residentes_editados["asistió_semana"]][["nombre"]]
st.dataframe(ausentes)

# Descargar Excel con ausentes
if st.button("📥 Descargar reporte de ausentes"):
    output = "ausentes_semana.xlsx"
    ausentes.to_excel(output, index=False)
    with open(output, "rb") as f:
        st.download_button("Descargar Excel", f, output)

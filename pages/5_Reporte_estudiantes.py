import streamlit as st
import pandas as pd
import datetime
from config import setup_page
from utils import (
    load_students,
    get_module_on_date, get_highest_module_credit, get_last_updated,
    get_module_name_by_id, load_modules, highlight_style
)

# --- Login Check ---
if not st.session_state.get('logged_in', False):
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.info("Por favor, regrese a la página principal para iniciar sesión.")
    st.stop()
# --- End Login Check ---

setup_page("Reporte de Estudiantes")

# Module section
# if 'modules_df' not in st.session_state:
#     st.session_state.modules_df = None

# if 'modules_df' not in st.session_state or st.session_state.modules_df is None or st.session_state.modules_df.empty:
#     with st.spinner("Cargando módulos..."):
#         st.session_state.modules_df = load_modules(st.session_state.get('email'))

if 'modules_df' not in st.session_state:
    st.session_state.modules_df = None

if 'current_module_id_for_today' not in st.session_state:
    st.session_state.current_module_id_for_today = None

if 'current_module_id_for_today' in st.session_state and st.session_state.current_module_id_for_today is None:
    result = get_module_on_date(st.session_state.get('email').replace('.', ','))
    print("\n\nresult\n", result)
    if result and 'module_id' in result:
        st.session_state.current_module_id_for_today = result['firebase_key']
        print("\n\ncurrent_module_id_for_today\n", result['firebase_key'])
    else:
        st.warning("No se encontró un módulo activo para hoy.")


st.button(
    "Limpiar Módulo Actual",
    on_click=lambda: st.session_state.update({"current_module_id_for_today": None}),
    help="Borra el módulo actual guardado en la sesión actual."
)

# Student section
students_last_updated = get_last_updated('students')
# print("\n\nstudents_last_updated\n", students_last_updated)
df_loaded, _ = load_students(students_last_updated)
print("\n\ndf_loaded\n", df_loaded)

if df_loaded is None or df_loaded.empty:
    st.info("No hay estudiantes registrados.")
else:
    # Clean and format the data
    if 'ciclo' in df_loaded.columns:
        df_loaded = df_loaded.drop(columns=['ciclo'])
    
    # Format date columns
    date_columns = ['fecha_inicio', 'fecha_fin']
    for col in date_columns:
        if col in df_loaded.columns:
            df_loaded[col] = pd.to_datetime(df_loaded[col], errors='coerce').dt.strftime('%m/%d/%Y')
    
    # Select and order columns to display
    display_columns = ['nombre', 'email', 'telefono', 'modulo', 'fecha_inicio','modulo_fin_name', 'fecha_fin', 'modulo_fin_id' ]
    display_columns = [col for col in display_columns if col in df_loaded.columns]
    
    # Get module names if modulo column exists
    # if 'modulo' in df_loaded.columns:
    #     user_email = st.session_state.get('email', '').replace('.', ',')
    #     df_loaded['modulo_nombre'] = df_loaded['modulo'].apply(
    #         lambda x: get_module_name_by_id(user_email, str(x)) if pd.notna(x) else 'Sin módulo'
    #     )
    
    # Rename columns for display
    column_names = {
        'nombre': 'Nombre',
        'email': 'Correo Electrónico',
        'telefono': 'Teléfono',
        'modulo': 'Módulo (ID)',
        'modulo_nombre': 'Módulo',
        'fecha_inicio': 'Fecha de Inicio',
        'fecha_fin': 'Fecha de Finalización',
        'modulo_fin_name': 'Módulo (Final)',
        }

    # if df_loaded is not None and not df_loaded.empty:
    #     # First, calculate all the necessary columns
    #     df_loaded['Módulos Restantes'] = df_loaded.apply(calculate_remaining_modules, axis=1)
    #     df_loaded['fecha_fin_modulo'] = df_loaded.apply(get_module_end_date, axis=1)
    #     df_loaded['Estado'] = df_loaded.apply(calculate_status, axis=1)
    
    # # Convert date columns to datetime objects
    # if 'fecha_inicio' in df_loaded.columns:
    #     df_loaded['fecha_inicio'] = pd.to_datetime(df_loaded['fecha_inicio'], errors='coerce')
    # if 'fecha_fin_modulo' in df_loaded.columns:
    #     df_loaded['fecha_fin_modulo'] = pd.to_datetime(df_loaded['fecha_fin_modulo'], errors='coerce')
    
    # # Now calculate statistics
    # total_students = len(df_loaded)
    # graduated = len(df_loaded[df_loaded['Estado'] == 'Graduado']) if 'Estado' in df_loaded.columns else 0
    # in_progress = len(df_loaded[df_loaded['Estado'] == 'En curso']) if 'Estado' in df_loaded.columns else 0
    # last_module = len(df_loaded[df_loaded['Estado'] == 'Último']) if 'Estado' in df_loaded.columns else 0
    

    # a, b, c, d, e = st.columns([2,2,2,2,2])

    # a.metric("Total", total_students, border=True)
    # b.metric("En Curso", in_progress, border=True)

    # c.metric("Último Módulo", last_module, border=True)
    # d.metric("Graduados", graduated, border=True)
    # e.metric("No comenzado", total_students - in_progress - last_module - graduated, border=True)
    current_module_id = st.session_state.get('current_module_id_for_today')

    total_students = len(df_loaded)
    print("total_students", total_students)

    df_loaded['_fecha_inicio_dt'] = pd.to_datetime(df_loaded['fecha_inicio']).dt.date
    df_loaded['_fecha_fin_dt'] = pd.to_datetime(df_loaded['fecha_fin']).dt.date

    # Then create formatted versions for display
    df_loaded['fecha_inicio'] = df_loaded['_fecha_inicio_dt'].apply(lambda x: x.strftime('%m/%d/%Y'))
    df_loaded['fecha_fin'] = df_loaded['_fecha_fin_dt'].apply(lambda x: x.strftime('%m/%d/%Y'))

    today = datetime.date.today()
    students_in_module = len(df_loaded[
        (df_loaded['_fecha_inicio_dt'] <= today) &
        (df_loaded['_fecha_fin_dt'] >= today)
    ])
    print("students_in_module", students_in_module)

    students_not_in_module = total_students - students_in_module
    print("students_not_in_module", students_not_in_module)

    students_in_last_module = len(df_loaded[
        (df_loaded['_fecha_fin_dt'] <= today)
    ])

    last_module_students = df_loaded[
        (df_loaded['_fecha_inicio_dt'] <= today) &
        (df_loaded['_fecha_fin_dt'] >= today) &
        (df_loaded['_fecha_fin_dt'] == df_loaded.groupby('email')['_fecha_fin_dt'].transform('max'))
    ]
    df_loaded['En Ultimo Módulo'] = df_loaded['email'].apply(
        lambda x: 'Sí' if x in last_module_students['email'].unique() else 'No'
    )

    today = pd.to_datetime(today)
    df_loaded['_fecha_inicio_dt'] = pd.to_datetime(df_loaded['_fecha_inicio_dt'])
    df_loaded['_fecha_fin_dt'] = pd.to_datetime(df_loaded['_fecha_fin_dt'])


    students_in_last_module = len(df_loaded[
        (df_loaded['_fecha_inicio_dt'] <= today) &
        (df_loaded['_fecha_fin_dt'] >= today) &
        (df_loaded['modulo_fin_id'] == current_module_id)
    ])
    print("students_in_last_module", students_in_last_module)


    students_finished = len(df_loaded[
        (df_loaded['_fecha_fin_dt'] <= today)
    ])
    print("students_finished", students_finished)


    # ------ Highlight current module section ------
    # This section will highlight the current module in the DataFrame
    # Assuming df_loaded is your initial DataFrame and is already loaded
    

    # 1. Define all columns you need, including the one for logic
    # Using a single DataFrame is simpler than maintaining two.
    internal_columns = [
        'nombre', 'email', 'telefono', 'modulo', 'fecha_inicio', 
        'modulo_fin_name', 'fecha_fin', 'modulo_fin_id'
    ]
    df = df_loaded[internal_columns].copy()

    # 2. Rename columns for user-friendly display
    # Note: We don't rename 'modulo_fin_id' so we can easily reference it later.
    column_renames = {
        'nombre': 'Nombre',
        'email': 'Correo Electrónico',
        'telefono': 'Teléfono',
        'modulo': 'Módulo (ID)',
        'fecha_inicio': 'Fecha de Inicio',
        'fecha_fin': 'Fecha de Finalización',
        'modulo_fin_name': 'Módulo (Final)'
    }
    df_renamed = df.rename(columns=column_renames)

    def highlight_row_warning(row):
        """
        Highlights a row in yellow if it's the current module and has already started.
        """
        try:
            is_current_module = row.get('modulo_fin_id') == current_module_id
            is_module_started = False
            start_date_val = row.get('Fecha de Inicio')

            if pd.notna(start_date_val):
                try:
                    start_date = pd.to_datetime(start_date_val).date()
                    is_module_started = start_date <= datetime.date.today()
                except (ValueError, TypeError):
                    is_module_started = False
            
            if is_current_module and is_module_started:

                return [highlight_style('warning') for _ in row]

        except Exception as e:
            print(f"Error processing row in highlight_function: {row.to_dict()}")
            print(f"Error was: {e}")

        return ['' for _ in row]

    def highlight_row_error(row):
        """
        Highlights a row in yellow if it's the current module and has already started.
        """
        try:
            # Asegúrate de que la columna exista y no sea nula antes de comparar
            end_date_val = row.get('Fecha de Finalización') # <--- CORREGIDO
            fecha_fin_in_past = False
            if pd.notna(end_date_val):
                # Convierte a fecha para una comparación segura
                end_date = pd.to_datetime(end_date_val).date()
                fecha_fin_in_past = end_date < datetime.date.today()
            
            if fecha_fin_in_past:
                return [highlight_style('error') for _ in row]

        except Exception as e:
            print(f"Error processing row in highlight_function: {row.to_dict()}")
            print(f"Error was: {e}")

        return ['' for _ in row]

    # 4. Decide whether to apply styling
    if current_module_id:
        # Apply the style to the renamed DataFrame
        df_to_show = df_renamed.style.apply(highlight_row_warning, axis=1).apply(highlight_row_error, axis=1)
    else:
        # If no ID is set, just use the regular DataFrame
        df_to_show = df_renamed

    # 5. Display the DataFrame and hide the column
    st.dataframe(
        df_to_show,
        hide_index=True,
        use_container_width=True,
        column_config={
            # Setting a column's configuration to None completely removes it from display.
            "modulo_fin_id": None,
            # Your other column configurations for renaming headers remain the same
            "Nombre": "Estudiante",
            "Correo Electrónico": "Email",
            "Teléfono": "Teléfono",
            "Módulo (ID)": "Módulo (Inicio)",
            "Fecha de Inicio": "Inicio",
            "Fecha de Finalización": "Fin"
        }
    )

    # st.error("No se ha seleccionado un módulo.")
    # st.info("Por favor, seleccione un módulo para ver los estudiantes.")
    # st.warning("Por favor, seleccione un módulo para ver los estudiantes.")
    # st.success("Por favor, seleccione un módulo para ver los estudiantes.")



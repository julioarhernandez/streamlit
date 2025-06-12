import streamlit as st
import pandas as pd
import datetime
# Assuming 'config' module has 'setup_page' and 'db' (Firebase instance)
from config import setup_page, db 
from utils import date_format

# --- Page Setup and Login Check ---
setup_page("Semanas de Descanso")
if not st.session_state.get('logged_in', False):
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.info("Por favor, regrese a la página principal para iniciar sesión.")
    st.stop()

# --- Database Operations ---

def load_breaks():
    """
    Loads all 'breaks' data from the Firebase Realtime Database.
    Handles cases where data is empty or not in expected dictionary format.
    """
    try:
        # Create a fresh reference to the 'breaks' child node
        breaks_ref = db.child("breaks")
        breaks_data = breaks_ref.get().val() or {} # Get data, default to empty dict if None
        
        # Ensure the retrieved data is a dictionary
        if not isinstance(breaks_data, dict):
            st.warning(f"Se esperaba un diccionario para 'breaks', pero se obtuvo: {type(breaks_data)}. Retornando diccionario vacío.")
            return {}
        return breaks_data
    except Exception as e:
        st.error(f"Error al cargar las semanas de descanso: {e}")
        return {}

def save_break(break_id, break_data):
    """
    Saves a single break record to the Firebase Realtime Database.
    'break_id' is the unique key, 'break_data' is a dictionary of the break's attributes.
    """
    try:
        # Create a fresh reference to the specific break using its ID
        break_ref = db.child("breaks").child(break_id)
        break_ref.set(break_data) # Set (create or overwrite) the data
        return True
    except Exception as e:
        st.error(f"Error al guardar la semana de descanso: {e}")
        return False

# --- UI Components ---

def display_breaks_table(breaks_data):
    """
    Displays the loaded breaks data in a Streamlit dataframe.
    Calculates the 'Fecha Fin' dynamically for display.
    """
    if not breaks_data:
        st.info("No hay semanas de descanso configuradas.")
        return []
    
    breaks_list = []
    for break_id, break_info in breaks_data.items():
        if isinstance(break_info, dict):
            start_date_str = break_info.get('start_date')
            start_date = None
            try:
                # Attempt to parse start_date from ISO format string
                if start_date_str:
                    start_date = datetime.datetime.fromisoformat(start_date_str).date()
            except ValueError:
                st.warning(f"Formato de fecha inválido para el ID '{break_id}': '{start_date_str}'. Se ignorará esta entrada o se mostrará como 'N/A'.")
                # start_date remains None, handled below
            
            duration_weeks = break_info.get('duration_weeks', 1)
            
            # Calculate end_date only if start_date was successfully parsed
            end_date = (start_date + datetime.timedelta(weeks=duration_weeks)) if start_date else None
            
            breaks_list.append({
                'ID': break_id,
                'Eliminar': False,  # Add checkbox column
                'Nombre': break_info.get('name', ''),
                'Duración (semanas)': duration_weeks,
                'Fecha Inicio': date_format(start_date, "%Y/%m/%d") if start_date else 'N/A',
                'Fecha Fin': date_format(end_date, "%Y/%m/%d") if end_date else 'N/A',
                'start_date_obj': start_date  # Store as date object for sorting
            })
    
    if not breaks_list:
        st.info("No hay semanas de descanso configuradas.")
        return []
    
    # Sort by start date (most recent first)
    breaks_list.sort(key=lambda x: x['start_date_obj'] or datetime.date.min, reverse=True)
    
    # Create DataFrame
    df = pd.DataFrame(breaks_list)
    
    # Reorder columns for display - 'Semanas' before 'Inicio'
    column_order = ['Eliminar', 'Nombre', 'Duración (semanas)', 'Fecha Inicio', 'Fecha Fin', 'ID']
    df = df[[col for col in column_order if col in df.columns]]
    
    # Display the DataFrame with checkboxes
    edited_df = st.data_editor(
        df,
        column_config={
            'Eliminar': st.column_config.CheckboxColumn(
                "Eliminar",
                help="Seleccione para eliminar",
                default=False,
                width="small",
                pinned=True
            ),
            'ID': None,  # Hide the internal ID column
            'Nombre': 'Nombre',
            'Fecha Inicio': 'Inicio',
            'Fecha Fin': 'Fin',
            'Duración (semanas)': 'Semanas',
            'start_date_obj': None  # Hide the sort helper column
        },
        hide_index=True,
        use_container_width=True,
        disabled=['ID', 'Nombre', 'Fecha Inicio', 'Duración (semanas)', 'Fecha Fin']
    )
    
    # Check for breaks selected for deletion
    if 'delete_breaks' not in st.session_state:
        st.session_state.delete_breaks = False
    
    # Show delete button if any breaks are selected
    breaks_to_delete = edited_df[edited_df['Eliminar']]
    if not breaks_to_delete.empty:
        st.warning(f"Se eliminarán {len(breaks_to_delete)} semana(s) de descanso. Esta acción no se puede deshacer.")
        
        if st.button("⚠️ Confirmar eliminación"):
            success_count = 0
            for _, row in breaks_to_delete.iterrows():
                try:
                    # Create a fresh reference for each deletion to avoid path issues
                    db.child("breaks").child(row['ID']).remove()
                    success_count += 1
                except Exception as e:
                    st.error(f"Error al eliminar la semana de descanso '{row['Nombre']}': {str(e)}")
            
            if success_count > 0:
                st.success(f"Se eliminaron {success_count} semana(s) de descanso correctamente.")
                st.rerun()
    
    return breaks_list

def add_break_form():
    """
    Displays inputs to add a new break.
    The 'Período' caption updates reactively with user input without a form.
    Returns dictionary of data if save button is pressed, otherwise None.
    """
    # Initialize default values for the input fields for consistent behavior
    default_name = ''
    default_start_date = datetime.date.today()
    default_duration_weeks = 1

    # Initialize session state for input fields if they don't exist
    if 'add_break_name' not in st.session_state:
        st.session_state.add_break_name = default_name
    if 'add_break_start_date' not in st.session_state:
        st.session_state.add_break_start_date = default_start_date
    if 'add_break_duration_weeks' not in st.session_state:
        st.session_state.add_break_duration_weeks = default_duration_weeks

    st.subheader("Agregar Semana de Descanso")
    
    # Single row with all inputs
    col1, col2, col3 = st.columns([2, 2, 1])
    
    # Text input for the break name
    name = col1.text_input(
        "Nombre de la Semana de Descanso",
        value=st.session_state.add_break_name,
        key="break_name_input"
    )
    
    # Date input for the start date
    start_date = col2.date_input(
        "Fecha de Inicio",
        value=st.session_state.add_break_start_date,
        key="break_start_date_input"
    )
    
    # Number input for duration in weeks
    duration_weeks = col3.number_input(
        "Semanas",
        min_value=1,
        value=st.session_state.add_break_duration_weeks,
        step=1,
        key="break_duration_input"
    )
    
    # Calculate and display the date range dynamically.
    # This caption will update immediately because start_date and duration_weeks
    # now directly reflect the current widget values on each re-run.
    end_date_display = start_date + datetime.timedelta(weeks=duration_weeks)
    st.caption(f"Período: {date_format(start_date, "%Y/%m/%d")} al {date_format(end_date_display, "%Y/%m/%d")}")
    
    # Regular Streamlit button for saving data.
    # This will trigger a re-run and the logic below.
    if st.button("Guardar Semana de Descanso"):
        if not name:
            st.error("El nombre es obligatorio.")
            return None 
        
        # Reset session state variables after successful submission.
        st.session_state.add_break_name = default_name
        st.session_state.add_break_start_date = default_start_date 
        st.session_state.add_break_duration_weeks = default_duration_weeks 

        # Return the data to be saved
        return {
            'name': name,
            'start_date': start_date.isoformat(),
            'duration_weeks': duration_weeks,
            'created_at': datetime.datetime.now().isoformat(),
            'created_by': st.session_state.get('email', 'system')
        }
    
    return None # Return None if the button has not been pressed

# --- Main App ---

def main():
    """
    Main function to run the Streamlit application for managing break weeks.
    Displays existing breaks, provides an area to add new ones, and a section to delete them.
    """
    
    st.markdown("""
    Administre las semanas de descanso que se aplicarán a todos los módulos.
    Estas fechas se utilizarán para saltar días no hábiles en los cálculos de programación.
    """)
    
    # Add new break form at the top
    break_data = add_break_form()
    
    if break_data:
        # Generate a unique ID for the new break based on current timestamp
        break_id = f"break_{datetime.datetime.now().strftime('%Y%m%d%H%M%S_%f')}" # Added microsecond for more uniqueness
        
        # Save the new break to Firebase
        try:
            db.child("breaks").child(break_id).set(break_data)
            st.success("¡Semana de descanso agregada exitosamente!")
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar la semana de descanso: {str(e)}")
    
    st.markdown("---")
    
    # Load and display existing breaks
    breaks_data = load_breaks()
    display_breaks_table(breaks_data)

# Entry point of the Streamlit application
if __name__ == "__main__":
    main()

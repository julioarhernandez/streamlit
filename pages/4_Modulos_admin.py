import streamlit as st
import pandas as pd
from config import setup_page
from utils_admin import admin_get_student_group_emails, save_new_module_to_db, admin_get_available_modules, load_breaks_from_db, parse_breaks, adjust_date_for_breaks, row_to_clean_dict, transform_module_input, sync_firebase_updates
import datetime

# --- Page Setup and Login Check ---
setup_page("Gestión de Módulos por Administrador")
if not st.session_state.get('logged_in', False):
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.info("Por favor, regrese a la página principal para iniciar sesión.")
    st.stop()

# --- Initialize session state variables at the very top ---
# This ensures they exist before any part of the script tries to access them.
if 'editor_key' not in st.session_state:
    st.session_state.editor_key = 0
if 'modules_df_by_course' not in st.session_state:
    st.session_state.modules_df_by_course = {} # This will store DataFrames per course
if 'force_refresh' not in st.session_state:
    st.session_state.force_refresh = False
# --- End Initialize session state variables ---

# --- Select Course ---
st.subheader("1. Seleccionar Curso")

# Get available courses (emails)
course_emails = admin_get_student_group_emails()

modules_selected_course = None # Initialize modules_selected_course before the if/else block

if course_emails:
    full_emails_for_options = course_emails.copy() # Good practice to copy if you modify original later
    course_options = {
        email: {
            'label': email.capitalize().split('@')[0], # Display part without domain
            'value': email                              # Full email with domain
        }
        for email in full_emails_for_options
    }

    modules_selected_course = st.selectbox(
        "Seleccione un Curso para agregar a los nuevos módulos:",
        options=full_emails_for_options,
        format_func=lambda x: course_options[x]['label'],
        index=0,
        key="course_selector" # Added key for consistency
    )

else:
    st.warning("No se encontraron cursos disponibles.")
    modules_selected_course = None # Ensure it's explicitly None if no courses


def calculate_dates(start_date):
    breaks_data = load_breaks_from_db()
    breaks = parse_breaks(breaks_data)
    # Ensure start_date is a date object for comparison
    if hasattr(start_date, 'date'):
        start_date = start_date.date()
    adjusted_start = adjust_date_for_breaks(start_date, breaks)
    # Convert back to datetime for consistency with the rest of the app
    if isinstance(adjusted_start, datetime.date):
        return pd.Timestamp(adjusted_start)
    return adjusted_start

# --- Select Module ---
if modules_selected_course: # Only show module selection if a course is selected
    st.divider()
    st.subheader("2. Seleccionar Módulo")

try:
    st.write("\n\nmodules_selected_course----->> ", modules_selected_course)
    module_options = admin_get_available_modules(modules_selected_course)
    print("\n\nmodu froom db\n\n ----- ", module_options)
    if module_options:
        df = pd.DataFrame(module_options)
        print("\n\nAvailable columns in module data:", df.columns.tolist())

        # Define your primary column mapping for known columns
        column_mapping = {
            'module_name': 'Nombre Módulo',
            'module_id': 'ID Módulo',
            'ciclo': 'Ciclo',
            'start_date': 'Fecha Inicio',
            'end_date': 'Fecha Fin',
            'duration_weeks': 'Duración',
            'credits': 'Orden',
            'description': 'Descripción',
            'firebase_key': 'Firebase Key'
        }

        # Dynamically create display_columns to include ALL columns present in the DataFrame
        # and create display names for them.
        display_columns = []
        reverse_display_names = {} # To map display names back to original for saving

        for col in df.columns:
            # Use the mapped name if available, otherwise use the original column name
            display_name = column_mapping.get(col, col)
            display_columns.append(display_name)
            reverse_display_names[display_name] = col # Store reverse mapping

        if not display_columns:
            st.warning("No se encontraron columnas válidas para mostrar.")
            st.json(module_options[0] if module_options else {})  # Show raw data for debugging
            st.stop()

        # Create a copy for display, renaming columns
        # Ensure only columns that exist in df are selected, and then rename them
        display_df = df.rename(columns=column_mapping)[display_columns].copy()
        
        # Hide specific columns from display
        columns_to_hide = ["Ciclo", "Firebase Key", "label", "ID Módulo"]  # Add any other columns you want to hide here
        display_df = display_df.drop(columns=[col for col in columns_to_hide if col in display_df.columns])
        
        # Convert date columns from string to datetime
        date_columns = ["Fecha Inicio", "Fecha Fin"]
        for date_col in date_columns:
            if date_col in display_df.columns:
                display_df[date_col] = pd.to_datetime(display_df[date_col], errors='coerce')

        # Define column configurations for st.data_editor
        editor_column_config = {
            "ID Módulo": st.column_config.TextColumn(disabled=True),
            "Fecha Inicio": st.column_config.DateColumn(format="MM/DD/YYYY"),
            "Fecha Fin": st.column_config.DateColumn(format="MM/DD/YYYY"),
            "Duración": st.column_config.NumberColumn(min_value=1, step=1),
            "Orden": st.column_config.NumberColumn(min_value=1, step=1),
            "Descripción": st.column_config.TextColumn()
        }

        # Initialize session state for this course if not exists OR if force refresh is needed
        if (modules_selected_course not in st.session_state.modules_df_by_course or 
            st.session_state.force_refresh):
            st.session_state.modules_df_by_course[modules_selected_course] = display_df.copy()
            st.session_state.force_refresh = False  # Reset force refresh flag

        st.write("Editar módulos:")
        
        # Create a unique key that changes when we need to force refresh
        editor_key = f"main_editor_{modules_selected_course}_{st.session_state.editor_key}"
        
        # Use the session state version for the editor
        edited_df = st.data_editor(
            st.session_state.modules_df_by_course[modules_selected_course],
            use_container_width=True,
            num_rows="dynamic",
            column_config=editor_column_config,
            key=editor_key
        )

        print("\n\n----Edited DataFrame------\n\n", edited_df)

        # You update the session state with the (potentially problematic) edited data
        # st.session_state.modules_df_by_course[modules_selected_course] = edited_df

        # This block cleans the data immediately after it has been edited.
        # date_columns_to_reconvert = ["Fecha Inicio", "Fecha Fin"]
        # for date_col in date_columns_to_reconvert:
        #     if date_col in st.session_state.modules_df_by_course[modules_selected_course].columns:
        #         st.session_state.modules_df_by_course[modules_selected_course][date_col] = pd.to_datetime(
        #             st.session_state.modules_df_by_course[modules_selected_course][date_col], 
        #             errors='coerce'
        #         )
        # Re-assign edited_df to the corrected dataframe from session state for consistency
        # edited_df = st.session_state.modules_df_by_course[modules_selected_course]
        

        # Handle date recalculation for empty start dates
       

        # Add save button

        last_row = edited_df.iloc[-1]
        # Check if all required fields are filled (using pd.notna for proper NaT handling)
        if all(pd.notna(last_row[col]) for col in ['Duración', 'Orden']):
            
            # Only show the button if the last row has empty start and end dates
            if all(pd.isna(last_row[col]) for col in ['Fecha Inicio', 'Fecha Fin']):
                # Check if there are any changes
                if st.button("Recalcular las fechas", key="recalcular_fechas"):
                    # Find the last module with a valid order number minus 1
                    last_orden = last_row['Orden'] - 1
                    valid_modules = edited_df[edited_df['Orden'] == last_orden]
                    if not valid_modules.empty:
                        last_module = valid_modules.sort_values('Orden').iloc[0]
                        last_orden = last_module['Orden']
                        
                        print(f"\n\nLast module with valid order:\n{last_module}")
                        
                        # Calculate the new start date (one day after the last module's end date)
                        if pd.notna(last_module['Fecha Fin']):
                            new_start_date =calculate_dates(last_module['Fecha Fin'] + pd.DateOffset(days=1))
                            # new_start_date = last_module['Fecha Fin'] + pd.DateOffset(days=1)
                            print(f"\n\nNew start date:\n{new_start_date}")
                            # Find the row with None Fecha de inicio and None Fecha de fin
                            mask = (edited_df['Fecha Inicio'].isna()) & (edited_df['Fecha Fin'].isna())
                            
                            if mask.any():
                                # Create a fresh copy of the session state dataframe
                                updated_df = edited_df.copy()
                                print("\n\n=----copy created - Updated DataFrame:\n", updated_df)
                                
                                # Update the start date of the empty row
                                updated_df.loc[mask, 'Fecha Inicio'] = new_start_date
                                
                                # Debug info
                                print("\n\nUpdating empty row with start date:", new_start_date)
                                print("Updated row:", updated_df.loc[mask, ['Orden', 'Fecha Inicio', 'Fecha Fin']])

                                # Calculate the new end date (one week after the last module's start date)
                                
                                # Update the session state with our modified copy
                                # st.session_state.modules_df_by_course[modules_selected_course] = updated_df
                                
                                # Increment editor key to force widget refresh
                                # st.session_state.editor_key += 1

                                edited_df = updated_df
                                st.session_state.modules_df_by_course[modules_selected_course] = edited_df
                                
                                st.rerun()
                            else:
                                st.warning("No se encontró ninguna fila vacía para actualizar.")
                        else:
                            st.warning("El último módulo no tiene fecha de fin definida.")
                    else:
                        st.warning("No se encontraron módulos con orden válido.")
                # end date calculation
            if all(pd.notna(last_row[col]) for col in ['Fecha Inicio', 'Fecha Fin', 'Duración', 'Orden']):
                if st.button("💾 Guardar Cambios"):
                    # Rename display columns back to original DB names
                    edited_df_for_save = edited_df.rename(columns=reverse_display_names)
                    new_rows = edited_df[~edited_df.apply(tuple, 1).isin(st.session_state.modules_df_by_course[modules_selected_course].apply(tuple, 1))]
                    if not new_rows.empty:
                        st.write("New rows:", new_rows)
                        for _, row in new_rows.iterrows():
                            st.write(transform_module_input(row_to_clean_dict(row)))
                            if save_new_module_to_db(modules_selected_course, transform_module_input(row_to_clean_dict(row))):
                                st.success("¡Cambios guardados exitosamente!")
                                st.session_state.editor_key += 1
                        # st.success(f"Se guardaron {len(new_rows)} fila(s).")
                        st.session_state.df = edited_df.copy()
                        st.success(f"Saved {len(new_rows)} new row(s) to Firebase.")
                        st.session_state.modules_df_by_course[modules_selected_course] = edited_df.copy()
                        # st.rerun()
                    else:
                        st.warning("No se encontraron filas nuevas para guardar.")
                        try:
                            sync_firebase_updates(st.session_state.modules_df_by_course[modules_selected_course], edited_df)
                            st.session_state.modules_df_by_course[modules_selected_course] = edited_df.copy()
                            st.success("Cambios sincronizados correctamente.")
                        except Exception as e:
                            st.error(f"Error al sincronizar con Firebase: {e}")

                    # --- IMPROVEMENT: Safely re-introduce hidden columns ---
                    # Get a list of columns that were in the original 'df' but not in the editor
                    # cols_to_preserve = [col for col in df.columns if col not in edited_df_for_save.columns]
                    
                    # if cols_to_preserve:
                    #     # Use a join on the index to safely merge the hidden columns.
                    #     # This prevents misalignment if rows were deleted.
                    #     edited_df_for_save = edited_df_for_save.join(df[cols_to_preserve])

                    # # Convert to list of dictionaries for processing
                    # modules_to_save = edited_df_for_save.to_dict('records')

                    # # --- Date formatting loop (your robust version is good) ---
                    # for module_data in modules_to_save:
                    #     for date_col in ['start_date', 'end_date']:
                    #         if date_col in module_data:
                    #             value = module_data[date_col]
                    #             if pd.isna(value):
                    #                 module_data[date_col] = None
                    #             else:
                    #                 try:
                    #                     if hasattr(value, 'strftime'):
                    #                         module_data[date_col] = value.strftime('%Y-%m-%d')
                    #                     else:
                    #                         module_data[date_col] = pd.to_datetime(value).strftime('%Y-%m-%d')
                    #                 except Exception:
                    #                     module_data[date_col] = None
                    
                    # --- FIX: Call the corrected save function ---
                    # st.write("Modules to save:", modules_to_save)
                   
                    
                    # if save_modules_to_db(modules_selected_course, modules_to_save):
                    #     st.success("¡Cambios guardados exitosamente!")
                        
                    #     # Your state management logic is excellent, no changes needed here
                    #     if modules_selected_course in st.session_state.modules_df_by_course:
                    #         del st.session_state.modules_df_by_course[modules_selected_course]
                    #     st.session_state.editor_key += 1
                    #     st.session_state.force_refresh = True
                    #     st.rerun()
    else:
        st.info("No hay módulos disponibles. Por favor, agregue módulos.") # Keep this message
except Exception as e:
    st.error(f"Error al cargar o procesar los módulos: {str(e)}")
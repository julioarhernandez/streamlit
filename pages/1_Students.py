import streamlit as st
import pandas as pd
from config import setup_page
from utils import save_students, load_students

# Setup page
setup_page("Students Management")

# Main UI
st.header("Manage Students")

# File upload section
uploaded_file = st.file_uploader("Upload Students File (CSV or Excel)", 
                               type=['csv'])

if uploaded_file is not None:
    try:
        df_upload = pd.read_csv(uploaded_file) # Renamed to df_upload to avoid conflict
    
        # Normalize column names (convert to lowercase)
        df_upload.columns = df_upload.columns.str.lower().str.strip()
        
        # Check for required columns
        required_columns = {'nombre'}
        missing_columns = required_columns - set(df_upload.columns)
        
        if missing_columns:
            st.error(f"Error: The uploaded file is missing required columns: {', '.join(missing_columns)}. "
                    f"Please make sure your file includes these columns: nombre")
        else:
            # Ensure ID is string and trim whitespace from string columns
            df_upload['nombre'] = df_upload['nombre'].astype(str).str.strip() # Ensure 'nombre' is string
            
            # Show preview
            st.subheader("Preview of Uploaded File")
            st.dataframe(df_upload.head())
            
            if st.button("Save Uploaded Students (replaces existing list)"):
                if save_students(df_upload):
                    st.success("Students data from file saved successfully! Existing list was replaced.")
                    st.rerun()
    
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        st.error("Please make sure the file is not open in another program and try again.")

st.divider()

# --- Add Multiple Students via Text Area ---
st.subheader("Add Multiple Students via Text Area")
st.caption("Enter one student name per line. Duplicates and existing names will be skipped.")
with st.form(key="add_students_textarea_form", clear_on_submit=True):
    students_text_area = st.text_area("Student Names (one per line)", height=150)
    submit_add_students_text = st.form_submit_button("Add Students from Text")

if submit_add_students_text:
    if not students_text_area.strip():
        st.warning("Text area is empty. Please enter student names.")
    else:
        lines = students_text_area.strip().split('\n')
        potential_new_names = [line.strip() for line in lines if line.strip()]
        
        if not potential_new_names:
            st.warning("No valid student names found in the text area after processing.")
        else:
            current_students_df, _ = load_students()
            if current_students_df is None:
                current_students_df = pd.DataFrame(columns=['nombre'])
            
            if 'nombre' not in current_students_df.columns:
                current_students_df['nombre'] = pd.Series(dtype='str')
            else:
                current_students_df['nombre'] = current_students_df['nombre'].astype(str)

            existing_normalized_names = set(current_students_df['nombre'].str.lower().str.strip())
            
            added_count = 0
            skipped_names = []
            students_to_add_list = []
            
            # Deduplicate within the input list first, preserving order
            unique_potential_new_names = []
            seen_in_input = set()
            for name in potential_new_names:
                normalized_name = name.lower().strip()
                if normalized_name not in seen_in_input:
                    unique_potential_new_names.append(name) # Keep original casing for adding
                    seen_in_input.add(normalized_name)
            
            for name in unique_potential_new_names:
                normalized_name = name.lower().strip() # Compare with normalized
                if normalized_name not in existing_normalized_names:
                    students_to_add_list.append({'nombre': name}) # Add with original casing
                    added_count += 1
                else:
                    skipped_names.append(name)
            
            if not students_to_add_list:
                st.info("No new students to add. All names provided either already exist or were duplicates in the input.")
                if skipped_names:
                    st.caption(f"Skipped names (already exist or duplicates): {', '.join(skipped_names)}")
            else:
                new_students_df = pd.DataFrame(students_to_add_list)
                updated_students_df = pd.concat([current_students_df, new_students_df], ignore_index=True)
                
                if save_students(updated_students_df):
                    st.success(f"{added_count} student(s) added successfully!")
                    if skipped_names:
                        st.caption(f"Skipped names (already exist or duplicates in input): {', '.join(skipped_names)}")
                    st.rerun()
                else:
                    st.error("Failed to add students from text area.")

st.divider()

# --- Display and Manage Current Students ---
st.subheader("Current Students")

# Show existing data
df_loaded, _ = load_students()

if df_loaded is not None and not df_loaded.empty:
    if 'nombre' not in df_loaded.columns:
        st.error("Student data is missing the 'nombre' column, which is required.")
    else:
        # Prepare DataFrame for st.data_editor
        df_display = df_loaded.copy()
        if '🗑️' not in df_display.columns:
            df_display.insert(0, '🗑️', False) # Add selection column at the beginning
        
        # Make 'nombre' non-editable, other columns can be edited if needed by user
        # For now, focus is on deletion, so let's make all original data non-editable.
        disabled_columns = [col for col in df_loaded.columns if col != '🗑️']

        st.info("Check the '🗑️' box for students you wish to delete, then click 'Delete Selected Students' below.")
        edited_df = st.data_editor(
            df_display, 
            disabled=disabled_columns, # Make original data columns non-editable
            hide_index=True,
            column_config={
                "🗑️": st.column_config.CheckboxColumn(
                    "Delete?",
                    help="Select students to delete",
                    default=False,
                )
            }
        )

        students_selected_for_deletion = edited_df[edited_df['🗑️'] == True]

        if not students_selected_for_deletion.empty:
            if st.button("Delete Selected Students", type="primary"):
                names_to_delete = students_selected_for_deletion['nombre'].tolist()
                
                # Perform batch deletion
                current_students_df_from_db, _ = load_students()
                if current_students_df_from_db is None:
                    st.error("Could not reload student data to perform deletion. Please try again.")
                else:
                    normalized_names_to_delete = {str(name).lower().strip() for name in names_to_delete}
                    
                    students_to_keep_df = current_students_df_from_db[
                        ~current_students_df_from_db['nombre'].astype(str).str.lower().str.strip().isin(normalized_names_to_delete)
                    ]
                    
                    if save_students(students_to_keep_df):
                        st.success(f"{len(names_to_delete)} student(s) deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to save changes after attempting to delete students.")
        elif any(edited_df['🗑️']):
             # This case might occur if boxes were checked then unchecked before button press
             # or if the button is shown even with no selections initially.
             # For a cleaner UI, the button could be conditionally shown only if selections exist.
             # For now, just ensure no action if button pressed with no actual selections.
             pass 

elif df_loaded is not None and df_loaded.empty:
    st.info("The student list is currently empty. Upload a file to add students.")
else: # df_loaded is None (error loading or no data)
    st.info("No students data found or failed to load. Please upload a file to get started.")

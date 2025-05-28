# c:\Users\JulioRodriguez\Documents\GitHub\streamlit\pages\2_Attendance.py
import streamlit as st
import pandas as pd
import datetime
import re
import io
from utils import save_attendance, load_students, load_attendance

# --- Session State Initialization ---
st.title("Attendance Management")

if 'uploader_key_suffix' not in st.session_state:
    st.session_state.uploader_key_suffix = "initial_attendance"

# Stores {date_obj: {set_of_names}} from currently uploaded and processed files
if 'current_batch_data_by_date' not in st.session_state:
    st.session_state.current_batch_data_by_date = {}

# Stores {date_obj: pd.DataFrame} for attendance tables ready for editing/saving
if 'prepared_attendance_dfs' not in st.session_state:
    st.session_state.prepared_attendance_dfs = {}

# Tracks filenames processed in the current interaction to avoid reprocessing if script reruns
if 'processed_files_this_session' not in st.session_state:
    st.session_state.processed_files_this_session = set()

# --- Helper Functions (extract_date_from_filename, parse_attendance_report) ---
def extract_date_from_filename(filename: str) -> datetime.date | None:
    # Try to find 'Attendance report MM-DD-YY' or 'Attendance report M-D-YY'
    # Case insensitive search for "Attendance report "
    match_keyword = re.search(r'Attendance report ', filename, re.IGNORECASE)
    if match_keyword:
        # Get the part of the string after "Attendance report "
        date_str_candidate = filename[match_keyword.end():]
        
        # Regex to find M-D-YY or MM-DD-YY at the start of the candidate string
        # This ensures we only match if the date is right after "Attendance report "
        match_date = re.match(r'(\d{1,2})-(\d{1,2})-(\d{2})', date_str_candidate)
        if match_date:
            month, day, year_short = map(int, match_date.groups())
            year = 2000 + year_short # Assuming 21st century
            try:
                return datetime.date(year, month, day)
            except ValueError: # Handles invalid dates like 2-30-25
                return None
    return None

def parse_attendance_report(file_content_str: str, filename_for_debug: str) -> list:
    # st.write(f"--- Debugging: Parsing '{filename_for_debug}' ---") # Uncomment for verbose debugging
    lines = file_content_str.splitlines()
    
    start_marker_found_at = -1
    end_marker_found_at = -1

    # Find start and end markers for the participant block
    for i, line in enumerate(lines):
        line_stripped_lower = line.strip().lower()
        if line_stripped_lower.startswith("2. participants"):
            start_marker_found_at = i
            continue 
        
        if start_marker_found_at != -1 and line_stripped_lower.startswith("3. in-meeting activities"):
            end_marker_found_at = i
            break 

    if start_marker_found_at == -1:
        st.warning(f"Could not find the '2. Participants' section marker in '{filename_for_debug}'.")
        return []

    actual_data_start_index = start_marker_found_at + 1
    
    if end_marker_found_at != -1:
        actual_data_end_index = end_marker_found_at
    else:
        actual_data_end_index = len(lines)

    participant_data_lines = lines[actual_data_start_index : actual_data_end_index]

    if not participant_data_lines:
        st.warning(f"No data lines found between '2. Participants' and '3. In-Meeting Activities' (or end of file) in '{filename_for_debug}'.")
        return []

    header_row_index_in_block = -1
    for i, line_in_block in enumerate(participant_data_lines):
        line_norm = line_in_block.strip().lower()
        if "name" in line_norm and ("first join" in line_norm or "last leave" in line_norm or "email" in line_norm or "duration" in line_norm):
            header_row_index_in_block = i
            break
            
    if header_row_index_in_block == -1:
        st.warning(f"Could not find the data header row (e.g., 'Name First Join...') within the '2. Participants' section of '{filename_for_debug}'.")
        return []

    csv_like_data_for_pandas = "\n".join(participant_data_lines[header_row_index_in_block:])
    
    try:
        df = pd.read_csv(io.StringIO(csv_like_data_for_pandas), sep='\t')
        df.columns = [col.strip().lower() for col in df.columns] 
        
        if "name" in df.columns:
            return df["name"].astype(str).str.strip().unique().tolist()
        else:
            st.warning(f"Column 'name' not found after parsing in '{filename_for_debug}'. Columns found: {df.columns.tolist()}")
            return []
    except pd.errors.EmptyDataError:
        st.warning(f"No data rows could be parsed from the CSV content in '{filename_for_debug}'. The identified header might have been the last line or data was empty.")
        return []
    except Exception as e:
        st.error(f"Error parsing CSV data from 'Participants' section of '{filename_for_debug}': {e}")
        return []

# --- Main UI --- 
st.header("Upload Attendance Report Files")
st.caption("Upload one or more attendance CSV report files. Dates will be detected from filenames.")

# File Uploader
uploaded_reports = st.file_uploader(
    "Upload meeting attendance CSV report(s)",
    type=['csv'],
    accept_multiple_files=True,
    key=f"report_uploader_daily_{st.session_state.uploader_key_suffix}",
    help="Upload CSV files. Date is detected from filename (e.g., '...Attendance report MM-DD-YY.csv')"
)

if uploaded_reports:
    files_processed_summary = {}
    files_skipped_summary = {}

    for report_file in uploaded_reports:
        if report_file.name in st.session_state.processed_files_this_session:
            # st.write(f"Skipping '{report_file.name}' as it was already processed in this session.") # DEBUG
            continue

        file_date = extract_date_from_filename(report_file.name)

        if not file_date:
            st.warning(f"Skipping '{report_file.name}': Could not extract date from filename.")
            files_skipped_summary[report_file.name] = "No date in filename"
            st.session_state.processed_files_this_session.add(report_file.name) # Mark as processed to avoid re-warning
            continue

        # --- File Decoding --- 
        file_bytes = report_file.getvalue()
        file_content_str = None
        successful_encoding = None
        # Encodings to try, with utf-16 prioritized for Microsoft-generated CSVs
        tried_encodings_list = ['utf-16', 'utf-8', 'utf-8-sig', 'latin-1', 'cp1252'] 

        try:
            # st.write(f"Attempting to decode {report_file.name} with utf-16...") # DEBUG
            file_content_str = file_bytes.decode('utf-16')
            successful_encoding = 'utf-16'
            # st.write(f"Successfully decoded {report_file.name} with utf-16.") # DEBUG
        except UnicodeDecodeError:
            # st.write(f"Failed to decode {report_file.name} with utf-16. Trying other encodings...") # DEBUG
            other_encodings_to_attempt = [enc for enc in tried_encodings_list if enc != 'utf-16']
            for enc in other_encodings_to_attempt:
                try:
                    # st.write(f"Attempting to decode {report_file.name} with {enc}...") # DEBUG
                    file_content_str = file_bytes.decode(enc)
                    successful_encoding = enc
                    # st.write(f"Successfully decoded {report_file.name} with {enc}.") # DEBUG
                    break 
                except UnicodeDecodeError:
                    # st.write(f"Failed to decode {report_file.name} with {enc}.") # DEBUG
                    continue
        
        if file_content_str is None:
            st.error(f"Failed to decode '{report_file.name}'. Tried: {', '.join(tried_encodings_list)}. File might be corrupted or in an unsupported encoding.")
            files_skipped_summary[report_file.name] = "Decoding failed"
            st.session_state.processed_files_this_session.add(report_file.name)
            continue
        # else:
            # st.success(f"Decoded '{report_file.name}' successfully using {successful_encoding}.") # DEBUG

        # --- Parse Names --- 
        names_from_report = parse_attendance_report(file_content_str, report_file.name)
        
        if names_from_report:
            st.session_state.current_batch_data_by_date.setdefault(file_date, set()).update(names_from_report)
            files_processed_summary.setdefault(file_date, []).append(report_file.name)
        else:
            st.warning(f"Could not extract names from '{report_file.name}' (after successful decoding). Check parser logic or file structure.")
            files_skipped_summary[report_file.name] = "Name parsing failed"
        
        st.session_state.processed_files_this_session.add(report_file.name)

    # --- Display Summary of File Processing --- 
    if files_processed_summary:
        st.markdown("**Successfully Processed Files:**")
        for date_obj, filenames in files_processed_summary.items():
            attendee_count = len(st.session_state.current_batch_data_by_date.get(date_obj, set()))
            st.write(f"- **{date_obj.strftime('%Y-%m-%d')}**: {len(filenames)} file(s) processed, contributing to {attendee_count} unique attendees for this date.")
            # for fname in filenames: st.caption(f"    - {fname}") # Optional: list filenames
    
    if files_skipped_summary:
        st.markdown("**Skipped Files:**")
        for filename, reason in files_skipped_summary.items():
            st.write(f"- {filename}: {reason}")

# --- Display Current Batch Data & Prepare Attendance Tables ---
if st.session_state.current_batch_data_by_date:
    st.divider()
    st.subheader("Step 2: Review Extracted Attendees and Prepare Attendance Tables")
    st.caption("The following attendees were found in the uploaded reports. Click below to load all registered students and generate attendance tables.")

    for date_obj, names_set in st.session_state.current_batch_data_by_date.items():
        with st.expander(f"Attendees for {date_obj.strftime('%Y-%m-%d')} ({len(names_set)} found)"):
            if names_set:
                st.write(sorted(list(names_set)))
            else:
                st.write("No attendees extracted for this date from the files.")

    if st.button("Load Students & Prepare Attendance Tables", key="prepare_tables_button"):
        all_students_df, _ = load_students() # Unpack the tuple here
        if all_students_df is None or all_students_df.empty:
            st.error("Could not load student list. Please ensure students are registered on the 'Students' page.")
        else:
            st.session_state.prepared_attendance_dfs = {} # Clear previous prepared tables
            for date_obj, present_student_names in st.session_state.current_batch_data_by_date.items():
                temp_df = all_students_df.copy()
                # Ensure 'nombre' column exists and is the correct one for matching
                if 'nombre' not in temp_df.columns:
                    st.error("Student data is missing 'nombre' column. Cannot prepare attendance.")
                    st.session_state.prepared_attendance_dfs = {} # Clear out on error
                    break
                
                temp_df['Present'] = temp_df['nombre'].apply(lambda x: x in present_student_names)
                st.session_state.prepared_attendance_dfs[date_obj] = temp_df[["nombre", "Present"]]
            
            if st.session_state.prepared_attendance_dfs: # Check if any tables were actually prepared
                st.success("Attendance tables prepared. You can now review and edit them below.")
                # Clear current_batch_data_by_date as it's now moved to prepared_attendance_dfs
                st.session_state.current_batch_data_by_date = {}
                st.session_state.processed_files_this_session = set() # Allow reprocessing if user uploads more files now
                st.rerun() # Rerun to show the data editors
            # If loop completed but prepared_attendance_dfs is empty (e.g. due to error above), no success message needed

# --- Display and Edit Attendance Tables --- 
if st.session_state.prepared_attendance_dfs:
    st.divider()
    st.subheader("Step 3: Review and Save Attendance")
    st.caption("Review the attendance records below. Check the 'Present' box for students who attended. Uncheck for absentees.")

    all_saves_successful = True
    save_button_pressed = st.button("Save All Prepared Attendance", key="save_all_button")

    for date_obj, attendance_df in st.session_state.prepared_attendance_dfs.items():
        st.markdown(f"#### Attendance for: {date_obj.strftime('%Y-%m-%d')}")
        if attendance_df.empty:
            st.warning(f"No student data to display for {date_obj.strftime('%Y-%m-%d')}. Ensure students are loaded.")
            continue

        edited_df = st.data_editor(
            attendance_df, 
            key=f"attendance_editor_{date_obj.strftime('%Y%m%d')}",
            column_config={
                "nombre": st.column_config.TextColumn("Student Name", disabled=True),
                "Present": st.column_config.CheckboxColumn("Present?", default=False)
            },
            use_container_width=True,
            hide_index=True
        )
        st.session_state.prepared_attendance_dfs[date_obj] = edited_df # Update with edits

    if save_button_pressed:
        if not st.session_state.prepared_attendance_dfs:
            st.warning("No attendance data to save.")
        else:
            for date_obj, df_to_save in st.session_state.prepared_attendance_dfs.items():
                # Convert DataFrame to the required format for save_attendance (list of dicts)
                final_attendance_to_save = []
                for _, row in df_to_save.iterrows():
                    final_attendance_to_save.append({
                        "name": row["nombre"],
                        "status": "Present" if row["Present"] else "Absent"
                        # Add other fields like 'notes' if they become relevant again
                    })
                
                if save_attendance(date_obj, final_attendance_to_save):
                    st.success(f"Attendance for {date_obj.strftime('%Y-%m-%d')} saved successfully!")
                else:
                    st.error(f"Failed to save attendance for {date_obj.strftime('%Y-%m-%d')}.")
                    all_saves_successful = False
            
            if all_saves_successful:
                st.balloons()
                st.session_state.prepared_attendance_dfs = {} # Clear after saving
                st.session_state.current_batch_data_by_date = {} # Clear any residual raw data
                st.session_state.processed_files_this_session = set() # Clear processed files log
                # Reset file uploader by changing its key
                st.session_state.uploader_key_suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
                st.rerun()

# --- Footer/Instructions or other UI elements ---
# st.markdown("--- ")
# st.info("Upload files. Review extracted names. Prepare tables. Edit. Save.")
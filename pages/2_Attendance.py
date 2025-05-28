# c:\Users\JulioRodriguez\Documents\GitHub\streamlit\pages\2_Attendance.py
import streamlit as st
import pandas as pd
import datetime
import io
import re # For regular expressions
from config import setup_page
from utils import load_students, save_attendance # Removed load_attendance from here

# Setup page
setup_page("Upload Daily Attendance")

def extract_date_from_filename(filename: str) -> datetime.date | None:
    """
    Extracts date (M-D-YY or MM-DD-YY) from filename, assuming it follows "Attendance report ".
    Converts to YYYY-MM-DD.
    """
    try:
        # Case-insensitive search for "Attendance report "
        # We split the string by "Attendance report " and take the part after it.
        parts = re.split(r'Attendance report ', filename, flags=re.IGNORECASE)
        if len(parts) > 1:
            # The date string should be at the beginning of parts[1]
            # Strip any leading/trailing whitespace from this part
            date_str_candidate = parts[1].strip()
            
            # Regex to find M-D-YY or MM-DD-YY at the start of the candidate string
            # This ensures we only match if the date is right after "Attendance report "
            match = re.match(r'(\d{1,2})-(\d{1,2})-(\d{2})', date_str_candidate)
            if match:
                month, day, year_short = map(int, match.groups())
                year = 2000 + year_short # Assuming 21st century
                try:
                    return datetime.date(year, month, day)
                except ValueError: # Handles invalid dates like 2-30-25
                    return None
    except Exception: 
        # Broad exception to catch any unexpected errors during splitting or matching
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
            # st.write(f"Found '2. Participants' at line index {i}") # DEBUG
            continue # Continue, as end marker could be later
        
        if start_marker_found_at != -1 and line_stripped_lower.startswith("3. in-meeting activities"):
            end_marker_found_at = i
            # st.write(f"Found '3. In-Meeting Activities' at line index {i}") # DEBUG
            break 

    if start_marker_found_at == -1:
        st.warning(f"Could not find the '2. Participants' section marker in '{filename_for_debug}'.")
        return []

    # Determine the slice of lines that contains participant data
    # These are lines *after* "2. Participants" and *before* "3. In-Meeting Activities"
    actual_data_start_index = start_marker_found_at + 1
    
    if end_marker_found_at != -1:
        actual_data_end_index = end_marker_found_at
    else:
        # If "3. In-Meeting Activities" wasn't found, assume data goes to end of file
        actual_data_end_index = len(lines)
        # st.write("'3. In-Meeting Activities' not found; processing until end of file.") # DEBUG

    participant_data_lines = lines[actual_data_start_index : actual_data_end_index]

    if not participant_data_lines:
        st.warning(f"No data lines found between '2. Participants' and '3. In-Meeting Activities' (or end of file) in '{filename_for_debug}'.")
        return []

    # st.write(f"Extracted {len(participant_data_lines)} lines for CSV parsing (Header + Data):") # DEBUG
    # for i, l_debug in enumerate(participant_data_lines[:5]): # DEBUG
    #     st.text(f"  Sample line {i}: '{l_debug}'") # DEBUG

    # Now, find the actual header row (e.g., "Name\tFirst Join...") within this block
    header_row_index_in_block = -1
    for i, line_in_block in enumerate(participant_data_lines):
        line_norm = line_in_block.strip().lower()
        # More robust check for typical header fields
        if "name" in line_norm and ("first join" in line_norm or "last leave" in line_norm or "email" in line_norm or "duration" in line_norm):
            header_row_index_in_block = i
            # st.write(f"Potential header found at index {i} in block: '{line_in_block.strip()}'") # DEBUG
            break
            
    if header_row_index_in_block == -1:
        st.warning(f"Could not find the data header row (e.g., 'Name First Join...') within the '2. Participants' section of '{filename_for_debug}'.")
        # st.write("Block where header was searched:") # DEBUG
        # for l_hdr_debug in participant_data_lines: st.text(l_hdr_debug) # DEBUG
        return []

    # The CSV-like data starts from this identified header line
    csv_like_data_for_pandas = "\n".join(participant_data_lines[header_row_index_in_block:])
    
    try:
        df = pd.read_csv(io.StringIO(csv_like_data_for_pandas), sep='\t')
        df.columns = [col.strip().lower() for col in df.columns] # Normalize column names
        
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

# Main UI
st.header("Upload Attendance Report Files")
st.caption("Upload one or more attendance CSV report files for a single day. The date will be detected from the filenames.")

target_date = st.session_state.get('target_attendance_date', None)
processed_files_this_run = set()

# Load master student list
students_df, _ = load_students()

if students_df is None or students_df.empty:
    st.warning("No students found in the master list. Please upload students on the 'Students' page first.")
else:
    students_df.columns = students_df.columns.str.lower()
    required_columns = {'nombre'} # Assuming 'nombre' is the key for matching
    if not required_columns.issubset(students_df.columns):
        st.error(f"Master student list is missing required columns: {required_columns - set(students_df.columns)}")
    else:
        all_student_names_from_master_list = sorted(students_df['nombre'].astype(str).str.strip().unique())

        uploaded_reports = st.file_uploader(
            "Upload meeting attendance CSV report(s)",
            type=['csv'],
            accept_multiple_files=True,
            key=f"report_uploader_daily" # Simpler key as date is dynamic
        )

        current_batch_target_date = None
        current_batch_present_students = set()
        files_processed_in_batch = 0
        files_skipped_in_batch = 0

        if uploaded_reports:
            # Determine target date from the first valid file in this batch
            for report_file in uploaded_reports:
                if report_file.name not in processed_files_this_run: # Avoid reprocessing if script re-runs without new upload
                    date_from_file = extract_date_from_filename(report_file.name)
                    if date_from_file:
                        current_batch_target_date = date_from_file
                        st.session_state['target_attendance_date'] = current_batch_target_date
                        target_date = current_batch_target_date # Update local target_date
                        st.info(f"Detected attendance date from '{report_file.name}': **{target_date.strftime('%B %d, %Y')}**")
                        break # Date set from the first valid file
            
            if not current_batch_target_date and not target_date: # If still no date after checking all new files
                 st.error("Could not determine attendance date from any of the uploaded filenames. Ensure filenames contain a date like 'MM-DD-YY'.")
            
            if target_date: # If a target date is established (either from this batch or previous in session)
                st.subheader(f"Preparing Attendance for: {target_date.strftime('%B %d, %Y')}")
                with st.spinner("Processing attendance reports..."):
                    for report_file in uploaded_reports:
                        if report_file.name in processed_files_this_run:
                            continue # Already processed this file in this specific script run / uploader state

                        date_from_this_file = extract_date_from_filename(report_file.name)
                        if not date_from_this_file or date_from_this_file != target_date:
                            st.warning(f"Skipping '{report_file.name}': Date mismatch or no date found (expected for {target_date.strftime('%Y-%m-%d')}).")
                            files_skipped_in_batch +=1
                            processed_files_this_run.add(report_file.name)
                            continue

                        file_bytes = report_file.getvalue()
                        file_content_str = None
                        successful_encoding = None # Keep track of which encoding worked

                        # Try UTF-16 first as it's common for these CSVs from Microsoft products
                        try:
                            # st.write(f"Attempting to decode {report_file.name} with utf-16...") # DEBUG
                            file_content_str = file_bytes.decode('utf-16')
                            successful_encoding = 'utf-16'
                            # st.write(f"Successfully decoded {report_file.name} with utf-16.") # DEBUG
                        except UnicodeDecodeError:
                            # st.write(f"Failed to decode {report_file.name} with utf-16. Trying other encodings...") # DEBUG
                            # If UTF-16 fails, try others
                            other_encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252'] # Added cp1252
                            for enc in other_encodings:
                                try:
                                    # st.write(f"Attempting to decode {report_file.name} with {enc}...") # DEBUG
                                    file_content_str = file_bytes.decode(enc)
                                    successful_encoding = enc
                                    # st.write(f"Successfully decoded {report_file.name} with {enc}.") # DEBUG
                                    break # Stop if an encoding works
                                except UnicodeDecodeError:
                                    # st.write(f"Failed to decode {report_file.name} with {enc}.") # DEBUG
                                    continue 
                            try:
                                file_content_str = file_bytes.decode(encoding)
                                break
                            except UnicodeDecodeError:
                                continue
                        
                        if file_content_str is None:
                            st.error(f"Failed to decode {report_file.name}. Tried: {', '.join(encodings_to_try)}.")
                            files_skipped_in_batch +=1
                            processed_files_this_run.add(report_file.name)
                            continue

                        names_from_report = parse_attendance_report(file_content_str, report_file.name)
                        if names_from_report:
                            current_batch_present_students.update(names_from_report)
                            files_processed_in_batch += 1
                        else:
                            st.warning(f"Could not extract names from '{report_file.name}'.")
                            files_skipped_in_batch +=1
                        processed_files_this_run.add(report_file.name)

                if files_processed_in_batch > 0:
                    st.success(f"Processed {files_processed_in_batch} report(s) for {target_date.strftime('%Y-%m-%d')}. Found {len(current_batch_present_students)} unique attendees.")
                if files_skipped_in_batch > 0:
                    st.warning(f"Skipped {files_skipped_in_batch} report(s) due to date mismatch or decoding issues.")


        if target_date: # Only show editor if a target date is set
            # Prepare DataFrame for st.data_editor
            # This is purely based on master list and current batch's processed reports
            editor_df_rows = []
            for student_name in all_student_names_from_master_list:
                is_present = student_name in current_batch_present_students
                editor_df_rows.append({
                    "Student Name": student_name,
                    "Present": is_present
                })

            if not editor_df_rows:
                st.info("No students to display from master list.")
            else:
                input_df = pd.DataFrame(editor_df_rows)
                
                st.markdown("### Mark Attendance")
                st.caption(f"Review and confirm attendance for **{target_date.strftime('%B %d, %Y')}**. Unlisted students from reports will not be added to the master list here.")

                edited_df = st.data_editor(
                    input_df,
                    key=f"attendance_editor_{target_date.strftime('%Y%m%d')}",
                    column_config={
                        "Student Name": st.column_config.TextColumn(disabled=True),
                        "Present": st.column_config.CheckboxColumn("Present", default=False),
                    },
                    use_container_width=True,
                    num_rows="fixed"
                )

                if st.button("Save Attendance", key=f"save_btn_{target_date.strftime('%Y%m%d')}"):
                    final_attendance_to_save = {}
                    for _, row in edited_df.iterrows():
                        s_name = row['Student Name']
                        s_present = row['Present']
                        final_status = 'present' if s_present else 'absent'
                        
                        final_attendance_to_save[s_name] = {
                            'name': s_name,
                            'status': final_status,
                            'notes': '' # Notes are not handled in this simplified import view
                        }
                    
                    if save_attendance(target_date, final_attendance_to_save):
                        st.success(f"Attendance for {target_date.strftime('%Y-%m-%d')} saved successfully!")
                        st.session_state['target_attendance_date'] = None # Reset for next batch
                        st.rerun() # To clear uploader and refresh
                    else:
                        st.error("Failed to save attendance.")
        elif not uploaded_reports: # Only show if no files are uploaded yet, and no target_date from session
            st.info("Upload attendance report files to begin.")
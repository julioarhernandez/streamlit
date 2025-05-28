# c:\Users\JulioRodriguez\Documents\GitHub\streamlit\pages\3_Reports.py
import streamlit as st
import pandas as pd
import datetime
from config import setup_page # Assuming db is implicitly used by load_attendance via utils
from utils import load_attendance, load_students # Use the centralized functions

# Setup page
setup_page("Attendance Reports")

# Main UI
st.header("View Attendance Records")

# Date selectors for range
today = datetime.date.today()
# Default start date to the first day of the current month for a more common report view
default_start_date = today.replace(day=1) 

start_date = st.date_input("Start Date", default_start_date, key="report_start_date")
end_date = st.date_input("End Date", today, key="report_end_date")

if start_date > end_date:
    st.error("Error: Start date cannot be after end date.")
else:
    if st.button("Generate Report", key="generate_report_btn"): # Changed button label
        # 1. Load all students
        all_students_df, _ = load_students()
        if all_students_df is None or all_students_df.empty:
            st.error("Could not load student list. Please register students on the 'Students' page.")
            st.stop()
        
        # Assuming student names are in 'nombre' column and are unique identifiers
        master_student_list = set(all_students_df['nombre'].astype(str).str.strip().unique())
        total_registered_students = len(master_student_list)

        # 2. Process attendance data for the date range
        daily_summary_data = []
        students_present_in_range = set()
        
        current_date_iter = start_date
        with st.spinner(f"Loading and processing attendance from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}..."):
            while current_date_iter <= end_date:
                daily_attendance_dict = load_attendance(current_date_iter) # {name: {'status': 'Present', ...}}
                
                present_today_count = 0
                if daily_attendance_dict:
                    for student_name, details in daily_attendance_dict.items():
                        # Ensure names are consistently handled (e.g. case, stripping) if needed for matching
                        # For now, assume names from load_attendance match those in master_student_list
                        if details.get('status', '').lower() == 'present':
                            present_today_count += 1
                            students_present_in_range.add(student_name) # Or details.get('name', student_name)
                
                absent_today_count = total_registered_students - present_today_count
                daily_summary_data.append({
                    'Date': current_date_iter.strftime('%Y-%m-%d'),
                    '# Present': present_today_count,
                    '# Absent': absent_today_count
                })
                current_date_iter += datetime.timedelta(days=1)
        
        # 3. Display Daily Summary Report
        if daily_summary_data:
            st.subheader(f"Daily Attendance Summary: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            df_summary_display = pd.DataFrame(daily_summary_data)
            st.dataframe(df_summary_display, use_container_width=True, hide_index=True)
            
            csv_export = df_summary_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Summary Report as CSV",
                data=csv_export,
                file_name=f"daily_attendance_summary_{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}.csv",
                mime='text/csv',
                key='download_summary_csv_btn'
            )
        else:
            st.info("No attendance data processed for the selected date range to generate a summary.")

        # 4. Identify and Display Students Who Never Attended
        st.divider()
        st.subheader("Students Who Never Attended in Selected Range")
        students_never_attended = master_student_list - students_present_in_range
        
        if students_never_attended:
            st.warning(f"{len(students_never_attended)} student(s) had no 'Present' records in this period:")
            for student_name in sorted(list(students_never_attended)):
                st.markdown(f"- {student_name}")
        else:
            st.success("All registered students attended at least once in the selected date range.")

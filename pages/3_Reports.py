# c:\Users\JulioRodriguez\Documents\GitHub\streamlit\pages\3_Reports.py
import streamlit as st
import pandas as pd
import datetime
from config import setup_page # Assuming db is implicitly used by load_attendance via utils
from utils import load_attendance # Use the centralized function

# Setup page
setup_page("Attendance Reports")

# Main UI
st.header("View Attendance Records")

# Date selectors for range
today = datetime.date.today()
default_start_date = today - datetime.timedelta(days=7)

start_date = st.date_input("Start Date", default_start_date, key="report_start_date")
end_date = st.date_input("End Date", today, key="report_end_date")

if start_date > end_date:
    st.error("Error: Start date cannot be after end date.")
else:
    if st.button("View Records", key="view_records_btn"):
        records_found = False
        all_attendance_data = []
        
        current_date_iter = start_date
        with st.spinner(f"Loading attendance records from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}..."):
            while current_date_iter <= end_date:
                daily_attendance_dict = load_attendance(current_date_iter) # Fetches {student_name: {details}}
                if daily_attendance_dict:
                    records_found = True
                    for student_name, details in daily_attendance_dict.items():
                        all_attendance_data.append({
                            'Date': current_date_iter.strftime('%Y-%m-%d'),
                            'Student Name': details.get('name', student_name), # Use stored name, fallback to key
                            'Status': details.get('status', 'N/A').title(),
                            'Notes': details.get('notes', '')
                        })
                current_date_iter += datetime.timedelta(days=1)
        
        if records_found:
            st.subheader(f"Attendance from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            df_display = pd.DataFrame(all_attendance_data)
            
            if df_display.empty:
                st.info("No attendance records found for the selected date range.")
            else:
                # Reorder columns for better display
                cols_order = ['Date', 'Student Name', 'Status', 'Notes']
                df_display = df_display[cols_order]
                st.dataframe(df_display, use_container_width=True)
                
                csv_export = df_display.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Report as CSV",
                    data=csv_export,
                    file_name=f"attendance_report_{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}.csv",
                    mime='text/csv',
                    key='download_report_csv_btn'
                )
        else:
            st.info("No attendance records found for the selected date range.")

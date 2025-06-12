# c:\Users\JulioRodriguez\Documents\GitHub\streamlit\utils.py
import streamlit as st
import pandas as pd
from config import db # Assuming db is your Firebase Realtime Database reference from config.py
import datetime # Added for type hinting and date operations

def get_students_by_email(email):
    """
    Retrieves student records from the database based on the provided email.
    This function is designed for a database structure where the email
    is the primary key under 'students', and its value is an object
    containing a 'data' array of student details.

    Args:
        email (str): The email address which is also the key under the 'students' node.

    Returns:
        dict: A dictionary of student records if found, or an empty dictionary
              if no students are found or an error occurs.
    """
    try:
        # Reference to the 'students' node in your database
        students_ref = db.child("students")

        # Directly access the student data using the email as the key.
        # Firebase keys cannot contain '.', '#', '$', '[', or ']'
        # If your email keys literally contain '.' like "cba2@iti.edu",
        # you might need to escape them or store them differently if direct
        # key access doesn't work. However, typically, Firebase handles
        # this if the key was set using a string.
        snapshot = students_ref.child(email.replace('.', ',')).get() # Common workaround for '.' in keys

        # Check if any data was returned for that specific email key
        if not snapshot.val():
            print(f"No student entry found for email key: {email}")
            return {}

        # The data under this email key is an object, and within it,
        # you have a 'data' array.
        student_data_array = snapshot.val().get("data")

        if not student_data_array:
            print(f"No 'data' array found for email key: {email}")
            return {}

        # If you want to return a dictionary where keys are derived (e.g., index)
        # or if you just want the list of student objects:
        found_students = {}
        for i, student_record in enumerate(student_data_array):
            # You might want a unique key for each student record.
            # Using a combination of email and index, or a 'canvas_id' if unique.
            key = f"{email}_{i}" # Example key: "cba2@iti.edu_0"
            found_students[key] = student_record

        print(f"Found {len(student_data_array)} records for email key: {email}")
        print(found_students)
        return found_students

    except Exception as e:
        print(f"Error querying students by email key '{email}': {str(e)}")
        return {}

@st.cache_data
def get_student_group_emails():
    """
    Retrieves the top-level email keys (representing student groups)
    from the 'students' node in the database.

    Returns:
        list: A list of email strings (e.g., "cba2@iti,edu"), or an empty list
              if no student groups are found or an error occurs.
    """
    try:
        students_ref = db.child("students")
        students_snapshot = students_ref.get()
        print('\n\n---------------------------------database readed-------------------------\n\n', {k: v['data'][0] if v and 'data' in v else None for k, v in students_snapshot.val().items()})

        if not students_snapshot.val():
            print("No student entries found in the database")
            return []

        email_keys = []
        for student_key, _ in students_snapshot.val().items():
            email_keys.append(student_key)

        print(f"Found {len(email_keys)} student group emails.")
        print(email_keys)
        return email_keys

    except Exception as e:
        print(f"Error retrieving student group emails: {str(e)}")
        return []
    
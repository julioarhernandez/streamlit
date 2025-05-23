import firebase_admin
from firebase_admin import credentials, firestore
import os

def initialize_firebase():
    try:
        # Check if Firebase app is already initialized
        if not firebase_admin._apps:
            # Initialize with service account key
            cred = credentials.Certificate('firebase-key.json')
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        return None

def save_user_session(user_id, session_data):
    try:
        db = initialize_firebase()
        if db:
            user_ref = db.collection('user_sessions').document(user_id)
            user_ref.set({
                'last_login': firestore.SERVER_TIMESTAMP,
                'sessions': firestore.ArrayUnion([session_data])
            }, merge=True)
            return True
    except Exception as e:
        print(f"Error saving user session: {e}")
    return False

def get_user_sessions(user_id):
    try:
        db = initialize_firebase()
        if db:
            user_doc = db.collection('user_sessions').document(user_id).get()
            if user_doc.exists:
                return user_doc.to_dict().get('sessions', [])
    except Exception as e:
        print(f"Error getting user sessions: {e}")
    return []

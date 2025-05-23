import firebase_admin
from firebase_admin import credentials, db, exceptions
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, Union, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firebase if not already initialized
def initialize_firebase():
    try:
        if not firebase_admin._apps:
            if not os.path.exists('firebase-key.json'):
                logger.error("Firebase key file not found. Please ensure firebase-key.json exists.")
                return False
                
            try:
                cred = credentials.Certificate('firebase-key.json')
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://attendance-bfa78-default-rtdb.firebaseio.com/'
                })
                logger.info("Firebase initialized successfully")
                return True
            except ValueError as ve:
                logger.error(f"Invalid Firebase credentials: {ve}")
                return False
            except Exception as e:
                logger.error(f"Error initializing Firebase: {e}")
                return False
        return True
    except Exception as e:
        logger.error(f"Unexpected error initializing Firebase: {e}")
        return False

# Initialize Firebase when this module is imported
firebase_initialized = initialize_firebase()

def get_reference(path: str = ''):
    """Get a reference to the specified path in the Realtime Database"""
    return db.reference(path)

def save_user_session(user_id: str, session_data: dict, residentes_data: dict = None, 
                     asistencia_data: list = None) -> bool:
    """
    Save user session and file contents to Firebase Realtime Database
    
    Args:
        user_id: Unique user identifier
        session_data: Session metadata (login time, etc.)
        residentes_data: Content of residentes file
        asistencia_data: List of asistencia file contents
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not firebase_initialized:
        logger.error("Cannot save session: Firebase not initialized")
        return False
        
    if not user_id or not isinstance(session_data, dict):
        logger.error("Invalid user_id or session_data")
        return False
    
    try:
        db_ref = get_reference(f'user_sessions/{user_id}')
        
        # Prepare data to save with timestamp
        timestamp = datetime.now().isoformat()
        data = {
            'last_login': timestamp,
            'sessions': {
                timestamp: {
                    **session_data,
                    'timestamp': timestamp
                }
            }
        }
        
        # Add file contents if provided
        if residentes_data and isinstance(residentes_data, dict):
            data['last_residentes'] = residentes_data
        
        if asistencia_data and isinstance(asistencia_data, list):
            data['last_asistencia'] = asistencia_data
        
        # Update the data
        db_ref.update(data)
        logger.info(f"Session saved successfully for user: {user_id}")
        return True
        
    except exceptions.FirebaseError as fe:
        logger.error(f"Firebase error saving session: {fe}")
        return False
    except Exception as e:
        logger.error(f"Error saving user session: {e}", exc_info=True)
        return False

def get_user_last_session(user_id: str) -> Optional[dict]:
    """
    Get the user's last session data including file contents
    
    Args:
        user_id: Unique user identifier
        
    Returns:
        dict: Contains session data and file contents if available, None if not found or error
    """
    if not firebase_initialized:
        logger.error("Cannot get session: Firebase not initialized")
        return None
        
    if not user_id:
        logger.error("Invalid user_id provided")
        return None
    
    try:
        db_ref = get_reference(f'user_sessions/{user_id}')
        data = db_ref.get()
        
        if not data:
            logger.info(f"No session data found for user: {user_id}")
            return None
            
        # Get the most recent session
        session_data = {}
        if 'sessions' in data and data['sessions']:
            try:
                # Get the most recent session by timestamp
                latest_session_key = max(data['sessions'].keys())
                session_data = data['sessions'][latest_session_key]
                
                # Ensure we have required session data
                if not isinstance(session_data, dict):
                    logger.warning("Invalid session data format")
                    return None
                
                # Add file contents to the session data if available
                if 'last_residentes' in data:
                    session_data['last_residentes'] = data['last_residentes']
                if 'last_asistencia' in data:
                    session_data['last_asistencia'] = data['last_asistencia']
                
                logger.info(f"Retrieved session data for user: {user_id}")
                return session_data
                
            except (ValueError, KeyError) as e:
                logger.error(f"Error processing session data: {e}")
                return None
                
        return None
        
    except exceptions.FirebaseError as fe:
        logger.error(f"Firebase error getting session: {fe}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting user session: {e}", exc_info=True)
        return None

def get_user_sessions(user_id: str) -> List[dict]:
    """
    Get all sessions for a specific user
    
    Args:
        user_id: Unique user identifier
        
    Returns:
        List[dict]: List of session data dictionaries, empty list if none found or error
    """
    if not firebase_initialized:
        logger.error("Cannot get sessions: Firebase not initialized")
        return []
        
    if not user_id:
        logger.error("Invalid user_id provided")
        return []
    
    try:
        db_ref = get_reference(f'user_sessions/{user_id}/sessions')
        sessions = db_ref.get()
        
        if not sessions:
            logger.info(f"No sessions found for user: {user_id}")
            return []
            
        # Convert the sessions dictionary to a list of session objects
        session_list = []
        try:
            for timestamp, session_data in sessions.items():
                if isinstance(session_data, dict):  # Ensure it's a session object
                    session_list.append({
                        'timestamp': timestamp,
                        'login_time': session_data.get('login_time', ''),
                        'user_agent': session_data.get('user_agent', ''),
                        'session_id': session_data.get('session_id', '')
                    })
            
            # Sort sessions by timestamp (newest first)
            session_list.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            logger.info(f"Retrieved {len(session_list)} sessions for user: {user_id}")
            return session_list
            
        except (ValueError, KeyError, AttributeError) as e:
            logger.error(f"Error processing sessions data: {e}")
            return []
        
    except exceptions.FirebaseError as fe:
        logger.error(f"Firebase error getting sessions: {fe}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting user sessions: {e}", exc_info=True)
        return []

def save_user_files(user_id: str, residentes_data: dict = None, asistencia_data: list = None) -> bool:
    """
    Save user files to Firebase Realtime Database
    
    Args:
        user_id: Unique user identifier
        residentes_data: Dict containing residentes file content and metadata
        asistencia_data: List of asistencia file contents with metadata
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not firebase_initialized:
        logger.error("Cannot save files: Firebase not initialized")
        return False
        
    if not user_id:
        logger.error("Invalid user_id provided")
        return False
    
    if not residentes_data and not asistencia_data:
        logger.warning("No data provided to save")
        return False
    
    try:
        db_ref = get_reference(f'user_sessions/{user_id}')
        
        # Prepare data to save with timestamp
        timestamp = datetime.now().isoformat()
        data = {
            'last_updated': timestamp
        }
        
        # Add residentes data if provided
        if residentes_data and isinstance(residentes_data, dict):
            data['residentes'] = {
                'content': residentes_data.get('content', {}),
                'filename': residentes_data.get('filename', 'residentes.csv'),
                'updated_at': timestamp
            }
            logger.info("Prepared residentes data for saving")
            
        # Add asistencia data if provided
        if asistencia_data and isinstance(asistencia_data, list):
            data['asistencia'] = {
                'content': asistencia_data,
                'filenames': [f.get('filename', 'asistencia.csv') for f in asistencia_data],
                'updated_at': timestamp
            }
            logger.info(f"Prepared {len(asistencia_data)} asistencia files for saving")
        
        # Update the data in Firebase
        db_ref.update(data)
        logger.info("Successfully saved user files to Firebase")
        return True
        
    except exceptions.FirebaseError as fe:
        logger.error(f"Firebase error saving files: {fe}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving user files: {e}", exc_info=True)
        return False
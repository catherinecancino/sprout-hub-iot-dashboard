import os
import firebase_admin
from firebase_admin import credentials, firestore

# Build path to the key file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_PATH = os.path.join(BASE_DIR, 'serviceAccountKey.json')

def initialize_firestore():
    # Check if firebase is already initialized to avoid errors during auto-reload
    if not firebase_admin._apps:
        cred = credentials.Certificate(KEY_PATH)
        firebase_admin.initialize_app(cred)
    
    # Return the database client
    return firestore.client()

# Initialize immediately
db = initialize_firestore()
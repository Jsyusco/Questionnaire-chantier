import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. INITIALISATION FIREBASE (ULTRA-SIMPLIFIÉE) ---
def initialize_firebase_test():
    """Initialise Firebase en utilisant le dictionnaire de secrets et l'ID de projet."""
    if firebase_admin._apps:
        # L'application est déjà initialisée si ce bloc est revu
        return firestore.client()

    try:
        # Récupération et assemblage manuel des secrets
        cred_dict = {
            "type": st.secrets["firebase_type"],
            "project_id": st.secrets["firebase_project_id"],
            "private_key_id": st.secrets["firebase_private_key_id"],
            # L'étape cruciale : gère les sauts de ligne
            "private_key": st.secrets["firebase_private_key"].replace('\\n', '\n'),
            "client_email": st.secrets["firebase_client_email"],
            "client_id": st.secrets["firebase_client_id"],
            "auth_uri": st.secrets["firebase_auth_uri"],
            "token_uri": st.secrets["firebase_token_uri"],
            "auth_provider_x509_cert_url": st.secrets["firebase_auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["firebase_client_x509_cert_url"],
            "universe_domain": st.secrets["firebase_universe_domain"],
        }
        
        project_id = cred_dict["project_id"]
        
        # 2. Utilisation du dictionnaire Python réel pour l'initialisation
        cred = credentials.Certificate(cred_dict) 
        
        # Initialisation explicite avec l'ID du projet
        firebase_admin.initialize_app(cred, {'projectId': project_id})
        
        st.success("1. Initialisation Firebase réussie ! ✅")
        return firestore.client()
    
    except KeyError as e:
        st.error(f"Erreur critique: Clé de secret manquante ({e}). Vérifiez votre fichier de secrets.")
        st.stop()
    except Exception as e:
        # Si une erreur 403 survient, elle sera affichée ici.
        st.error(f"1. Erreur d'initialisation Firebase (Connexion) : {e}")
        st.stop()

# --- 2. FONCTION DE TEST D'ACCÈS À FIREBASE ---
def test_firestore_access(db):
    """Tente de lire un seul document dans la collection 'formsquestions'."""
    st.header("Test d'Accès à Firestore")
    
    COLLECTION_NAME = 'formsquestions'
    
    try:
        # Tente de lire les 5 premiers documents de la collection 'formsquestions'
        docs = db.collection(COLLECTION_NAME).limit(5).get()
        
        if not docs:
            st.warning(f"2. Succès de la lecture, mais la collection '{COLLECTION_NAME}' est vide.")
        else:
            doc_count = len(docs)
            st.success(f"2. Accès Firestore réussi ! {doc_count} document(s) lu(s) dans '{COLLECTION_NAME}'. 🥳")
            # Afficher le premier document pour confirmation
            st.json(docs[0].to_dict()) 
            
    except Exception as e:
        # Si l'erreur 403 apparaît ici, cela confirme un problème de permissions (IAM ou Règles).
        st.error(f"2. Erreur lors de la lecture de la collection '{COLLECTION_NAME}' : {e}")
        st.stop()

# --- 3. FLUX PRINCIPAL ---
if __name__ == "__main__":
    st.set_page_config(page_title="Test Accès Firestore", layout="centered")
    
    db = initialize_firebase_test()
    
    if db:
        test_firestore_access(db)

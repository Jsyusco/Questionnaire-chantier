# --- IMPORTS ET PRÉPARATION ---
import streamlit as st
import pandas as pd
import uuid
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import numpy as np
import zipfile
import io
import json

# IMPORTS NÉCESSAIRES POUR GOOGLE DRIVE
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# --- CONFIGURATION ET STYLE (inchangés) ---
st.set_page_config(page_title="Formulaire Dynamique - Firestore", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #121212; color: #e0e0e0; }
    .main-header { background-color: #1e1e1e; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; border-bottom: 3px solid #E9630C; }
    .block-container { max-width: 800px; }
    .phase-block { background-color: #1e1e1e; padding: 25px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #333; }
    .question-card { background-color: transparent; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 3px solid #E9630C; }
    h1, h2, h3 { color: #ffffff !important; }
    .description { font-size: 0.9em; color: #aaaaaa; }
    .stButton>button {
        background-color: #E9630C;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        font-weight: bold;
        box-shadow: 0 4px #c2520a;
        transition: all 0.2s ease;
    }
    .stButton>button:active {
        box-shadow: 0 0 #c2520a;
        transform: translateY(4px);
    }
    .stDownloadButton>button {
        background-color: #333;
        color: #E9630C;
        border: 1px solid #E9630C;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# INITIALISATION FIREBASE & GOOGLE DRIVE
# ---------------------------------------------------------

# Initialisation de Firebase
def initialize_firebase():
    """Initialise Firebase si ce n'est pas déjà fait."""
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(json.loads(st.secrets["firebase"]["service_account"]))
            # Pas besoin de spécifier storageBucket ici car nous utilisons l'API Google Drive séparément
            firebase_admin.initialize_app(cred)
            st.toast("Firebase initialisé.")
        except Exception as e:
            st.error(f"Erreur d'initialisation de Firebase : Vérifiez les secrets 'firebase' ({e})")
            return None
    return firestore.client()

# Initialisation Google Drive
def get_drive_service():
    """Initialise et retourne le service Google Drive."""
    try:
        service_account_info = json.loads(st.secrets["google_drive"]["service_account_json"])
        
        creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/drive'] # Scope pour accès complet à Google Drive
        )
        
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Erreur d'initialisation Google Drive : Vérifiez les secrets 'google_drive' ({e})")
        return None

db = initialize_firebase()

# ---------------------------------------------------------
# FONCTIONS DE GESTION GOOGLE DRIVE
# ---------------------------------------------------------

def upload_file_to_drive(file_obj, project_name, phase_name, drive_service):
    """
    Uploade un objet fichier (UploadedFile) vers Google Drive.
    
    Retourne l'URL de visualisation du fichier.
    """
    try:
        # L'ID du dossier cible est stocké dans les secrets
        DRIVE_FOLDER_ID = st.secrets["google_drive"]["target_folder_id"]

        # Créer un nom de fichier unique et lisible
        # Ex: Auchan_Aubiere_Phase1_NomFichier.jpg
        sanitized_project = project_name.replace(' | ', '_').replace(' ', '_').replace('/', '_')
        sanitized_phase = phase_name.replace(' ', '_').replace('/', '_')
        file_name = f"{sanitized_project}_{sanitized_phase}_{file_obj.name}"
        
        # Méta-données du fichier
        file_metadata = {
            'name': file_name,
            'parents': [DRIVE_FOLDER_ID]  # Indique le dossier cible
        }
        
        # Préparer le contenu binaire
        file_obj.seek(0)
        media = MediaIoBaseUpload(io.BytesIO(file_obj.read()),
                                  mimetype=file_obj.type,
                                  resumable=True)
        
        # Exécuter l'upload
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink' # Récupère l'ID et le lien de visualisation
        ).execute()
        
        return uploaded_file.get('webViewLink')
    except Exception as e:
        st.error(f"Erreur lors de l'upload du fichier {file_obj.name} vers Google Drive : {e}")
        return None


# ---------------------------------------------------------
# FONCTIONS DE GESTION DES DONNÉES (CHARGEMENT, SAUVEGARDE)
# ---------------------------------------------------------

@st.cache_data
def load_data():
    """Charge les données du fichier Excel et prépare la structure."""
    try:
        # Le chemin du fichier est supposé être accessible par le script
        df = pd.read_excel("votre_fichier.xlsx", sheet_name='Site')
        df = df.fillna("-")
    except Exception as e:
        st.error(f"Erreur lors du chargement de l'Excel: {e}. Veuillez vérifier que 'votre_fichier.xlsx' est présent et que la feuille 'Site' existe.")
        # Utilisation des données de démo si l'Excel n'est pas trouvé
        data = {
            'Intitulé': ['Auchan | Aubière', 'Auchan | Aubervilliers', 'Auchan | Angoulême - La Couronne'],
            'L [Plan de Déploiement]': [10, '-', 8],
            'R [Plan de Déploiement]': [8, '-', 6],
            'Fournisseur Bornes DC [Bornes]': ['ALPITRONIC', '-', 'ALPITRONIC']
        }
        df = pd.DataFrame(data)

    # Créer une structure de formulaire basée sur les colonnes (sauf 'Intitulé')
    form_structure = [
        {"phase_name": col, "questions": [{"key": col, "type": "text_area", "label": f"Commentaire sur {col}", "description": "Saisissez les informations de suivi ici"},
                                         {"key": f"Photos_{col}", "type": "file_uploader", "label": "Photos / Justificatifs", "description": "Ajouter des photos du site", "accept_multiple_files": True, "type_files": ["png", "jpg", "jpeg"]}]}
        for col in df.columns if col != 'Intitulé'
    ]
    return df, form_structure


def save_form_data(collected_data, project_data, user_id, drive_service):
    """
    Sauvegarde les données du formulaire dans Firestore et uploade les photos
    vers Google Drive.
    """
    if not db:
        st.error("Connexion à Firestore échouée. Impossible de sauvegarder.")
        return False
        
    try:
        # Récupération du nom du projet
        project_name = project_data.get('Intitulé', 'Projet Inconnu')
        
        # Création du document principal pour Firestore
        document_data = {
            "project_id": project_data.get('Intitulé'),
            "project_metadata": project_data.to_dict(),
            "user_id": user_id,
            "timestamp": datetime.now(),
            "answers": []
        }
        
        # Traitement des réponses par phase
        for phase in collected_data:
            clean_phase = {
                "phase_name": phase["phase_name"],
                "answers": {}
            }
            
            for k, v in phase["answers"].items():
                # ---------------------------------------------
                # GESTION SPÉCIFIQUE DES FICHIERS (UPLOAD DRIVE)
                # ---------------------------------------------
                if isinstance(v, list) and v and hasattr(v[0], 'read'): 
                    drive_urls = []
                    
                    with st.spinner(f"Upload des photos pour '{phase['phase_name']}'..."):
                        for file_obj in v:
                            # APPEL À LA FONCTION D'UPLOAD DRIVE
                            url = upload_file_to_drive(file_obj, project_name, phase["phase_name"], drive_service)
                            if url:
                                drive_urls.append(url)
                    
                    # On sauvegarde la liste des URLs Google Drive dans Firestore
                    clean_phase["answers"][str(k)] = drive_urls
                    if not drive_urls:
                         st.warning(f"Aucune photo n'a été uploadée pour {phase['phase_name']} - {k}.")
                # ---------------------------------------------
                # GESTION DES AUTRES TYPES DE RÉPONSES
                # ---------------------------------------------
                else:
                    clean_phase["answers"][str(k)] = v

            document_data["answers"].append(clean_phase)

        # Sauvegarde finale dans Firestore
        doc_ref = db.collection("deploiement_form_submissions").document(f"{project_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        doc_ref.set(document_data)
        
        st.session_state['last_doc_id'] = doc_ref.id
        st.success(f"Données sauvegardées dans Firestore (Doc ID: {doc_ref.id}) et photos uploadées sur Google Drive !")
        return True

    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde finale ou de l'upload : {e}")
        return False

# --- FONCTIONS D'EXPORT (INCHANGÉES) ---

def create_csv_export(collected_data, df_struct):
    """Crée un buffer CSV à partir des données collectées."""
    # ... (code inchangé)
    # Simplified CSV creation for demonstration
    rows = []
    header = ['Project ID']
    
    # Construction de l'en-tête (une colonne par question)
    for phase in collected_data:
        for question_key in phase["answers"].keys():
            # Ajout de l'ID du projet + chaque question comme colonne
            header.append(f"{phase['phase_name']}_{question_key}")

    # Construction des lignes (ici une seule soumission)
    row_data = [st.session_state['project_data'].get('Intitulé', 'N/A')]
    for phase in collected_data:
        for v in phase["answers"].values():
            if isinstance(v, list):
                # Pour les URLs Drive, on les joint par un séparateur
                row_data.append("|".join(v)) 
            else:
                row_data.append(str(v))
    rows.append(row_data)

    df_export = pd.DataFrame(rows, columns=header)
    output = io.StringIO()
    df_export.to_csv(output, index=False)
    return output.getvalue()

def create_zip_export(collected_data):
    """
    Crée un buffer ZIP avec les fichiers (MAIS ICI NON DISPONIBLE CAR
    L'UPLOAD EST FAIT DIRECTEMENT SUR GOOGLE DRIVE)
    Nous retournons juste un message dans le ZIP ou un ZIP vide.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Ajout d'un fichier texte expliquant où trouver les photos
        message = (
            "Les photos ont été uploadées directement sur Google Drive.\n"
            "Veuillez consulter le lien enregistré dans la base de données Firestore "
            f"pour le document ID: {st.session_state.get('last_doc_id', 'N/A')}"
        )
        zf.writestr('LisezMoi_Photos_GoogleDrive.txt', message)
    zip_buffer.seek(0)
    return zip_buffer

# ---------------------------------------------------------
# LOGIQUE D'ÉTAT ET INTERFACE UTILISATEUR
# ---------------------------------------------------------

# Initialisations d'état
if 'current_index' not in st.session_state: st.session_state.current_index = 0
if 'form_page' not in st.session_state: st.session_state.form_page = 0
if 'collected_data' not in st.session_state: st.session_state.collected_data = []
if 'project_selected' not in st.session_state: st.session_state.project_selected = False
if 'data_saved' not in st.session_state: st.session_state.data_saved = False
if 'user_id' not in st.session_state: st.session_state['user_id'] = str(uuid.uuid4()) # ID utilisateur unique pour la session

df_struct, form_structure = load_data()
df_struct_cols = df_struct.columns.tolist()

# --- Fonctions de navigation ---
def next_page():
    if st.session_state.form_page < len(form_structure):
        # Sauvegarde temporaire des réponses avant de changer de page
        st.session_state.form_page += 1

def prev_page():
    if st.session_state.form_page > 0:
        st.session_state.form_page -= 1

def update_index_from_select():
    selection = st.session_state.selectbox_project
    idx = df_struct[df_struct['Intitulé'] == selection].index[0]
    st.session_state.current_index = idx
    st.session_state.project_selected = True # Indique que le formulaire peut démarrer

# --- Affichage du titre ---
st.markdown("<div class='main-header'><h1>FORMULAIRE DE SUIVI DE DÉPLOIEMENT</h1></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# ÉTAPE 1 : SÉLECTION DU PROJET
# ---------------------------------------------------------
if not st.session_state.project_selected:
    st.markdown("<h3>1. Sélectionner le Projet</h3>", unsafe_allow_html=True)
    
    st.selectbox(
        "Projet :",
        options=df_struct['Intitulé'].tolist(),
        index=st.session_state.current_index,
        key="selectbox_project",
        on_change=update_index_from_select,
        placeholder="Choisir l'intitulé du projet"
    )
    
    if st.session_state.project_selected:
        st.success(f"Projet sélectionné : {df_struct.iloc[st.session_state.current_index]['Intitulé']}")
        st.button("Démarrer le Formulaire", on_click=next_page)
    else:
        st.warning("Veuillez choisir un projet pour commencer le formulaire.")

# ---------------------------------------------------------
# ÉTAPE 2 : LE FORMULAIRE DYNAMIQUE
# ---------------------------------------------------------
elif st.session_state.form_page <= len(form_structure):
    project_data = df_struct.iloc[st.session_state.current_index]
    st.session_state['project_data'] = project_data

    current_phase_index = st.session_state.form_page - 1
    
    if current_phase_index >= 0:
        current_phase = form_structure[current_phase_index]
        
        st.markdown(f"<h3>Phase en cours : {current_phase['phase_name']}</h3>", unsafe_allow_html=True)
        st.caption(f"Étape {st.session_state.form_page} sur {len(form_structure)}")
        
        # Affichage des métadonnées du projet pour cette phase (lecture de l'Excel)
        st.markdown(f"<div class='question-card'><b>Métadonnée Excel :</b> {project_data[current_phase['phase_name']]}</div>", unsafe_allow_html=True)

        with st.form(key=f"form_phase_{current_phase_index}"):
            phase_answers = {}
            
            # Affichage des questions de la phase
            for question in current_phase['questions']:
                
                # Question de type Commentaire (Text Area)
                if question['type'] == 'text_area':
                    phase_answers[question['key']] = st.text_area(
                        label=question['label'],
                        help=question.get('description', ''),
                        key=f"ans_{question['key']}_{current_phase_index}"
                    )
                
                # Question de type Photo/Fichier (File Uploader)
                elif question['type'] == 'file_uploader':
                    uploaded_files = st.file_uploader(
                        label=question['label'],
                        type=question.get('type_files'),
                        accept_multiple_files=question.get('accept_multiple_files', False),
                        help=question.get('description', ''),
                        key=f"ans_{question['key']}_{current_phase_index}"
                    )
                    # Sauvegarder la liste des objets UploadedFile
                    phase_answers[question['key']] = uploaded_files
            
            # Bouton de soumission
            submitted = st.form_submit_button("Valider la Phase et Suivant")
            
            if submitted:
                # Stockage des données collectées
                phase_data = {
                    "phase_name": current_phase["phase_name"],
                    "answers": phase_answers
                }
                
                # Mise à jour de la session_state (on remplace si on revient en arrière)
                if len(st.session_state.collected_data) <= current_phase_index:
                    st.session_state.collected_data.append(phase_data)
                else:
                    st.session_state.collected_data[current_phase_index] = phase_data
                    
                next_page()
                st.rerun() # Rerun pour passer à la phase suivante ou à la page de confirmation

    # --- Barre de navigation ---
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.session_state.form_page > 1:
            st.button("⬅ Précédent", on_click=prev_page)
    with col2:
        if st.session_state.form_page <= len(form_structure) and current_phase_index < 0:
             # Cas où on vient de sélectionner le projet mais n'a pas encore cliqué sur "Démarrer"
             st.button("Démarrer", on_click=next_page)


# ---------------------------------------------------------
# ÉTAPE 3 : CONFIRMATION ET SAUVEGARDE
# ---------------------------------------------------------
elif st.session_state.form_page == len(form_structure) + 1:
    st.markdown("<h2>✅ Confirmation et Sauvegarde</h2>", unsafe_allow_html=True)
    st.info("Toutes les phases sont complétées. Vous pouvez maintenant sauvegarder les données.")
    
    # Affichage d'un résumé
    st.markdown("### Aperçu des réponses collectées")
    for data in st.session_state.collected_data:
        st.markdown(f"<div class='phase-block'><h4>{data['phase_name']}</h4></div>", unsafe_allow_html=True)
        for q, a in data['answers'].items():
            value_display = f"({len(a)} fichier(s) prêt(s) à l'upload)" if isinstance(a, list) else str(a)
            st.caption(f"**{q}:** {value_display}")
    
    if st.button("💾 Sauvegarder Définitivement dans Firestore & Google Drive"):
        # Initialiser le service Drive juste avant la sauvegarde
        drive_service = get_drive_service()
        if drive_service:
            if save_form_data(st.session_state.collected_data, st.session_state.project_data, st.session_state.user_id, drive_service):
                st.session_state['data_saved'] = True
            else:
                st.error("Échec de la sauvegarde.")

    st.button("⬅ Retour à la phase précédente", on_click=prev_page)

    # ---------------------------------------------------------
    # EXPORTS (UNIQUEMENT APRES SAUVEGARDE)
    # ---------------------------------------------------------
    if st.session_state['data_saved']:
        st.markdown("### 📥 Télécharger les données")
        
        col_csv, col_zip = st.columns(2)
        
        # --- Export CSV (Contiendra les URLs Drive) --
        csv_data = create_csv_export(st.session_state['collected_data'], df_struct)
        date_str = datetime.now().strftime('%Y%m%d_%H%M')
        file_name_csv = f"Export_{st.session_state['project_data'].get('Intitulé', 'Projet')}_{date_str}.csv"
        
        with col_csv:
            st.download_button(
                label="📄 Télécharger les réponses (CSV)",
                data=csv_data,
                file_name=file_name_csv,
                mime='text/csv'
            )

        # --- Export ZIP (Maintenant un message d'information) ---
        zip_buffer = create_zip_export(st.session_state['collected_data'])
        
        with col_zip:
            if zip_buffer:
                file_name_zip = f"InfoPhotos_{st.session_state['project_data'].get('Intitulé', 'Projet')}_{date_str}.zip"
                st.download_button(
                    label="ℹ️ Info Photos Drive (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=file_name_zip,
                    mime='application/zip',
                    help="Les fichiers réels sont sur Google Drive. Ce ZIP contient juste un fichier d'information."
                )

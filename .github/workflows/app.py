# --- IMPORTS ET PRÉPARATION ---
import streamlit as st
import pandas as pd
import uuid
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app 
from datetime import datetime
import numpy as np
import zipfile
import io
import urllib.parse 
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import json as JSON 

# --- CONSTANTES ESSENTIELLES ---
# DÉFINITION GLOBALE DE LA CONSTANTE MANQUANTE/INACCESSIBLE
ID_SECTION_NAME = "Identification du Projet"
REQUIRED_FIELDS = ['Intitulé', 'Site', 'Date']
DEFAULT_START_TIME = datetime.now()


# --- FIREBASE SETUP (Utilisation des variables globales fournies par Canvas) ---
db = None
try:
    # Les variables __app_id, __firebase_config, __initial_auth_token
    # sont fournies par l'environnement Canvas
    
    # 1. Parsing de la configuration
    if '__firebase_config' in locals() or '__firebase_config' in globals():
        firebaseConfig = JSON.loads(__firebase_config)
    else:
        firebaseConfig = {}
        raise NameError("__firebase_config n'est pas définie. Tentative d'initialisation en mode simulation.")
        
    # Initialize Firebase Admin SDK if not already done (pour Firestore)
    if not firebase_admin._apps:
        if 'project_id' in firebaseConfig:
            cred = credentials.Certificate(firebaseConfig)
            initialize_app(cred)
            db = firestore.client()
        else:
             raise Exception("Configuration Firebase invalide ou non fournie pour l'Admin SDK.")

except NameError as ne:
    st.warning(f"Avertissement: {ne}. Utilisation d'un dictionnaire local pour simuler la base de données.")
    db = {} 
except Exception as e:
    st.error(f"Erreur d'initialisation Firebase : {e}. Le formulaire ne pourra pas sauvegarder.")
    db = {}

# --- CONFIGURATION ET STYLE ---
st.set_page_config(page_title="Formulaire Dynamique - Firestore", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #121212; color: #e0e0e0; }
    .main-header { background-color: #1e1e1e; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; border-bottom: 3px solid #E9630C; }
    .block-container { max-width: 800px; }
    .phase-block { background-color: #1e1e1e; padding: 25px; border-radius: 10px; margin-top: 15px; border-left: 5px solid #E9630C; }
    .stButton>button {
        background-color: #E9630C;
        color: white;
        font-weight: bold;
        border: none;
        padding: 10px 20px;
        border-radius: 8px;
        transition: background-color 0.3s;
    }
    .stButton>button:hover {
        background-color: #d15a0b;
    }
</style>
""", unsafe_allow_html=True)


# --- FONCTIONS UTILITAIRES CRUCIALES POUR LES IMAGES ---

def process_files_for_storage(answers):
    """
    Convertit les objets UploadedFile temporaires en dictionnaires persistants 
    contenant les données binaires (bytes) pour les stocker dans le Session State.
    """
    processed_answers = {}
    for k, v in answers.items():
        # Cas d'une liste de fichiers (multi-upload)
        if isinstance(v, list) and v and hasattr(v[0], 'read'):
            files_data = []
            for f in v:
                f.seek(0) # IMPORTANT: repositionne le curseur au début
                files_data.append({
                    "name": f.name,
                    "type": f.type,
                    "content": f.read() # Stockage des bytes
                })
            processed_answers[k] = files_data
        # Cas d'un fichier unique
        elif hasattr(v, 'read'):
             v.seek(0)
             processed_answers[k] = {
                 "name": v.name, 
                 "type": v.type, 
                 "content": v.read()
             }
        else:
            processed_answers[k] = v
    return processed_answers


# --- FONCTIONS DE GESTION DE BASE ---

def init_session_state(df):
    """Initialise tous les états de session nécessaires."""
    if 'current_phase_index' not in st.session_state:
        st.session_state['current_phase_index'] = 0
    if 'step' not in st.session_state:
        st.session_state['step'] = 'UPLOAD_EXCEL'
    if 'excel_data' not in st.session_state:
        st.session_state['excel_data'] = None
    if 'all_phases' not in st.session_state:
        st.session_state['all_phases'] = []
    if 'collected_data' not in st.session_state:
        st.session_state['collected_data'] = []
    if 'current_phase_temp' not in st.session_state:
        st.session_state['current_phase_temp'] = {}
    if 'identification_completed' not in st.session_state:
        st.session_state['identification_completed'] = False
    if 'project_data' not in st.session_state:
        st.session_state['project_data'] = {}
    if 'show_comment_on_error' not in st.session_state:
        st.session_state['show_comment_on_error'] = False
    if 'form_start_time' not in st.session_state:
        st.session_state['form_start_time'] = DEFAULT_START_TIME
    if 'submission_id' not in st.session_state:
        st.session_state['submission_id'] = str(uuid.uuid4())
    if 'df_struct' not in st.session_state:
        # Initialise avec le dataframe de structure si disponible
        if df is not None:
             st.session_state['df_struct'] = df
        else:
             st.session_state['df_struct'] = pd.DataFrame()


def load_excel_structure(uploaded_file):
    """Charge l'Excel et prépare la structure des phases."""
    try:
        df = pd.read_excel(uploaded_file)
        
        # Nettoyage et préparation de la structure
        df.columns = df.columns.str.lower().str.strip()
        df = df.rename(columns={'id_phase': 'phase', 'question': 'question', 'type_reponse': 'type', 'id_question': 'id'})
        df['id'] = df['id'].astype(int)
        
        # Détermination des phases
        all_phases = [p for p in df['phase'].unique() if p != ID_SECTION_NAME and pd.notna(p)]
        
        # Stockage dans le session state
        st.session_state['excel_data'] = uploaded_file.name
        st.session_state['df_struct'] = df
        st.session_state['all_phases'] = all_phases
        st.session_state['step'] = 'IDENTIFICATION'
        st.session_state['form_start_time'] = datetime.now()
        st.session_state['submission_id'] = str(uuid.uuid4())
        st.session_state['collected_data'] = []
        st.session_state['current_phase_index'] = 0
        st.session_state['identification_completed'] = False
        st.success(f"Fichier '{uploaded_file.name}' chargé avec succès. {len(all_phases)} phases détectées.")
        
    except Exception as e:
        st.error(f"Erreur lors du chargement ou de la lecture du fichier Excel: {e}")

def get_phase_questions(df, phase_name):
    """Retourne les questions pour une phase donnée."""
    if df is not None and not df.empty and 'phase' in df.columns:
        return df[df['phase'] == phase_name].to_dict('records')
    return []

def save_form_data(collected_data, project_data):
    """Sauvegarde les données (sans les bytes d'images) dans Firestore."""
    global db 
    
    try:
        if db is None or isinstance(db, dict) and not db:
            return False, "Firestore n'est pas initialisé ou est en mode simulation sans collection."
            
        cleaned_data = []
        for phase in collected_data:
            clean_phase = {
                "phase_name": phase["phase_name"],
                "answers": {}
            }
            for k, v in phase["answers"].items():
                # On ne stocke pas les bytes d'images dans Firestore
                if isinstance(v, list) and v and isinstance(v[0], dict) and 'name' in v[0]: 
                    file_names = ", ".join([f['name'] for f in v])
                    clean_phase["answers"][str(k)] = f"Fichiers (non stockés en DB): {file_names}"
                else:
                    clean_phase["answers"][str(k)] = v
            
            cleaned_data.append(clean_phase)
        
        submission_id = st.session_state.get('submission_id', str(uuid.uuid4()))
        final_document = {
            "project_intitule": project_data.get('Intitulé', 'N/A'),
            "project_details": project_data,
            "submission_id": submission_id,
            "start_date": st.session_state.get('form_start_time', datetime.now()),
            "submission_date": datetime.now(),
            "status": "Completed",
            "collected_phases": cleaned_data
        }
        
        if isinstance(db, dict):
            print(f"Simulating Firestore save: {submission_id} with data...")
            
        else:
            doc_id_base = str(project_data.get('Intitulé', 'form')).replace(" ", "_").replace("/", "_")[:20]
            doc_id = f"{doc_id_base}_{datetime.now().strftime('%Y%m%d_%H%M')}_{submission_id[:6]}"
            db.collection('FormAnswers').document(doc_id).set(final_document)
            
        return True, submission_id 
    except Exception as e:
        return False, str(e)

# Attention: Cette partie doit être exécutée après la partie 1 
# et suppose que toutes les fonctions et constantes de la partie 1 sont chargées 
# (db, ID_SECTION_NAME, etc.)

# --- FONCTIONS DE VALIDATION ---

def validate_identification(df, phase_name, answers, collected_data):
    """Valide la section d'identification."""
    errors = []
    
    # Validation des champs obligatoires
    for field in REQUIRED_FIELDS:
        q_id_map = {'Intitulé': 1, 'Site': 2, 'Date': 3}
        q_id = q_id_map.get(field)
        
        if q_id is not None:
            value = answers.get(q_id)
            if not value or (isinstance(value, str) and value.strip() == ""):
                errors.append(f"Le champ '{field}' est obligatoire.")

    if errors:
        st.error("Veuillez remplir tous les champs obligatoires avant de valider.")
        return False, errors
    
    # Stockage de l'identification dans project_data 
    project_data = {}
    q_map = {1: 'Intitulé', 2: 'Site', 3: 'Date'}
    
    for q_id, val in answers.items():
        key = q_map.get(q_id, f"Q{q_id}")
        project_data[key] = val
        
    st.session_state['project_data'] = project_data
    
    return True, []

def validate_phase(df, phase_name, answers, collected_data):
    """Valide une phase complète (pour l'instant, seulement si le nombre de photos est correct)."""
    errors = []
    phase_df = df[df['phase'] == phase_name]
    
    # Logique pour le contrôle du nombre de photos
    photo_questions = phase_df[phase_df['type'] == 'photo']
    if not photo_questions.empty:
        try:
             total_photos_expected = int(photo_questions.iloc[0]['nb_photos_attendues'])
        except (ValueError, TypeError):
             total_photos_expected = 0 
        
        uploaded_photos_count = 0
        for q_id, val in answers.items():
            if int(q_id) in photo_questions['id'].tolist():
                if isinstance(val, list):
                    # Compter les UploadedFile ou les dicts stockés
                    uploaded_photos_count += len(val)

        if total_photos_expected > 0 and uploaded_photos_count != total_photos_expected:
            if st.session_state['show_comment_on_error']:
                # Deuxième clic: Valider si le commentaire d'écart photo (ID 100) est rempli
                if not answers.get(100) or str(answers.get(100)).strip() == "":
                     errors.append(f"Vous devez fournir un commentaire d'écart (Question ID 100) car {uploaded_photos_count} photos ont été uploadées au lieu des {total_photos_expected} attendues.")
                else:
                    return True, [] # Validation OK avec commentaire
            else:
                # Premier clic: Afficher l'erreur et demander le commentaire
                errors.append(f"Nombre de photos incorrect. Attendues: {total_photos_expected}, Uploadées: {uploaded_photos_count}. Veuillez justifier l'écart dans le champ de commentaire qui vient d'apparaître.")
                st.session_state['show_comment_on_error'] = True
                
    if errors:
        st.error("\n".join(errors))
        return False, errors
    
    return True, []


# --- FONCTIONS D'EXPORTATION AVEC GESTION DES BYTES ---

def create_zip_export(collected_data):
    """
    Crée un fichier ZIP contenant le fichier Word généré et les images.
    Les images sont extraites des données binaires stockées.
    """
    
    # Les fonctions create_word_export et create_csv_export doivent être définies plus loin ou dans la partie 1
    df_struct = st.session_state['df_struct']
    project_data = st.session_state['project_data']
    
    docx_buffer = create_word_export(collected_data, df_struct, project_data)
    csv_string = create_csv_export(collected_data, df_struct)
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        files_added = 0
        
        # Ajout du Word
        zip_file.writestr("rapport_audit.docx", docx_buffer.getvalue())
        
        # Ajout du CSV
        zip_file.writestr("rapport_audit.csv", csv_string.encode('utf-8-sig'))
        
        # Ajout des photos
        for phase in collected_data:
            phase_name_clean = str(phase['phase_name']).replace("/", "_").replace(" ", "_")
            
            for q_id, answer in phase['answers'].items():
                if isinstance(answer, list) and answer and isinstance(answer[0], dict) and 'content' in answer[0]:
                    for idx, file_data in enumerate(answer):
                        try:
                            file_content = file_data['content']
                            original_name = file_data['name'].split('/')[-1].split('\\')[-1]
                            filename = f"PHOTOS/{phase_name_clean}_Q{q_id}_{idx+1}_{original_name}"
                            zip_file.writestr(filename, file_content)
                            files_added += 1
                        except Exception as e:
                            print(f"Erreur ajout fichier zip: {e}")
                            
        info_txt = f"Export généré le {datetime.now()}\nNombre de photos incluses : {files_added}"
        zip_file.writestr("info.txt", info_txt)
                    
    zip_buffer.seek(0)
    return zip_buffer


def create_word_export(collected_data, df_struct, project_data):
    """
    Crée un fichier DOCX incluant le texte et les images à partir des bytes.
    """
    doc = Document()
    project_name = project_data.get('Intitulé', 'Projet Inconnu')
    title = doc.add_heading(f"Rapport d'Audit de Chantier : {project_name}", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph(f"Date de génération : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    doc.add_paragraph(f"ID Submission : {st.session_state.get('submission_id', 'N/A')}")
    doc.add_paragraph("---")

    # Ajouter les données d'identification en haut du document
    doc.add_heading("Informations d'Identification", level=1)
    
    # Utilisation de la constante ID_SECTION_NAME corrigée.
    id_answers = collected_data[0]['answers'] if collected_data and collected_data[0]['phase_name'] == ID_SECTION_NAME else {}
    for key, value in project_data.items():
        doc.add_paragraph(f"**{key}** : {str(value)}")
    
    doc.add_paragraph("---")

    for phase in collected_data:
        phase_name = phase['phase_name']
        if phase_name == ID_SECTION_NAME:
            continue

        doc.add_heading(phase_name, level=1)
        answers = phase['answers']
        
        for q_id, val in answers.items():
            
            is_image_data = isinstance(val, list) and val and isinstance(val[0], dict) and 'content' in val[0] and 'type' in val[0]
            
            if int(q_id) == 100:
                q_text = "Commentaire sur l'écart de photos"
            else:
                q_row = df_struct[df_struct['id'] == int(q_id)]
                q_text = q_row.iloc[0]['question'] if not q_row.empty else f"Question ID {q_id}"

            p_q = doc.add_paragraph()
            run_q = p_q.add_run(f"Q{q_id}. {q_text}")
            run_q.bold = True
            
            if is_image_data:
                doc.add_paragraph("Photos jointes :")
                
                for img_data in val:
                    if img_data['content'] and img_data['type'].startswith('image/'):
                        try:
                            image_stream = io.BytesIO(img_data['content'])
                            doc.add_picture(image_stream, width=Inches(5.5))
                            
                            lbl = doc.add_paragraph(f"Nom du fichier: {img_data['name']}")
                            lbl.style = "Caption"
                        except Exception as e:
                            doc.add_paragraph(f"[Erreur lors de l'insertion de l'image {img_data.get('name', '')} : {e}]", style="Intense Quote")
                    else:
                        doc.add_paragraph(f"[Fichier non image: {img_data.get('name', 'N/A')}, Type: {img_data.get('type', 'N/A')}]")
            
            else:
                if val is None or str(val) == "":
                    doc.add_paragraph("Non renseigné", style="No Spacing")
                else:
                    doc.add_paragraph(str(val), style="No Spacing")
                    
            doc.add_paragraph("") 

    docx_buffer = io.BytesIO()
    doc.save(docx_buffer)
    docx_buffer.seek(0)
    return docx_buffer

def create_csv_export(collected_data, df_struct):
    """Crée un fichier CSV des réponses."""
    rows = []
    submission_id = st.session_state.get('submission_id', 'N/A')
    project_name = st.session_state['project_data'].get('Intitulé', 'Projet Inconnu')
    start_time_str = st.session_state.get('form_start_time', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
    end_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for item in collected_data:
        phase_name = item['phase_name']
        for q_id, val in item['answers'].items():
            if int(q_id) == 100:
                q_text = "Commentaire Écart Photo"
            else:
                q_row = df_struct[df_struct['id'] == int(q_id)]
                q_text = q_row.iloc[0]['question'] if not q_row.empty else f"Question ID {q_id}"
            
            if isinstance(val, list) and val and isinstance(val[0], dict) and 'name' in val[0]:
                file_names = ", ".join([f['name'] for f in val])
                final_val = f"[Pièces jointes] {len(val)} fichiers: {file_names}"
            else:
                final_val = str(val)
            
            rows.append({
                "ID Formulaire": submission_id,
                "Date Début": start_time_str,
                "Date Fin": end_time_str,
                "Projet": project_name,
                "Phase": phase_name,
                "ID": q_id,
                "Question": q_text,
                "Réponse": final_val
            })
            
    df_export = pd.DataFrame(rows)
    return df_export.to_csv(index=False, sep=';', encoding='utf-8-sig')


# --- WIDGETS DE FORMULAIRE ---

def render_question_widget(question, answers):
    """Affiche le widget de formulaire approprié pour la question."""
    q_id = int(question['id'])
    q_text = question['question']
    q_type = question['type']
    
    col1, col2 = st.columns([0.1, 0.9])
    with col1:
        st.write(f"**{q_id}**")
    with col2:
        st.markdown(q_text)

    current_value = answers.get(q_id, None)

    if q_type == 'text':
        answers[q_id] = st.text_input("Réponse", value=current_value if current_value is not None else "", key=f"q_{q_id}")
    elif q_type == 'number':
        answers[q_id] = st.number_input("Valeur", value=current_value if current_value is not None else None, key=f"q_{q_id}")
    elif q_type == 'select':
        options = [o.strip() for o in question['options'].split(';') if o.strip()]
        options_with_placeholder = ["Choisir une option..."] + options
        
        default_index = 0
        if current_value is not None and current_value in options_with_placeholder:
            default_index = options_with_placeholder.index(current_value)
            
        selected_option = st.selectbox("Option", options_with_placeholder, index=default_index, key=f"q_{q_id}")
        answers[q_id] = selected_option if selected_option != "Choisir une option..." else None
        
    elif q_type == 'photo':
        nb_photos = question.get('nb_photos_attendues')
        try:
             nb_photos = int(nb_photos)
        except (ValueError, TypeError):
             nb_photos = 1 

        
        stored_files = answers.get(q_id, [])
        is_stored = stored_files and isinstance(stored_files, list) and isinstance(stored_files[0], dict) and 'content' in stored_files[0]
        
        if is_stored:
            st.caption(f"**Fichiers déjà enregistrés ({len(stored_files)}) :**")
            cols = st.columns(min(len(stored_files), 4))
            for idx, file_data in enumerate(stored_files):
                if file_data['content'] and file_data['type'].startswith('image/'):
                    try:
                        cols[idx % 4].image(io.BytesIO(file_data['content']), caption=file_data['name'], width=100)
                    except Exception:
                        cols[idx % 4].write(f"[Photo {file_data['name']}]")
                else:
                    cols[idx % 4].write(f"[Fichier {file_data['name']}]")

        uploaded_files = st.file_uploader(
            f"Veuillez charger {nb_photos} photo(s) [Format: {question.get('format', 'jpg, png')}]",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key=f"q_{q_id}_upload"
        )
        
        if uploaded_files:
            answers[q_id] = uploaded_files
        elif is_stored:
            answers[q_id] = stored_files
        else:
            answers[q_id] = []

    st.markdown("---")


# --- FLUX PRINCIPAL DE L'APPLICATION ---

def main_app():
    """Fonction principale de l'application."""
    
    # 0. Initialisation de l'état de session (Fonction de la Partie 1)
    if 'df_struct' not in st.session_state:
        init_session_state(None)
    
    # --- HEADER ---
    st.markdown("<div class='main-header'><h1>Formulaire d'Audit Dynamique</h1></div>", unsafe_allow_html=True)

    # --- ÉTAPE 1: UPLOAD EXCEL ---
    if st.session_state['step'] == 'UPLOAD_EXCEL':
        st.subheader("Chargement du Fichier de Structure")
        st.info("Veuillez charger le fichier Excel contenant les phases, questions, types de réponse et nombre de photos attendues.")
        
        uploaded_file = st.file_uploader("Charger le fichier Excel", type=["xlsx", "xls"])
        
        if uploaded_file is not None:
            load_excel_structure(uploaded_file)
            st.rerun()

    # --- ÉTAPE 2: IDENTIFICATION DU PROJET ---
    elif st.session_state['step'] == 'IDENTIFICATION':
        st.subheader(f"1. {ID_SECTION_NAME}")
        st.markdown("<div class='phase-block'>", unsafe_allow_html=True)
        
        questions = get_phase_questions(st.session_state['df_struct'], ID_SECTION_NAME)
        
        if not st.session_state['current_phase_temp']:
            st.session_state['current_phase_temp'] = {3: datetime.now().date()}
        
        for q in questions:
            q_id = int(q['id'])
            default_value = st.session_state['current_phase_temp'].get(q_id)
            
            if q_id == 1:
                st.session_state['current_phase_temp'][q_id] = st.text_input("Intitulé du projet (Obligatoire)", 
                                                                             value=default_value if default_value is not None else "", 
                                                                             key=f"id_{q_id}")
            elif q_id == 2:
                st.session_state['current_phase_temp'][q_id] = st.text_input("Site / Emplacement (Obligatoire)", 
                                                                             value=default_value if default_value is not None else "", 
                                                                             key=f"id_{q_id}")
            elif q_id == 3:
                date_val = datetime.now().date()
                if default_value is not None:
                     if isinstance(default_value, datetime):
                         date_val = default_value.date()
                     elif isinstance(default_value, str):
                         try:
                             date_val = pd.to_datetime(default_value, errors='coerce').date()
                         except Exception:
                             pass 

                st.session_state['current_phase_temp'][q_id] = st.date_input("Date du jour (Obligatoire)", 
                                                                             value=date_val, 
                                                                             key=f"id_{q_id}")
            else:
                 st.session_state['current_phase_temp'][q_id] = st.text_area(q['question'], 
                                                                              value=default_value if default_value is not None else "", 
                                                                              key=f"id_{q_id}")

        st.markdown("</div>", unsafe_allow_html=True)
        
        if st.button("✅ Valider l'identification"):
            is_valid, errors = validate_identification(st.session_state['df_struct'], ID_SECTION_NAME, st.session_state['current_phase_temp'], st.session_state['collected_data'])
            if is_valid:
                clean_answers = process_files_for_storage(st.session_state['current_phase_temp'])
                id_entry = {"phase_name": ID_SECTION_NAME, "answers": clean_answers}
                
                if st.session_state['collected_data'] and st.session_state['collected_data'][0]['phase_name'] == ID_SECTION_NAME:
                    st.session_state['collected_data'][0] = id_entry
                else:
                    st.session_state['collected_data'].insert(0, id_entry)

                st.session_state['identification_completed'] = True
                st.session_state['step'] = 'LOOP_DECISION'
                st.session_state['current_phase_temp'] = {}
                st.session_state['show_comment_on_error'] = False
                st.success("Identification validée.")
                st.rerun()

    # --- ÉTAPE 3: DÉCISION DE BOUCLE (Passer à la phase suivante ou Fin) ---
    elif st.session_state['step'] == 'LOOP_DECISION':
        
        current_idx = st.session_state['current_phase_index']
        phases = st.session_state['all_phases']
        
        st.subheader("Progression du Formulaire")
        total_steps = len(phases) + 1
        current_step = current_idx + 1
        st.progress(current_step / total_steps)
        st.info(f"Phases complétées : {current_idx} / {len(phases)}")

        if current_idx < len(phases):
            next_phase_name = phases[current_idx]
            st.success(f"Prêt pour la phase suivante : **{next_phase_name}**")
            
            if st.button(f"Commencer la phase {current_idx + 1} / {len(phases)}"):
                st.session_state['step'] = 'FILL_PHASE'
                st.session_state['current_phase_temp'] = {}
                st.session_state['show_comment_on_error'] = False
                st.rerun()
        else:
            st.success("Toutes les phases ont été complétées ! 🎉")
            if st.button("Passer à l'exportation finale"):
                st.session_state['step'] = 'EXPORT'
                st.rerun()

    # --- ÉTAPE 4: REMPLIR UNE PHASE ---
    elif st.session_state['step'] == 'FILL_PHASE':
        current_phase = st.session_state['all_phases'][st.session_state['current_phase_index']]
        st.subheader(f"Phase {st.session_state['current_phase_index'] + 1} : {current_phase}")
        
        st.markdown("<div class='phase-block'>", unsafe_allow_html=True)

        questions = get_phase_questions(st.session_state['df_struct'], current_phase)
        
        for q in questions:
            render_question_widget(q, st.session_state['current_phase_temp'])

        if st.session_state['show_comment_on_error']:
            st.error("Raison de l'écart de photos requise :")
            default_comment = st.session_state['current_phase_temp'].get(100, "")
            st.session_state['current_phase_temp'][100] = st.text_area(
                "Commentaire d'écart (Obligatoire en cas de divergence de photos)",
                value=default_comment,
                key="q_100_comment_gap"
            )
        
        st.markdown("</div>", unsafe_allow_html=True)

        c1, c2, c3 = st.columns([1, 1, 1])
        
        with c1:
            if st.button("⬅️ Retour"):
                st.session_state['step'] = 'LOOP_DECISION'
                st.session_state['show_comment_on_error'] = False
                st.rerun()

        with c2:
            if st.button("💾 Valider la phase"):
                temp_answers_copy = st.session_state['current_phase_temp'].copy()
                
                was_error_shown = st.session_state['show_comment_on_error']
                st.session_state['show_comment_on_error'] = False 
                
                is_valid, errors = validate_phase(st.session_state['df_struct'], current_phase, temp_answers_copy, st.session_state['collected_data'])
                
                if is_valid:
                    clean_answers = process_files_for_storage(temp_answers_copy)

                    new_entry = {"phase_name": current_phase, "answers": clean_answers}
                    
                    phase_index_in_collected = st.session_state['current_phase_index'] + 1
                    
                    if len(st.session_state['collected_data']) > phase_index_in_collected:
                         st.session_state['collected_data'][phase_index_in_collected] = new_entry
                    else:
                         st.session_state['collected_data'].append(new_entry)


                    st.success("Enregistré !")
                    st.session_state['current_phase_index'] += 1
                    st.session_state['step'] = 'LOOP_DECISION'
                    st.rerun()
                
                elif not is_valid and was_error_shown != st.session_state['show_comment_on_error']:
                    st.rerun()


    # --- ÉTAPE 5: EXPORTATION FINALE ---
    elif st.session_state['step'] == 'EXPORT':
        st.subheader("5. Exportation du Rapport Final")
        project_name = st.session_state['project_data'].get('Intitulé', 'Projet Inconnu')
        
        # 1. Sauvegarde dans Firestore (sans les bytes d'images)
        success, result_id = save_form_data(st.session_state['collected_data'], st.session_state['project_data'])
        if success:
            st.success(f"Les données textuelles et de structure ont été sauvegardées dans la base de données. ID Submission : {result_id}")
        else:
            st.error(f"Erreur lors de la sauvegarde Firestore: {result_id}")
            
        st.markdown("---")
        st.markdown("### 💾 1. Télécharger les Fichiers")

        # 2. Génération du DOCX (inclut les images)
        docx_buffer = create_word_export(
            st.session_state['collected_data'], 
            st.session_state['df_struct'], 
            st.session_state['project_data']
        )
        file_name_word = f"Rapport_Audit_{project_name.replace(' ', '_').replace('/', '')}.docx"
        st.download_button(
            label="Télécharger le rapport Word (.docx)",
            data=docx_buffer.getvalue(),
            file_name=file_name_word,
            mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            help="Ce fichier inclut toutes les réponses et les images."
        )

        # 3. Génération du ZIP (inclut Word, CSV et les images brutes)
        zip_buffer = create_zip_export(st.session_state['collected_data'])
        file_name_zip = f"Export_Complet_{project_name.replace(' ', '_').replace('/', '')}.zip"
        st.download_button(
            label="Télécharger l'export complet (.zip)",
            data=zip_buffer.getvalue(),
            file_name=file_name_zip,
            mime='application/zip',
            help="Contient le Word, le CSV des données brutes, et les dossiers de photos originales."
        )
        
        # 4. Génération du CSV (sans les images)
        csv_string = create_csv_export(st.session_state['collected_data'], st.session_state['df_struct'])
        file_name_csv = f"Donnees_Brutes_{project_name.replace(' ', '_').replace('/', '')}.csv"
        st.download_button(
            label="Télécharger les données brutes (.csv)",
            data=csv_string,
            file_name=file_name_csv,
            mime='text/csv',
            help="Contient les questions et réponses dans un format tabulaire."
        )

        # --- 5. OUVERTURE DE L'APPLICATION NATIVE (MAILTO) ---
        st.markdown("---")
        st.markdown("### 📧 2. Partager par Email")
        
        subject = f"Rapport Audit : {project_name}"
        body = (
            f"Bonjour,\\n\\n"
            f"Veuillez trouver ci-joint le rapport d'audit pour le projet {project_name}.\\n"
            f"(N'oubliez pas d'ajouter les fichiers Word, CSV et ZIP que vous avez téléchargés précédemment).\\n\\n"
            f"Cordialement."
        )
        
        mailto_link = (
            f"mailto:?" 
            f"subject={urllib.parse.quote(subject)}" 
            f"&body={urllib.parse.quote(body)}"
        )
        
        st.markdown(
            f'<a href="{mailto_link}" target="_blank" style="text-decoration: none;">'
            f'<button style="background-color: #E9630C; color: white; border: none; padding: 10px 20px; border-radius: 8px; width: 100%; font-size: 16px; cursor: pointer;">'
            f'Ouvrir l\'Email pour Partager'
            f'</button></a>',
            unsafe_allow_html=True
        )

        st.markdown("---")
        if st.button("🔄 Démarrer un nouveau formulaire"):
            init_session_state(st.session_state['df_struct'])
            st.session_state['step'] = 'UPLOAD_EXCEL'
            st.rerun()

# --- EXÉCUTION ---
if __name__ == '__main__':
    # Cette ligne dépend de la fonction init_session_state (Partie 1)
    init_session_state(st.session_state.get('df_struct'))
    main_app()

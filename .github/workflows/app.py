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

# --- CONFIGURATION ET STYLE (inchangés) ---
st.set_page_config(page_title="Formulaire Dynamique - Firestore", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #121212; color: #e0e0e0; }
    .main-header { background-color: #1e1e1e; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; border-bottom: 3px solid #4285F4; }
    .block-container { max-width: 800px; }
    .phase-block { background-color: #1e1e1e; padding: 25px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #333; }
    .question-card { background-color: transparent; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #4285F4; }
    h1, h2, h3 { color: #ffffff !important; }
    .description { font-size: 0.9em; color: #aaaaaa; font-style: italic; margin-bottom: 10px; }
    .mandatory { color: #F4B400; font-weight: bold; margin-left: 5px; }
    .success-box { background-color: #1e4620; padding: 15px; border-radius: 8px; border-left: 5px solid #4caf50; color: #fff; margin: 10px 0; }
    .error-box { background-color: #3d1f1f; padding: 15px; border-radius: 8px; border-left: 5px solid #ff6b6b; color: #ffdad9; margin: 10px 0; }
    .stButton > button { border-radius: 8px; font-weight: bold; padding: 0.5rem 1rem; }
    div[data-testid="stButton"] > button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- NOUVELLE LOGIQUE DE RENOMMAGE ET D'AFFICHAGE DU PROJET ---

PROJECT_RENAME_MAP = {
    'Intitulé': 'Intitulé',
    'Fournisseur Bornes AC [Bornes]': 'Fournisseur Bornes AC',
    'Fournisseur Bornes DC [Bornes]': 'Fournisseur Bornes DC',
    'L [Plan de Déploiement]': 'PDC Lent',
    'R [Plan de Déploiement]': 'PDC Rapide',
    'UR [Plan de Déploiement]': 'PDC Ultra-rapide',
    'Pré L [Plan de Déploiement]': 'PDC L pré-équipés',
    'Pré UR [Plan de Déploiement]': 'PDC UR pré-équipés',
    'Pré R [Plan de Déploiement]': 'PDC R pré-équipés',
}

DISPLAY_GROUPS = [
    # Ligne 1 : Fournisseurs (Ordre 1, 2, 3)
    ['Intitulé', 'Fournisseur Bornes AC [Bornes]', 'Fournisseur Bornes DC [Bornes]'],
    # Ligne 2 : Déploiements Standard (Ordre 4, 5, 6)
    ['L [Plan de Déploiement]', 'R [Plan de Déploiement]', 'UR [Plan de Déploiement]'],
    # Ligne 3 : Déploiements Pré-équipés (Ordre 7, 8, 9)
    ['Pré L [Plan de Déploiement]', 'Pré UR [Plan de Déploiement]', 'Pré R [Plan de Déploiement]'],
]

# --- INITIALISATION FIREBASE SÉCURISÉE (inchangée) ---
def initialize_firebase():
    """Initialise Firebase avec les secrets individuels et force l'ID du projet."""
    if not firebase_admin._apps:
        try:
            cred_dict = {
                "type": st.secrets["firebase_type"],
                "project_id": st.secrets["firebase_project_id"],
                "private_key_id": st.secrets["firebase_private_key_id"],
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
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {'projectId': project_id})
            st.sidebar.success("Connexion BDD réussie 🟢")
        
        except KeyError as e:
            st.sidebar.error(f"Erreur de configuration Secrets : Clé manquante ({e})")
            st.stop()
        except Exception as e:
            st.sidebar.error(f"Erreur de connexion Firebase : {e}")
            st.stop()
    return firestore.client()

db = initialize_firebase()

# --- FONCTIONS DE CHARGEMENT ET SAUVEGARDE FIREBASE (inchangées) ---

@st.cache_data(ttl=3600)
def load_form_structure_from_firestore():
    # Logique inchangée
    try:
        docs = db.collection('formsquestions').order_by('id').get()
        data = [doc.to_dict() for doc in docs]
        
        if not data:
            st.error("La collection 'formsquestions' est vide.")
            return None
        
        df = pd.DataFrame(data)
        df.columns = df.columns.str.strip()
        
        rename_map = {
            'Conditon value': 'Condition value', 'condition value': 'Condition value',
            'Condition Value': 'Condition value', 'Condition': 'Condition value',
            'Conditon on': 'Condition on', 'condition on': 'Condition on'
        }
        actual_rename = {k: v for k, v in rename_map.items() if k in df.columns}
        df = df.rename(columns=actual_rename)
        
        expected_cols = ['options', 'Description', 'Condition value', 'Condition on', 'section', 'id', 'question', 'type', 'obligatoire']
        for col in expected_cols:
            if col not in df.columns:
                df[col] = np.nan 
        
        # Nettoyage des données
        df['options'] = df['options'].fillna('')
        df['Description'] = df['Description'].fillna('')
        df['Condition value'] = df['Condition value'].fillna('')
        df['Condition on'] = df['Condition on'].apply(lambda x: int(x) if pd.notna(x) and str(x).isdigit() else 0)
        
        # Correction d'encodage
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
            try:
                df[col] = df[col].apply(lambda x: x.encode('utf-8', 'ignore').decode('utf-8', 'ignore'))
            except Exception:
                pass 
        
        return df
    except Exception as e:
        st.error(f"Erreur lecture 'formsquestions': {e}")
        st.exception(e)
        return None

@st.cache_data(ttl=3600)
def load_site_data_from_firestore():
    # Logique inchangée
    try:
        docs = db.collection('Sites').get()
        data = [doc.to_dict() for doc in docs]
        
        if not data:
            st.error("La collection 'Sites' est vide.")
            return None
            
        df_site = pd.DataFrame(data)
        df_site.columns = df_site.columns.str.strip()
        return df_site
    except Exception as e:
        st.error(f"Erreur lecture 'Sites': {e}")
        st.exception(e) 
        return None

def save_form_data(collected_data, project_data):
    """Gère les listes de fichiers pour la sauvegarde Firestore."""
    try:
        cleaned_data = []
        for phase in collected_data:
            clean_phase = {
                "phase_name": phase["phase_name"],
                "answers": {}
            }
            for k, v in phase["answers"].items():
                # Gère une liste de fichiers au lieu d'un seul
                if isinstance(v, list) and v and hasattr(v[0], 'read'): 
                    # C'est une liste d'objets FileUploader (Photos)
                    file_names = ", ".join([f.name for f in v])
                    clean_phase["answers"][str(k)] = f"Images chargées ({len(v)} fichiers) : {file_names}"
                elif hasattr(v, 'read'): 
                    # Cas d'un seul fichier (par sécurité, si le type n'était pas 'photo')
                    clean_phase["answers"][str(k)] = f"Image chargée (Nom: {v.name})"
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
        
        doc_id_base = str(project_data.get('Intitulé', 'form')).replace(" ", "_").replace("/", "_")[:20]
        doc_id = f"{doc_id_base}_{datetime.now().strftime('%Y%m%d_%H%M')}_{submission_id[:6]}"
        
        db.collection('FormAnswers').document(doc_id).set(final_document)
        return True, submission_id 
    except Exception as e:
        return False, str(e)

# --- FONCTIONS EXPORT (inchangées) ---

def create_csv_export(collected_data, df_struct):
    """Gère les listes de fichiers dans l'export CSV et ajoute l'ID/dates."""
    rows = []
    
    submission_id = st.session_state.get('submission_id', 'N/A')
    project_name = st.session_state['project_data'].get('Intitulé', 'Projet Inconnu')
    
    start_time = st.session_state.get('form_start_time', 'N/A')
    end_time = datetime.now() 
    
    start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S') if isinstance(start_time, datetime) else 'N/A'
    end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')

    for item in collected_data:
        phase_name = item['phase_name']
        for q_id, val in item['answers'].items():
            
            q_row = df_struct[df_struct['id'] == int(q_id)]
            q_text = q_row.iloc[0]['question'] if not q_row.empty else f"Question ID {q_id}"
            
            # Gérer la valeur (fichier vs texte)
            if isinstance(val, list) and val and hasattr(val[0], 'name'):
                # Gère une liste de fichiers
                file_names = ", ".join([f.name for f in val])
                final_val = f"[Fichiers] {len(val)} photos: {file_names}"
            elif hasattr(val, 'name'):
                final_val = f"[Fichier] {val.name}"
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

def create_zip_export(collected_data):
    """Gère l'itération sur la liste de fichiers pour le ZIP."""
    zip_buffer = io.BytesIO()
    has_files = False
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for item in collected_data:
            phase_name = str(item['phase_name']).replace(" ", "_").replace("/", "-")
            
            for q_id, val in item['answers'].items():
                
                # Récupère tous les fichiers à zipper (simple ou multiple)
                files_to_zip = []
                if isinstance(val, list) and val and hasattr(val[0], 'read'):
                    files_to_zip = val
                elif hasattr(val, 'read') and hasattr(val, 'name'):
                    files_to_zip = [val]
                
                for file_obj in files_to_zip:
                    has_files = True
                    file_obj.seek(0)
                    file_content = file_obj.read()
                    
                    clean_phase = phase_name.replace(" ", "_").replace("/", "-")
                    archive_name = f"{clean_phase}_Q{q_id}_{file_obj.name}"
                    
                    zip_file.writestr(archive_name, file_content)
                    
    return zip_buffer if has_files else None

# --- GESTION DE L'ÉTAT (inchangée) ---
def init_session_state():
    """Initialisation de l'état de la session, incluant ID et dates."""
    defaults = {
        'step': 'PROJECT_LOAD',
        'project_data': None,
        'collected_data': [],
        'current_phase_temp': {},
        'current_phase_name': None,
        'iteration_id': str(uuid.uuid4()), 
        'identification_completed': False,
        'data_saved': False,
        'id_rendering_ident': None,
        'form_start_time': None,
        'submission_id': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- LOGIQUE MÉTIER (inchangée) ---

def check_condition(row, current_answers, collected_data):
    # Logique de condition inchangée
    try:
        if int(row.get('Condition on', 0)) != 1: return True
    except (ValueError, TypeError): return True

    all_past_answers = {}
    for phase_data in collected_data: all_past_answers.update(phase_data['answers'])
    combined_answers = {**all_past_answers, **current_answers}
    
    condition_str = str(row.get('Condition value', '')).strip()
    if not condition_str or "=" not in condition_str: return True

    try:
        target_id_str, expected_value_raw = condition_str.split('=', 1)
        target_id = int(target_id_str.strip())
        expected_value = expected_value_raw.strip().strip('"').strip("'")
        user_answer = combined_answers.get(target_id)
        if user_answer is not None:
            return str(user_answer).lower() == str(expected_value).lower()
        else:
            return False
    except Exception: return True

def validate_section(df_questions, section_name, answers, collected_data):
    # La validation doit vérifier si la LISTE est vide pour les questions 'photo' obligatoires
    missing = []
    section_rows = df_questions[df_questions['section'] == section_name]
    for _, row in section_rows.iterrows():
        if not check_condition(row, answers, collected_data): continue
        is_mandatory = str(row['obligatoire']).strip().lower() == 'oui'
        if is_mandatory:
            q_id = int(row['id'])
            val = answers.get(q_id)
            
            if isinstance(val, list):
                if not val:
                    missing.append(f"Question {q_id} : {row['question']} (photo(s) manquante(s))")
            elif val is None or val == "" or (isinstance(val, (int, float)) and val == 0):
                missing.append(f"Question {q_id} : {row['question']}")
    return len(missing) == 0, missing

validate_phase = validate_section
validate_identification = validate_section

# --- COMPOSANTS UI (inchangée) ---

def render_question(row, answers, phase_name, key_suffix, loop_index):
    """Utilise 'accept_multiple_files=True' pour les photos et gère l'ID 9 comme un entier."""
    q_id = int(row['id'])
    q_text = row['question']
    q_type = str(row['type']).strip().lower()
    q_desc = row['Description']
    q_mandatory = str(row['obligatoire']).lower() == 'oui'
    q_options = str(row['options']).split(',') if row['options'] else []
    
    q_text = str(q_text).strip()
    q_desc = str(q_desc).strip()
    
    label_html = f"<strong>{q_id}. {q_text}</strong>" + (' <span class="mandatory">*</span>' if q_mandatory else "")
    
    widget_key = f"q_{q_id}_{phase_name}_{key_suffix}_{loop_index}"
    
    current_val = answers.get(q_id)
    val = current_val

    st.markdown(f'<div class="question-card"><div>{label_html}</div>', unsafe_allow_html=True)
    if q_desc: st.markdown(f'<div class="description">{q_desc}</div>', unsafe_allow_html=True)

    if q_type == 'text':
        val = st.text_input("Réponse", value=current_val if current_val else "", key=widget_key, label_visibility="collapsed")
    elif q_type == 'select':
        clean_opts = [opt.strip() for opt in q_options]
        if "" not in clean_opts: clean_opts.insert(0, "")
        idx = clean_opts.index(current_val) if current_val in clean_opts else 0
        val = st.selectbox("Sélection", clean_opts, index=idx, key=widget_key, label_visibility="collapsed")
    
    # --- MODIFICATION POUR ID 9 ---
    elif q_type == 'number':
        if q_id == 9:
            # Forcer les entiers pour l'ID 9
            
            # Assurer que la valeur par défaut est un entier si possible
            if current_val is not None:
                try:
                    default_val = int(float(current_val))
                except (ValueError, TypeError):
                    default_val = 0
            else:
                default_val = 0
                
            val = st.number_input(
                "Nombre (entier)", 
                value=default_val, 
                step=1, 
                format="%d", # Force l'affichage d'un entier
                key=widget_key, 
                label_visibility="collapsed"
            )
        else:
            # Comportement par défaut pour les autres nombres (décimaux autorisés)
            default_val = float(current_val) if current_val and str(current_val).replace('.', '', 1).isdigit() else 0.0
            val = st.number_input("Nombre", value=default_val, key=widget_key, label_visibility="collapsed")
    # --- FIN MODIFICATION ID 9 ---
        
    elif q_type == 'photo':
        # Ajout de accept_multiple_files=True
        val = st.file_uploader(
            "Images", 
            type=['png', 'jpg', 'jpeg'], 
            accept_multiple_files=True, 
            key=widget_key, 
            label_visibility="collapsed"
        )
        
        # Affichage des confirmations
        if val:
            file_names = ", ".join([f.name for f in val])
            st.success(f"Nombre d'images chargées : {len(val)} ({file_names})")
        # Si des fichiers sont déjà dans current_val (après un re-run) et que l'utilisateur n'a rien re-uploadé
        elif current_val and isinstance(current_val, list) and current_val:
             names = ", ".join([getattr(f, 'name', 'Fichier') for f in current_val])
             st.info(f"Fichiers conservés : {len(current_val)} ({names})")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Stockage de la valeur (liste de fichiers ou autre)
    if val is not None:
         answers[q_id] = val 
    elif current_val is not None:
        answers[q_id] = current_val

# --- FLUX PRINCIPAL (Partiellement Modifié) ---

st.markdown('<div class="main-header"><h1>📝Formulaire Chantier </h1></div>', unsafe_allow_html=True)

if st.session_state['step'] == 'PROJECT_LOAD':
    st.info("Tentative de chargement de la structure des formulaires...")
    with st.spinner("Chargement en cours..."):
        df_struct = load_form_structure_from_firestore()
        df_site = load_site_data_from_firestore()
        
        if df_struct is not None and df_site is not None:
            st.session_state['df_struct'] = df_struct
            st.session_state['df_site'] = df_site
            st.session_state['step'] = 'PROJECT'
            st.rerun()
        else:
            st.error("Impossible de charger les données.")
            if st.button("Réessayer le chargement"):
                load_form_structure_from_firestore.clear() 
                load_site_data_from_firestore.clear() 
                st.session_state['step'] = 'PROJECT_LOAD'
                st.rerun()

elif st.session_state['step'] == 'PROJECT':
    df_site = st.session_state['df_site']
    st.markdown("### 🏗️ Sélection du Chantier")
    
    if 'Intitulé' not in df_site.columns:
        st.error("Colonne 'Intitulé' manquante.")
    else:
        
        search_term = st.text_input("Rechercher un projet (Veuillez renseigner au minimum 3 caractères pour le nom de la ville)", key="project_search_input").strip()

        filtered_projects = []
        selected_proj = None
        
        if len(search_term) >= 3:
            mask = df_site['Intitulé'].str.contains(search_term, case=False, na=False)
            filtered_projects_df = df_site[mask]
            
            filtered_projects = [""] + filtered_projects_df['Intitulé'].dropna().unique().tolist()
            
            if filtered_projects:
                selected_proj = st.selectbox("Résultats de la recherche", filtered_projects)
            else:
                st.warning(f"Aucun projet trouvé pour **'{search_term}'**.")
        
        elif len(search_term) > 0 and len(search_term) < 3:
            st.info("Veuillez entrer au moins **3 caractères** pour lancer la recherche.")
        
        
        if selected_proj:
            row = df_site[df_site['Intitulé'] == selected_proj].iloc[0]
            st.info(f"Projet sélectionné : **{selected_proj}**")
            
            if st.button("✅ Démarrer l'identification"):
                st.session_state['project_data'] = row.to_dict()
                st.session_state['form_start_time'] = datetime.now() 
                st.session_state['submission_id'] = str(uuid.uuid4())
                st.session_state['step'] = 'IDENTIFICATION'
                st.session_state['current_phase_temp'] = {}
                st.session_state['iteration_id'] = str(uuid.uuid4()) 
                st.session_state['id_rendering_ident'] = None
                st.rerun()

elif st.session_state['step'] == 'IDENTIFICATION':
    df = st.session_state['df_struct']
    ID_SECTION_NAME = df['section'].iloc[0]
    
    st.markdown(f"### 👤 Étape unique : {ID_SECTION_NAME}")

    identification_questions = df[df['section'] == ID_SECTION_NAME]
    
    if st.session_state['id_rendering_ident'] is None:
         st.session_state['id_rendering_ident'] = str(uuid.uuid4())
    
    rendering_id = st.session_state['id_rendering_ident']
    
    for idx, (index, row) in enumerate(identification_questions.iterrows()):
        if check_condition(row, st.session_state['current_phase_temp'], st.session_state['collected_data']):
            render_question(row, st.session_state['current_phase_temp'], ID_SECTION_NAME, rendering_id, idx)
            
    st.markdown("---")
    
    if st.button("✅ Valider l'identification"):
        is_valid, errors = validate_identification(
            df, ID_SECTION_NAME, st.session_state['current_phase_temp'], st.session_state['collected_data']
        )
        
        if is_valid:
            id_entry = {
                "phase_name": ID_SECTION_NAME,
                "answers": st.session_state['current_phase_temp'].copy()
            }
            st.session_state['collected_data'].append(id_entry)
            st.session_state['identification_completed'] = True
            st.session_state['step'] = 'LOOP_DECISION'
            st.session_state['current_phase_temp'] = {}
            st.success("Identification validée.")
            st.rerun()
        else:
            st.markdown('<div class="error-box"><b>⚠️ Erreur de validation :</b><br>' + '<br>'.join([f"- {e}" for e in errors]) + '</div>', unsafe_allow_html=True)

elif st.session_state['step'] in ['LOOP_DECISION', 'FILL_PHASE']:
    
    project_intitule = st.session_state['project_data'].get('Intitulé', 'Projet Inconnu')
    with st.expander(f"📍 Projet : {project_intitule}", expanded=False):
        
        # --- DÉBUT AFFICHAGE COMPACT DU PROJET ---
        project_details = st.session_state['project_data']

        st.write("Détails du Projet Sélectionné")
        
        # Ligne 1 : Les Fournisseurs (Ordre 1, 2, 3)
        st.markdown("#### 1. Identification & Fournisseurs")
        # Création de 3 colonnes de taille égale
        cols1 = st.columns([1, 1, 1]) 
        fields_l1 = DISPLAY_GROUPS[0]
        for i, field_key in enumerate(fields_l1):
            renamed_key = PROJECT_RENAME_MAP.get(field_key, field_key)
            value = project_details.get(field_key, 'N/A')
            with cols1[i]:
                # Utilisation de Markdown pour un affichage "clé : valeur" minimaliste
                st.markdown(f"**{renamed_key}** : {value}")
        
        # Ligne 2 : Les Nouveaux Déploiements (Ordre 4, 5, 6)
        st.markdown("#### 2. Déploiement Standard")
        cols2 = st.columns([1, 1, 1])
        fields_l2 = DISPLAY_GROUPS[1]
        for i, field_key in enumerate(fields_l2):
            renamed_key = PROJECT_RENAME_MAP.get(field_key, field_key)
            value = project_details.get(field_key, 'N/A')
            with cols2[i]:
                st.markdown(f"**{renamed_key}** : {value}")

        # Ligne 3 : Les Déploiements Pré-équipés (Ordre 7, 8, 9)
        st.markdown("## 3. Déploiement Pré-équipé")
        cols3 = st.columns([1, 1, 1])
        fields_l3 = DISPLAY_GROUPS[2]
        for i, field_key in enumerate(fields_l3):
            renamed_key = PROJECT_RENAME_MAP.get(field_key, field_key)
            value = project_details.get(field_key, 'N/A')
            with cols3[i]:
                st.markdown(f"**{renamed_key}** : {value}")

        # --- FIN AFFICHAGE COMPACT DU PROJET ---
        
        st.write("Phases et Identification déjà complétées")
        for idx, item in enumerate(st.session_state['collected_data']):
            st.write(f"• **{item['phase_name']}** : {len(item['answers'])} réponses")

    if st.session_state['step'] == 'LOOP_DECISION':
        st.markdown("### 🔄 Gestion des Phases")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Ajouter une phase"):
                st.session_state['step'] = 'FILL_PHASE'
                st.session_state['current_phase_temp'] = {}
                st.session_state['current_phase_name'] = None
                st.session_state['iteration_id'] = str(uuid.uuid4())
                st.rerun()
        with col2:
            if st.button("🏁 Terminer l'audit"):
                st.session_state['step'] = 'FINISHED'
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state['step'] == 'FILL_PHASE':
        df = st.session_state['df_struct']
        
        ID_SECTION_NAME = df['section'].iloc[0]
        ID_SECTION_CLEAN = str(ID_SECTION_NAME).strip().lower()
        SECTIONS_TO_EXCLUDE_CLEAN = {ID_SECTION_CLEAN, "phase"}
        
        all_sections_raw = df['section'].unique().tolist()
        available_phases = []
        for sec in all_sections_raw:
            if pd.isna(sec) or not sec or str(sec).strip().lower() in SECTIONS_TO_EXCLUDE_CLEAN:
                continue
            available_phases.append(sec)
        
        if not st.session_state['current_phase_name']:
              st.markdown("### 📑 Sélection de la phase")
              phase_choice = st.selectbox("Quelle phase ?", [""] + available_phases)
              if phase_choice:
                  st.session_state['current_phase_name'] = phase_choice
                  st.rerun()
              if st.button("⬅️ Retour"):
                  st.session_state['step'] = 'LOOP_DECISION'
                  st.session_state['current_phase_temp'] = {}
                  st.rerun()
        else:
            current_phase = st.session_state['current_phase_name']
            st.markdown(f"### 📝 {current_phase}")
            st.markdown("---")
            if st.button("🔄 Changer de phase"):
                st.session_state['current_phase_name'] = None
                st.session_state['current_phase_temp'] = {}
                st.session_state['iteration_id'] = str(uuid.uuid4())
                st.rerun()
            
            st.markdown("---")
            
            section_questions = df[df['section'] == current_phase]
            
            visible_count = 0
            for idx, (index, row) in enumerate(section_questions.iterrows()):
                if check_condition(row, st.session_state['current_phase_temp'], st.session_state['collected_data']):
                    render_question(row, st.session_state['current_phase_temp'], current_phase, st.session_state['iteration_id'], idx)
                    visible_count += 1
            
            if visible_count == 0:
                st.warning("Aucune question visible.")

            st.markdown("---")
            
            c1, c2 = st.columns([1, 2])
            with c1:
                if st.button("❌ Annuler"):
                    st.session_state['step'] = 'LOOP_DECISION'
                    st.rerun()
            with c2:
                if st.button("💾 Valider la phase"):
                    is_valid, errors = validate_phase(
                        df, current_phase, st.session_state['current_phase_temp'], st.session_state['collected_data']
                    )
                    
                    if is_valid:
                        new_entry = {
                            "phase_name": current_phase,
                            "answers": st.session_state['current_phase_temp'].copy()
                        }
                        st.session_state['collected_data'].append(new_entry)
                        st.success("Enregistré !")
                        st.session_state['step'] = 'LOOP_DECISION'
                        st.rerun()
                    else:
                        st.markdown('<div class="error-box"><b>⚠️ Erreurs :</b><br>' + '<br>'.join([f"- {e}" for e in errors]) + '</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state['step'] == 'FINISHED':
    st.markdown("## 🎉 Formulaire Terminé")
    st.write(f"Projet : **{st.session_state['project_data'].get('Intitulé')}**")
    
    # 1. SAUVEGARDE SUR FIREBASE
    if not st.session_state['data_saved']:
        with st.spinner("Sauvegarde dans Firestore en cours..."):
            success, submission_id_returned = save_form_data(st.session_state['collected_data'], st.session_state['project_data'])
            
            if success:
                st.balloons()
                st.success(f"Données sauvegardées avec succès ! (ID: {submission_id_returned})")
                st.session_state['data_saved'] = True
            else:
                st.error(f"Erreur lors de la sauvegarde : {submission_id_returned}")
                if st.button("Réessayer la sauvegarde"):
                    st.rerun()
    else:
        st.info("Les données ont déjà été sauvegardées sur Firestore.")

    st.markdown("---")
    
    # 2. GENERATION DES EXPORTS (UNIQUEMENT APRES SAUVEGARDE)
    if st.session_state['data_saved']:
        st.markdown("### 📥 Télécharger les données")
        
        col_csv, col_zip = st.columns(2)
        
        # --- Export CSV ---
        csv_data = create_csv_export(st.session_state['collected_data'], st.session_state['df_struct'])
        date_str = datetime.now().strftime('%Y%m%d_%H%M')
        file_name_csv = f"Export_{st.session_state['project_data'].get('Intitulé', 'Projet')}_{date_str}.csv"
        
        with col_csv:
            st.download_button(
                label="📄 Télécharger les réponses (CSV)",
                data=csv_data,
                file_name=file_name_csv,
                mime='text/csv'
            )

        # --- Export ZIP (Photos) ---
        zip_buffer = create_zip_export(st.session_state['collected_data'])
        
        with col_zip:
            if zip_buffer:
                file_name_zip = f"Photos_{st.session_state['project_data'].get('Intitulé', 'Projet')}_{date_str}.zip"
                st.download_button(
                    label="📷 Télécharger les photos (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=file_name_zip,
                    mime="application/zip"
                )
            else:
                st.info("Aucune photo à télécharger.")

    st.markdown("---")

    # Affichage JSON technique
    for i, phase in enumerate(st.session_state['collected_data']):
        with st.expander(f"Section {i+1} : {phase['phase_name']}"):
            # Gère l'affichage d'une liste de fichiers pour l'expandeur JSON
            clean_display = {
                k: (
                    [f.name for f in v] if isinstance(v, list) and v and hasattr(v[0], 'name') else 
                    (v.name if hasattr(v, 'name') else v)
                ) for k, v in phase['answers'].items()
            }
            st.json(clean_display)
            
    if st.button("🔄 Nouveau projet"):
        st.session_state.clear()
        st.rerun()

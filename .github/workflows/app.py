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
    .main-header { background-color: #1e1e1e; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; border-bottom: 3px solid #E9630C; }
    .block-container { max-width: 800px; }
    .phase-block { background-color: #1e1e1e; padding: 25px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #333; }
    .question-card { background-color: transparent; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 3px solid #E9630C; }
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
    'Pré R [Plan de Déploiement]': 'PDC R pré-équipés',
    'Pré UR [Plan de Déploiement]': 'PDC UR pré-équipés',
}

DISPLAY_GROUPS = [
    # Ligne 1 : Fournisseurs (Ordre 1, 2, 3)
    ['Intitulé', 'Fournisseur Bornes AC [Bornes]', 'Fournisseur Bornes DC [Bornes]'],
    # Ligne 2 : Déploiements Standard (Ordre 4, 5, 6)
    ['L [Plan de Déploiement]', 'R [Plan de Déploiement]', 'UR [Plan de Déploiement]'],
    # Ligne 3 : Déploiements Pré-équipés (Ordre 7, 8, 9)
    ['Pré L [Plan de Déploiement]', 'Pré R [Plan de Déploiement]','Pré UR [Plan de Déploiement]' ],
]

# -----------------------------------------------------------
# --- LOGIQUE D'ATTENTE DE PHOTOS ---
# -----------------------------------------------------------

# Dictionnaire : "Nom de la Section" : ["Colonne1 à additionner", "Colonne2 à additionner", ...]
SECTION_PHOTO_RULES = {
    "Bornes DC": ['R [Plan de Déploiement]', 'UR [Plan de Déploiement]'],
    # Ajoutez d'autres sections ici si nécessaire.
}

def get_expected_photo_count(section_name, project_data):
    """Calcule le nombre attendu de photos basé sur les colonnes du projet."""
    if section_name not in SECTION_PHOTO_RULES:
        return None, None # Pas de règle pour cette section

    columns = SECTION_PHOTO_RULES[section_name]
    total_expected = 0
    details = []

    for col in columns:
        val = project_data.get(col, 0)
        try:
            if pd.isna(val) or val == "":
                num = 0
            else:
                # Gère "2.0" ou "2,0"
                num = int(float(str(val).replace(',', '.'))) 
        except Exception:
            num = 0
        
        total_expected += num
        short_name = PROJECT_RENAME_MAP.get(col, col) 
        details.append(f"{num} {short_name}")

    detail_str = " + ".join(details)
    return total_expected, detail_str

# --- INITIALISATION FIREBASE SÉCURISÉE ---
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

# --- FONCTIONS DE CHARGEMENT ET SAUVEGARDE FIREBASE ---

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
    # Logique inchangée
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
                    file_names = ", ".join([f.name for f in v])
                    clean_phase["answers"][str(k)] = f"Images chargées ({len(v)} fichiers) : {file_names}"
                elif hasattr(v, 'read'): 
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

# --- FONCTIONS EXPORT ---

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
            
            # Utilise une version temporaire de df_struct si l'ID est 1000 (le commentaire dynamique)
            if int(q_id) == 1000:
                q_text = "Commentaire Écart Photo"
                q_row = pd.Series({'question': q_text})
            else:
                q_row = df_struct[df_struct['id'] == int(q_id)]
                q_text = q_row.iloc[0]['question'] if not q_row.empty else f"Question ID {q_id}"
            
            # Gérer la valeur (fichier vs texte)
            if isinstance(val, list) and val and hasattr(val[0], 'name'):
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
    # Logique inchangée
    zip_buffer = io.BytesIO()
    has_files = False
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for item in collected_data:
            phase_name = str(item['phase_name']).replace(" ", "_").replace("/", "-")
            
            for q_id, val in item['answers'].items():
                
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

# --- GESTION DE L'ÉTAT ---
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

# --- LOGIQUE MÉTIER ---

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

# -----------------------------------------------------------
# --- FONCTION VALIDATION (CORRIGÉE : SUPPRESSION unsafe_allow_html) ---
# -----------------------------------------------------------
# ID Arbitraire pour le champ de commentaire dynamique
COMMENT_ID = 1000
COMMENT_QUESTION = "Veuillez préciser pourquoi le nombre de photo partagé ne correspond pas au minimum attendu"

def validate_section(df_questions, section_name, answers, collected_data):
    missing = []
    section_rows = df_questions[df_questions['section'] == section_name]
    
    # 1. Validation Standard (Champs obligatoires)
    for _, row in section_rows.iterrows():
        # Ignorer l'ID 1000 s'il n'est pas dans le DF (il est géré séparément)
        if int(row['id']) == COMMENT_ID: continue

        if not check_condition(row, answers, collected_data): continue
        is_mandatory = str(row['obligatoire']).strip().lower() == 'oui'
        
        q_id = int(row['id'])
        val = answers.get(q_id)
        
        if is_mandatory:
            if isinstance(val, list):
                if not val:
                    missing.append(f"Question {q_id} : {row['question']} (photo(s) manquante(s))")
            elif val is None or val == "" or (isinstance(val, (int, float)) and val == 0):
                missing.append(f"Question {q_id} : {row['question']}")

    # 2. Validation du Nombre de Photos (Logique)
    project_data = st.session_state.get('project_data', {})
    expected_total, detail_str = get_expected_photo_count(section_name, project_data)
    
    # Indicateur si un écart est détecté
    is_photo_count_incorrect = False

    if expected_total is not None and expected_total > 0:
        current_photo_count = 0
        photo_questions_found = False
        
        # Compter le total des fichiers uploadés (uniques ou multiples) dans la section
        for _, row in section_rows.iterrows():
            if str(row['type']).strip().lower() == 'photo':
                photo_questions_found = True
                q_id = int(row['id'])
                val = answers.get(q_id)
                if isinstance(val, list):
                    current_photo_count += len(val)
        
        # Comparaison
        if photo_questions_found and current_photo_count != expected_total:
            is_photo_count_incorrect = True
            
            # --- CORRECTION ICI : Utilisation de Markdown au lieu de HTML avec unsafe_allow_html ---
            # On utilise ** pour le gras et \n pour les sauts de ligne
            st.error(
                f"⚠️ **Écart de Photos pour '{str(section_name)}'**.\n\n"
                f"Attendu : **{str(expected_total)}** (calculé : {str(detail_str)}).\n\n"
                f"Reçu : **{str(current_photo_count)}**.\n\n"
                f"Veuillez remplir le champ de commentaire ci-dessous."
            )
        
    # 3. Validation du Commentaire Conditionnel
    comment_val = answers.get(COMMENT_ID)
    
    if is_photo_count_incorrect:
        # Si un écart est trouvé, le commentaire ID 1000 devient OBLIGATOIRE
        if not comment_val or str(comment_val).strip() == "":
            missing.append(
                f"**Commentaire (ID {COMMENT_ID}) :** {COMMENT_QUESTION} "
                f"(requis en raison de l'écart de photo : Attendu {expected_total}, Reçu {current_photo_count})."
            )
        else:
            # Si le commentaire est présent, l'écart est enregistré, mais la validation passe
            pass
    else:
        # Si aucun écart n'est trouvé, s'assurer que le commentaire est retiré des réponses
        if COMMENT_ID in answers:
            del answers[COMMENT_ID]


    return len(missing) == 0, missing

validate_phase = validate_section
validate_identification = validate_section

# -----------------------------------------------------------
# --- COMPOSANTS UI ---
# -----------------------------------------------------------

def render_question(row, answers, phase_name, key_suffix, loop_index):
    """Gère l'affichage des questions, y compris le champ de commentaire dynamique (ID 1000)."""
    
    # 1. Extraction des données de la question
    q_id = int(row.get('id', 0)) # Sûr que q_id est un int
    
    # Cas Spécial pour le commentaire dynamique
    is_dynamic_comment = q_id == COMMENT_ID
    if is_dynamic_comment:
        q_text = COMMENT_QUESTION
        q_type = 'text' # ou textarea, mais 'text' est suffisant pour le moment
        q_desc = "Ce champ est obligatoire si le nombre de photos n'est pas conforme."
        q_mandatory = True
        q_options = []
    else:
        # Cas des questions normales
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

    # 2. Rendu du widget
    st.markdown(f'<div class="question-card"><div>{label_html}</div>', unsafe_allow_html=True)
    if q_desc: st.markdown(f'<div class="description">{q_desc}</div>', unsafe_allow_html=True)

    if q_type == 'text':
        # Utilisation de text_area pour le commentaire (ID 1000) pour plus de place
        if is_dynamic_comment:
             val = st.text_area("Justification de l'écart", value=current_val if current_val else "", key=widget_key, label_visibility="collapsed")
        else:
             val = st.text_input("Réponse", value=current_val if current_val else "", key=widget_key, label_visibility="collapsed")

    elif q_type == 'select':
        clean_opts = [opt.strip() for opt in q_options]
        if "" not in clean_opts: clean_opts.insert(0, "")
        idx = clean_opts.index(current_val) if current_val in clean_opts else 0
        val = st.selectbox("Sélection", clean_opts, index=idx, key=widget_key, label_visibility="collapsed")
    
    # --- GESTION DES NOMBRES (inchangée) ---
    elif q_type == 'number':
        if q_id == 9:
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
                format="%d", 
                key=widget_key, 
                label_visibility="collapsed"
            )
        else:
            default_val = float(current_val) if current_val and str(current_val).replace('.', '', 1).isdigit() else 0.0
            val = st.number_input("Nombre", value=default_val, key=widget_key, label_visibility="collapsed")
    
    # --- GESTION DES PHOTOS (inchangée) ---
    elif q_type == 'photo':
        val = st.file_uploader(
            "Images", 
            type=['png', 'jpg', 'jpeg'], 
            accept_multiple_files=True, 
            key=widget_key, 
            label_visibility="collapsed"
        )
        
        if val:
            file_names = ", ".join([f.name for f in val])
            st.success(f"Nombre d'images chargées : {len(val)} ({file_names})")
        elif current_val and isinstance(current_val, list) and current_val:
            names = ", ".join([getattr(f, 'name', 'Fichier') for f in current_val])
            st.info(f"Fichiers conservés : {len(current_val)} ({names})")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 3. Stockage de la valeur (liste de fichiers ou autre)
    if val is not None and (not is_dynamic_comment or val.strip() != ""):
        answers[q_id] = val 
    elif current_val is not None and not is_dynamic_comment:
        answers[q_id] = current_val

# --- FLUX PRINCIPAL (inchangé) ---

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
    # Logique inchangée
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
    # Logique inchangée
    df = st.session_state['df_struct']
    ID_SECTION_NAME = df['section'].iloc[0]
    
    st.markdown(f"### 👤 Étape unique : {ID_SECTION_NAME}")

    identification_questions = df[df['section'] == ID_SECTION_NAME]
    
    if st.session_state['id_rendering_ident'] is None:
         st.session_state['id_rendering_ident'] = str(uuid.uuid4())
    
    rendering_id = st.session_state['id_rendering_ident']
    
    for idx, (index, row) in enumerate(identification_questions.iterrows()):
        if check_condition(row, st.session_state['current_phase_temp'], st.session_state['collected_data']):
            # Aucune question ID 1000 ne devrait être rendue ici
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
    # Logique inchangée pour l'affichage du projet
    project_intitule = st.session_state['project_data'].get('Intitulé', 'Projet Inconnu')
    with st.expander(f"📍 Projet : {project_intitule}", expanded=False):
        project_details = st.session_state['project_data']

        st.write("**Détails du Projet Sélectionné**")
        
        cols1 = st.columns([1, 1, 1]) 
        fields_l1 = DISPLAY_GROUPS[0]
        for i, field_key in enumerate(fields_l1):
            renamed_key = PROJECT_RENAME_MAP.get(field_key, field_key)
            value = project_details.get(field_key, 'N/A')
            with cols1[i]:
                st.markdown(f"**{renamed_key}** : {value}")
        
        st.markdown("**Points de charge Standard**")
        cols2 = st.columns([1, 1, 1])
        fields_l2 = DISPLAY_GROUPS[1]
        for i, field_key in enumerate(fields_l2):
            renamed_key = PROJECT_RENAME_MAP.get(field_key, field_key)
            value = project_details.get(field_key, 'N/A')
            with cols2[i]:
                st.markdown(f"**{renamed_key}** : {value}")

        st.markdown("**Points de charge Pré-équipés**")
        cols3 = st.columns([1, 1, 1])
        fields_l3 = DISPLAY_GROUPS[2]
        for i, field_key in enumerate(fields_l3):
            renamed_key = PROJECT_RENAME_MAP.get(field_key, field_key)
            value = project_details.get(field_key, 'N/A')
            with cols3[i]:
                st.markdown(f"**{renamed_key}** : {value}")
        
        st.write("**Phases et Identification déjà complétées**")
        for idx, item in enumerate(st.session_state['collected_data']):
            st.write(f"• **{item['phase_name']}** : {len(item['answers'])} réponses")

    if st.session_state['step'] == 'LOOP_DECISION':
        # Logique inchangée
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
              # Logique inchangée
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
            
            # ------------------------------------------------------------------
            # --- CALCUL ET AFFICHAGE DE L'ATTENTE PHOTO ---
            # ------------------------------------------------------------------
            expected, details = get_expected_photo_count(current_phase, st.session_state['project_data'])
            
            # Booléen pour savoir si l'écart est attendu
            is_photo_rule_active = expected is not None and expected > 0
            
            if is_photo_rule_active:
                st.info(f"📸 **Attente Photos :** Il est attendu **{expected}** photos pour cette section (Total des bornes : {details}).")
            # ------------------------------------------------------------------

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
                # Ne pas rendre le champ de commentaire si c'est la question 1000
                if int(row.get('id', 0)) == COMMENT_ID: continue

                if check_condition(row, st.session_state['current_phase_temp'], st.session_state['collected_data']):
                    render_question(row, st.session_state['current_phase_temp'], current_phase, st.session_state['iteration_id'], idx)
                    visible_count += 1
            
            # ------------------------------------------------------------------
            # --- RENDU CONDITIONNEL DU COMMENTAIRE (Logique inchangée) ---
            # ------------------------------------------------------------------
            # Effectuer une pré-validation pour voir si le commentaire DOIT être affiché
            
            # Note: Nous utilisons le même calcul que dans validate_section
            current_photo_count = 0
            for _, row in section_questions.iterrows():
                if str(row['type']).strip().lower() == 'photo':
                    q_id = int(row['id'])
                    val = st.session_state['current_phase_temp'].get(q_id)
                    if isinstance(val, list):
                        current_photo_count += len(val)

            is_photo_count_incorrect = is_photo_rule_active and current_photo_count != expected

            if is_photo_count_incorrect:
                # Créer une ligne de question temporaire pour l'ID 1000
                comment_row = pd.Series({'id': COMMENT_ID})
                # Rendre le champ de commentaire
                render_question(comment_row, st.session_state['current_phase_temp'], current_phase, st.session_state['iteration_id'], 999) # Utilise un index élevé
            # ------------------------------------------------------------------


            if visible_count == 0 and not is_photo_count_incorrect:
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
                            # La fonction validate_section a déjà nettoyé l'ID 1000 si non requis
                            "answers": st.session_state['current_phase_temp'].copy() 
                        }
                        st.session_state['collected_data'].append(new_entry)
                        st.success("Enregistré !")
                        st.session_state['step'] = 'LOOP_DECISION'
                        st.rerun()
                    else:
                        html_errors = '<br>'.join([f"- {e}" for e in errors])
                        st.markdown(f'<div class="error-box"><b>⚠️ Erreurs :</b><br>{html_errors}</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state['step'] == 'FINISHED':
    # Logique inchangée
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
                    label="🖼️ Télécharger les photos (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=file_name_zip,
                    mime='application/zip'
                )
            else:
                st.info("Aucune photo à exporter.")
    
    st.markdown("---")
    if st.button("⬅️ Recommencer l'audit"):
        st.session_state.clear()
        st.rerun()

# --- IMPORTS ET PRÉPARATION ---
import streamlit as st
import pandas as pd
import uuid
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import json

# --- CONFIGURATION ET STYLE (Conservé pour l'esthétique) ---
st.set_page_config(page_title="Formulaire Dynamique - Firestore", layout="centered")

# Style CSS pour une meilleure UI Streamlit
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

# --- INITIALISATION FIREBASE SÉCURISÉE (via st.secrets) ---
def initialize_firebase():
    if not firebase_admin._apps:
        try:
            # Utilise les secrets stockés dans le cloud Streamlit sous la clé 'firebase'
            cred = credentials.Certificate(st.secrets["firebase"]) 
            firebase_admin.initialize_app(cred)
            st.sidebar.success("Connexion à Firebase réussie.")
        except KeyError:
            st.sidebar.error("Erreur critique: La section 'firebase' est manquante ou mal formatée dans st.secrets.")
            st.stop()
        except Exception as e:
            st.sidebar.error(f"Erreur d'initialisation Firebase : {e}")
            st.stop()
    
    return firestore.client()

db = initialize_firebase()


# --- FONCTIONS DE CHARGEMENT FIREBASE ---

@st.cache_data(ttl=3600)
def load_form_structure_from_firestore():
    """Charge la structure du formulaire depuis la collection 'formsquestions'."""
    try:
        docs = db.collection('formsquestions').order_by('id').get()
        data = [doc.to_dict() for doc in docs]
        
        if not data:
            st.error("Aucun document trouvé dans la collection 'formsquestions'.")
            return None
        
        df = pd.DataFrame(data)
        df.columns = df.columns.str.strip()
        
        # Normalisation des colonnes de condition
        rename_map = {
            'Condition value': 'Condition value', 'condition value': 'Condition value',
            'Condition Value': 'Condition value', 'Condition': 'Condition value',
            'Conditon on': 'Condition on', 'condition on': 'Condition on'
        }
        actual_rename = {k: v for k, v in rename_map.items() if k in df.columns}
        df = df.rename(columns=actual_rename)
        
        # Remplacer les NaN/None par des valeurs par défaut
        df['options'] = df['options'].fillna('')
        df['Description'] = df['Description'].fillna('')
        df['Condition value'] = df['Condition value'].fillna('')
        # Conversion sûre en nombre (0 par défaut)
        df['Condition on'] = df['Condition on'].apply(lambda x: int(x) if pd.notna(x) else 0)
        
        return df
    except Exception as e:
        st.error(f"Erreur lors de la lecture de la structure 'formsquestions' : {e}")
        return None

@st.cache_data(ttl=3600)
def load_site_data_from_firestore():
    """Charge les données des sites depuis la collection 'Sites'."""
    try:
        docs = db.collection('Sites').get()
        data = [doc.to_dict() for doc in docs]
        
        if not data:
            st.error("Aucun document trouvé dans la collection 'Sites'.")
            return None
            
        df_site = pd.DataFrame(data)
        df_site.columns = df_site.columns.str.strip()
        return df_site
    except Exception as e:
        st.error(f"Erreur lors de la lecture des données de site 'Sites' : {e}")
        return None

# --- NOUVELLE FONCTION DE SAUVEGARDE DANS FIRESTORE ---
def save_form_data(collected_data, project_data, project_id=None):
    """Sauvegarde les données collectées dans la collection 'FormAnswers'."""
    try:
        # Construction du document principal à sauvegarder
        final_document = {
            "project_id": project_data.get('Intitulé', 'N/A'),
            "project_details": project_data,
            "submission_date": datetime.now(),
            "status": "Completed",
            "collected_phases": collected_data
        }
        
        # Utilisation de l'ID du projet comme ID de document si disponible
        doc_id = project_data.get('Intitulé', f"form_submit_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # Sauvegarde
        db.collection('FormAnswers').document(doc_id).set(final_document)
        
        st.success(f"💾 Données sauvegardées avec succès dans Firestore ! (Collection: FormAnswers, ID: {doc_id})")
        return True
    except Exception as e:
        st.error(f"❌ Erreur lors de la sauvegarde dans Firestore : {e}")
        return False

# --- GESTION DE L'ÉTAT ---
def init_session_state():
    defaults = {
        'step': 'PROJECT_LOAD',
        'project_data': None,
        'collected_data': [],
        'current_phase_temp': {},
        'current_phase_name': None,
        'iteration_id': str(uuid.uuid4()),
        'identification_completed': False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- LOGIQUE MÉTIER (Condition & Validation - Fonctions inchangées) ---

def check_condition(row, current_answers, collected_data):
    """Vérifie si une question doit être affichée (Condition on = 1 ET Condition value satisfaite)."""
    try:
        if int(row.get('Condition on', 0)) != 1:
            return True
    except (ValueError, TypeError):
        return True

    all_past_answers = {}
    for phase_data in collected_data:
        all_past_answers.update(phase_data['answers'])
    combined_answers = {**all_past_answers, **current_answers}
    
    condition_str = str(row.get('Condition value', '')).strip()
    
    if not condition_str or "=" not in condition_str:
        return True

    try:
        target_id_str, expected_value_raw = condition_str.split('=', 1)
        target_id = int(target_id_str.strip())
        expected_value = expected_value_raw.strip().strip('"').strip("'")
        
        user_answer = combined_answers.get(target_id)
        
        if user_answer is not None:
            return str(user_answer).lower() == str(expected_value).lower()
        else:
            return False
            
    except Exception as e:
        return True

def validate_section(df_questions, section_name, answers, collected_data):
    """Valide si toutes les questions obligatoires visibles ont une réponse."""
    missing = []
    section_rows = df_questions[df_questions['section'] == section_name]
    
    for _, row in section_rows.iterrows():
        if not check_condition(row, answers, collected_data):
            continue
            
        is_mandatory = str(row['obligatoire']).strip().lower() == 'oui'
        if is_mandatory:
            q_id = int(row['id'])
            val = answers.get(q_id)
            if val is None or val == "" or (isinstance(val, (int, float)) and val == 0):
                missing.append(f"Question {q_id} : {row['question']}")
                
    return len(missing) == 0, missing

validate_phase = validate_section
validate_identification = validate_section

def render_question(row, answers, key_suffix):
    """Affiche un widget Streamlit."""
    q_id = int(row['id'])
    q_text = row['question']
    q_type = str(row['type']).strip().lower()
    q_desc = row['Description']
    q_mandatory = str(row['obligatoire']).lower() == 'oui'
    q_options = str(row['options']).split(',') if row['options'] else []
    
    label_html = f"<strong>{q_id}. {q_text}</strong>" + (' <span class="mandatory">*</span>' if q_mandatory else "")
    widget_key = f"q_{q_id}_{key_suffix}"
    
    current_val = answers.get(q_id)
    val = current_val

    st.markdown(f'<div class="question-card"><div>{label_html}</div>', unsafe_allow_html=True)
    if q_desc:
        st.markdown(f'<div class="description">{q_desc}</div>', unsafe_allow_html=True)

    if q_type == 'text':
        val = st.text_input("Réponse", value=current_val if current_val else "", key=widget_key, label_visibility="collapsed")
    
    elif q_type == 'select':
        clean_opts = [opt.strip() for opt in q_options]
        if "" not in clean_opts: clean_opts.insert(0, "")
        
        idx = 0
        if current_val in clean_opts:
            idx = clean_opts.index(current_val)
        val = st.selectbox("Sélection", clean_opts, index=idx, key=widget_key, label_visibility="collapsed")
        
    elif q_type == 'number':
        default_val = float(current_val) if current_val else 0.0
        val = st.number_input("Nombre", value=default_val, key=widget_key, label_visibility="collapsed")
        
    elif q_type == 'photo':
        # Les fichiers chargés doivent être gérés si nécessaire (stockage dans GCS ou autre)
        val = st.file_uploader("Image", type=['png', 'jpg', 'jpeg'], key=widget_key, label_visibility="collapsed")
        if val:
            st.success(f"Image chargée : {val.name}")
            # Note: Pour une sauvegarde complète, l'image devrait être uploadée séparément (ex: Storage)
        elif current_val:
            st.info("Image conservée.")
            
    st.markdown('</div>', unsafe_allow_html=True)
    
    if val is not None:
        answers[q_id] = val


# --- FLUX PRINCIPAL DE L'APPLICATION ---

st.markdown('<div class="main-header"><h1>📝Formulaire Chantier</h1></div>', unsafe_allow_html=True)

# 1. CHARGEMENT DE FIREBASE
if st.session_state['step'] == 'PROJECT_LOAD':
    st.markdown("### ☁️ Chargement de la structure et des sites depuis Firestore...")
    
    df_struct = load_form_structure_from_firestore()
    df_site = load_site_data_from_firestore()
    
    if df_struct is not None and df_site is not None:
        st.session_state['df_struct'] = df_struct
        st.session_state['df_site'] = df_site
        st.session_state['step'] = 'PROJECT'
        st.success("Données de configuration chargées. Prêt à démarrer.")
        st.rerun()
    else:
        st.warning("Veuillez vérifier vos collections 'Sites' et 'formsquestions'.")


# 2. SÉLECTION PROJET
elif st.session_state['step'] == 'PROJECT':
    df_site = st.session_state['df_site']
    st.markdown("### 🏗️ Sélection du Chantier")
    
    if 'Intitulé' not in df_site.columns:
        st.error("Colonne 'Intitulé' manquante dans la collection 'Sites'.")
        
    projects = [""] + df_site['Intitulé'].dropna().unique().tolist()
    selected_proj = st.selectbox("Rechercher un projet", projects)
    
    if selected_proj:
        row = df_site[df_site['Intitulé'] == selected_proj].iloc[0]
        st.info(f"Projet sélectionné : {selected_proj} ")
        
        if st.button("✅ Démarrer l'identification"):
            st.session_state['project_data'] = row.to_dict()
            st.session_state['step'] = 'IDENTIFICATION'
            st.session_state['current_phase_temp'] = {}
            st.session_state['iteration_id'] = str(uuid.uuid4())
            st.rerun()

# 3. IDENTIFICATION
elif st.session_state['step'] == 'IDENTIFICATION':
    df = st.session_state['df_struct']
    ID_SECTION_NAME = df['section'].iloc[0]
    
    st.markdown(f"### 👤 Étape unique : {ID_SECTION_NAME}")

    identification_questions = df[df['section'] == ID_SECTION_NAME]
    
    for _, row in identification_questions.iterrows():
        if check_condition(row, st.session_state['current_phase_temp'], st.session_state['collected_data']):
            render_question(row, st.session_state['current_phase_temp'], st.session_state['iteration_id'])
            
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
            st.success("Identification validée. Prêt pour les phases.")
            st.rerun()
        else:
            st.markdown('<div class="error-box"><b>⚠️ Erreur de validation :</b><br>' + '<br>'.join([f"- {e}" for e in errors]) + '</div>', unsafe_allow_html=True)

# 4. LA BOUCLE (Ajout/Remplissage des phases)
elif st.session_state['step'] in ['LOOP_DECISION', 'FILL_PHASE']:
    
    with st.expander(f"📍 Projet : {st.session_state['project_data'].get('Intitulé')}", expanded=False):
        st.write("Phases et Identification déjà complétées :")
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
            if st.button("🏁 Terminer l'audit et Sauvegarder"):
                st.session_state['step'] = 'FINISHED'
                st.rerun()
    
    elif st.session_state['step'] == 'FILL_PHASE':
        # ... (Logique de sélection et de remplissage de phase inchangée)
        df = st.session_state['df_struct']
        
        ID_SECTION_NAME = df['section'].iloc[0]
        ID_SECTION_CLEAN = str(ID_SECTION_NAME).strip().lower()
        SECTIONS_TO_EXCLUDE_CLEAN = {ID_SECTION_CLEAN, "phase"}
        
        all_sections_raw = df['section'].unique().tolist()
        available_phases = [sec for sec in all_sections_raw if pd.notna(sec) and str(sec).strip().lower() not in SECTIONS_TO_EXCLUDE_CLEAN]
        
        # Sélection de phase
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
            
            if st.button("🔄 Changer de phase"):
                st.session_state['current_phase_name'] = None
                st.session_state['current_phase_temp'] = {}
                st.rerun()
            
            st.markdown("---")
            
            section_questions = df[df['section'] == current_phase]
            visible_count = 0
            
            for _, row in section_questions.iterrows():
                if check_condition(row, st.session_state['current_phase_temp'], st.session_state['collected_data']):
                    render_question(row, st.session_state['current_phase_temp'], st.session_state['iteration_id'])
                    visible_count += 1
            
            if visible_count == 0: st.warning("Aucune question visible.")

            st.markdown("---")
            
            c1, c2 = st.columns([1, 2])
            with c1:
                if st.button("❌ Annuler"):
                    st.session_state['step'] = 'LOOP_DECISION'
                    st.rerun()
            with c2:
                if st.button("💾 Valider la phase"):
                    is_valid, errors = validate_phase(df, current_phase, st.session_state['current_phase_temp'], st.session_state['collected_data'])
                    
                    if is_valid:
                        new_entry = {
                            "phase_name": current_phase,
                            "answers": st.session_state['current_phase_temp'].copy()
                        }
                        st.session_state['collected_data'].append(new_entry)
                        st.success("Phase enregistrée !")
                        st.session_state['step'] = 'LOOP_DECISION'
                        st.rerun()
                    else:
                        st.markdown('<div class="error-box"><b>⚠️ Erreurs :</b><br>' + '<br>'.join([f"- {e}" for e in errors]) + '</div>', unsafe_allow_html=True)


# 5. FIN (Ajout de la sauvegarde)
elif st.session_state['step'] == 'FINISHED':
    st.markdown("## 🎉 Sauvegarde et Fin")
    st.write(f"Projet : **{st.session_state['project_data'].get('Intitulé')}**")
    
    # Tentative de sauvegarde
    if 'data_saved' not in st.session_state:
        # Sauvegarde uniquement la première fois qu'on arrive à l'étape FINISHED
        success = save_form_data(st.session_state['collected_data'], st.session_state['project_data'])
        if success:
            st.balloons()
            st.session_state['data_saved'] = True
    else:
        st.success("Le formulaire a déjà été sauvegardé dans Firestore.")

    st.markdown("### Résumé des données collectées :")
    for i, phase in enumerate(st.session_state['collected_data']):
        with st.expander(f"Section {i+1} : {phase['phase_name']}"):
            # Afficher le JSON sans les fichiers photo (qui sont des objets Streamlit non sérialisables)
            display_data = {k: v for k, v in phase['answers'].items() if not hasattr(v, 'read')}
            st.json(display_data)
            
    if st.button("🔄 Nouveau projet"):
        st.session_state.clear()
        st.rerun()

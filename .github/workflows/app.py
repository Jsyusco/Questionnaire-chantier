import streamlit as st
import pandas as pd
import uuid

# --- CONFIGURATION ET STYLE ---
st.set_page_config(page_title="Formulaire Dynamique - Mode Boucle V3", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #121212; color: #e0e0e0; } 
    .main-header { background-color: #1e1e1e; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; border-bottom: 3px solid #4285F4; }
    .block-container { max-width: 800px; }
    
    /* Styles des blocs */
    .phase-block { background-color: #1e1e1e; padding: 25px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #333; }
    .question-card { background-color: #262626; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #4285F4; }
    
    /* Textes */
    h1, h2, h3 { color: #ffffff !important; }
    .description { font-size: 0.9em; color: #aaaaaa; font-style: italic; margin-bottom: 10px; }
    .mandatory { color: #F4B400; font-weight: bold; margin-left: 5px; }
    
    /* Messages de validation */
    .success-box { background-color: #1e4620; padding: 15px; border-radius: 8px; border-left: 5px solid #4caf50; color: #fff; margin: 10px 0; }
    .error-box { background-color: #3d1f1f; padding: 15px; border-radius: 8px; border-left: 5px solid #ff6b6b; color: #ffdad9; margin: 10px 0; }
    
    /* Boutons */
    .stButton > button { border-radius: 8px; font-weight: bold; padding: 0.5rem 1rem; }
    div[data-testid="stButton"] > button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- FONCTIONS DE CHARGEMENT ---
@st.cache_data
def load_form_structure(file):
    try:
        df = pd.read_excel(file, sheet_name='Questions', engine='openpyxl')
        df.columns = df.columns.str.strip()
        rename_map = {k: 'Condition value' for k in ['Conditon value', 'condition value', 'Condition Value']}
        rename_map.update({k: 'Condition on' for k in ['Conditon on', 'condition on']})
        df = df.rename(columns=rename_map)
        
        df['options'] = df['options'].fillna('')
        df['Description'] = df['Description'].fillna('')
        df['Condition value'] = df['Condition value'].fillna('')
        df['Condition on'] = df['Condition on'].fillna(0)
        return df
    except Exception as e:
        st.error(f"Erreur technique lors de la lecture du fichier structure : {e}")
        return None

@st.cache_data
def load_site_data(file):
    try:
        df_site = pd.read_excel(file, sheet_name='Site', engine='openpyxl')
        df_site.columns = df_site.columns.str.strip()
        return df_site
    except Exception as e:
        st.error(f"Erreur lors de la lecture de la feuille 'Site' : {e}")
        return None

# --- GESTION DE L'ÉTAT (SESSION STATE) ---
def init_session_state():
    defaults = {
        # Nouvelle étape 'IDENTIFICATION' ajoutée
        'step': 'UPLOAD',              # UPLOAD, PROJECT, IDENTIFICATION, LOOP_DECISION, FILL_PHASE, FINISHED
        'project_data': None,          # Données du projet sélectionné
        'collected_data': [],          # Liste des phases validées (dictionnaires)
        'current_phase_temp': {},      # Réponses temporaires de la phase en cours
        'current_phase_name': None,    # Nom de la phase en cours (Section)
        'iteration_id': str(uuid.uuid4()), # ID unique pour les widgets pour éviter les conflits
        'identification_completed': False # Flag pour s'assurer que l'ID a été faite
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- LOGIQUE MÉTIER ---

def check_condition(row, current_answers, collected_data):
    """
    Vérifie si une question doit être affichée.
    Recherche la réponse dans l'historique complet (phases validées) et la phase courante.
    """
    
    # 1. Collecter toutes les réponses précédentes (Phases terminées)
    all_past_answers = {}
    for phase_data in collected_data:
        all_past_answers.update(phase_data['answers'])

    # 2. Combiner avec les réponses de la phase en cours (Les temporaires ont priorité)
    combined_answers = {**all_past_answers, **current_answers}
    
    try:
        if int(row.get('Condition on', 0)) != 1:
            return True
        
        condition_rule = str(row.get('Condition value', '')).strip()
        if not condition_rule:
            return True
            
        if '=' in condition_rule:
            target_id_str, target_value = condition_rule.split('=', 1

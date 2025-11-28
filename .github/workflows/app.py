import streamlit as st
import pandas as pd
import uuid

# --- CONFIGURATION ET STYLE ---
st.set_page_config(page_title="Formulaire Dynamique - Esthétique Simple", layout="centered")

# Nous n'excluons plus la section 'phase' ou 'identification' de la logique de la boucle.
# Nous conservons uniquement l'esthétique simplifiée.
EXCLUDED_PHASE_SELECTION_NAME = "N/A" # Variable non utilisée dans cette version

st.markdown("""
<style>
    /* Général */
    .stApp { background-color: #121212; color: #e0e0e0; } 
    .block-container { max-width: 800px; }
    
    /* En-tête principal */
    h1 { color: #ffffff !important; border-bottom: 2px solid #4285F4; padding-bottom: 10px; margin-bottom: 20px; text-align: center;}
    
    /* Styles des blocs de phase (conservés) */
    .phase-block { 
        background-color: #1e1e1e; 
        padding: 25px; 
        border-radius: 12px; 
        margin-bottom: 20px; 
        border: 1px solid #333; 
    }
    
    /* MISE EN FORME DES QUESTIONS : Suppression de l'arrière-plan coloré */
    .question-card { 
        background-color: transparent !important; /* Rendre transparent */
        padding: 10px 0; /* Réduire le padding */
        border-radius: 0;
        margin-bottom: 15px; 
        border-left: 4px solid #4285F4; /* Conserver la ligne bleue pour la démarcation */
        padding-left: 15px; /* Ajouter un espace à gauche de la ligne */
    }
    
    /* Textes */
    h2, h3 { color: #ffffff !important; }
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
        # Reversion à la logique où tout est dans la boucle
        'step': 'UPLOAD',              # UPLOAD, PROJECT, LOOP_DECISION, FILL_PHASE, FINISHED
        'project_data': None,          
        'collected_data': [],          
        'current_phase_temp': {},      
        'current_phase_name': None,    
        'iteration_id': str(uuid.uuid4())
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
    (Logique de condition conservée de la version précédente pour la robustesse inter-phases)
    """
    
    all_past_answers = {}
    for phase_data in collected_data:
        all_past_answers.update(phase_data['answers'])

    combined_answers = {**all_past_answers, **current_answers}
    
    try:
        if int(row.get('Condition on', 0)) != 1:
            return True
        
        condition_rule = str(row.get('Condition value', '')).strip()
        if not condition_rule:
            return True
            
        if '=' in condition_rule:
            target_id_str, target_value = condition_rule.split('=', 1)
            target_id = int(target_id_str.strip())
            target_value = target_value.strip()
            
            user_answer = combined_answers.get(target_id)
            return str(user_answer) == str(target_value)
        return True
    except:
        return True

def validate_phase(df_questions, phase_name, answers, collected_data):
    """
    Valide si toutes les questions obligatoires de la phase ont une réponse.
    (Logique de validation conservée pour la robustesse inter-phases)
    """
    missing = []
    phase_rows = df_questions[df_questions['section'] == phase_name]
    
    for _, row in phase_rows.iterrows():
        # Utilise l'historique complet pour vérifier la condition
        if not check_condition(row, answers, collected_data): 
            continue
            
        is_mandatory = str(row['obligatoire']).strip().lower() == 'oui'
        if is_mandatory:
            q_id = int(row['id'])
            val = answers.get(q_id)
            if val is None or val == "" or (isinstance(val, (int, float)) and val == 0):
                missing.append(f"Question {q_id} : {row['question']}")
                
    return len(missing) == 0, missing

# --- COMPOSANTS UI (MODIFIÉ ESTHÉTIQUE) ---

def render_question(row, answers, key_suffix):
    """Affiche un widget pour une question donnée, avec le style épuré."""
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

    # Utilisation du CSS de "question-card" pour l'esthétique épurée
    st.markdown(f'<div class="question-card"><div>{label_html}</div>', unsafe_allow_html=True)
    if q_desc:
        st.markdown(f'<div class="description">{q_desc}</div>', unsafe_allow_html=True)
    
    with st.container():
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
            val = st.file_uploader("Image", type=['png', 'jpg', 'jpeg'], key=widget_key, label_visibility="collapsed")
            if val:
                st.success(f"Image chargée : {val.name}")
            elif current_val:
                st.info("Image conservée de la session précédente.")

    st.markdown('</div>', unsafe_allow_html=True)
    
    if val is not None:
        answers[q_id] = val

# --- MAIN APP FLOW ---

# Titre principal simple (sans le bloc indésirable)
st.markdown('<h1>📝 Audit & Formulaire Dynamique</h1>', unsafe_allow_html=True)
df = st.session_state.get('df_struct')

# 1. CHARGEMENT
if st.session_state['step'] == 'UPLOAD':
    uploaded_file = st.file_uploader("📂 Chargez le fichier de configuration (Excel)", type=["xlsx"])
    if uploaded_file:
        df_struct = load_form_structure(uploaded_file)
        df_site = load_site_data(uploaded_file)
        
        if df_struct is not None and df_site is not None:
            st.session_state['df_struct'] = df_struct
            st.session_state['df_site'] = df_site
            st.session_state['step'] = 'PROJECT'
            st.rerun()

# 2. SÉLECTION PROJET
elif st.session_state['step'] == 'PROJECT':
    df_site = st.session_state['df_site']
    st.markdown("### 🏗️ Sélection du Chantier")
    
    if 'Intitulé' not in df_site.columns:
        st.error("Colonne 'Intitulé' manquante dans la feuille 'Site'. Impossible de continuer.")
        st.session_state['step'] = 'UPLOAD'
        st.rerun()
        
    projects = [""] + df_site['Intitulé'].dropna().unique().tolist()
    selected_proj = st.selectbox("Rechercher un projet", projects)
    
    if selected_proj:
        row = df_site[df_site['Intitulé'] == selected_proj].iloc[0]
        st.info(f"Projet sélectionné : {selected_proj} (Code: {row.get('Code Site', 'N/A')})")
        
        if st.button("✅ Démarrer l'audit (Mode Boucle)"):
            st.session_state['project_data'] = row.to_dict()
            # Passe directement à la décision de boucle (toutes les phases sont sélectionnables ici)
            st.session_state['step'] = 'LOOP_DECISION' 
            st.rerun()

# 3. LA BOUCLE (LOGIQUE PRINCIPALE - Toutes les phases y compris l'identification sont gérées ici)
elif st.session_state['step'] in ['LOOP_DECISION', 'FILL_PHASE']:
    
    # HEADER PROJET (Toujours visible)
    with st.expander(f"📍 Projet : {st.session_state['project_data'].get('Intitulé')}", expanded=False):
        st.write("Phases déjà complétées :")
        for idx, item in enumerate(st.session_state['collected_data']):
            st.write(f"• **{item['phase_name']}** : {len(item['answers'])} réponses")
        st.markdown("---")
        st.json(st.session_state['project_data'])

    # --- A. DÉCISION (HUB) ---
    if st.session_state['step'] == 'LOOP_DECISION':
        st.markdown('<div class="phase-block">', unsafe_allow_html=True)
        st.markdown("### 🔄 Gestion des Phases")
        
        st.markdown("---")
        st.markdown("#### Souhaitez-vous déclarer une nouvelle phase ?")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ OUI, Ajouter une phase"):
                st.session_state['step'] = 'FILL_PHASE'
                st.session_state['current_phase_temp'] = {} 
                st.session_state['current_phase_name'] = None
                st.session_state['iteration_id'] = str(uuid.uuid4())
                st.rerun()
        with col2:
            if st.button("🏁 NON, Terminer l'audit"):
                st.session_state['step'] = 'FINISHED'
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- B. REMPLISSAGE (FORMULAIRE) ---
    elif st.session_state['step'] == 'FILL_PHASE':
        df = st.session_state['df_struct']
        
        st.markdown(f'<div class="phase-block">', unsafe_allow_html=True)
        
        # Toutes les sections sont disponibles pour la sélection (y compris identification et phase)
        available_phases = df['section'].unique().tolist()
        
        if not st.session_state['current_phase_name']:
             st.markdown("### 📑 Sélection de la phase")
             # L'utilisateur peut sélectionner n'importe quelle phase, y compris celles qui devraient être uniques
             phase_choice = st.selectbox("Quelle phase souhaitez-vous renseigner ?", [""] + available_phases)
             if phase_choice:
                 st.session_state['current_phase_name'] = phase_choice
                 st.rerun()
             if st.button("⬅️ Retour au Menu Principal"):
                 st.session_state['step'] = 'LOOP_DECISION'
                 st.rerun()
                 
        else:
            current_phase = st.session_state['current_phase_name']
            st.markdown(f"### 📝 Remplissage : {current_phase}")
            
            if st.button("🔄 Changer de phase"):
                st.session_state['current_phase_name'] = None
                st.session_state['current_phase_temp'] = {}
                st.rerun()
            
            st.markdown("---")
            
            section_questions = df[df['section'] == current_phase]
            
            visible_count = 0
            for _, row in section_questions.iterrows():
                # Utilise la logique de condition complète
                if check_condition(row, st.session_state['current_phase_temp'], st.session_state['collected_data']): 
                    render_question(row, st.session_state['current_phase_temp'], st.session_state['iteration_id'])
                    visible_count += 1
            
            if visible_count == 0:
                st.warning("Aucune question applicable pour cette phase. Vérifiez les conditions d'affichage et l'orthographe de la section dans votre fichier Excel.")

            st.markdown("---")
            
            c1, c2 = st.columns([1, 2])
            with c1:
                if st.button("❌ Annuler cette phase"):
                    st.session_state['step'] = 'LOOP_DECISION'
                    st.rerun()
            with c2:
                if st.button("💾 Valider et Enregistrer la phase"):
                    is_valid, errors = validate_phase(
                        df, 
                        current_phase, 
                        st.session_state['current_phase_temp'],
                        st.session_state['collected_data'] 
                    )
                    
                    if is_valid:
                        new_entry = {
                            "phase_name": current_phase,
                            "answers": st.session_state['current_phase_temp'].copy()
                        }
                        st.session_state['collected_data'].append(new_entry)
                        
                        st.success("Phase enregistrée avec succès !")
                        st.session_state['step'] = 'LOOP_DECISION'
                        st.rerun()
                    else:
                        st.markdown('<div class="error-box"><b>⚠️ Impossible de valider :</b><br>' + 
                                    '<br>'.join([f"- {e}" for e in errors]) + '</div>', 
                                    unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)

# 4. FIN
elif st.session_state['step'] == 'FINISHED':
    st.balloons()
    st.markdown('<div class="phase-block" style="text-align:center;">', unsafe_allow_html=True)
    st.markdown("## 🎉 Formulaire Terminé")
    st.write(f"Projet : **{st.session_state['project_data'].get('Intitulé')}**")
    st.write(f"Nombre total de sections complétées : **{len(st.session_state['collected_data'])}**")
    st.markdown('</div>', unsafe_allow_html=True)
    
    for i, phase in enumerate(st.session_state['collected_data']):
        with st.expander(f"Section {i+1} : {phase['phase_name']}"):
            st.json(phase['answers'])
            
    if st.button("🔄 Commencer un nouveau projet"):
        st.session_state.clear()
        st.rerun()

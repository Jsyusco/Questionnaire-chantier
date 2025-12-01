# --- IMPORTS ET PRÉPARATION ---
import streamlit as st # La bibliothèque principale pour créer l'application web.
import pandas as pd # Utilisé pour lire et manipuler les données du fichier Excel.
import uuid # Utilisé pour générer des identifiants uniques (UUID), essentiels pour les clés de widgets dynamiques dans Streamlit.

# --- CONFIGURATION ET STYLE ---
# Configure les paramètres de base de la page : titre d'onglet, et mise en page centrée.
st.set_page_config(page_title="Formulaire Dynamique - Mode Boucle V3", layout="centered")

# Injection de CSS pour personnaliser l'apparence (thème sombre).
st.markdown("""
<style>
    /* Fond général sombre */
    .stApp { background-color: #121212; color: #e0e0e0; }
    /* En-tête principal stylisé */
    .main-header { background-color: #1e1e1e; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; border-bottom: 3px solid #4285F4; }
    /* Limite la largeur du contenu pour une meilleure lisibilité */
    .block-container { max-width: 800px; }
    
    /* Styles des blocs de phase/section */
    .phase-block { background-color: #1e1e1e; padding: 25px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #333; }
    /* Style pour chaque carte de question */
    .question-card { background-color: transparent; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #4285F4; }
    
    /* Styles de texte */
    h1, h2, h3 { color: #ffffff !important; }
    .description { font-size: 0.9em; color: #aaaaaa; font-style: italic; margin-bottom: 10px; }
    /* Style pour l'indicateur (*) de question obligatoire */
    .mandatory { color: #F4B400; font-weight: bold; margin-left: 5px; }
    
    /* Messages de validation personnalisés */
    .success-box { background-color: #1e4620; padding: 15px; border-radius: 8px; border-left: 5px solid #4caf50; color: #fff; margin: 10px 0; }
    .error-box { background-color: #3d1f1f; padding: 15px; border-radius: 8px; border-left: 5px solid #ff6b6b; color: #ffdad9; margin: 10px 0; }
    
    /* Styles des boutons */
    .stButton > button { border-radius: 8px; font-weight: bold; padding: 0.5rem 1rem; }
    div[data-testid="stButton"] > button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- FONCTIONS DE CHARGEMENT ---
# Le décorateur @st.cache_data met en cache le résultat de cette fonction.
# Si le même fichier est chargé plusieurs fois, la fonction ne s'exécute qu'une seule fois, améliorant les performances.
@st.cache_data
def load_form_structure(file):
    try:
        df = pd.read_excel(file, sheet_name='Questions', engine='openpyxl')
        # Lecture de la feuille 'Questions' (structure du formulaire)
        df = pd.read_excel(file, sheet_name='Questions', engine='openpyxl')
        df.columns = df.columns.str.strip() # Nettoie les noms de colonnes
        # Mapping pour gérer les variations de nom pour les colonnes de condition
        rename_map = {k: 'Condition value' for k in ['Conditon value', 'condition value', 'Condition Value']}
        rename_map.update({k: 'Condition on' for k in ['Conditon on', 'condition on']})
        df = df.rename(columns=rename_map)
        
        # Remplace les valeurs manquantes (NaN) par des chaînes vides ou 0 pour éviter les erreurs.
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
        # Lecture de la feuille 'Site' (liste des projets)
        df_site = pd.read_excel(file, sheet_name='Site', engine='openpyxl')
        df_site.columns = df_site.columns.str.strip()
        return df_site
    except Exception as e:
        st.error(f"Erreur lors de la lecture de la feuille 'Site' : {e}")
        return None

# --- GESTION DE L'ÉTAT (SESSION STATE) ---
# Le Session State (st.session_state) permet de conserver les données à travers les re-runs de Streamlit.
# C'est la mémoire de l'application.
def init_session_state():
    defaults = {
        'step': 'UPLOAD', # État actuel de l'application (le flux/machine à états)
        'project_data': None, # Données du projet sélectionné
        'collected_data': [], # Liste pour stocker les réponses de toutes les phases complétées.
        'current_phase_temp': {}, # Réponses temporaires de la phase en cours (avant validation).
        'current_phase_name': None, # Nom de la phase en cours de remplissage
        'iteration_id': str(uuid.uuid4()), # ID unique de l'itération pour les clés de widgets dynamiques.
        'identification_completed': False # Indicateur si l'étape d'identification est terminée.
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state() # Initialisation dès le début du script

# --- LOGIQUE MÉTIER ---

def check_condition(row, current_answers, collected_data):
    """Vérifie si une question doit être affichée en fonction des réponses passées et actuelles."""
    
    # Combine toutes les réponses disponibles (passées et actuelles)
    all_past_answers = {}
    for phase_data in collected_data:
        all_past_answers.update(phase_data['answers'])

    combined_answers = {**all_past_answers, **current_answers}
    
    try:
        # Si 'Condition on' n'est pas 1, la condition est ignorée et la question est affichée.
        if int(row.get('Condition on', 0)) != 1:
            return True
        
        condition_rule = str(row.get('Condition value', '')).strip()
        if not condition_rule:
            return True
            
        # Gère la règle de condition au format: ID_QUESTION=VALEUR_ATTENDUE
        if '=' in condition_rule:
            target_id_str, target_value = condition_rule.split('=', 1)
            target_id = int(target_id_str.strip())
            target_value = target_value.strip()
            
            user_answer = combined_answers.get(target_id)
            # La condition est remplie si la réponse de l'utilisateur correspond à la valeur attendue (en tant que chaînes)
            return str(user_answer) == str(target_value)
        return True
    except:
        # En cas d'erreur de format de condition, la question est affichée par défaut.
        return True

def validate_section(df_questions, section_name, answers, collected_data):
    """Valide si toutes les questions obligatoires visibles d'une section ont une réponse."""
    missing = []
    section_rows = df_questions[df_questions['section'] == section_name]
    
    for _, row in section_rows.iterrows():
        # Vérifie d'abord si la question doit être affichée (conditionnelle)
        if not check_condition(row, answers, collected_data):
            continue
            
        is_mandatory = str(row['obligatoire']).strip().lower() == 'oui'
        if is_mandatory:
            q_id = int(row['id'])
            val = answers.get(q_id)
            # Vérifie si la réponse est vide (None, "", ou 0 pour les nombres)
            if val is None or val == "" or (isinstance(val, (int, float)) and val == 0):
                missing.append(f"Question {q_id} : {row['question']}")
                
    return len(missing) == 0, missing

# Alias pour la validation des différentes étapes
validate_phase = validate_section
validate_identification = validate_section

# --- COMPOSANTS UI ---

def render_question(row, answers, key_suffix):
    """Affiche un widget Streamlit basé sur le type de question du fichier Excel."""
    q_id = int(row['id'])
    q_text = row['question']
    q_type = str(row['type']).strip().lower()
    q_desc = row['Description']
    q_mandatory = str(row['obligatoire']).lower() == 'oui'
    q_options = str(row['options']).split(',') if row['options'] else []
    
    # Construction du label HTML (avec l'étoile pour obligatoire)
    label_html = f"<strong>{q_id}. {q_text}</strong>" + (' <span class="mandatory">*</span>' if q_mandatory else "")
    # Clé de widget unique (ID de la question + UUID) pour assurer le bon fonctionnement du state management
    widget_key = f"q_{q_id}_{key_suffix}"
    
    current_val = answers.get(q_id)
    val = current_val

    # Affichage de la carte de question stylisée
    st.markdown(f'<div class="question-card"><div>{label_html}</div>', unsafe_allow_html=True)
    if q_desc:
        st.markdown(f'<div class="description">{q_desc}</div>', unsafe_allow_html=True)

    # Création du widget Streamlit selon le type
    if q_type == 'text':
        val = st.text_input("Réponse", value=current_val if current_val else "", key=widget_key, label_visibility="collapsed")
    
    elif q_type == 'select':
        clean_opts = [opt.strip() for opt in q_options]
        # Ajout d'une option vide au début pour permettre une réponse non-sélectionnée (utile pour la validation)
        if "" not in clean_opts: clean_opts.insert(0, "")
        
        idx = 0
        if current_val in clean_opts:
            idx = clean_opts.index(current_val)
        val = st.selectbox("Sélection", clean_opts, index=idx, key=widget_key, label_visibility="collapsed")
        
    elif q_type == 'number':
        # Conversion en float ou 0.0 par défaut pour le number_input
        default_val = float(current_val) if current_val else 0.0
        val = st.number_input("Nombre", value=default_val, key=widget_key, label_visibility="collapsed")
        
    elif q_type == 'photo':
        val = st.file_uploader("Image", type=['png', 'jpg', 'jpeg'], key=widget_key, label_visibility="collapsed")
        if val:
            st.success(f"Image chargée : {val.name}")
        elif current_val:
            st.info("Image conservée de la session précédente.")

    st.markdown('</div>', unsafe_allow_html=True)
    
    # Stocke la valeur du widget dans le dictionnaire de réponses temporaires
    if val is not None:
        answers[q_id] = val

# --- FLUX PRINCIPAL DE L'APPLICATION (MACHINE À ÉTATS) ---

st.markdown('<div class="main-header"><h1>📝 Audit & Formulaire Dynamique</h1></div>', unsafe_allow_html=True)
df = st.session_state.get('df_struct') # Récupération de la structure du formulaire

# 1. CHARGEMENT (state: 'UPLOAD')
if st.session_state['step'] == 'UPLOAD':
    # L'utilisateur charge le fichier de configuration Excel.
    uploaded_file = st.file_uploader("📂 Chargez le fichier de configuration (Excel)", type=["xlsx"])
    if uploaded_file:
        df_struct = load_form_structure(uploaded_file)
        df_site = load_site_data(uploaded_file)
        
        if df_struct is not None and df_site is not None:
            # Stockage des DataFrames dans le Session State
            st.session_state['df_struct'] = df_struct
            st.session_state['df_site'] = df_site
            st.session_state['step'] = 'PROJECT' # Passage à l'étape suivante
            st.rerun() # Force la ré-exécution du script pour afficher la nouvelle étape

# 2. SÉLECTION PROJET (state: 'PROJECT')
elif st.session_state['step'] == 'PROJECT':
    df_site = st.session_state['df_site']
    st.markdown("### 🏗️ Sélection du Chantier")
    
    # Vérification de la présence de la colonne clé
    if 'Intitulé' not in df_site.columns:
        st.error("Colonne 'Intitulé' manquante dans la feuille 'Site'. Impossible de continuer.")
        st.session_state['step'] = 'UPLOAD'
        st.rerun()
        
    projects = [""] + df_site['Intitulé'].dropna().unique().tolist()
    selected_proj = st.selectbox("Rechercher un projet", projects)
    
    if selected_proj:
        row = df_site[df_site['Intitulé'] == selected_proj].iloc[0]
        st.info(f"Projet sélectionné : {selected_proj} (Code: {row.get('Code Site', 'N/A')})")
        
        if st.button("✅ Démarrer l'identification"):
            st.session_state['project_data'] = row.to_dict()
            st.session_state['step'] = 'IDENTIFICATION'
            st.session_state['current_phase_temp'] = {}
            # Génère un nouvel UUID pour la première phase (Identification)
            st.session_state['iteration_id'] = str(uuid.uuid4()) 
            st.rerun()

# 3. IDENTIFICATION (state: 'IDENTIFICATION')
elif st.session_state['step'] == 'IDENTIFICATION':
    df = st.session_state['df_struct']
    
    # Récupère le nom de la première section de l'Excel (considérée comme l'identification)
    ID_SECTION_NAME = df['section'].iloc[0]
    
    st.markdown(f'<div class="phase-block">', unsafe_allow_html=True)
    st.markdown(f"### 👤 Étape unique : {ID_SECTION_NAME}")

    identification_questions = df[df['section'] == ID_SECTION_NAME]
    
    # Boucle pour afficher toutes les questions d'identification
    for _, row in identification_questions.iterrows():
        # N'affiche la question que si la condition est remplie
        if check_condition(row, st.session_state['current_phase_temp'], st.session_state['collected_data']):
            # Les réponses sont stockées dans 'current_phase_temp'
            render_question(row, st.session_state['current_phase_temp'], st.session_state['iteration_id'])
           
    st.markdown("---")
    
    if st.button("✅ Valider l'identification et passer aux phases"):
        # Validation des champs obligatoires
        is_valid, errors = validate_identification(
            df,
            ID_SECTION_NAME,
            st.session_state['current_phase_temp'],
            st.session_state['collected_data']
        )
        
        if is_valid:
            # Enregistrement des données d'identification dans collected_data
            id_entry = {
                "phase_name": ID_SECTION_NAME,
                "answers": st.session_state['current_phase_temp'].copy()
            }
            st.session_state['collected_data'].append(id_entry)
            st.session_state['identification_completed'] = True
            
            st.session_state['step'] = 'LOOP_DECISION' # Passage au menu de la boucle
            st.session_state['current_phase_temp'] = {}
            st.success("Identification validée. Passage au mode boucle.")
            st.rerun()
        else:
            # Affichage des erreurs de validation
            st.markdown('<div class="error-box"><b>⚠️ Erreur de validation :</b><br>' +
                        '<br>'.join([f"- {e}" for e in errors]) + '</div>',
                        unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

# 4. LA BOUCLE (state: 'LOOP_DECISION' ou 'FILL_PHASE')
elif st.session_state['step'] in ['LOOP_DECISION', 'FILL_PHASE']:
    
    # Affiche un résumé du projet et des phases déjà complétées (dans un expander)
    with st.expander(f"📍 Projet : {st.session_state['project_data'].get('Intitulé')}", expanded=False):
        st.write("Phases et Identification déjà complétées :")
        for idx, item in enumerate(st.session_state['collected_data']):
            st.write(f"• **{item['phase_name']}** : {len(item['answers'])} réponses")
        st.markdown("---")
        st.json(st.session_state['project_data'])

    # --- A. DÉCISION (HUB) ---
    if st.session_state['step'] == 'LOOP_DECISION':
        st.markdown('<div class="phase-block">', unsafe_allow_html=True)
        st.markdown("### 🔄 Gestion des Phases de Travaux")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ OUI, Ajouter une phase de travail"):
                st.session_state['step'] = 'FILL_PHASE' # Passe au remplissage
                st.session_state['current_phase_temp'] = {}
                st.session_state['current_phase_name'] = None
                st.session_state['iteration_id'] = str(uuid.uuid4()) # Génère un nouvel ID pour les widgets de la nouvelle phase
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
        
        # Détermination des sections à exclure (l'Identification et toute section nommée "phase" pour éviter les confusions)
        ID_SECTION_NAME = None
        if st.session_state['collected_data']:
            ID_SECTION_NAME = st.session_state['collected_data'][0]['phase_name']
        elif not df.empty:
            ID_SECTION_NAME = df['section'].iloc[0]

        ID_SECTION_CLEAN = str(ID_SECTION_NAME).strip().lower() if ID_SECTION_NAME else None
        SECTIONS_TO_EXCLUDE_CLEAN = {ID_SECTION_CLEAN, "phase"}
        
        all_sections_raw = df['section'].unique().tolist()
        available_phases = []
        for sec in all_sections_raw:
            # Filtre les sections exclues (identification, NaN, ou nommées "phase")
            if pd.isna(sec) or not sec or str(sec).strip().lower() in SECTIONS_TO_EXCLUDE_CLEAN:
                continue
            available_phases.append(sec)
        
        if not st.session_state['current_phase_name']:
             st.markdown("### 📑 Sélection de la phase")
             phase_choice = st.selectbox("Quelle phase souhaitez-vous renseigner ?", [""] + available_phases)
             if phase_choice:
                 st.session_state['current_phase_name'] = phase_choice
                 st.rerun()
             if st.button("⬅️ Retour au Menu Principal"):
                 st.session_state['step'] = 'LOOP_DECISION'
                 st.session_state['current_phase_temp'] = {}
                 st.rerun()
                 
        else:
            # Affichage du formulaire de remplissage de la phase sélectionnée
            current_phase = st.session_state['current_phase_name']
            st.markdown(f"### 📝 Remplissage : {current_phase}")
            
            if st.button("🔄 Changer de phase"):
                st.session_state['current_phase_name'] = None
                st.session_state['current_phase_temp'] = {}
                st.rerun()
            
            st.markdown("---")
            
            section_questions = df[df['section'] == current_phase]
            
            # Boucle de rendu des questions, en appliquant les conditions d'affichage
            visible_count = 0
            for _, row in section_questions.iterrows():
                if check_condition(row, st.session_state['current_phase_temp'], st.session_state['collected_data']):
                    render_question(row, st.session_state['current_phase_temp'], st.session_state['iteration_id'])
                    visible_count += 1
            
            if visible_count == 0:
                st.warning("Aucune question applicable pour cette phase. Vérifiez les conditions d'affichage et l'orthographe de la section dans votre fichier Excel.")

            st.markdown("---")
            
            # BOUTONS D'ACTION
            c1, c2 = st.columns([1, 2])
            with c1:
                if st.button("❌ Annuler cette phase"):
                    st.session_state['step'] = 'LOOP_DECISION' # Retour au menu sans enregistrer
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
                        # Création de l'entrée finale et ajout à collected_data
                        new_entry = {
                            "phase_name": current_phase,
                            "answers": st.session_state['current_phase_temp'].copy()
                        }
                        st.session_state['collected_data'].append(new_entry)
                        
                        st.success("Phase enregistrée avec succès !")
                        st.session_state['step'] = 'LOOP_DECISION' # Retour au menu
                        st.rerun()
                    else:
                        # Affichage des erreurs de validation
                        st.markdown('<div class="error-box"><b>⚠️ Impossible de valider :</b><br>' +
                                    '<br>'.join([f"- {e}" for e in errors]) + '</div>',
                                    unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)

# 5. FIN (state: 'FINISHED')
elif st.session_state['step'] == 'FINISHED':
    st.balloons()
    st.markdown('<div class="phase-block" style="text-align:center;">', unsafe_allow_html=True)
    st.markdown("## 🎉 Formulaire Terminé")
    st.write(f"Projet : **{st.session_state['project_data'].get('Intitulé')}**")
    st.write(f"Nombre total de sections complétées : **{len(st.session_state['collected_data'])}**")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Affichage des données collectées sous forme de JSON
    for i, phase in enumerate(st.session_state['collected_data']):
        with st.expander(f"Section {i+1} : {phase['phase_name']}"):
            st.json(phase['answers'])
            
    if st.button("🔄 Commencer un nouveau projet"):
        st.session_state.clear() # Efface toutes les données de la session
        st.rerun()

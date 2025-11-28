import streamlit as st
import pandas as pd

# --- CONFIGURATION ET STYLE (Non Modifié) ---
st.set_page_config(page_title="Formulaire Dynamique", layout="centered")

st.markdown("""
    <style>
    /* Fond de l'application (Noir/Gris très foncé) */
    .stApp { background-color: #121212; } 
    
    /* Conteneur principal du formulaire */
    .form-container {
        background-color: #1e1e1e; /* Gris foncé pour le bloc principal */
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5); /* Ombre plus visible sur fond sombre */
        margin-bottom: 20px;
        color: #e0e0e0; /* Texte clair */
    }
    
    /* Bloc de question individuel */
    .question-block {
        margin-bottom: 20px;
        padding: 15px;
        /* Barre d'accentuation Gemini Blue/Cyan */
        border-left: 4px solid #4285F4; 
        background-color: #2d2d2d; /* Gris moyen pour distinguer */
        border-radius: 4px;
    }
    
    /* Description/Texte d'aide */
    .description {
        font-size: 0.85em;
        color: #aaaaaa;
        margin-top: -10px;
        margin-bottom: 10px;
        font-style: italic;
    }
    
    /* Texte obligatoire */
    .mandatory {
        color: #F4B400; /* Jaune/Ambre pour attirer l'attention */
        font-weight: bold;
    }
    
    /* Titres (h1, h2, h3) */
    h1, h2, h3 { 
        color: #ffffff; /* Blanc pur */
    }
    
    /* Boutons de navigation */
    .stButton > button { 
        width: 100%; 
        border-radius: 8px;
        /* Fond Cyan/Bleu d'accentuation */
        background-color: #4285F4; 
        color: white; 
        border: none;
        font-weight: bold;
    }
    
    /* Effet au survol des boutons */
    .stButton > button:hover { 
        background-color: #5b9ffc;
        color: white; 
    }
    
    /* Pour Streamlit (barre de progression, inputs) */
    .stProgress > div > div > div > div {
        background-color: #4285F4;
    }

    /* Style pour les inputs/select (moins de contrôle direct en CSS, mais on peut influencer le conteneur) */
    .stTextInput label, .stSelectbox label, .stNumberInput label {
        color: #e0e0e0;
    }
    
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DES DONNÉES CORRIGÉ (Non Modifié) ---
@st.cache_data
def load_form_structure(file):
    try:
        df = pd.read_excel(file, sheet_name='Questions', engine='openpyxl')
        df.columns = df.columns.str.strip()
        df = df.rename(columns={
            'Conditon value': 'Condition value',
            'Conditon on': 'Condition on',
            'condition value': 'Condition value',
            'Condition Value': 'Condition value'
        })

        if 'Condition value' not in df.columns:
            st.error(f"Colonne 'Condition value' introuvable. Colonnes détectées : {list(df.columns)}")
            return None

        df['options'] = df['options'].fillna('')
        df['Description'] = df['Description'].fillna('')
        df['Condition value'] = df['Condition value'].fillna('')
        df['Condition on'] = df['Condition on'].fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Erreur technique lors de la lecture : {e}")
        return None

# --- GESTION DE L'ÉTAT (SESSION STATE) ---
if 'form_answers' not in st.session_state:
    st.session_state['form_answers'] = {} # Stocke les réponses : {id_question: valeur}

if 'current_section_index' not in st.session_state:
    st.session_state['current_section_index'] = 0

# --- FONCTIONS LOGIQUES ---

def check_condition(row, answers):
    """
    Vérifie si une question DOIT être affichée en fonction des réponses précédentes.
    Structure attendue dans 'Condition value': "ID_QUESTION = VALEUR"
    """
    try:
        is_conditional = int(row['Condition on']) == 1
    except:
        is_conditional = False

    if not is_conditional:
        return True

    condition_rule = str(row['Condition value']).strip()
    if not condition_rule:
        return True
    
    try:
        if '=' in condition_rule:
            target_id_str, target_value = condition_rule.split('=', 1)
            target_id = int(target_id_str.strip())
            target_value = target_value.strip()
            
            user_answer = answers.get(target_id)
            
            # Correction pour les select qui sont "" si rien n'est sélectionné.
            if user_answer is None or str(user_answer).strip() == "":
                return False # Si la question parente n'a pas été remplie, la condition est fausse
            
            return str(user_answer) == str(target_value)
        else:
            return True 
    except Exception as e:
        # En cas d'erreur de parsing, on affiche pour ne pas bloquer
        return True

def render_field(row):
    """Génère le widget Streamlit approprié selon le type et met à jour l'état."""
    q_id = int(row['id'])
    q_text = row['question']
    q_type = str(row['type']).strip().lower()
    q_desc = row['Description']
    q_mandatory = str(row['obligatoire']).lower() == 'oui'
    q_options = str(row['options']).split(',') if row['options'] else []
    
    label = f"{q_id}. {q_text}" + (" " + st.markdown('<span class="mandatory">*</span>', unsafe_allow_html=True) if q_mandatory else "")
    widget_key = f"q_{q_id}"
    current_val = st.session_state['form_answers'].get(q_id)

    with st.container():
        st.markdown(f'<div class="question-block">', unsafe_allow_html=True)
        
        # Le label est affiché en Markdown pour intégrer la classe 'mandatory' de manière plus flexible
        st.markdown(f'<h3 style="color:#e0e0e0; font-size:1.1em;">{label}</h3>', unsafe_allow_html=True)
        
        val = None
        
        if q_type == 'text':
            # On utilise le `key` pour la valeur et l'état
            st.text_input(q_text, value=current_val if current_val else "", key=widget_key, label_visibility="collapsed")
            val = st.session_state[widget_key]
            
        elif q_type == 'select':
            clean_options = [opt.strip() for opt in q_options]
            if "" not in clean_options:
                clean_options.insert(0, "")
                
            index = clean_options.index(current_val) if current_val in clean_options else 0
                
            st.selectbox(q_text, clean_options, index=index, key=widget_key, label_visibility="collapsed")
            val = st.session_state[widget_key]

        elif q_type == 'number':
            # Assurez-vous que la valeur par défaut est 0 ou None
            num_val = float(current_val) if current_val else None 
            st.number_input(q_text, value=num_val, key=widget_key, label_visibility="collapsed")
            val = st.session_state[widget_key]

        elif q_type == 'photo':
            st.file_uploader(q_text, type=['png', 'jpg', 'jpeg'], key=widget_key, label_visibility="collapsed")
            val = st.session_state[widget_key]
            if val is not None:
                st.success(f"Image chargée : {val.name}")
            elif current_val is not None:
                st.info("Image déjà chargée précédemment.")

        if q_desc:
            st.markdown(f'<p class="description">{q_desc}</p>', unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)

        # Mise à jour du dictionnaire d'answers pour la condition
        st.session_state['form_answers'][q_id] = val


def get_visible_sections(df, answers):
    """
    Détermine la liste ordonnée des sections qui DOIVENT être affichées 
    en fonction de la question conditionnelle principale (Q4).
    """
    all_sections = df['section'].unique().tolist()
    visible_sections = []
    
    # La section 'Identification' doit toujours être visible
    # La section 'Phase' (où se trouve la Q4) doit toujours être visible
    
    # On itère sur toutes les sections pour vérifier si une question dedans est conditionnelle
    for section_name in all_sections:
        section_questions = df[df['section'] == section_name]
        is_visible = False
        
        # On vérifie si au moins UNE question de cette section est visible
        for index, row in section_questions.iterrows():
            if check_condition(row, answers):
                is_visible = True
                break
        
        if is_visible:
            visible_sections.append(section_name)
            
    # La première section du fichier est souvent l'identification et doit toujours être là.
    # On s'assure que 'Identification' et 'Phase' sont bien incluses même si elles n'ont pas de condition explicite.
    if 'Identification' in all_sections and 'Identification' not in visible_sections:
         visible_sections.insert(0, 'Identification')
    if 'Phase' in all_sections and 'Phase' not in visible_sections:
         # On la place après Identification s'ils sont distincts
         try:
            id_index = visible_sections.index('Identification')
            if 'Phase' not in visible_sections:
                visible_sections.insert(id_index + 1, 'Phase')
         except ValueError: # 'Identification' n'était pas la première (si le fichier est mal ordonné)
             visible_sections.append('Phase')
    
    # Utiliser un Set pour garantir l'unicité tout en maintenant l'ordre
    unique_visible_sections = []
    for sec in all_sections:
        if sec in visible_sections:
            if sec not in unique_visible_sections:
                unique_visible_sections.append(sec)
                
    return unique_visible_sections

def validate_section(df, current_section_name):
    """Vérifie si toutes les questions OBLIGATOIRES et VISIBLES sont remplies."""
    section_questions = df[df['section'] == current_section_name]
    answers = st.session_state['form_answers']
    
    missing_fields = []
    
    for index, row in section_questions.iterrows():
        q_id = int(row['id'])
        q_mandatory = str(row['obligatoire']).lower() == 'oui'
        
        # 1. Vérifie si la question doit être affichée
        if check_condition(row, answers) and q_mandatory:
            answer = answers.get(q_id)
            
            # 2. Vérifie si la réponse est vide (pour tous les types)
            is_empty = False
            
            if answer is None:
                is_empty = True
            elif isinstance(answer, (str, int, float)) and (str(answer).strip() == "" or str(answer) == "0"):
                 # Gère les chaînes vides, et les selectbox qui valent "" par défaut
                 # Gère les number input à 0 si la question attend un nombre > 0 (si non spécifié, on accepte 0)
                if row['type'].strip().lower() != 'number':
                    is_empty = True
                elif row['type'].strip().lower() == 'select' and str(answer).strip() == "":
                    is_empty = True
            elif row['type'].strip().lower() == 'photo' and answer is None:
                is_empty = True

            if is_empty:
                missing_fields.append(f"• Question {q_id}: {row['question']}")

    if missing_fields:
        st.error(f"⚠️ Veuillez répondre à toutes les questions obligatoires de la section **{current_section_name}** avant de continuer :")
        for field in missing_fields:
            st.markdown(f"<p style='color:#F4B400; margin-left:20px;'>{field}</p>", unsafe_allow_html=True)
        return False
    
    return True

# --- ACTIONS DE NAVIGATION ---
def navigate(direction, df):
    """Fonction principale de navigation avec validation et saut de sections."""
    
    # 1. Obtenir la liste des sections VISIBLES
    visible_sections = get_visible_sections(df, st.session_state['form_answers'])
    
    # 2. Trouver l'index actuel dans la liste visible
    current_section_name = visible_sections[st.session_state['current_section_index']]
    
    if direction == 'next':
        # --- VALIDATION ---
        if validate_section(df, current_section_name):
            # 3. Trouver la PROCHAINE section VUE
            try:
                # On cherche l'index de la section suivante dans la liste visible
                new_index = st.session_state['current_section_index'] + 1
                if new_index < len(visible_sections):
                    st.session_state['current_section_index'] = new_index
                else:
                    st.session_state['current_section_index'] = len(visible_sections) - 1
            except IndexError:
                st.session_state['current_section_index'] = len(visible_sections) - 1
                
    elif direction == 'prev':
        # 3. Trouver la section PRÉCÉDENTE VUE
        st.session_state['current_section_index'] -= 1
        if st.session_state['current_section_index'] < 0:
            st.session_state['current_section_index'] = 0

# --- MAIN APP ---

st.markdown('<div class="form-container"><h1>📝 Formulaire de Travaux</h1></div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Chargez le fichier Excel de structure (Questions)", type=["xlsx"])

if uploaded_file is not None:
    df = load_form_structure(uploaded_file)
    
    if df is not None:
        
        # Liste des sections à afficher (dynamique)
        visible_sections = get_visible_sections(df, st.session_state['form_answers'])
        
        # Sécurité index
        if st.session_state['current_section_index'] >= len(visible_sections):
             st.session_state['current_section_index'] = len(visible_sections) - 1
        if st.session_state['current_section_index'] < 0:
             st.session_state['current_section_index'] = 0

        current_section_name = visible_sections[st.session_state['current_section_index']]
        
        # Barre de progression
        progress = (st.session_state['current_section_index'] + 1) / len(visible_sections)
        st.progress(progress)
        st.caption(f"Section {st.session_state['current_section_index'] + 1}/{len(visible_sections)} : **{current_section_name}**")

        # --- AFFICHAGE DU FORMULAIRE POUR LA SECTION COURANTE ---
        st.markdown(f"## {current_section_name}")
        
        section_questions = df[df['section'] == current_section_name]
        
        visible_questions_count = 0
        
        # Utilisation d'un Form Streamlit pour regrouper les questions et forcer la mise à jour
        with st.container():
            for index, row in section_questions.iterrows():
                # Vérification Conditionnelle
                if check_condition(row, st.session_state['form_answers']):
                    render_field(row)
                    visible_questions_count += 1
        
        if visible_questions_count == 0:
            st.info("Aucune question visible pour cette section selon vos choix précédents. Cliquez sur 'Suivant' pour passer à la prochaine section pertinente.")

        # --- BOUTONS DE NAVIGATION ---
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.session_state['current_section_index'] > 0:
                # Utilise une lambda pour passer le DataFrame à la fonction navigate
                st.button("⬅️ Précédent", on_click=lambda: navigate('prev', df))
        
        with col3:
            is_last_section = st.session_state['current_section_index'] == len(visible_sections) - 1
            
            if not is_last_section:
                st.button("Suivant ➡️", on_click=lambda: navigate('next', df))
            else:
                if st.button("✅ Soumettre le rapport"):
                    # On valide une dernière fois avant la soumission
                    if validate_section(df, current_section_name):
                        st.balloons()
                        st.success("Formulaire terminé et validé !")
                        st.write("Récapitulatif des données collectées :")
                        # Affichage des réponses valides uniquement
                        final_data = {}
                        for q_id, answer in st.session_state['form_answers'].items():
                            if answer is not None and str(answer).strip() != "":
                                # Retrouver la question pour la clarté
                                q_row = df[df['id'] == q_id]
                                if not q_row.empty:
                                    final_data[f"{q_id}. {q_row.iloc[0]['question']}"] = str(answer)
                                else:
                                    final_data[str(q_id)] = str(answer)

                        st.json(final_data)

else:
    st.info("Veuillez charger le fichier Excel contenant l'onglet 'Questions'.")

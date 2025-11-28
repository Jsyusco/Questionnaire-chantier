import streamlit as st
import pandas as pd

# --- CONFIGURATION ET STYLE (Gemini Dark Mode) ---
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

# --- CHARGEMENT DES DONNÉES (Avec Correction de Faute de Frappe) ---
@st.cache_data
def load_form_structure(file):
    """Charge et prépare les données de la feuille 'Questions', incluant le nettoyage des noms de colonnes."""
    try:
        df = pd.read_excel(file, sheet_name='Questions', engine='openpyxl')
        
        # 1. Nettoyage et standardisation des noms de colonnes
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

        # 2. Remplissage des valeurs vides
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
    """Vérifie si une question DOIT être affichée."""
    try:
        is_conditional = int(row['Condition on']) == 1
    except:
        is_conditional = False

    if not is_conditional:
        return True

    condition_rule = str(row['Condition value']).strip()
    if not condition_rule or '=' not in condition_rule:
        return True
    
    try:
        target_id_str, target_value = condition_rule.split('=', 1)
        target_id = int(target_id_str.strip())
        target_value = target_value.strip()
        
        user_answer = answers.get(target_id)
        
        # Si la question parente n'a pas été remplie, la condition est fausse
        if user_answer is None or str(user_answer).strip() == "":
            return False 
        
        return str(user_answer) == str(target_value)
    except:
        return True

def render_field(row):
    """Génère le widget Streamlit approprié selon le type et met à jour l'état."""
    q_id = int(row['id'])
    q_text = row['question']
    q_type = str(row['type']).strip().lower()
    q_desc = row['Description']
    q_mandatory = str(row['obligatoire']).lower() == 'oui'
    q_options = str(row['options']).split(',') if row['options'] else []
    
    display_text = f"{q_id}. {q_text}"
    widget_key = f"q_{q_id}"
    current_val = st.session_state['form_answers'].get(q_id)

    with st.container():
        st.markdown(f'<div class="question-block">', unsafe_allow_html=True)
        
        # Affichage du titre avec astérisque stylisé
        mandatory_star = f'<span class="mandatory">*</span>' if q_mandatory else ""
        st.markdown(f'<h3 style="color:#e0e0e0; font-size:1.1em; margin-bottom: 5px;">{display_text} {mandatory_star}</h3>', unsafe_allow_html=True)
        
        val = None
        
        # Rendu des widgets (label_visibility="collapsed" car le titre est déjà affiché)
        if q_type == 'text':
            st.text_input(display_text, value=current_val if current_val else "", key=widget_key, label_visibility="collapsed")
            val = st.session_state[widget_key]
            
        elif q_type == 'select':
            clean_options = [opt.strip() for opt in q_options]
            if "" not in clean_options:
                clean_options.insert(0, "")
                
            index = clean_options.index(current_val) if current_val in clean_options else 0
                
            st.selectbox(display_text, clean_options, index=index, key=widget_key, label_visibility="collapsed")
            val = st.session_state[widget_key]

        elif q_type == 'number':
            num_val = float(current_val) if current_val else None 
            st.number_input(display_text, value=num_val, key=widget_key, label_visibility="collapsed")
            val = st.session_state[widget_key]

        elif q_type == 'photo':
            st.file_uploader(display_text, type=['png', 'jpg', 'jpeg'], key=widget_key, label_visibility="collapsed")
            val = st.session_state[widget_key]
            if val is not None:
                st.success(f"Image chargée : {val.name}")
            elif current_val is not None:
                st.info("Image déjà chargée précédemment.")

        if q_desc:
            st.markdown(f'<p class="description">{q_desc}</p>', unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)

        # Mise à jour de la réponse dans le dictionnaire pour la condition
        st.session_state['form_answers'][q_id] = val


def get_visible_sections(df, answers):
    """Détermine la liste ordonnée des sections qui DOIVENT être affichées."""
    all_sections = df['section'].unique().tolist()
    final_visible_sections = []
    
    for section_name in all_sections:
        section_questions = df[df['section'] == section_name]
        is_visible = False
        
        # Les premières sections (Identification, Phase) sont toujours visibles.
        # On suppose que les deux premières sections ne sont pas conditionnelles à elles-mêmes.
        if all_sections.index(section_name) < 2: 
            is_visible = True
        else:
            # Vérifie si au moins UNE question de cette section est visible
            for _, row in section_questions.iterrows():
                if check_condition(row, answers):
                    is_visible = True
                    break
        
        if is_visible:
            final_visible_sections.append(section_name)
                
    return final_visible_sections

def validate_section(df, current_section_name):
    """Vérifie si toutes les questions OBLIGATOIRES et VISIBLES sont remplies."""
    section_questions = df[df['section'] == current_section_name]
    answers = st.session_state['form_answers']
    
    missing_fields = []
    
    for _, row in section_questions.iterrows():
        q_id = int(row['id'])
        q_mandatory = str(row['obligatoire']).lower() == 'oui'
        
        # 1. Vérifie si la question doit être affichée ET si elle est obligatoire
        if check_condition(row, answers) and q_mandatory:
            answer = answers.get(q_id)
            
            is_empty = False
            
            if answer is None:
                is_empty = True
            elif isinstance(answer, (str, int, float)):
                # Gère les chaînes vides, les selectbox à "" et les number input à 0 (si non souhaité, 
                # il faudrait ajouter une règle pour les numbers)
                if str(answer).strip() == "":
                    is_empty = True
                elif row['type'].strip().lower() == 'select' and str(answer).strip() == "":
                    is_empty = True
                # Pour les number input, on suppose 0 est acceptable sauf indication contraire
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

def navigate(direction, df):
    """Fonction principale de navigation avec validation et saut de sections."""
    
    # 1. Obtenir la liste des sections VISIBLES (la plus récente)
    visible_sections = get_visible_sections(df, st.session_state['form_answers'])
    
    # 2. Gérer la navigation "Précédent"
    if direction == 'prev':
        new_index = st.session_state['current_section_index'] - 1
        if new_index >= 0:
            st.session_state['current_section_index'] = new_index
        return
        
    # --- Navigation "Suivant" avec Validation ---
    
    try:
        current_section_name = visible_sections[st.session_state['current_section_index']]
    except IndexError:
        st.session_state['current_section_index'] = 0
        return
        
    # 3. Validation de la section actuelle
    if validate_section(df, current_section_name):
        
        # 4. Calculer le nouvel index
        new_index = st.session_state['current_section_index'] + 1
        
        if new_index < len(visible_sections):
            st.session_state['current_section_index'] = new_index
        else:
            # S'assurer que l'on reste sur la dernière section (pour voir le bouton soumettre)
            st.session_state['current_section_index'] = len(visible_sections) - 1

# --- MAIN APP ---

st.markdown('<div class="form-container"><h1>📝 Formulaire de Travaux</h1></div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Chargez le fichier Excel de structure (Questions)", type=["xlsx"])

if uploaded_file is not None:
    df = load_form_structure(uploaded_file)
    
    if df is not None:
        
        # Liste des sections à afficher (dynamique)
        visible_sections = get_visible_sections(df, st.session_state['form_answers'])
        
        # Sécurité de l'index : Assure que l'index reste dans les limites de la liste visible
       # Sécurité de l'index : Assure que l'index reste dans les limites de la nouvelle liste
        if not visible_sections:
            st.warning("Aucune section visible.")
            # On utilise 'pass' ou on laisse le bloc se terminer sans return
            # Le reste du code ci-dessous ne sera pas exécuté s'il n'y a pas de sections visibles
            # (Ce qui est géré plus bas)
            pass 
            
        if st.session_state['current_section_index'] >= len(visible_sections):
            # Rediriger vers la fin (bouton Soumettre)
            st.session_state['current_section_index'] = len(visible_sections) - 1
        if st.session_state['current_section_index'] < 0:
            st.session_state['current_section_index'] = 0
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
        
        with st.container():
            for _, row in section_questions.iterrows():
                # Vérification Conditionnelle : n'affiche que les questions nécessaires
                if check_condition(row, st.session_state['form_answers']):
                    render_field(row)
                    visible_questions_count += 1
        
        if visible_questions_count == 0:
            st.info("Aucune question visible pour cette section selon vos choix précédents. Cliquez sur 'Suivant' pour passer à la prochaine section pertinente.")

        # --- BOUTONS DE NAVIGATION ---
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.session_state['current_section_index'] > 0:
                st.button("⬅️ Précédent", on_click=lambda: navigate('prev', df))
        
        with col3:
            is_last_section = st.session_state['current_section_index'] == len(visible_sections) - 1
            
            if not is_last_section:
                st.button("Suivant ➡️", on_click=lambda: navigate('next', df))
            else:
                if st.button("✅ Soumettre le rapport"):
                    # Validation finale avant la soumission
                    if validate_section(df, current_section_name):
                        st.balloons()
                        st.success("Formulaire terminé et validé !")
                        st.write("Récapitulatif des données collectées :")
                        final_data = {}
                        for q_id, answer in st.session_state['form_answers'].items():
                            if answer is not None and str(answer).strip() not in ["", "0"]:
                                q_row = df[df['id'] == q_id]
                                if not q_row.empty:
                                    final_data[f"{q_row.iloc[0]['section']} - {q_row.iloc[0]['question']}"] = str(answer)
                                else:
                                    final_data[str(q_id)] = str(answer)

                        st.json(final_data)

else:
    st.info("Veuillez charger le fichier Excel contenant l'onglet 'Questions'.")

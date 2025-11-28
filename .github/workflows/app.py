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
    
    # Construction du label (texte simple)
    display_text = f"{q_id}. {q_text}"
    
    # Clé unique pour le widget
    widget_key = f"q_{q_id}"
    current_val = st.session_state['form_answers'].get(q_id)

    with st.container():
        
        
        # --- CORRECTION APPORTÉE ICI ---
        # 1. On construit le titre en HTML
        mandatory_star = f'<span class="mandatory">*</span>' if q_mandatory else ""
        
        # 2. On affiche le titre de la question (avec l'astérisque inclus en HTML si obligatoire)
        st.markdown(f'<h3 style="color:#e0e0e0; font-size:1.1em; margin-bottom: 5px;">{display_text} {mandatory_star}</h3>', unsafe_allow_html=True)
        
        val = None
        
        # L'affichage des widgets reste le même, mais nous utilisons display_text comme clé pour label_visibility="collapsed"
        
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

        # Mise à jour du dictionnaire d'answers pour la condition
        st.session_state['form_answers'][q_id] = val


def check_condition(row, answers):
    """
    Vérifie si une question DOIT être affichée en fonction des réponses précédentes.
    (Non modifié - il fonctionne pour les questions individuelles)
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
                return False 
            
            return str(user_answer) == str(target_value)
        else:
            return True 
    except Exception as e:
        return True

def get_visible_sections(df, answers):
    """
    Détermine la liste ordonnée des sections qui DOIVENT être affichées 
    en fonction de toutes les conditions.
    """
    all_sections = df['section'].unique().tolist()
    final_visible_sections = []
    
    for section_name in all_sections:
        # On vérifie si au moins UNE question de cette section est visible
        section_questions = df[df['section'] == section_name]
        is_visible = False
        
        # Le premier élément du fichier (souvent Identification/Phase) est toujours visible.
        # On assume que les deux premières sections ne sont pas conditionnelles à elles-mêmes.
        if all_sections.index(section_name) < 2: 
            is_visible = True
        else:
            for index, row in section_questions.iterrows():
                if check_condition(row, answers):
                    is_visible = True
                    break
        
        if is_visible:
            final_visible_sections.append(section_name)
                
    return final_visible_sections

def validate_section(df, current_section_name):
    # ... (La fonction validate_section n'est pas modifiée) ...
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

def navigate(direction, df):
    """Fonction principale de navigation avec validation et saut de sections."""
    
    # 1. Obtenir la liste des sections VISIBLES
    # IMPORTANT : On doit refaire cette liste car une réponse peut avoir changé les sections visibles
    visible_sections = get_visible_sections(df, st.session_state['form_answers'])
    
    # 2. Gérer la navigation "Précédent" (pas de validation nécessaire)
    if direction == 'prev':
        new_index = st.session_state['current_section_index'] - 1
        if new_index >= 0:
            st.session_state['current_section_index'] = new_index
        return
        
    # --- Navigation "Suivant" avec Validation ---
    
    # 3. Trouver l'index actuel dans la liste visible
    try:
        current_section_name = visible_sections[st.session_state['current_section_index']]
    except IndexError:
        # Peut arriver si l'index est trop grand après une modification des conditions.
        st.session_state['current_section_index'] = 0
        return
        
    # 4. Validation
    if validate_section(df, current_section_name):
        
        # 5. Calculer le nouvel index
        new_index = st.session_state['current_section_index'] + 1
        
        if new_index < len(visible_sections):
            # C'est bon, on peut avancer
            st.session_state['current_section_index'] = new_index
        else:
            # On est arrivé à la fin de la liste visible (ce qui déclenchera le bouton "Soumettre")
            # On s'assure que l'index ne dépasse pas la taille de la liste
            st.session_state['current_section_index'] = len(visible_sections) - 1

# --- MAIN APP ---

st.markdown('<div class="form-container"><h1>📝 Formulaire de Travaux</h1></div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Chargez le fichier Excel de structure (Questions)", type=["xlsx"])

# ... (Dans le bloc MAIN APP) ...

if uploaded_file is not None:
    df = load_form_structure(uploaded_file)
    
    if df is not None:
        
        # 1. Mise à jour DYNAMIQUE des sections visibles à chaque exécution
        visible_sections = get_visible_sections(df, st.session_state['form_answers'])
        
        # 2. Sécurité de l'index : Assure que l'index reste dans les limites de la nouvelle liste
        if not visible_sections:
            st.warning("Aucune section visible après Identification/Phase.")
            return # Sortir si rien n'est visible
            
        if st.session_state['current_section_index'] >= len(visible_sections):
             # Rediriger vers la fin (bouton Soumettre)
             st.session_state['current_section_index'] = len(visible_sections) - 1
        if st.session_state['current_section_index'] < 0:
             st.session_state['current_section_index'] = 0
        
        # ... (le reste du code est inchangé) ...
        
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

import streamlit as st
import pandas as pd

# --- CONFIGURATION ET STYLE ---
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

# --- CHARGEMENT DES DONNÉES CORRIGÉ ---
@st.cache_data
def load_form_structure(file):
    try:
        # On lit la feuille 'Questions'
        df = pd.read_excel(file, sheet_name='Questions', engine='openpyxl')
        
        # 1. Nettoyage des noms de colonnes (supprime les espaces avant/après)
        df.columns = df.columns.str.strip()
        
        # 2. Correction automatique de la faute de frappe connue "Conditon" -> "Condition"
        # On renomme les colonnes si elles existent mal orthographiées
        df = df.rename(columns={
            'Conditon value': 'Condition value',  # Corrige la faute
            'Conditon on': 'Condition on',        # Au cas où
            'condition value': 'Condition value', # Gère la casse
            'Condition Value': 'Condition value'
        })

        # Debug : Si la colonne n'est toujours pas là, on affiche ce qu'on a trouvé
        if 'Condition value' not in df.columns:
            st.error(f"Colonne 'Condition value' introuvable. Colonnes détectées : {list(df.columns)}")
            return None

        # On remplit les valeurs vides
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
    Vérifie si une question doit être affichée en fonction des réponses précédentes.
    Structure attendue dans 'Condition value': "ID_QUESTION = VALEUR"
    Exemple: "4 = Sécurité"
    """
    # Si la colonne 'Condition on' ne contient pas 1 (ou est vide), pas de condition
    try:
        is_conditional = int(row['Condition on']) == 1
    except:
        is_conditional = False

    if not is_conditional:
        return True

    condition_rule = str(row['Condition value']).strip()
    if not condition_rule:
        return True # Si condition active mais pas de règle, on affiche par défaut
    
    try:
        # Parsing basique de la règle "ID = VALEUR"
        if '=' in condition_rule:
            target_id_str, target_value = condition_rule.split('=', 1)
            target_id = int(target_id_str.strip())
            target_value = target_value.strip()
            
            # Récupération de la réponse actuelle de l'utilisateur pour la question cible
            user_answer = answers.get(target_id)
            
            # Comparaison (en string pour éviter les soucis de type)
            return str(user_answer) == str(target_value)
        else:
            return True 
    except Exception as e:
        # En cas d'erreur de parsing, on affiche pour ne pas bloquer
        return True

def render_field(row):
    """Génère le widget Streamlit approprié selon le type."""
    q_id = int(row['id'])
    q_text = row['question']
    q_type = str(row['type']).strip().lower()
    q_desc = row['Description']
    q_mandatory = str(row['obligatoire']).lower() == 'oui'
    q_options = str(row['options']).split(',') if row['options'] else []
    
    # Label avec astérisque si obligatoire
    label = f"{q_id}. {q_text}" + (" *" if q_mandatory else "")
    
    # Clé unique pour le widget
    widget_key = f"q_{q_id}" 
    
    # Récupération de la valeur existante ou None
    current_val = st.session_state['form_answers'].get(q_id)

    with st.container():

        
        if q_type == 'text':
            val = st.text_input(label, value=current_val if current_val else "", key=widget_key)
            
        elif q_type == 'select':
            # Gestion de l'index pour la valeur par défaut
            index = 0
            clean_options = [opt.strip() for opt in q_options]
            # Ajouter une option vide au début pour forcer un choix conscient
            if "" not in clean_options:
                clean_options.insert(0, "")
                
            if current_val in clean_options:
                index = clean_options.index(current_val)
                
            val = st.selectbox(label, clean_options, index=index, key=widget_key)
            
        elif q_type == 'number':
            val = st.number_input(label, value=int(current_val) if current_val else 0, key=widget_key)
            
        elif q_type == 'photo':
            val = st.file_uploader(label, type=['png', 'jpg', 'jpeg'], key=widget_key)
            # Pour les fichiers, on stocke l'objet ou un indicateur
            if val is not None:
                st.success(f"Image chargée : {val.name}")
            elif current_val is not None:
                 st.info("Image déjà chargée précédemment.")

        # Affichage de la description
        if q_desc:
            st.markdown(f'<p class="description">{q_desc}</p>', unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)

        # Mise à jour immédiate de la réponse dans le dictionnaire principal
        # Note : Pour les selectbox/text, la mise à jour est auto via session_state[key], 
        # mais on synchronise ici notre dictionnaire 'form_answers' pour un accès plus facile par ID
        if val is not None:
            st.session_state['form_answers'][q_id] = val


# --- NAVIGATION ET VALIDATION ---
def next_section():
    st.session_state['current_section_index'] += 1

def prev_section():
    st.session_state['current_section_index'] -= 1

# --- MAIN APP ---

st.markdown('<div class="form-container"><h1>📝 Formulaire de Travaux</h1></div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Chargez le fichier Excel de structure (Questions)", type=["xlsx"])

if uploaded_file is not None:
    df = load_form_structure(uploaded_file)
    
    if df is not None:
        # Récupération des sections uniques dans l'ordre
        sections = df['section'].unique().tolist()
        
        # Sécurité index
        if st.session_state['current_section_index'] >= len(sections):
             st.session_state['current_section_index'] = len(sections) - 1
        
        current_section_name = sections[st.session_state['current_section_index']]
        
        # Barre de progression
        progress = (st.session_state['current_section_index'] + 1) / len(sections)
        st.progress(progress)
        st.caption(f"Section {st.session_state['current_section_index'] + 1}/{len(sections)} : {current_section_name}")

        # --- AFFICHAGE DU FORMULAIRE POUR LA SECTION COURANTE ---
        st.markdown(f"## {current_section_name}")
        
        # Filtrer les questions de la section
        section_questions = df[df['section'] == current_section_name]
        
        visible_questions_count = 0
        
        for index, row in section_questions.iterrows():
            # Vérification Conditionnelle
            if check_condition(row, st.session_state['form_answers']):
                render_field(row)
                visible_questions_count += 1
        
        if visible_questions_count == 0:
            st.info("Aucune question visible pour cette section selon vos choix précédents.")

        # --- BOUTONS DE NAVIGATION ---
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.session_state['current_section_index'] > 0:
                st.button("⬅️ Précédent", on_click=prev_section)
        
        with col3:
            if st.session_state['current_section_index'] < len(sections) - 1:
                st.button("Suivant ➡️", on_click=next_section)
            else:
                if st.button("✅ Soumettre le rapport"):
                    st.success("Formulaire terminé !")
                    st.write("Récapitulatif des données collectées (JSON):")
                    # Nettoyage pour affichage (exclure les objets fichiers bruts pour l'affichage JSON)
                    display_data = {k: str(v) for k, v in st.session_state['form_answers'].items()}
                    st.json(display_data)

else:
    st.info("Veuillez charger le fichier Excel contenant l'onglet 'Questions'.")

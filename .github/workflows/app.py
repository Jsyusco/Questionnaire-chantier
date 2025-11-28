import streamlit as st
import pandas as pd

# --- CONFIGURATION ET STYLE ---
st.set_page_config(page_title="Formulaire Dynamique", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #121212; } 
    .form-container {
        background-color: #1e1e1e;
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5);
        margin-bottom: 20px;
        color: #e0e0e0;
    }
    .question-block {
        margin-bottom: 20px;
        padding: 15px;
        border-left: 4px solid #4285F4; 
        background-color: #2d2d2d;
        border-radius: 4px;
    }
    .description {
        font-size: 0.85em;
        color: #aaaaaa;
        margin-top: 5px; 
        margin-bottom: 10px;
        font-style: italic;
    }
    .mandatory { color: #F4B400; font-weight: bold; }
    .validation-error {
        color: #ff6b6b; background-color: #3d1f1f;
        padding: 10px; border-radius: 5px;
        border-left: 4px solid #ff6b6b; margin: 10px 0;
    }
    h1, h2, h3 { color: #ffffff; }
    .stButton > button { 
        width: 100%; border-radius: 8px;
        background-color: #4285F4; color: white; 
        border: none; font-weight: bold;
    }
    .stButton > button:hover { background-color: #5b9ffc; color: white; }
    .stTextInput label, .stSelectbox label, .stNumberInput label, .stRadio label { color: #e0e0e0; }
    /* Style spécifique pour la question transition (ID 5) */
    .transition-block {
        border: 2px solid #F4B400;
        padding: 20px;
        border-radius: 10px;
        margin-top: 30px;
        background-color: #2b2b2b;
    }
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data
def load_form_structure(file):
    try:
        df = pd.read_excel(file, sheet_name='Questions', engine='openpyxl')
        df.columns = df.columns.str.strip()
        df = df.rename(columns={
            'Conditon value': 'Condition value', 'Conditon on': 'Condition on',
            'condition value': 'Condition value', 'Condition Value': 'Condition value'
        })
        if 'Condition value' not in df.columns:
            st.error(f"Colonne 'Condition value' manquante.")
            return None

        df['options'] = df['options'].fillna('')
        df['Description'] = df['Description'].fillna('')
        df['Condition value'] = df['Condition value'].fillna('')
        df['Condition on'] = df['Condition on'].fillna(0)
        return df
    except Exception as e:
        st.error(f"Erreur technique : {e}")
        return None

@st.cache_data
def load_site_data(file):
    try:
        df_site = pd.read_excel(file, sheet_name='Site', engine='openpyxl')
        df_site.columns = df_site.columns.str.strip()
        return df_site
    except Exception as e:
        st.error(f"Erreur feuille 'site' : {e}")
        return None

# --- GESTION DE L'ÉTAT ---
if 'form_answers' not in st.session_state:
    st.session_state['form_answers'] = {}

if 'current_section_index' not in st.session_state:
    st.session_state['current_section_index'] = 0

if 'selected_project' not in st.session_state:
    st.session_state['selected_project'] = None

if 'project_data' not in st.session_state:
    st.session_state['project_data'] = {}

if 'form_submitted' not in st.session_state:
    st.session_state['form_submitted'] = False

# --- FONCTIONS LOGIQUES ---

def check_condition(row, answers):
    try:
        is_conditional = int(row['Condition on']) == 1
    except:
        is_conditional = False

    if not is_conditional: return True

    condition_rule = str(row['Condition value']).strip()
    if not condition_rule: return True
    
    try:
        if '=' in condition_rule:
            target_id_str, target_value = condition_rule.split('=', 1)
            target_id = int(target_id_str.strip())
            target_value = target_value.strip()
            user_answer = answers.get(target_id)
            return str(user_answer) == str(target_value)
        else:
            return True 
    except:
        return True

def validate_mandatory_questions(section_df, answers):
    missing = []
    # On filtre pour ne pas valider la question ID 5 ici car elle est gérée manuellement à la fin
    for _, row in section_df.iterrows():
        if int(row['id']) == 5: 
            continue 

        if not check_condition(row, answers):
            continue
            
        q_id = int(row['id'])
        q_mandatory = str(row['obligatoire']).lower() == 'oui'
        
        if q_mandatory:
            answer = answers.get(q_id)
            # Vérification robuste (texte vide, None, 0, ou liste vide pour photos)
            if answer is None or answer == "" or answer == 0 or (isinstance(answer, list) and len(answer) == 0):
                missing.append(f"Question {q_id}: {row['question']}")
    
    return len(missing) == 0, missing

def render_field(row):
    q_id = int(row['id'])
    
    # NE PAS AFFICHER LA QUESTION 5 DANS LA BOUCLE NORMALE (elle est affichée manuellement à la fin)
    if q_id == 5:
        return

    q_text = row['question']
    q_type = str(row['type']).strip().lower()
    q_desc = row['Description']
    q_mandatory = str(row['obligatoire']).lower() == 'oui'
    q_options = str(row['options']).split(',') if row['options'] else []
    
    display_question = f"{q_id}. {q_text}" + (' <span class="mandatory">*</span>' if q_mandatory else "")
    widget_key = f"q_{q_id}" 
    current_val = st.session_state['form_answers'].get(q_id)
    val = None

    with st.container():
        st.markdown(f"**{display_question}**", unsafe_allow_html=True)
        if q_desc:
            st.markdown(f'<p class="description">{q_desc}</p>', unsafe_allow_html=True)
            
        if q_type == 'text':
            val = st.text_input(" ", value=current_val if current_val else "", key=widget_key, label_visibility="collapsed")
        elif q_type == 'select':
            clean_options = [opt.strip() for opt in q_options]
            if "" not in clean_options: clean_options.insert(0, "")
            index = clean_options.index(current_val) if current_val in clean_options else 0
            val = st.selectbox(" ", clean_options, index=index, key=widget_key, label_visibility="collapsed")
        elif q_type == 'number':
            val = st.number_input(" ", value=int(current_val) if current_val else 0, key=widget_key, label_visibility="collapsed")
        elif q_type == 'photo':
            # --- MODIF 1 : MULTIPLES PHOTOS ---
            val = st.file_uploader(
                " ", type=['png', 'jpg', 'jpeg'], key=widget_key, 
                label_visibility="collapsed", accept_multiple_files=True
            )
            if val: st.success(f"{len(val)} photo(s) chargée(s).")
            elif current_val: st.info(f"{len(current_val) if isinstance(current_val, list) else 1} photo(s) existante(s).")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if val is not None:
            st.session_state['form_answers'][q_id] = val

# --- NAVIGATION ---
def go_to_phase_selection():
    st.session_state['current_section_index'] = 0

def go_to_submission():
    st.session_state['form_submitted'] = True

def next_section_linear():
    st.session_state['current_section_index'] += 1

# --- MAIN APP ---

st.markdown('<div class="form-container"><h1>📝 Formulaire de Travaux</h1></div>', unsafe_allow_html=True)

if st.session_state['form_submitted']:
    # --- PAGE DE FIN (RÉSUMÉ) ---
    st.success("✅ Formulaire terminé !")
    st.markdown("### Récapitulatif des données")
    st.json({k: str(v) for k,v in st.session_state['form_answers'].items()})
    if st.button("🔄 Recommencer un nouveau formulaire"):
        st.session_state.clear()
        st.rerun()
    st.stop()

uploaded_file = st.file_uploader("Chargez le fichier Excel de structure", type=["xlsx"])

if uploaded_file:
    df = load_form_structure(uploaded_file)
    df_site = load_site_data(uploaded_file)
    
    if df is not None and df_site is not None:
        
        # 1. Sélection Projet (Code inchangé pour la sélection)
        if st.session_state['selected_project'] is None:
            st.markdown("### 🏗️ Sélection du Projet")
            if 'Intitulé' in df_site.columns:
                opts = [""] + df_site['Intitulé'].dropna().tolist()
                sel = st.selectbox("Projet", opts)
                if sel and st.button("✅ Valider"):
                    st.session_state['selected_project'] = sel
                    # Chargement des infos projet
                    row = df_site[df_site['Intitulé'] == sel].iloc[0]
                    # (Code simplifié pour l'exemple, reprenant votre mapping)
                    st.session_state['project_data'] = {k: str(v) for k,v in row.to_dict().items()}
                    st.rerun()
            else:
                st.error("Colonne 'Intitulé' manquante.")
        
        else:
            # 2. Affichage du Formulaire
            st.markdown(f"### 🏗️ Projet : {st.session_state['selected_project']}")
            
            # Gestion des sections
            all_sections = df['section'].unique().tolist()
            
            # Si index hors limites, reset
            if st.session_state['current_section_index'] >= len(all_sections):
                st.session_state['current_section_index'] = 0
                
            current_section = all_sections[st.session_state['current_section_index']]
            
            # Barre de progression simplifiée (0 = Choix Phase, 1+ = Saisie)
            is_phase_selection = (st.session_state['current_section_index'] == 0)
            
            st.markdown(f"## {current_section}")
            
            # Récupérer les questions de la section
            section_questions = df[df['section'] == current_section]
            
            # Afficher les questions (Sauf ID 5)
            for _, row in section_questions.iterrows():
                if check_condition(row, st.session_state['form_answers']):
                    render_field(row)

            # Validation des champs obligatoires
            is_valid, missing = validate_mandatory_questions(section_questions, st.session_state['form_answers'])

            # --- LOGIQUE DE NAVIGATION MODIFIÉE ---
            st.markdown("---")
            
            if is_phase_selection:
                # --- CAS 1 : PREMIÈRE SECTION (Choix de phase) ---
                # Ici, on a juste un bouton "Suivant" classique pour aller remplir les détails
                if st.button("Suivant ➡️ Commencer la saisie"):
                    if is_valid:
                        next_section_linear()
                        st.rerun()
                    else:
                        st.error(f"Champs manquants : {', '.join(missing)}")
            
            else:
                # --- CAS 2 : SECTION DE CONTENU (On a déjà choisi une phase) ---
                # C'est ICI qu'on pose la question ID 5
                
                # Récupérer la vraie question ID 5 depuis l'Excel si elle existe, sinon défaut
                q5_row = df[df['id'] == 5]
                if not q5_row.empty:
                    q5_text = q5_row.iloc[0]['question']
                    q5_desc = q5_row.iloc[0]['Description']
                else:
                    q5_text = "Transition : Avez-vous d'autres éléments à ajouter (nouvelle phase) ?"
                    q5_desc = "Si Oui, vous retournerez à la sélection. Si Non, le formulaire sera clôturé."

                # Bloc visuel pour la question de transition
                st.markdown('<div class="transition-block">', unsafe_allow_html=True)
                st.markdown(f"**5. {q5_text}**")
                if q5_desc: st.caption(q5_desc)
                
                transition_response = st.radio(
                    "Votre choix :",
                    ["Non", "Oui"], # Ordre par défaut
                    key=f"trans_{st.session_state['current_section_index']}",
                    label_visibility="collapsed"
                )
                
                # Enregistrer la réponse ID 5 pour la logique conditionnelle future
                st.session_state['form_answers'][5] = transition_response
                
                st.markdown('</div>', unsafe_allow_html=True)

                col_nav1, col_nav2 = st.columns(2)
                
                with col_nav2:
                    if transition_response == "Oui":
                        # --- MODIF 2A : RENVOI VERS SÉLECTION (INDEX 0) ---
                        if st.button("🔄 Valider et Ajouter une phase"):
                            if is_valid:
                                go_to_phase_selection() # Retour case départ
                                st.rerun()
                            else:
                                st.error("Remplissez les champs obligatoires avant de passer à la suite.")
                    else:
                        # --- MODIF 2B : RENVOI VERS FIN ---
                        if st.button("✅ Valider et Terminer"):
                            if is_valid:
                                go_to_submission() # Fin du form
                                st.rerun()
                            else:
                                st.error("Remplissez les champs obligatoires avant de terminer.")

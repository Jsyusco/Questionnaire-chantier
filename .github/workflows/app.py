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

        background-color: #1e1e1e;

        padding: 30px;

        border-radius: 12px;

        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5);

        margin-bottom: 20px;

        color: #e0e0e0;

    }

    

    /* Bloc de question individuel */

    .question-block {

        margin-bottom: 20px;

        padding: 15px;

        border-left: 4px solid #4285F4; 

        background-color: #2d2d2d;

        border-radius: 4px;

    }

    

    /* Description/Texte d'aide */

    .description {

        font-size: 0.85em;

        color: #aaaaaa;

        /* La marge est ajustée pour un meilleur espacement entre la question (markdown) et l'input (widget) */

        margin-top: 5px; 

        margin-bottom: 10px;

        font-style: italic;

    }

    

    /* Texte obligatoire */

    .mandatory {

        color: #F4B400;

        font-weight: bold;

    }

    

    /* Message d'erreur de validation */

    .validation-error {

        color: #ff6b6b;

        background-color: #3d1f1f;

        padding: 10px;

        border-radius: 5px;

        border-left: 4px solid #ff6b6b;

        margin: 10px 0;

    }

    

    /* Titres (h1, h2, h3) */

    h1, h2, h3 { 

        color: #ffffff;

    }

    

    /* Boutons de navigation */

    .stButton > button { 

        width: 100%; 

        border-radius: 8px;

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



    /* Style pour les inputs/select */

    .stTextInput label, .stSelectbox label, .stNumberInput label {

        color: #e0e0e0;

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



@st.cache_data

def load_site_data(file):

    """Charge les données de la feuille 'site' pour sélection du projet"""

    try:

        df_site = pd.read_excel(file, sheet_name='Site', engine='openpyxl')

        df_site.columns = df_site.columns.str.strip()

        return df_site

    except Exception as e:

        st.error(f"Erreur lors de la lecture de la feuille 'site' : {e}")

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



# --- FONCTIONS LOGIQUES ---



def check_condition(row, answers):

    """Vérifie si une question doit être affichée."""

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

            return str(user_answer) == str(target_value)

        else:

            return True 

    except Exception as e:

        return True



def check_section_condition(section_df, answers):

    """

    Vérifie si au moins une question de la section est visible.

    Une section n'est affichée que si elle contient au moins une question visible.

    """

    for _, row in section_df.iterrows():

        if check_condition(row, answers):

            return True

    return False



def validate_mandatory_questions(section_df, answers):

    """

    Valide que toutes les questions obligatoires visibles ont été remplies.

    Retourne (is_valid, missing_questions_list)

    """

    missing = []

    

    for _, row in section_df.iterrows():

        # La question doit être visible

        if not check_condition(row, answers):

            continue

            

        q_id = int(row['id'])

        q_mandatory = str(row['obligatoire']).lower() == 'oui'

        

        if q_mandatory:

            answer = answers.get(q_id)

            # Vérifier si la réponse est vide ou non valide

            if answer is None or answer == "" or answer == 0:

                missing.append(f"Question {q_id}: {row['question']}")

    

    return len(missing) == 0, missing



def render_field(row):

    """

    Génère le widget Streamlit approprié. 

    Affiche la Question manuellement, puis la Description, puis le Champ de saisie (avec label masqué).

    """

    q_id = int(row['id'])

    q_text = row['question']

    q_type = str(row['type']).strip().lower()

    q_desc = row['Description']

    q_mandatory = str(row['obligatoire']).lower() == 'oui'

    q_options = str(row['options']).split(',') if row['options'] else []

    

    # 1. Préparation du texte de la question pour l'affichage manuel

    display_question = f"{q_id}. {q_text}" + (' <span class="mandatory">*</span>' if q_mandatory else "")

    widget_key = f"q_{q_id}" 

    current_val = st.session_state['form_answers'].get(q_id)

    val = None



    with st.container():

        

        

        # Affichage manuel de la Question (en haut)

        st.markdown(f"**{display_question}**", unsafe_allow_html=True)

        

        # Affichage de la Description (au milieu)

        if q_desc:

            st.markdown(f'<p class="description">{q_desc}</p>', unsafe_allow_html=True)

            

        # Affichage du Champ de Saisie (en bas)

        # On utilise label_visibility="collapsed" pour masquer le label du widget et éviter la duplication de la question

        

        if q_type == 'text':

            val = st.text_input(" ", value=current_val if current_val else "", key=widget_key, label_visibility="collapsed")

            

        elif q_type == 'select':

            index = 0

            clean_options = [opt.strip() for opt in q_options]

            if "" not in clean_options:

                clean_options.insert(0, "")

                

            if current_val in clean_options:

                index = clean_options.index(current_val)

                

            val = st.selectbox(" ", clean_options, index=index, key=widget_key, label_visibility="collapsed")

            

        elif q_type == 'number':

            val = st.number_input(" ", value=int(current_val) if current_val else 0, key=widget_key, label_visibility="collapsed")

            

        elif q_type == 'photo':

            # Pour le file_uploader, on utilise quand même le label_visibility pour la cohérence

            val = st.file_uploader(" ", type=['png', 'jpg', 'jpeg'], key=widget_key, label_visibility="collapsed")

            if val is not None:

                st.success(f"Image chargée : {val.name}")

            elif current_val is not None:

                st.info("Image déjà chargée précédemment.") 

        

        st.markdown('</div>', unsafe_allow_html=True) # Fin du bloc Question

        

        # Enregistrement de la réponse

        if val is not None:

            st.session_state['form_answers'][q_id] = val



# --- NAVIGATION ---

def next_section():

    st.session_state['current_section_index'] += 1



def prev_section():

    st.session_state['current_section_index'] -= 1



# --- MAIN APP ---



st.markdown('<div class="form-container"><h1>📝 Formulaire de Travaux</h1></div>', unsafe_allow_html=True)



uploaded_file = st.file_uploader("Chargez le fichier Excel de structure (Questions)", type=["xlsx"])



if uploaded_file is not None:

    df = load_form_structure(uploaded_file)

    df_site = load_site_data(uploaded_file)

    

    if df is not None and df_site is not None:

        

        # --- SÉLECTION DU PROJET ---

        if st.session_state['selected_project'] is None:

            

            st.markdown("### 🏗️ Sélection du Projet")

            

            # Liste des intitulés de projets

            if 'Intitulé' in df_site.columns:

                project_options = [""] + df_site['Intitulé'].dropna().tolist()

                

                selected = st.selectbox(

                    "Choisissez l'intitulé du projet",

                    project_options,

                    key="project_selector"

                )

                

                if selected and selected != "":

                    # Récupérer les données du projet sélectionné

                    project_row = df_site[df_site['Intitulé'] == selected].iloc[0]

                    

                    # Mapping des colonnes à afficher

                    display_mapping = {

                        'L [Plan de Déploiement]': 'PDC L',

                        'R [Plan de Déploiement]': 'PDC R',

                        'UR [Plan de Déploiement]': 'PDC UR',

                        'Pré L [Plan de Déploiement]': 'PDC pré-équipés L',

                        'Pré R [Plan de Déploiement]': 'PDC pré-équipés R',

                        'Pré UR [Plan de Déploiement]': 'PDC pré-équipés UR',

                        'Fournisseur Bornes AC [Bornes]': 'Fournisseur Bornes AC',

                        'Fournisseur Bornes DC [Bornes]': 'Fournisseur Bornes DC'

                    }

                    

                    # Afficher les informations du projet

                    st.markdown("---")

                    st.markdown("#### 📊 Informations du Projet")

                    

                    project_info = {}

                    for col_name, display_name in display_mapping.items():

                        if col_name in project_row.index:

                            value = project_row[col_name]

                            project_info[display_name] = value



                    # --- DÉBUT DE LA MODIFICATION POUR LES 3 COLONNES ---

                    cols = st.columns(3)

                    

                    # Utiliser un compteur pour distribuer les éléments

                    i = 0

                    for display_name, value in project_info.items():

                        # Afficher dans la colonne i % 3 (0, 1, 2, 0, 1, 2, ...)

                        with cols[i % 3]:

                            st.write(f"**{display_name}:** {value}")

                        i += 1

                    

                    # --- FIN DE LA MODIFICATION POUR LES 3 COLONNES ---

                    

                    st.markdown("---")

                    

                    # Bouton de validation

                    if st.button("✅ Valider et commencer le formulaire", key="validate_project"):

                        st.session_state['selected_project'] = selected

                        st.session_state['project_data'] = project_info

                        st.rerun()

                else:

                    st.info("Veuillez choisir un projet pour continuer.")



            else:

                st.error("La colonne 'Intitulé' n'a pas été trouvée dans la feuille 'site'.")

        

        else:

            # --- AFFICHAGE DU FORMULAIRE (projet déjà sélectionné) ---

            

            # Afficher le projet sélectionné en haut

            st.markdown('<div class="form-container">', unsafe_allow_html=True)

            st.markdown(f"### 🏗️ Projet : {st.session_state['selected_project']}")

            

            # Affichage des infos dans l'expander (laisse le code original en liste pour cet expander)

            with st.expander("📊 Voir les informations du projet"):

                # --- MODIFICATION DE L'EXPANDER POUR AFFICHER EN 3 COLONNES AUSSI ---

                cols_expander = st.columns(3)

                i_expander = 0

                for key, value in st.session_state['project_data'].items():

                     with cols_expander[i_expander % 3]:

                          st.write(f"**{key}:** {value}")

                     i_expander += 1

                # --- FIN DE LA MODIFICATION DANS L'EXPANDER ---

            

            if st.button("🔄 Changer de projet"):

                st.session_state['selected_project'] = None

                st.session_state['current_section_index'] = 0

                st.session_state['form_answers'] = {}

                st.rerun()

            

            st.markdown('</div>', unsafe_allow_html=True)

            

            # Récupération de toutes les sections

            all_sections = df['section'].unique().tolist()

            

            # Filtrer les sections visibles selon les conditions

            visible_sections = []

            for section_name in all_sections:

                section_df = df[df['section'] == section_name]

                if check_section_condition(section_df, st.session_state['form_answers']):

                    visible_sections.append(section_name)

            

            # Si aucune section n'est visible, afficher la première par défaut

            if not visible_sections:

                if all_sections:

                     visible_sections = [all_sections[0]]

                else:

                     st.warning("Le fichier Excel ne contient aucune section de question.")

                     st.stop()

            

            # Sécurité index

            if st.session_state['current_section_index'] >= len(visible_sections):

                st.session_state['current_section_index'] = len(visible_sections) - 1

            

            current_section_name = visible_sections[st.session_state['current_section_index']]

            

            # Barre de progression

            progress = (st.session_state['current_section_index'] + 1) / len(visible_sections)

            st.progress(progress)

            st.caption(f"Section {st.session_state['current_section_index'] + 1}/{len(visible_sections)} : **{current_section_name}**")



            # --- AFFICHAGE DU FORMULAIRE POUR LA SECTION COURANTE ---

            st.markdown(f"## {current_section_name}")

            

            section_questions = df[df['section'] == current_section_name]

            

            visible_questions_count = 0

            

            for index, row in section_questions.iterrows():

                if check_condition(row, st.session_state['form_answers']):

                    render_field(row)

                    visible_questions_count += 1

            

            if visible_questions_count == 0:

                st.info("Aucune question visible pour cette section selon vos choix précédents.")



            # --- VALIDATION DES QUESTIONS OBLIGATOIRES ---

            is_valid, missing_questions = validate_mandatory_questions(

                section_questions, 

                st.session_state['form_answers']

            )



            # --- BOUTONS DE NAVIGATION ---

            col1, col2, col3 = st.columns([1, 2, 1])

            

            with col1:

                if st.session_state['current_section_index'] > 0:

                    st.button("⬅️ Précédent", on_click=prev_section)

            

            with col3:

                if st.session_state['current_section_index'] < len(visible_sections) - 1:

                    # Bouton "Suivant" avec validation

                    if st.button("Suivant ➡️"):

                        if is_valid:

                            next_section()

                            st.rerun()

                        else:

                            # Afficher les erreurs de validation

                            st.markdown('<div class="validation-error">', unsafe_allow_html=True)

                            st.error("⚠️ Veuillez répondre à toutes les questions obligatoires (*) avant de continuer :")

                            for missing in missing_questions:

                                st.write(f"• {missing}")

                            st.markdown('</div>', unsafe_allow_html=True)

                else:

                    # Bouton "Soumettre" avec validation

                    if st.button("✅ Soumettre le rapport"):

                        if is_valid:

                            st.success("✅ Formulaire terminé avec succès et prêt à être soumis !")

                            st.write("**Projet :**", st.session_state['selected_project'])

                            st.write("**Récapitulatif des réponses :**")

                            display_data = {k: str(v) for k, v in st.session_state['form_answers'].items()}

                            st.json(display_data)

                            st.info("Vous pouvez maintenant traiter ces données (enregistrement en base de données, exportation Excel, etc.)")



                        else:

                            st.markdown('<div class="validation-error">', unsafe_allow_html=True)

                            st.error("⚠️ Veuillez répondre à toutes les questions obligatoires (*) avant de soumettre :")

                            for missing in missing_questions:

                                st.write(f"• {missing}")

                            st.markdown('</div>', unsafe_allow_html=True)

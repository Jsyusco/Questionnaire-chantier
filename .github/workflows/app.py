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
        # tolerant column names
        if 'Condition value' not in df.columns and 'Condition value' not in df.columns:
            # fallback handled later: we don't error out, but ensure necessary columns exist.
            pass

        # normalisations
        df['options'] = df.get('options', pd.Series([''] * len(df))).fillna('')
        df['Description'] = df.get('Description', pd.Series([''] * len(df))).fillna('')
        df['Condition value'] = df.get('Condition value', pd.Series([''] * len(df))).fillna('')
        df['Condition on'] = df.get('Condition on', pd.Series([0] * len(df))).fillna(0)
        return df
    except Exception as e:
        st.error(f"Erreur technique lors de la lecture : {e}")
        return None

@st.cache_data
def load_site_data(file):
    """Charge les données de la feuille 'Site' pour sélection du projet"""
    try:
        df_site = pd.read_excel(file, sheet_name='Site', engine='openpyxl')
        df_site.columns = df_site.columns.str.strip()
        return df_site
    except Exception as e:
        st.error(f"Erreur lors de la lecture de la feuille 'Site' : {e}")
        return None

# --- GESTION DE L'ÉTAT ---
# stockage par phase : { "phase_1": {id: answer, ...}, "phase_2": {...} }
if 'form_answers' not in st.session_state:
    st.session_state['form_answers'] = {}  # dict par phase

if 'current_phase' not in st.session_state:
    st.session_state['current_phase'] = 1

if 'current_section_index' not in st.session_state:
    st.session_state['current_section_index'] = 0

if 'selected_project' not in st.session_state:
    st.session_state['selected_project'] = None

if 'project_data' not in st.session_state:
    st.session_state['project_data'] = {}

# helper: ensure phase exists
def ensure_phase_exists(n):
    key = f"phase_{n}"
    if key not in st.session_state['form_answers']:
        st.session_state['form_answers'][key] = {}

# initialize first phase answers
ensure_phase_exists(st.session_state['current_phase'])

# --- FONCTIONS LOGIQUES ---
def get_current_phase_key():
    return f"phase_{st.session_state['current_phase']}"

def get_current_phase_answers():
    return st.session_state['form_answers'].get(get_current_phase_key(), {})

def check_condition(row, answers):
    """Vérifie si une question doit être affichée en se basant sur les réponses passées de la phase courante."""
    try:
        is_conditional = int(row.get('Condition on', 0)) == 1
    except:
        is_conditional = False

    if not is_conditional:
        return True

    condition_rule = str(row.get('Condition value', '')).strip()
    if not condition_rule:
        return True

    try:
        if '=' in condition_rule:
            target_id_str, target_value = condition_rule.split('=', 1)
            target_id = int(target_id_str.strip())
            target_value = target_value.strip()

            user_answer = answers.get(target_id)
            # compare stringified versions
            return str(user_answer) == str(target_value)
        else:
            return True
    except Exception:
        return True

def check_section_condition(section_df, answers):
    """
    Vérifie si au moins une question de la section est visible dans la phase courante.
    """
    for _, row in section_df.iterrows():
        if check_condition(row, answers):
            return True
    return False

def validate_mandatory_questions(section_df, answers):
    """
    Valide que toutes les questions obligatoires visibles ont été remplies pour la phase courante.
    Retourne (is_valid, missing_questions_list)
    """
    missing = []
    for _, row in section_df.iterrows():
        if not check_condition(row, answers):
            continue

        try:
            q_id = int(row['id'])
        except:
            continue

        q_mandatory = str(row.get('obligatoire', '')).lower() == 'oui'
        if q_mandatory:
            answer = answers.get(q_id)
            if answer is None or answer == "" or answer == 0:
                missing.append(f"Question {q_id}: {row.get('question', '')}")
    return len(missing) == 0, missing

def render_field(row):
    """
    Génère le widget Streamlit pour la question en se basant sur les réponses de la phase courante.
    """
    q_id = int(row['id'])
    q_text = row.get('question', '')
    q_type = str(row.get('type', '')).strip().lower()
    q_desc = row.get('Description', '')
    q_mandatory = str(row.get('obligatoire', '')).lower() == 'oui'
    q_options = str(row.get('options', '')).split(',') if row.get('options', '') else []

    display_question = f"{q_id}. {q_text}" + (' <span class=\"mandatory\">*</span>' if q_mandatory else "")
    widget_key = f"phase{st.session_state['current_phase']}_q_{q_id}"
    # read/write from phase-specific answers
    current_phase_answers = get_current_phase_answers()
    current_val = current_phase_answers.get(q_id)

    val = None
    with st.container():
        st.markdown(f"**{display_question}**", unsafe_allow_html=True)
        if q_desc:
            st.markdown(f'<p class="description">{q_desc}</p>', unsafe_allow_html=True)

        if q_type == 'text':
            val = st.text_input(" ", value=current_val if current_val else "", key=widget_key, label_visibility="collapsed")
        elif q_type == 'select':
            index = 0
            clean_options = [opt.strip() for opt in q_options if opt is not None]
            # ensure an empty option is available
            if "" not in clean_options:
                clean_options.insert(0, "")
            if current_val in clean_options:
                index = clean_options.index(current_val)
            val = st.selectbox(" ", clean_options, index=index, key=widget_key, label_visibility="collapsed")
        elif q_type == 'number':
            try:
                val0 = int(current_val) if (current_val is not None and str(current_val) != "") else 0
            except:
                val0 = 0
            val = st.number_input(" ", value=val0, key=widget_key, label_visibility="collapsed")
        elif q_type == 'photo':
            val = st.file_uploader(" ", type=['png', 'jpg', 'jpeg'], key=widget_key, label_visibility="collapsed")
            if val is not None:
                st.success(f"Image chargée : {val.name}")
            elif current_val is not None:
                st.info("Image déjà chargée précédemment pour cette phase.")
        else:
            # fallback to text input if unknown type
            val = st.text_input(" ", value=current_val if current_val else "", key=widget_key, label_visibility="collapsed")

        # enregistrer la réponse dans la phase courante
        if val is not None:
            phase_key = get_current_phase_key()
            if phase_key not in st.session_state['form_answers']:
                st.session_state['form_answers'][phase_key] = {}
            st.session_state['form_answers'][phase_key][q_id] = val

# --- NAVIGATION ---
def next_section():
    st.session_state['current_section_index'] += 1

def prev_section():
    st.session_state['current_section_index'] -= 1

# --- MAIN APP ---
st.markdown('<div class="form-container"><h1>📝 Formulaire de Travaux (multi-phase)</h1></div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Chargez le fichier Excel de structure (Questions)", type=["xlsx"])

if uploaded_file is not None:
    df = load_form_structure(uploaded_file)
    df_site = load_site_data(uploaded_file)

    if df is not None and df_site is not None:
        # --- SÉLECTION DU PROJET ---
        if st.session_state['selected_project'] is None:
            st.markdown("### 🏗️ Sélection du Projet")
            if 'Intitulé' in df_site.columns:
                project_options = [""] + df_site['Intitulé'].dropna().tolist()
                selected = st.selectbox("Choisissez l'intitulé du projet", project_options, key="project_selector")
                if selected and selected != "":
                    project_row = df_site[df_site['Intitulé'] == selected].iloc[0]
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
                    st.markdown("---")
                    st.markdown("#### 📊 Informations du Projet")
                    project_info = {}
                    for col_name, display_name in display_mapping.items():
                        if col_name in project_row.index:
                            value = project_row[col_name]
                            project_info[display_name] = value
                    cols = st.columns(3)
                    i = 0
                    for display_name, value in project_info.items():
                        with cols[i % 3]:
                            st.write(f"**{display_name}:** {value}")
                        i += 1
                    st.markdown("---")
                    if st.button("✅ Valider et commencer le formulaire", key="validate_project"):
                        st.session_state['selected_project'] = selected
                        st.session_state['project_data'] = project_info
                        st.rerun()
                else:
                    st.info("Veuillez choisir un projet pour continuer.")
            else:
                st.error("La colonne 'Intitulé' n'a pas été trouvée dans la feuille 'Site'.")
        else:
            # --- AFFICHAGE DU FORMULAIRE (projet déjà sélectionné) ---
            st.markdown('<div class="form-container">', unsafe_allow_html=True)
            st.markdown(f"### 🏗️ Projet : {st.session_state['selected_project']}")
            with st.expander("📊 Voir les informations du projet"):
                cols_expander = st.columns(3)
                i_expander = 0
                for key, value in st.session_state['project_data'].items():
                    with cols_expander[i_expander % 3]:
                        st.write(f"**{key}:** {value}")
                    i_expander += 1
            if st.button("🔄 Changer de projet"):
                st.session_state['selected_project'] = None
                st.session_state['current_section_index'] = 0
                st.session_state['form_answers'] = {}
                st.session_state['current_phase'] = 1
                ensure_phase_exists(1)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            # Récupération de toutes les sections
            all_sections = df['section'].unique().tolist()

            # Filtrer les sections visibles selon les conditions pour la phase courante
            current_answers = get_current_phase_answers()
            visible_sections = []
            for section_name in all_sections:
                section_df = df[df['section'] == section_name]
                if check_section_condition(section_df, current_answers):
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
            st.caption(f"Phase {st.session_state['current_phase']} — Section {st.session_state['current_section_index'] + 1}/{len(visible_sections)} : **{current_section_name}**")

            # --- AFFICHAGE DU FORMULAIRE POUR LA SECTION COURANTE ---
            st.markdown(f"## {current_section_name}")

            section_questions = df[df['section'] == current_section_name]
            visible_questions_count = 0

            for index, row in section_questions.iterrows():
                if check_condition(row, current_answers):
                    render_field(row)
                    visible_questions_count += 1

            if visible_questions_count == 0:
                st.info("Aucune question visible pour cette section selon vos choix précédents dans cette phase.")

            # --- VALIDATION DES QUESTIONS OBLIGATOIRES pour la phase courante ---
            is_valid, missing_questions = validate_mandatory_questions(section_questions, current_answers)

            # --- BOUTONS DE NAVIGATION ---
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.session_state['current_section_index'] > 0:
                    st.button("⬅️ Précédent", on_click=prev_section)
            with col3:
                if st.session_state['current_section_index'] < len(visible_sections) - 1:
                    if st.button("Suivant ➡️"):
                        # Validation avant de passer à la section suivante
                        # Attention : validate_mandatory_questions n'analyse que la section courante,
                        # on demande de remplir les obligatoires visibles dans la section courante.
                        is_valid_section, missing_for_section = validate_mandatory_questions(section_questions, current_answers)
                        if is_valid_section:
                            next_section()
                            st.rerun()
                        else:
                            st.markdown('<div class="validation-error">', unsafe_allow_html=True)
                            st.error("⚠️ Veuillez répondre à toutes les questions obligatoires (*) avant de continuer :")
                            for missing in missing_for_section:
                                st.write(f"• {missing}")
                            st.markdown('</div>', unsafe_allow_html=True)
                else:
                    # Nous sommes sur la dernière section visible de la phase courante.
                    # Ici : on pose la question "Voulez-vous déclarer une nouvelle phase ?"
                    st.markdown("---")
                    st.markdown("### ➕ Déclaration de nouvelle phase")
                    declare_new_phase = st.radio("Voulez-vous déclarer une nouvelle phase ?", ["Non", "Oui"], horizontal=True, key=f"declare_phase_phase{st.session_state['current_phase']}")

                    if declare_new_phase == "Oui":
                        # on ne crée la nouvelle phase que si la phase courante est valide (toutes les obligatoires visibles remplies)
                        # pour éviter de perdre des réponses incomplètes
                        is_valid_phase, missing_phase = True, []
                        # To be thorough, check all sections in this phase for mandatory questions that are visible.
                        for sec in visible_sections:
                            sec_df = df[df['section'] == sec]
                            valid_sec, missing_sec = validate_mandatory_questions(sec_df, current_answers)
                            if not valid_sec:
                                is_valid_phase = False
                                missing_phase.extend(missing_sec)

                        if is_valid_phase:
                            if st.button("✅ Démarrer une nouvelle phase"):
                                # incrémenter la phase et réinitialiser l'état (chaque phase repart de zéro)
                                st.session_state['current_phase'] += 1
                                new_phase_key = get_current_phase_key()
                                st.session_state['form_answers'][new_phase_key] = {}
                                st.session_state['current_section_index'] = 0
                                st.experimental_rerun()
                        else:
                            st.markdown('<div class="validation-error">', unsafe_allow_html=True)
                            st.error("⚠️ Impossible de commencer une nouvelle phase : des questions obligatoires sont manquantes dans la phase courante.")
                            for m in missing_phase:
                                st.write(f"• {m}")
                            st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        # Non => comportement comme si terminé : proposer la soumission finale
                        if st.button("📤 Soumettre le rapport final"):
                            # Avant soumission, valider la phase courante entièrement (toutes les sections)
                            is_valid_phase, missing_phase = True, []
                            for sec in visible_sections:
                                sec_df = df[df['section'] == sec]
                                valid_sec, missing_sec = validate_mandatory_questions(sec_df, current_answers)
                                if not valid_sec:
                                    is_valid_phase = False
                                    missing_phase.extend(missing_sec)

                            if is_valid_phase:
                                st.success("✅ Formulaire multi-phase prêt à être soumis.")
                                st.write("### 📄 Récapitulatif complet des phases")
                                # Afficher les réponses de toutes les phases
                                # Convertir en formes sérialisables (ex: fichiers -> noms)
                                def serialize_answers(all_phases):
                                    serialized = {}
                                    for pkey, answers in all_phases.items():
                                        serialized[pkey] = {}
                                        for qid, ans in answers.items():
                                            try:
                                                # si file_uploader
                                                name = getattr(ans, "name", None)
                                                if name:
                                                    serialized[pkey][str(qid)] = f"FILE: {name}"
                                                else:
                                                    serialized[pkey][str(qid)] = str(ans)
                                            except Exception:
                                                serialized[pkey][str(qid)] = str(ans)
                                    return serialized

                                st.json(serialize_answers(st.session_state['form_answers']))
                                st.info("Vous pouvez maintenant traiter ces données (enregistrement en base de données, exportation Excel, etc.)")
                            else:
                                st.markdown('<div class="validation-error">', unsafe_allow_html=True)
                                st.error("⚠️ Veuillez répondre à toutes les questions obligatoires (*) de la phase courante avant de soumettre :")
                                for missing in missing_phase:
                                    st.write(f"• {missing}")
                                st.markdown('</div>', unsafe_allow_html=True)

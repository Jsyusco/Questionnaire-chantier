import streamlit as st
import pandas as pd

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Visualisation Projets", layout="centered")

# --- STYLE CSS "DARK MODE" ---
st.markdown("""
    <style>
    /* 1. Fond général de l'application (Noir profond) */
    .stApp {
        background-color: #121212;
    }
    
    /* 2. Conteneur Principal (Gris foncé) */
    .form-container {
        background-color: #1e1e1e;
        padding: 30px;
        border-radius: 12px;
        /* Bordure supérieure blanche pour le contraste */
        border-top: 8px solid #ffffff; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.5);
        margin-bottom: 20px;
        color: white;
    }
    
    /* 3. Cartes de données (Gris intermédiaire) */
    .data-card {
        background-color: #2d2d2d;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #404040; /* Bordure grise subtile */
        margin-bottom: 15px;
    }

    /* 4. Typographie */
    h1 {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #ffffff;
        font-weight: 300;
    }
    
    h2 {
        color: #ffffff;
        border-bottom: 1px solid #404040;
        padding-bottom: 10px;
    }

    p {
        color: #b0b0b0; /* Gris clair pour les descriptions */
    }
    
    /* Libellé de la question (Blanc) */
    .label-text {
        font-size: 16px;
        font-weight: 600;
        color: #e0e0e0;
        margin-bottom: 8px;
    }
    
    /* Réponse (Gris clair) */
    .value-text {
        font-size: 15px;
        color: #b0b0b0;
        padding-bottom: 5px;
        border-bottom: 1px dotted #505050;
    }
    
    /* Modification des boutons Streamlit pour qu'ils s'intègrent mieux */
    .stButton > button {
        background-color: #ffffff;
        color: #121212;
        border: none;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #e0e0e0;
        color: #000000;
    }

    /* Cache menu et footer standard */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- GESTION DE L'ÉTAT (NAVIGATION) ---
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'selected_project' not in st.session_state:
    st.session_state.selected_project = None

# --- FONCTIONS DE NAVIGATION ---
def go_to_step_2():
    st.session_state.step = 2

def go_to_step_1():
    st.session_state.step = 1

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data
def load_data(file):
    try:
        # Lecture de la feuille "Site"
        # engine='openpyxl' est spécifié explicitement pour éviter les ambiguïtés
        df = pd.read_excel(file, sheet_name='Site', engine='openpyxl')
        df = df.fillna("-") 
        # Convertir toutes les données en string pour éviter les erreurs d'affichage
        df = df.astype(str)
        return df
    except Exception as e:
        st.error(f"Erreur technique : {e}")
        return None

# --- INTERFACE UTILISATEUR ---

# En-tête global
st.markdown('<div class="form-container"><h1>Suivi de Déploiement</h1><p>Interface de consultation sombre.</p></div>', unsafe_allow_html=True)

# Widget Upload
uploaded_file = st.file_uploader("Chargez votre fichier Excel", type=["xlsx"])

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None:
        col_intitule = df.columns[0]
        
        # --- PAGE 1 : SÉLECTION ---
        if st.session_state.step == 1:
            st.markdown('<div class="form-container">', unsafe_allow_html=True)
            st.subheader("Sélection du Projet")
            
            options = df[col_intitule].unique().tolist()
            choice = st.selectbox("Rechercher un site :", options)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Bouton Suivant (centré ou aligné à droite via colonnes)
            col1, col2, col3 = st.columns([1,1,1])
            with col2:
                if st.button("Suivant  ➜", use_container_width=True):
                    st.session_state.selected_project = choice
                    go_to_step_2()
                    st.rerun()

        # --- PAGE 2 : AFFICHAGE DÉTAILLÉ ---
        elif st.session_state.step == 2:
            # Récupération de la ligne correspondante
            try:
                project_data = df[df[col_intitule] == st.session_state.selected_project].iloc[0]
                
                # Titre du projet sélectionné
                st.markdown(f'<div class="form-container"><h2>{st.session_state.selected_project}</h2></div>', unsafe_allow_html=True)
                
                # Affichage des colonnes
                cols = df.columns[1:] 
                
                for col_name in cols:
                    valeur = project_data[col_name]
                    # Nettoyage si la valeur est "nan" string
                    if valeur == 'nan': valeur = "-"

                    html_card = f"""
                    <div class="data-card">
                        <div class="label-text">{col_name}</div>
                        <div class="value-text">{valeur}</div>
                    </div>
                    """
                    st.markdown(html_card, unsafe_allow_html=True)
                
                # Bouton Précédent
                col1, col2, col3 = st.columns([1,1,1])
                with col1:
                    if st.button("⬅ Précédent"):
                        go_to_step_1()
                        st.rerun()
            except IndexError:
                st.error("Erreur : Projet introuvable dans les données.")
                if st.button("Retour"):
                     go_to_step_1()
                     st.rerun()

else:
    # Message d'attente stylisé
    st.markdown("""
    <div style='text-align: center; color: #666; margin-top: 50px;'>
        En attente du fichier Excel...
    </div>
    """, unsafe_allow_html=True)

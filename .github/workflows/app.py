import streamlit as st
import pandas as pd

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Visualisation Projets", layout="centered")

# --- STYLE CSS "GOOGLE FORMS" ---
# On injecte du CSS pour donner l'apparence de Google Forms (fond gris, blocs blancs)
st.markdown("""
    <style>
    /* Couleur de fond générale */
    .stApp {
        background-color: #f0ebf8;
    }
    
    /* Style des conteneurs (cartes blanches) */
    .form-container {
        background-color: white;
        padding: 30px;
        border-radius: 8px;
        border-top: 10px solid #673ab7; /* La barre violette typique de Google Forms */
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        margin-bottom: 20px;
    }
    
    .data-card {
        background-color: white;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #dadce0;
        margin-bottom: 15px;
    }

    /* Style des titres */
    h1 {
        font-family: 'Google Sans', Roboto, Arial, sans-serif;
        color: #202124;
    }
    
    /* Style des libellés (colonnes) */
    .label-text {
        font-size: 16px;
        font-weight: 500;
        color: #202124;
        margin-bottom: 8px;
    }
    
    /* Style des réponses (valeurs) */
    .value-text {
        font-size: 14px;
        color: #5f6368;
        padding-bottom: 5px;
        border-bottom: 1px dotted #e0e0e0;
    }
    
    /* Cacher le menu par défaut Streamlit pour plus de propreté */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- GESTION DE L'ÉTAT (NAVIGATION) ---
# On initialise les variables de session si elles n'existent pas
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'selected_project' not in st.session_state:
    st.session_state.selected_project = None
if 'dataframe' not in st.session_state:
    st.session_state.dataframe = None

# --- FONCTIONS DE NAVIGATION ---
def go_to_step_2():
    st.session_state.step = 2

def go_to_step_1():
    st.session_state.step = 1

# --- CHARGEMENT DES DONNÉES ---
# Fonction pour charger le fichier. 
# NOTE: Remplacez 'votre_fichier.xlsx' par le chemin réel ou utilisez l'uploader ci-dessous.
@st.cache_data
def load_data(file):
    try:
        # Lecture de la feuille "Site" comme demandé
        df = pd.read_excel(file, sheet_name='Site')
        # On remplit les cases vides par des tirets pour l'affichage
        df = df.fillna("-") 
        return df
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier : {e}")
        return None

# --- INTERFACE UTILISATEUR ---

# Titre principal (simulé dans une carte)
st.markdown('<div class="form-container"><h1>Suivi de Déploiement</h1><p>Sélectionnez un site pour voir les détails.</p></div>', unsafe_allow_html=True)

# Widget pour uploader le fichier (ou vous pouvez coder le chemin en dur)
uploaded_file = st.file_uploader("Chargez votre fichier Excel", type=["xlsx"])

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None:
        # Récupération du nom de la première colonne (Intitulé)
        col_intitule = df.columns[0]
        
        # --- PAGE 1 : SÉLECTION ---
        if st.session_state.step == 1:
            st.markdown('<div class="form-container">', unsafe_allow_html=True)
            st.subheader("Sélection du Projet")
            
            # Liste déroulante basée sur la colonne 1
            options = df[col_intitule].unique().tolist()
            choice = st.selectbox("Quel site souhaitez-vous consulter ?", options)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Bouton Suivant
            if st.button("Suivant"):
                st.session_state.selected_project = choice
                go_to_step_2()
                st.rerun()

        # --- PAGE 2 : AFFICHAGE DÉTAILLÉ ---
        elif st.session_state.step == 2:
            # Filtrer les données pour le projet sélectionné
            project_data = df[df[col_intitule] == st.session_state.selected_project].iloc[0]
            
            st.markdown(f'<div class="form-container"><h2>{st.session_state.selected_project}</h2></div>', unsafe_allow_html=True)
            
            # Boucle sur les colonnes pour afficher les infos
            # On commence à l'index 1 pour sauter la colonne "Intitulé" déjà affichée en titre
            cols = df.columns[1:] 
            
            for col_name in cols:
                valeur = project_data[col_name]
                
                # Création d'une "carte" pour chaque champ
                html_card = f"""
                <div class="data-card">
                    <div class="label-text">{col_name}</div>
                    <div class="value-text">{valeur}</div>
                </div>
                """
                st.markdown(html_card, unsafe_allow_html=True)
            
            # Bouton Précédent
            col_back, col_void = st.columns([1, 4])
            with col_back:
                if st.button("Précédent"):
                    go_to_step_1()
                    st.rerun()

else:
    st.info("Veuillez charger un fichier Excel pour commencer.")

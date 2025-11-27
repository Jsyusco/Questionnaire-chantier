import streamlit as st
import pandas as pd

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Visualisation Projets Condensée", layout="centered")

# --- STYLE CSS "DARK MODE" ---
# Conserve le style sombre de la version précédente
st.markdown("""
    <style>
    .stApp {
        background-color: #121212;
    }
    
    .form-container {
        background-color: #1e1e1e;
        padding: 30px;
        border-radius: 12px;
        border-top: 8px solid #ffffff; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.5);
        margin-bottom: 20px;
        color: white;
    }
    
    /* Style pour le mode condensé (un seul bloc) */
    .condensed-block {
        background-color: #2d2d2d;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #404040;
        margin-bottom: 15px;
        color: #e0e0e0;
        line-height: 1.6;
        white-space: pre-wrap; /* Permet un meilleur affichage des retours à la ligne */
    }

    h1, h2 {
        color: #ffffff;
    }
    
    /* Cache menu et footer standard */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

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
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data
def load_data(file):
    """Charge et prépare les données du fichier Excel."""
    try:
        df = pd.read_excel(file, sheet_name='Site', engine='openpyxl')
        df = df.fillna("-") 
        df = df.astype(str)
        return df
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier : {e}")
        return None

# --- INTERFACE UTILISATEUR PRINCIPALE ---

# En-tête de l'application
st.markdown('<div class="form-container"><h1>Suivi de Déploiement Condensé</h1><p>Sélectionnez un site pour voir les détails instantanément dans un seul bloc.</p></div>', unsafe_allow_html=True)

# 1. Widget Upload
uploaded_file = st.file_uploader("Chargez votre fichier Excel", type=["xlsx"])

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None and not df.empty:
        col_intitule = df.columns[0]
        
        # 2. SÉLECTION DU PROJET
        with st.container():
            st.markdown('<div class="form-container">', unsafe_allow_html=True)
            st.subheader("Sélection du Projet")
            
            # Liste déroulante pour la sélection du projet
            options = df[col_intitule].unique().tolist()
            selected_project = st.selectbox("Site à consulter :", options)
            
            st.markdown('</div>', unsafe_allow_html=True)

        # 3. AFFICHAGE CONDENSÉ DES RÉSULTATS
        
        # Titre pour l'affichage
        st.markdown(f'<div class="form-container"><h2>Détails du projet : {selected_project}</h2></div>', unsafe_allow_html=True)

        # Filtrer les données pour le projet sélectionné
        project_data = df[df[col_intitule] == selected_project].iloc[0]
        cols_to_display = df.columns[1:] 
        
        # Construction du contenu condensé
        condensed_content = ""
        for col_name in cols_to_display:
            valeur = project_data[col_name]
            
            # Utilisation de Markdown pour le gras et les retours à la ligne
            # Note: Le \n est interprété par le CSS 'white-space: pre-wrap;'
            condensed_content += f"**{col_name}** : {valeur} \n" 
        
        # Affichage dans un grand bloc unique
        st.markdown(f"""
            <div class="condensed-block">
                {condensed_content}
            </div>
        """, unsafe_allow_html=True)

    elif df is not None and df.empty:
        st.error("Le fichier Excel chargé est vide ou la feuille 'Site' est vide.")

else:
    # Message d'attente stylisé
    st.markdown("""
    <div style='text-align: center; color: #666; margin-top: 50px;'>
        En attente du fichier Excel...
   
    """, unsafe_allow_html=True)

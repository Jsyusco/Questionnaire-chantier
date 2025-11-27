import streamlit as st
import pandas as pd

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Visualisation Projets Simple", layout="centered")

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
    
    .data-card {
        background-color: #2d2d2d;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #404040;
        margin-bottom: 15px;
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
    }

    h1, h2 {
        color: #ffffff;
    }
    
    .label-text {
        font-size: 16px;
        font-weight: 600;
        color: #e0e0e0;
        margin-bottom: 8px;
    }
    
    .value-text {
        font-size: 15px;
        color: #b0b0b0;
        padding-bottom: 5px;
        border-bottom: 1px dotted #505050;
    }
    
    /* Cache menu et footer standard */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
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

st.markdown('<div class="form-container"><h1>Suivi de Déploiement</h1><p>Sélectionnez un site pour voir les détails instantanément.</p></div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Chargez votre fichier Excel", type=["xlsx"])

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None and not df.empty:
        col_intitule = df.columns[0]
        
        # --- SÉLECTION DU PROJET ---
        with st.container():
            st.markdown('<div class="form-container">', unsafe_allow_html=True)
            st.subheader("Sélection du Projet et Mode d'Affichage")
            
            # 1. Liste déroulante pour la sélection du projet
            options = df[col_intitule].unique().tolist()
            selected_project = st.selectbox("Site à consulter :", options)
            
            # 2. Sélecteur de mode d'affichage
            display_mode = st.radio(
                "Choisissez le mode d'affichage :",
                ('Indépendant (un bloc par colonne)', 'Condensé (un seul bloc)'),
                horizontal=True
            )
            
            st.markdown('</div>', unsafe_allow_html=True)

        # --- AFFICHAGE DES RÉSULTATS ---
        st.markdown(f'<div class="form-container"><h2>Détails du projet : {selected_project}</h2></div>', unsafe_allow_html=True)

        # Filtrer les données pour le projet sélectionné
        project_data = df[df[col_intitule] == selected_project].iloc[0]
        cols_to_display = df.columns[1:] 
        
        # --- MODE 1 : INDÉPENDANT (Plusieurs blocs) ---
        if display_mode == 'Indépendant (un bloc par colonne)':
            for col_name in cols_to_display:
                valeur = project_data[col_name]
                
                html_card = f"""
                <div class="data-card">
                    <div class="label-text">{col_name}</div>
                    <div class="value-text">{valeur}</div>
                </div>
                """
                st.markdown(html_card, unsafe_allow_html=True)

        # --- MODE 2 : CONDENSÉ (Un seul bloc) ---
        elif display_mode == 'Condensé (un seul bloc)':
            condensed_content =

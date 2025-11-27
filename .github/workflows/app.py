import streamlit as st
import pandas as pd

# --- MAPPAGE DES COLONNES ---
# Clé = Nom exact de la colonne dans le fichier Excel (à vérifier !)
# Valeur = Nom descriptif que l'utilisateur verra à l'écran
COLUMN_MAPPING = {
    'L [Plan de Déploiement]': 'Bornes Lentes',
    'R [Plan de Déploiement]': 'Bornes Rapides',
    'UR [Plan de Déploiement]': 'Bornes Ultra-rapides',
    'Pré L [Plan de Déploiement]': 'Pré-équipement Bornes Lentes',
    'Pré R [Plan de Déploiement]': 'Pré-équipement Bornes Rapides',
    'Pré UR [Plan de Déploiement]': 'Pré-équipement Bornes Ultra-rapides',
    'Fournisseur Bornes AC [Bornes]': 'Fournisseur Bornes AC',
    'Fournisseur Bornes DC [Bornes]': 'Fournisseur Bornes DC',
}

# --- CONFIGURATION ET STYLE ---
st.set_page_config(page_title="Visualisation Projets Mappée", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #121212; }
    .form-container {
        background-color: #1e1e1e;
        padding: 30px;
        border-radius: 12px;
        border-top: 8px solid #ffffff; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.5);
        margin-bottom: 20px;
        color: white;
    }
    .condensed-block {
        background-color: #2d2d2d;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #404040;
        margin-bottom: 15px;
        color: #e0e0e0;
        line-height: 1.6;
        white-space: pre-wrap;
    }
    h1, h2 { color: #ffffff; }
    #MainMenu, footer { visibility: hidden; }
    .stButton > button { background-color: #ffffff; color: #121212; border: none; font-weight: bold; }
    .stButton > button:hover { background-color: #e0e0e0; color: #000000; }
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

st.markdown('<div class="form-container"><h1>Suivi de Déploiement</h1><p>Veuillez charger votre fichier et sélectionner un site.</p></div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Chargez votre fichier Excel", type=["xlsx"])

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None and not df.empty:
        col_intitule = df.columns[0]
        
        # 1. SÉLECTION DU PROJET
        with st.container():
            st.subheader("Sélection du Site")
            
            options = df[col_intitule].unique().tolist()
            selected_project = st.selectbox("Site à consulter :", options)


        # 2. AFFICHAGE CONDENSÉ AVEC MAPPAGE
        st.markdown(f'<div class="form-container"><h2>Détails du projet : {selected_project}</h2></div>', unsafe_allow_html=True)

        project_data = df[df[col_intitule] == selected_project].iloc[0]
        
        # Construction du contenu condensé
        condensed_content = ""
        
        # On itère sur le dictionnaire de mappage (les clés sont les noms des colonnes Excel)
        for excel_col_name, display_label in COLUMN_MAPPING.items():
            
            # Vérifier que la colonne existe dans le DataFrame chargé
            if excel_col_name in project_data:
                valeur = project_data[excel_col_name]
                
                # Format d'affichage : Nom Lisible en gras : Valeur
                condensed_content += f"**{display_label}** : {valeur} \n" 
            else:
                # Ajouter une ligne d'erreur si la colonne est manquante
                 condensed_content += f"**{display_label}** : Colonne Excel '{excel_col_name}' introuvable. \n"

        # Affichage dans un grand bloc unique
        st.markdown(f"""
            <div class="condensed-block">
                {condensed_content}
            
        """, unsafe_allow_html=True)

    elif df is not None and df.empty:
        st.error("Le fichier Excel chargé est vide ou la feuille 'Site' est vide.")

else:
    st.markdown("""
    <div style='text-align: center; color: #666; margin-top: 50px;'>
        En attente du fichier Excel...
    </div>
    """, unsafe_allow_html=True)

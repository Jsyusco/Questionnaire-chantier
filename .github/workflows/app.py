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
    
    /* Pour Streamlit (barre de progression

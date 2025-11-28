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

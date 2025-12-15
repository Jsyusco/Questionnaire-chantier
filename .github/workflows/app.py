import pandas as pd
import streamlit as st

# --- SIMULATION DE VOTRE FONCTION DE CHARGEMENT ET NETTOYAGE ---

def debug_column_cleaning(df):
    """
    Simule la logique de nettoyage des colonnes et vérifie le type de chaque colonne
    pour identifier la source de l'AttributeError: 'DataFrame' object has no attribute 'str'.
    """
    st.write("### 🔎 Début de l'analyse des colonnes")
    
    # Simulez la liste des colonnes que vous essayez de nettoyer
    # Remplacez ceci par les vrais noms de colonnes qui pourraient nécessiter un nettoyage
    cols_to_clean = ['question', 'type', 'section', 'mandatory', 'condition', 'options'] 

    for col in cols_to_clean:
        if col in df.columns:
            st.write(f"--- Colonne : **{col}** ---")
            
            # 1. Vérification du type initial
            st.write(f"Type initial de la colonne : **{df[col].dtype}**")
            
            # 2. Vérification du type de l'objet indexé
            indexed_object = df[col]
            
            st.write(f"Type de l'objet df['{col}'] : **{type(indexed_object)}**")
            
            # POINT DE CONTRÔLE CRITIQUE: Si c'est un DataFrame, le code va planter ici.
            if isinstance(indexed_object, pd.DataFrame):
                st.error(f"⚠️ ERREUR DÉTECTÉE : L'objet indexé pour '{col}' est un DataFrame (et non une Series)!")
                st.warning("Action corrective : Vérifiez que 'col' est bien un *string* et non une *liste de strings* (ex: ['question']) dans le code appelant.")
                # st.dataframe(indexed_object) # Décommentez pour voir les données
                return
            
            # 3. Simulation de l'opération qui échoue (astype(str) doit d'abord se faire)
            try:
                # Simule l'échec pour cette colonne
                df[col] = df[col].astype(str).str.strip()
                st.success("✅ Opération `.str.strip()` réussie pour cette colonne.")
            except AttributeError as e:
                st.error(f"❌ Échec de l'opération pour '{col}' : {e}")
                st.warning("Cela confirme que l'objet `df[col]` n'est pas une Series de chaînes de caractères au moment de l'appel.")
                return

    st.write("### ✅ Analyse terminée. Aucune anomalie majeure de type 'DataFrame' detectée.")


# --- SIMULATION DES DONNÉES ENTRANTES ---

# 1. Scénario correct (Les colonnes sont des Series)
correct_data = {
    'question': [' Q1 ', ' Q2 '],
    'type': [' select ', ' photo ']
}
df_correct = pd.DataFrame(correct_data)


# 2. Scénario d'erreur (Simule un DataFrame à la place d'une Series)
# ATTENTION : La création d'un DataFrame avec un objet DataFrame dans une colonne n'est pas standard
# et est difficile à reproduire directement, car l'erreur est dans le code précédent qui a créé le DF.
# Nous allons simuler la cause la plus courante: une mauvaise indexation dans un code précédent.

# Si vous aviez un code comme df[['question']] = df['question'] à un moment,
# cela pourrait écraser la Series par un DataFrame.

# Pour l'analyse, nous allons nous concentrer sur la simulation correcte.
# Si vous exécutez ce code sur votre application:

# Remplacer cette ligne par votre chargement réel de Firestore :
# df_structure = utils.load_form_structure_from_firestore()

# Utilisons la simulation pour l'exemple :
df_structure = df_correct

# --- EXÉCUTION DE L'ANALYSE ---
debug_column_cleaning(df_structure.copy())

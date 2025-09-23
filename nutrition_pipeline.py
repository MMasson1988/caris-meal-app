"""
RAPPORT JARDINAGE - Script Python exécutable avec python {MODULE}.py
"""

import pandas as pd
import numpy as np
import os
import re
import time
import warnings
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import openpyxl
import xlsxwriter
import pymysql
from sqlalchemy import create_engine
from selenium import webdriver


print("="*60)
today_date = pd.to_datetime('today')
print(f"DEBUT DE LA PIPELINE DE NUTRITION à {today_date}")
print("="*60)


#=================================================================================================
def extraire_data(df, start_date, end_date, date_col):
    # Conversion des dates d'entrée
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Conversion de la colonne de date dans le DataFrame
    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    else:
        raise ValueError(f"Colonne '{date_col}' absente du DataFrame.")

    # Filtrage
    df = df[df[date_col].between(start_date, end_date)]

    return df
#=============================================
import pandas as pd

def clean_column_names(df, expr_to_remove):
    """
    Supprime une expression donnée au début des noms de colonnes d'un DataFrame.

    Args:
        df (pd.DataFrame): le dataframe cible
        expr_to_remove (str): l'expression à supprimer (ex: 'form.depistage.')

    Returns:
        pd.DataFrame: un DataFrame avec colonnes renommées
    """
    df = df.rename(columns=lambda col: col.replace(expr_to_remove, ""))
    return df
#========================================================================================
import pandas as pd

def create_binary_symptom_columns(df, col="symptoms"):
    """
    Transforme une colonne de type string en colonnes indicatrices binaires (0/1).
    - Si 'aucun' est présent avec d'autres modalités => on ignore 'aucun'.
    - Si 'aucun' est la seule modalité => on crée une colonne 'aucun'=1.
    
    Args:
        df (pd.DataFrame): le DataFrame source
        col (str): nom de la colonne contenant les modalités séparées par espaces

    Returns:
        pd.DataFrame: DataFrame avec colonnes indicatrices ajoutées
    """
    # Créer une liste de sets de symptômes par ligne
    df[col] = df[col].fillna("").str.lower()
    df[col] = df[col].str.strip()
    df[col] = df[col].str.split()

    # Extraire toutes les modalités distinctes
    all_modalities = set(mod for mods in df[col] for mod in mods)

    # On retire 'aucun' provisoirement
    if "aucun" in all_modalities:
        all_modalities.remove("aucun")

    # Créer colonnes indicatrices pour chaque modalité (hors 'aucun')
    for mod in all_modalities:
        df[mod] = df[col].apply(lambda mods: 1 if mod in mods else 0)

    # Gérer la règle spéciale pour 'aucun'
    df["aucun"] = df[col].apply(lambda mods: 1 if mods == ["aucun"] else 0)

    return df
#============================================================================
def get_age_in_year(df, dob_col):
    """
    Calcule l'âge en années pour chaque ligne d'un DataFrame où la colonne date de naissance n'est pas NaN.
    
    Args:
        df (pd.DataFrame): le DataFrame d'entrée
        dob_col (str): nom de la colonne contenant la date de naissance
        
    Returns:
        pd.DataFrame: DataFrame avec une nouvelle colonne 'age_years'
    """
    # Faire une copie du DataFrame pour éviter les modifications sur l'original
    df_copy = df.copy()
    
    # Vérifier que la colonne existe
    if dob_col not in df_copy.columns:
        raise ValueError(f"Colonne '{dob_col}' absente du DataFrame.")
    
    # Convertir la colonne date de naissance en datetime
    df_copy[dob_col] = pd.to_datetime(df_copy[dob_col], errors='coerce')
    
    # Calculer l'âge seulement là où dob_col n'est pas NaN
    today = pd.Timestamp.now()
    
    # Créer la colonne age_years avec des NaN par défaut
    df_copy['age_years'] = pd.NaT
    
    # Calculer l'âge seulement pour les lignes où date de naissance n'est pas NaN
    mask = df_copy[dob_col].notna()
    df_copy.loc[mask, 'age_years'] = (
        (today - df_copy.loc[mask, dob_col]).dt.days / 365.25
    ).round(0)
    df_copy['age_years'] = df_copy['age_years'].fillna(0).astype(int)
    return df_copy
#=====================================================================
import pandas as pd

def create_normalized_health_index(df):
    """
    Crée un indice pondéré et normalisé (0-10) basé sur symptômes et variables nutritionnelles,
    puis ajoute une catégorisation de risque.
    """

    # Pondération malnutrition
    df["malnutrition_score"] = df["manutrition_type"].map(
        {"MAM": 2, "MAS": 4}
    ).fillna(0)

    # Pondération diarrhée
    df["diarrhea_score"] = df["diarrhea"].map(
        {"yes": 3, "no": 0}
    ).fillna(0)

    # Pondération oedème
    df["oedem_score"] = df["edema"].map(
        {"yes": 5, "no": 0}
    ).fillna(0)
    
        # Pondération oedème
    df["lesion_cutane_score"] = df["lesion_cutane"].map(
        {"yes": 3, "no": 0}
    ).fillna(0)

    # Score brut pondéré
    df["health_index_raw"] = (
        df["toux"] * 1 +
        df["fievre"] * 2 +
        df["douleurs_abdominales"] * 2 +
        df["vomissements"] * 2 +
        df["malnutrition_score"] +
        df["diarrhea_score"] +
        df["oedem_score"]+
        df["lesion_cutane_score"]
    )

    # Maximum théorique possible
    max_score = 22
    df["health_index_norm"] = (df["health_index_raw"] / max_score) * 10

    # Catégorisation
    def categorize(score):
        if score <= 3.0:
            return "Faible risque"
        elif score <= 6.0:
            return "Risque modéré"
        else:
            return "Haut risque"

    df["risk_category"] = df["health_index_norm"].apply(categorize)

    return df
# df[["toux","fievre","vomissement","manutrition_type","edema","lesion_cutane","diarrhea","douleurs_abdominales","health_index_raw","health_index_norm","risk_category"]]

#========================================================================================================================
today_str = datetime.today().strftime('%Y-%m-%d')
enroled = pd.read_excel(f"~/Downloads/caris-meal-app/data/Nutrition (created 2025-04-25) {today_str}.xlsx",
                          parse_dates=True)
enroled_col = [
    "caseid", "name", "eligible", "manutrition_type", "date_of_birth",
    "gender", "muac", "nbr_visit", "is_alive", "death_date",
    "death_reason", "nbr_visit_succeed", "admission_muac", "office", "commune",
    "departement", "household_collection_date", "household_number", "has_household", "closed",
    "closed_date", "last_modified_date", "opened_date", "case_link", "enrollement_date_de_visite",
    "enrollment_date", "enrollment_eligibility", "enrollment_manutrition_type", "is_enrolled", "hiv_test_done",
    "hiv_test_result", "club_id", "club_name"
]
enroled = enroled[enroled_col]
print(f"Fichier enrollement Télechargé avec {enroled.shape[0]} lignes")
#=======================================================================================================================
depistage = pd.read_excel(f"~/Downloads/caris-meal-app/data/Caris Health Agent - NUTRITON[HIDDEN] - Dépistage Nutritionnel (created 2025-06-26) {today_str}.xlsx",
                          parse_dates=True)
dep_col = [
    "form.depistage.date_de_visite", "form.depistage.last_name", "form.depistage.first_name", "form.depistage.gender",
    "form.depistage.date_of_birth", "form.depistage.muac", "form.depistage.weight_kg", "form.depistage.height",
    
    "form.depistage.edema", "form.depistage.lesion_cutane", "form.depistage.diarrhea", "form.depistage.autres_symptomes",
    "form.depistage.phone_number", "form.depistage.photo_depistage", "form.depistage.office", "form.depistage.departement",
    
    "form.depistage.commune", "form.depistage.date_de_depistage", "form.depistage.fullname", "form.depistage.eligible",
    "form.depistage.manutrition_type", "form.case.@case_id", "completed_time", "started_time",
    
    "username", "received_on", "form_link"
]
depistage = depistage[dep_col]
print(f"dépistage télechargés avec {depistage.shape[0]} lignes")
#========================================================================================================================
#Caris Health Agent - NUTRITON[HIDDEN] - Dépistage Nutritionnel (created 2025-06-26) 2025-09-23

depistage = clean_column_names(depistage, expr_to_remove='form.depistage.')
end_date_week = pd.to_datetime('today')
# Date de début = 7 jours avant
start_date_week = end_date_week - timedelta(days=7)

start_date = pd.Timestamp("2025-05-01")
end_date = pd.Timestamp(datetime.today().date())

print("=== Nombre depistage pour la semaine ===")
depistage_week = extraire_data(df=depistage, start_date=start_date_week, end_date=end_date_week, date_col='date_de_visite')
print(f"{depistage_week.shape[0]} dépistage réalisés pour la semaine")
print("=== Nombre depistage de mai 2025 à aujourd'hui ===")
depistage_nut = extraire_data(df=depistage, start_date=start_date, end_date=end_date, date_col='date_de_visite')
print(f"{depistage_nut.shape[0]} dépistage réalisés pour la periode")
depistage_nut.to_excel("depistage_nutritionel.xlsx", sheet_name="Mai_a_aujourdhui", index=False)
#===============================================================================================
depistage_index=create_binary_symptom_columns(depistage_nut, 'autres_symptomes')
depistage_index.to_excel("depistage_index.xlsx", sheet_name="index", index=False)

# Ajouter l'âge au DataFrame de dépistage
depistage_nut = get_age_in_year(depistage_nut, 'date_of_birth')
print(f"Colonne âge ajoutée. Échantillon:")
print(depistage_nut[['date_of_birth', 'age_years']].head())

depistage_indice = create_normalized_health_index(depistage_nut)
depistage_indice.to_excel("depistage_indice.xlsx", sheet_name="indice", index=False)

# Vous pouvez aussi l'appliquer au DataFrame enroled
#enroled = get_age_in_year(enroled, 'date_of_birth')
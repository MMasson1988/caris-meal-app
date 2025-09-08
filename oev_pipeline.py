# Standard library imports
import os
import re
import time
import warnings
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse

# Third-party imports
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import openpyxl
import xlsxwriter
import pymysql
from sqlalchemy import create_engine
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
# import functions
from utils import get_commcare_odata
# Download charges virales database from "Charges_virales_pediatriques.sql file"
from caris_fonctions import execute_sql_query



# ========== FILTRAGE OEV ==========
def filter_oev_data(df):
    print(f"Initial dataset: {df.shape[0]} rows")
    df = df[~df['office'].isin(['BOM', 'PDP'])]
    df = df[~df['network'].isin(['PIH', 'UGP', 'MSPP'])]
    df['age'] = pd.to_numeric(df['age'], errors='coerce')
    df = df[df['age'].between(0, 17)]

    sites_to_exclude = ['PAP/CHAP', 'PAP/OBCG', 'PAP/OGRE', 'PEG/HNDP', 'PAP/SMFO', 'LEG/HSCL', 'PAP/HAHD', 'ARC/SADA']
    df = df[~df['site'].isin(sites_to_exclude)]

    df['is_abandoned'] = pd.to_numeric(df['is_abandoned'], errors='coerce')
    df = df[df['is_abandoned'] != 1]


    df = df.drop_duplicates(subset='patient_code', keep='last')

    print(f"Filtered dataset: {df.shape[0]} rows")
    df.to_excel("TX_CURR.xlsx", index=False)
    return df


# ========== ANALYSE CLUB ==========
def filter_by_age_club(df, age_column, age_club):
    df[age_column] = pd.to_numeric(df[age_column], errors='coerce')
    df = df[df[age_column].isin(age_club)]
    df = df[df['club_type'].isin(['club_9_12', 'club_13_17'])]
    return df[['site', 'office', 'patient_code', 'age', 'sex', 'club_type',
               'took_viral_load_test', 'indetectable_ou_inf_1000',
               'last_viral_load_collection_date', 'arv_start_date', 'viral_load_date']]


def process_age_ranges(df, age_column='age'):
    df[age_column] = pd.to_numeric(df[age_column], errors='coerce')

    def age_range(age):
        if pd.isna(age): return None
        if age < 1: return '< 1'
        if age < 5: return '1 - 4'
        if age < 10: return '5 - 9'
        if age < 15: return '10 - 14'
        if age < 18: return '15 - 17'
        if age < 21: return '18 - 20'
        return '21+'

    df['age_range'] = df[age_column].map(age_range)
    order = ['< 1', '1 - 4', '5 - 9', '10 - 14', '15 - 17']
    df['age_range'] = pd.Categorical(df['age_range'], categories=order, ordered=True)
    return df[['site', 'office', 'patient_code', 'age', 'sex', 'club_type',
               'took_viral_load_test', 'indetectable_ou_inf_1000',
               'last_viral_load_collection_date', 'arv_start_date', 'viral_load_date']]


# ========== MAIN ==========
def main():
    # Étape 1 : Téléchargement du fichier depuis CommCare
    #download_case_data()

    # Étape 2 : Charger le fichier téléchargé
    today_str = datetime.today().strftime('%Y-%m-%d')
    path = f"C:\\Users\\moise\\caris-app\\caris-dashboard-app\\data\\All_child_PatientCode_CaseID {today_str}.xlsx"

    # Ou encore mieux, utiliser une structure plus flexible :
    base_path = "C:\\Users\\moise\\caris-app\\caris-dashboard-app\\data"
    path = f"{base_path}\\All_child_PatientCode_CaseID {today_str}.xlsx"
    caseid = pd.read_excel(os.path.expanduser(path))

    # Étape 3 : Charger la base de données charges virales
    oev_data = execute_sql_query('dot.env', './Charges_virales_pediatriques.sql')

    # Étape 4 : Nettoyer les doublons
    oev_data = oev_data.loc[:, ~oev_data.columns.duplicated()]

    # Étape 5 : Filtrage
    filtered_df = filter_oev_data(oev_data)
    filtered_df['sex'] = filtered_df['sex'].str.replace('0', 'F').str.replace('3', 'F')

    # Étape 6 : Analyse club
    age_club = range(9, 18)
    age_in_club_now = filtered_df[filtered_df['age'].isin(age_club)]
    oev_in_club = filter_by_age_club(age_in_club_now, 'age', age_club)
    not_in_club = age_in_club_now[~age_in_club_now['patient_code'].isin(oev_in_club['patient_code'])]
    not_in_club_anymore = filtered_df[~filtered_df['age'].isin(age_club)]

    print(f"Total enfants: {filtered_df.shape[0]}")
    print(f"Âge club (9-17): {age_in_club_now.shape[0]}")
    print(f"En club: {oev_in_club.shape[0]}")
    print(f"Hors club: {not_in_club.shape[0]}")
    print(f"Hors catégorie (pas 9-17): {not_in_club_anymore.shape[0]}")
    oev_in_club.to_excel("oev_in_club.xlsx", index=False)
    print("DataFrame oev_in_club sauvegardé dans oev_in_club.xlsx")
    not_in_club.to_excel("oev_not_in_club.xlsx", index=False)
    print("DataFrame not_in_club sauvegardé dans oev_not_in_club.xlsx")
    filtered_df.to_excel('oev_data_final.xlsx', index=False)
    print("DataFrame final sauvegardé dans oev_data_final.xlsx")
    # ========== EXTRACTION AJOUT + CHILD ==========

    ajout_url = 'https://www.commcarehq.org/a/caris-test/api/odata/forms/v1/41b99d862f48b671c2b2880b6e2c4cea/feed'
    child_url = 'https://www.commcarehq.org/a/caris-test/api/odata/cases/v1/41b99d862f48b671c2b2880b6e2c74cb/feed'
    hh_child_url ='https://www.commcarehq.org/a/caris-test/api/odata/cases/v1/e7c7fb14a8fd38961090d420c3fb64c2/feed'
    auth = (os.getenv('CC_USERNAME'), os.getenv('CC_PASSWORD'))
    params = {}
    # Lire le fichier avec pd.read_excel

    # Extraction depuis CommCare OData
    ajout = pd.DataFrame(get_commcare_odata(ajout_url, auth, params))
    child = pd.DataFrame(get_commcare_odata(child_url, auth, params))
    hh_child = pd.DataFrame(get_commcare_odata(hh_child_url, auth, params))

    # Nettoyage des colonnes
    ajout.columns = ajout.columns.str.replace(' ', '_').str.replace('form_', '', regex=False)
    ajout.rename(columns={'case_case_id': 'caseid'}, inplace=True)
    # Assurez-vous que les DataFrames ont bien la colonne 'caseid'
    if 'caseid' not in caseid.columns:
        print("❌ Colonne 'caseid' non trouvée dans le DataFrame 'caseid'.")
    if 'caseid' not in ajout.columns:
        print("❌ Colonne 'caseid' non trouvée dans le DataFrame 'ajout'.")

    # Fusion des données avec contrôle et affichage
    ajout_comptage = pd.merge(oev_in_club, caseid, on='patient_code', how='left').drop_duplicates('patient_code').fillna(0)
    
    print(f"✅ Le jeu de données fusionné comptage_ajout contient {ajout_comptage.shape[0]} observations.")
    ajout_comptage.to_excel("ajout_comptage.xlsx", index=False)


    child.columns = child.columns.str.replace(' ', '_')
    hh_child.columns = [col.replace(' ', '_') for col in hh_child.columns]
    hh_child = hh_child.drop(columns=['patient_code'], errors='ignore')
    # Rename column in hh_child DataFrame
    hh_child.rename(columns={'main_infant_code': 'patient_code'}, inplace=True)
    hh_child.to_excel("hh_child.xlsx", index=False)
    hh_child = hh_child[['first_name', 'last_name','name',
    'age_in_year', 'caregiver_yes_no', 'caseid', 'dob', 'full_code_patient_menage',
    'gender', 'hiv_test', 'hiv_test_date', 'hiv_test_result',
    'household_collection_date', 'indices_child', 'infant_relationship',
    'is_accepted', 'is_caris_beneficiary', 'last_modified_date',
    'patient_code', 'non_consent_reason', 'not_accepted_reason',
    'opened_by_username', 'opened_date']]
    
    print(f'This hh_child Household dataset has {hh_child.shape[0]} observations')

    print(f"This Household dataset has {ajout.shape[0]} observations")
    print(f"This Child dataset has {child.shape[0]} observations")

    # Merge des deux
    merged_df_ajout_child = pd.merge(ajout, child, on='caseid', how='left')
    merged_df_ajout_child = merged_df_ajout_child.drop_duplicates(subset='caseid').fillna(0)
    print(f"The merged dataset has {merged_df_ajout_child.shape[0]} observations")

    # Sauvegarde
    ajout.to_excel("new_ajout.xlsx", index=False)

    # Comptage des OEV en club avec ou sans ajout dans CommCare
    oev_avec_comptage = oev_in_club[
        oev_in_club['patient_code'].str.lower().isin(merged_df_ajout_child['patient_code'].astype(str).str.lower())
    ].drop_duplicates('patient_code', keep='first')
    oev_avec_comptage['patient_code'] = oev_avec_comptage['patient_code'].str.upper()
    print(f"OEV avec comptage: {oev_avec_comptage.shape[0]}")

    oev_sans_comptage = oev_in_club[
        ~oev_in_club['patient_code'].str.lower().isin(merged_df_ajout_child['patient_code'].astype(str).str.lower())
    ].drop_duplicates('patient_code', keep='first')
    oev_sans_comptage['patient_code'] = oev_sans_comptage['patient_code'].str.upper()
    print(f"OEV sans comptage: {oev_sans_comptage.shape[0]}")

    oev_avec_comptage.to_excel("oev_avec_comptage.xlsx", index=False)
    oev_sans_comptage.to_excel("oev_sans_comptage.xlsx", index=False)
    
    hhm_club = hh_child[hh_child['patient_code'].str.lower().isin(oev_in_club['patient_code'].str.lower())]
    hhm_club['patient_code'] = hhm_club['patient_code'].str.upper()
    hhm_club.to_excel('hhm_club.xlsx', index=False)

if __name__ == "__main__":
    main()
    print("✅ Pipeline exécuté avec succès.")

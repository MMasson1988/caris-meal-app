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

# In[2]:
from utils import get_commcare_odata
from ptme_fonction import creer_colonne_match_conditional
# In[3]:

def filter_ptme_data(
    df,
    excluded_offices=['BOM', 'PDP'],
    excluded_networks=['PIH', 'UGP', 'MSPP'],
    excluded_site=['GON/CSAR'],# à ajouter dans la base de données des sites fermés
    excluded_term=['Miscarriage'], # Exclude specific termination reasons
    abandoned_flag=1,
    next_appointment_start='2025-05-01',
    output_file='filtered_df2.xlsx'):
    print(f"Initial dataset has {df.shape[0]} observations")

    # Exclude specified offices
    df = df[~df['office'].isin(excluded_offices)]
    print(f"After excluding offices: {df.shape[0]} observations")

    # Exclude specified networks
    df = df[~df['network'].isin(excluded_networks)]
    print(f"After excluding networks: {df.shape[0]} observations")
    
    # Exclude specified networks
    df = df[~df['network'].isin(excluded_site)]
    print(f"After excluding networks: {df.shape[0]} observations")
    
    # Exclude specified networks
    df = df[~df['network'].isin(excluded_term)]
    print(f"After excluding networks: {df.shape[0]} observations")

    # Convert 'is_abandoned' to numeric and exclude abandoned
    df['is_abandoned'] = pd.to_numeric(df['is_abandoned'], errors='coerce')
    df = df[df['is_abandoned'] != abandoned_flag]
    print(f"After excluding abandoned: {df.shape[0]} observations")

    df = df[~df['site'].str.lower().isin(site_ferme['site'].str.lower())]
    df['site'] = df['site'].str.upper()
    print(f"After excluding closed site: {df.shape[0]} observations")
    # Export to Excel
    df.to_excel(output_file, index=False)
    print(f"Filtered data exported to {output_file}")

    return df


# #### **DOWNLOAD DATABASES**

# In[4]:
pregnancy_url ='https://www.commcarehq.org/a/caris-test/api/odata/cases/v1/8d0dd8d8adef91a238920cad1db6cfd1/feed'
# Define the headers for the request
auth = (os.getenv('CC_USERNAME'), os.getenv('CC_PASSWORD'))
# Define parameters to filter inactive, non-graduated groups
params = {}
pregnancy_woman = get_commcare_odata(pregnancy_url, auth, params)
pregnancy_woman = pd.DataFrame(pregnancy_woman)
pregnancy_woman.columns = [col.replace(' ', '_') for col in pregnancy_woman.columns]
print(f'This Household dataset has {pregnancy_woman.shape[0]} observations')
pregnancy_woman.head(2)


# In[5]:


pregnancy_woman = pregnancy_woman[[
    'birth_place_plan',
    'case_link',
    'caseid',
    'club_name',
    'date_of_visit',
    'date_of_visit_ratio_other',
    'ddr',
    'delivery_date',
    'dpa',
    'health_id',
    'household_collection_date',
    'household_number',
    'id_patient',
    'is_benficiary_present_ratio_other',
    'is_currently_pregnant',
    'is_this_girl_belong_to_a_club',
    'last_modified_by_user_username',
    'last_modified_date',
    'mobile_phone_number',
    'mother_phone_number',
    'mother_plans_to_get_child_tested',
    'mother_secondary_number',
    'mother_secondary_phone_number',
    'nbr_call'
]]
pregnancy_woman.rename(columns={'health_id': 'patient_code'}, inplace=True)
pregnancy = pregnancy_woman[pregnancy_woman['household_collection_date'] != "---"]
pregnancy.shape[0]


# ## **1. STATISTIQUES SUR LES FEMMES ENCEINTES**

# In[6]:


# Download charges virales database from "Charges_virales_pediatriques.sql file"
from caris_fonctions import execute_sql_query
env_path = 'dot.env'
sql_file_path = './PTME_Enceinte.sql'

ptme_enceinte = execute_sql_query(env_path, sql_file_path)
duplicates = ptme_enceinte.columns[ptme_enceinte.columns.duplicated()].tolist()
if duplicates:
    print("Attention : des colonnes en double ont été trouvées dans le DataFrame.")
    print("Colonnes en double :", duplicates)
else:
    print("Aucune colonne en double trouvée dans le DataFrame.")
# print the shape of the DataFrame
print(ptme_enceinte.shape[0])
# print the first few rows of the DataFrame
print(ptme_enceinte.head(2))


# In[7]:


env_path = 'dot.env'
sql_file_path = './Mastersheet PTME.sql'

ptme = execute_sql_query(env_path, sql_file_path)
duplicates = ptme.columns[ptme.columns.duplicated()].tolist()
if duplicates:
    print("Attention : des colonnes en double ont été trouvées dans le DataFrame.")
    print("Colonnes en double :", duplicates)
else:
    print("Aucune colonne en double trouvée dans le DataFrame.")
ptme.rename(columns={'mother_patient_code':'patient_code'}, inplace=True)
# print the shape of the DataFrame
print(ptme.shape[0])
# print the first few rows of the DataFrame
print(ptme.head(2))


# Conversion des colonnes en datetime
ptme['DPA_calculated'] = pd.to_datetime(ptme['DPA_calculated'], errors='coerce')
ptme['actual_delivery_date'] = pd.to_datetime(ptme['actual_delivery_date'], errors='coerce')

# Définir les bornes de date
start_date = pd.to_datetime("2024-01-01")
end_date = pd.to_datetime(datetime.today().date())

# Filtrer selon les critères
delinquency = ptme[
    (ptme['DPA_calculated'].between(start_date, end_date)) &
    (ptme['actual_delivery_date'].isna()) &
    (ptme['termination_of_pregnancy_reason'].isna()) &
    (ptme['is_actually_in_club'].str.lower() == 'yes')
]

# Nombre de cas trouvés
delinquency.shape[0]
delinquency.to_excel("delinquency.xlsx", index=False)


# In[8]:


mapping_p = {'both': 'yes', 'left_only': 'no'}
woman_in_ptme = creer_colonne_match_conditional(ptme_enceinte, ptme, on='patient_code', nouvelle_colonne='woman_found', mapping=mapping_p).drop_duplicates('patient_code', keep = 'first')
woman_in_ptme.shape[0]
print(woman_in_ptme['woman_found'].value_counts())
woman_ptme = woman_in_ptme[woman_in_ptme['woman_found']=="yes"]
woman_not_ptme = woman_in_ptme[woman_in_ptme['woman_found']=="no"]
print(f'{woman_ptme.shape[0]} femmes enceintes font parti du Programme PTME pour cette periode')
print(f"{woman_not_ptme.shape[0]} femmes à retrouver")



# In[9]:


site_ferme = pd.read_excel('sites_fermés.xlsx', engine='openpyxl')
# Ensure 'site' column is in uppercase for consistency
site_ferme.rename(columns={'site_code': 'site'}, inplace=True)
site_ferme['site'] = site_ferme['site'].str.upper()

ptme_enceinte = ptme[ptme['patient_code'].str.lower().isin(ptme_enceinte['patient_code'].str.lower())]
ptme_enceinte['patient_code'] = ptme_enceinte['patient_code'].str.upper()


# In[10]:


ptme_enceinte = filter_ptme_data(ptme_enceinte)

delinquency = filter_ptme_data(delinquency)
delinquency.to_excel("delinquency.xlsx",index=True)

# In[ ]:


# Assure-toi que les colonnes patient_code existent dans ptme et ptme_enceinte avant
ptme_enceinte = ptme[ptme['patient_code'].str.lower().isin(ptme_enceinte['patient_code'].str.lower())].copy()

# Mets patient_code en majuscules
ptme_enceinte['patient_code'] = ptme_enceinte['patient_code'].str.upper()
ptme_enceinte['club_session_date'] = ptme_enceinte['club_session_date'].fillna('---')

# Crée la colonne is_in_club selon les conditions
ptme_enceinte["is_in_club"] = np.where(
    (ptme_enceinte["is_actually_in_club"] == "yes") | 
    (ptme_enceinte["in_club"] == "yes"), # attention, comparaison à chaîne vide
    "yes",
    "no"
)

# DataFrames filtrés selon la présence dans le club
woman_in_club = ptme_enceinte[
    (ptme_enceinte['is_actually_in_club'] == "yes") | 
    (ptme_enceinte['in_club'] == "yes")
]
ptme_not_in_club = ptme_enceinte[~ptme_enceinte['patient_code'].str.lower().isin(woman_in_club['patient_code'].str.lower())]
ptme_not_in_club['patient_code'] = ptme_not_in_club['patient_code'].str.upper()
print(f'{woman_in_club.shape[0]} femmes enceintes font partie du Programme PTME pour cette période')
print(f'{ptme_not_in_club.shape[0]} femmes non en club')

# Affiche la distribution des valeurs dans la nouvelle colonne
print(ptme_enceinte["is_in_club"].value_counts())


# In[12]:


ptme_enceinte.to_excel('ptme_enceinte.xlsx', index=False)
woman_in_club.to_excel('woman_in_club.xlsx', index=False)
ptme_not_in_club.to_excel('ptme_not_in_club.xlsx', index=False)


# ##### **COMPTAGE DE MENAGE**

# In[21]:


# file_path_patient = first_part + 'PTME WITH PATIENT CODE ' + datetime.now().strftime("%Y-%m-%d") + ".xlsx"
    # Étape 2 : Charger le fichier téléchargé
today_str = datetime.today().strftime('%Y-%m-%d')
# path = f"~/Downloads/caris-dashboard-app/data/PTME WITH PATIENT CODE {today_str}.xlsx"
path = f"C:\\Users\\moise\\caris-app\\caris-dashboard-app\\data\\PTME WITH PATIENT CODE {today_str}.xlsx"
# Ou encore mieux, utiliser une structure plus flexible :
base_path = "C:\\Users\\moise\\caris-app\\caris-dashboard-app\\data"
path = f"{base_path}\\PTME WITH PATIENT CODE {today_str}.xlsx"

caseid = pd.read_excel(os.path.expanduser(path))
caseid = caseid.rename(columns={
    'caseid': 'case_id',
    'health_id': 'patient_code'
})
print(caseid.shape[0])
print(caseid.head(2))


# In[24]:


ajout_url ='https://www.commcarehq.org/a/caris-test/api/odata/forms/v1/9387f1f8311bcc699a02ef3c47780a38/feed'
# Define the headers for the request
auth = (os.getenv('CC_USERNAME'), os.getenv('CC_PASSWORD'))
# Define parameters to filter inactive, non-graduated groups
params = {}
ajout = get_commcare_odata(ajout_url, auth, params)
ajout = pd.DataFrame(ajout)
ajout.columns = [col.replace(' ', '_') for col in ajout.columns]
# Assuming 'df' is your DataFrame
ajout.columns = ajout.columns.str.replace('form_', '', regex=False)
print(f'This dataset dataset has {ajout.shape[0]} observations')
ajout.head(1)


# In[28]:


ajout.rename(columns={'case_case_id': 'caseid'}, inplace=True)
caseid.rename(columns={'case_id': 'caseid'}, inplace=True)
ajout.rename(columns={'full_code_patient_menage': 'patient_code'}, inplace=True)


# In[17]:


ajout.to_excel('ajout.xlsx', index = False)


# In[30]:


merged_df_ajout_child = pd.merge(ajout, caseid[['caseid', 'patient_code']], on='caseid', how='left', suffixes=('_x', '_y')).drop_duplicates('caseid').fillna(0)
print(f'The merged dataset has {merged_df_ajout_child.shape[0]} observations')
merged_df_ajout_child = merged_df_ajout_child.iloc[:, :-1]
merged_df_ajout_child.head(2)


# In[31]:


woman_in_club_with_casied = pd.merge(woman_in_club, caseid[['caseid', 'patient_code']], on='patient_code', how='left', suffixes=('_x', '_y')).drop_duplicates('patient_code').fillna(0)
print(f'The merged dataset has {woman_in_club_with_casied.shape[0]} observations')
woman_in_club_with_casied.head(2)


ptme_sans_comptage = woman_in_club[~woman_in_club['patient_code'].str.lower().isin(pregnancy['patient_code'].str.lower())]
ptme_sans_comptage['patient_code'] = ptme_sans_comptage['patient_code'].str.upper()
ptme_sans_comptage.shape[0]

ptme_sans_comptage.to_excel('ptme_sans_comptage.xlsx', index=False)


# In[36]:


ptme_avec_comptage = woman_in_club[woman_in_club['patient_code'].str.lower().isin(pregnancy['patient_code'].str.lower())]
ptme_avec_comptage['patient_code'] = ptme_avec_comptage['patient_code'].str.upper()
ptme_avec_comptage.shape[0]

# In[37]:


ptme_avec_comptage.to_excel('ptme_avec_comptage.xlsx', index=False)


# In[38]:


ptme_not_in_club.to_excel('ptme_not_in_club.xlsx', index=False)


# In[39]:


# In[40]:


comptage = pregnancy[pregnancy['patient_code'].str.lower().isin(woman_in_club['patient_code'].str.lower())]
comptage['patient_code'] = comptage['patient_code'].str.upper()

# Jointure interne sur le code patient en minuscules
ptme_enceinte_merge = pd.merge(
    pregnancy, 
    woman_in_club, 
    on='patient_code', 
    how='left', 
    suffixes=('_ptme', '_enceinte')
)

# (Optionnel) Supprimer la colonne intermédiaire
ptme_enceinte_merge.to_excel('ptme_enceinte_merge.xlsx', index=False)


# In[41]:


mapping_p = {'both': 'no', 'left_only': 'yes'}
comptage = creer_colonne_match_conditional(pregnancy, woman_in_club, on='patient_code', nouvelle_colonne='menage', mapping=mapping_p).drop_duplicates('patient_code', keep = 'first')
comptage.shape[0]
print(comptage['menage'].value_counts())
ptme_comptage_yes = comptage[comptage['menage']=="yes"]


# ##### **INDEX TESTING**

# In[42]:


hh_ptme_url ='https://www.commcarehq.org/a/caris-test/api/odata/cases/v1/ee225c4d8798c640f836403288aff52a/feed'
# Define the headers for the request
auth = (os.getenv('CC_USERNAME'), os.getenv('CC_PASSWORD'))
# Define parameters to filter inactive, non-graduated groups
params = {}
hh_ptme = get_commcare_odata(hh_ptme_url, auth, params)
hh_ptme = pd.DataFrame(hh_ptme)
hh_ptme.columns = [col.replace(' ', '_') for col in hh_ptme.columns]
print(f'This Household dataset has {hh_ptme.shape[0]} observations')
hh_ptme.head(2)


# In[43]:


hh_ptme = hh_ptme[['patient_code', 'age_in_year', 'ptme_relationship', 'full_code_patient_menage',
                          'hiv_test', 'hiv_test_result', 'caseid', 'non_consent_reason']]
hh_ptme['patient_code'] = hh_ptme['patient_code'].str.strip()
hh_ptme['age_in_year'] = pd.to_numeric(hh_ptme['age_in_year'], errors='coerce').fillna(0)
# Afficher les deux premières lignes
print(hh_ptme.shape[0])
print(hh_ptme.head(2))


# In[44]:


# Assure-toi que les colonnes patient_code existent dans ptme et ptme_enceinte avant
hh_depistage = hh_ptme[hh_ptme['patient_code'].str.lower().isin(woman_in_club['patient_code'].str.lower())]
# Mets patient_code en majuscules
hh_depistage.shape[0]


# In[45]:


hh_depistage.to_excel('hh_depistage.xlsx', index=False)


# In[46]:


# Assure-toi que les colonnes patient_code existent dans ptme et ptme_enceinte avant
ptme_depistage = woman_in_club[woman_in_club['patient_code'].str.lower().isin(hh_ptme['patient_code'].str.lower())].drop_duplicates('patient_code', keep = 'first')
# Mets patient_code en majuscules
ptme_depistage.shape[0]


# In[47]:


# Assure-toi que les colonnes patient_code existent dans ptme et ptme_enceinte avant
ptme_no_depistage = woman_in_club[~woman_in_club['patient_code'].str.lower().isin(hh_ptme['patient_code'].str.lower())].drop_duplicates('patient_code', keep = 'first')
# Mets patient_code en majuscules
ptme_no_depistage.shape[0]


# In[48]:


def plot_txcurr_by_office(df, title='🎯 TX_CURR: Number of Patients by Office'):
    """
    Affiche un graphique en barres horizontales du nombre de patients par bureau (office).

    Paramètres :
    - df : DataFrame contenant au moins les colonnes 'office' et 'patient_code'
    - title : Titre du graphique (optionnel)
    """
    # Regrouper et trier
    txcurr_by_office = df.groupby('office')['patient_code'].count().sort_values(ascending=True)

    # Couleurs
    colors = px.colors.qualitative.Plotly
    color_list = [colors[i % len(colors)] for i in range(len(txcurr_by_office))]

    # Création du graphique
    fig = go.Figure(go.Bar(
        x=txcurr_by_office.values,
        y=txcurr_by_office.index,
        orientation='h',
        marker=dict(
            color=color_list,
            line=dict(color='rgba(0,0,0,0.8)', width=1)
        ),
        text=txcurr_by_office.values,
        textposition='auto',
        textfont=dict(size=14, color='white'),
        hovertemplate='<b>%{y}</b><br>Patients: %{x}<extra></extra>'
    ))

    # Mise en page
    fig.update_layout(
        title=dict(
            text=title,
            x=0.5,
            xanchor='center',
            font=dict(size=22)
        ),
        xaxis=dict(
            title='Number of Patients',
            showgrid=False,
            zeroline=False
        ),
        yaxis=dict(
            title='Office',
            tickfont=dict(size=14, color='black'),
            showgrid=False,
            zeroline=False
        ),
        template='plotly_white',
        height=600,
        width=950,
        margin=dict(l=100, r=40, t=60, b=40)
    )

    fig.show()


# In[49]:


#plot_txcurr_by_office(ptme_enceinte, title="📊 Nombre de femmes enceintes par bureau")


# In[50]:


#plot_txcurr_by_office(woman_in_club, title="📊 Nombre de femmes enceintes actives en club par bureau")


# In[51]:


#plot_txcurr_by_office(ptme_not_in_club, title="📊 Nombre de femmes enceintes non en club par bureau")


# In[52]:


#plot_txcurr_by_office(ptme_with_no_comptage, title="📊 Nombre de femmes enceintes sans comptage par bureau")


# In[53]:


from datetime import date
import pandas as pd

def save_dataframes_excel(output_name="output", df1=None, df2=None, df3=None, df4=None, df5=None, df6=None, sheet_names=None):
    """
    Sauvegarde jusqu'à 6 DataFrames dans un fichier Excel avec un nom dynamique basé sur la date.

    Args:
        output_name (str): Nom de base du fichier de sortie (sans extension).
        df1, df2, df3, df4, df5, df6 (pd.DataFrame, optional): DataFrames à sauvegarder.
        sheet_names (list, optional): Liste des noms de feuilles.
    """
    # Définir une date pour le nom du fichier
    today_str = date.today().strftime("%Y-%m-%d")
    file_name = f"{output_name}_{today_str}.xlsx"

    # Définir les noms des feuilles si non fournis
    sheet_names = sheet_names or ['Sheet1', 'Sheet2', 'Sheet3', 'Sheet4', 'Sheet5', 'Sheet6']

    # Créer l'écrivain Excel
    writer = pd.ExcelWriter(file_name, engine='xlsxwriter')

    # Stocker les DataFrames dans une liste
    dfs = [df1, df2, df3, df4, df5, df6]

    # Écrire chaque DataFrame dans sa feuille correspondante s'il est défini
    for i, df in enumerate(dfs):
        if df is not None:
            df.to_excel(writer, sheet_name=sheet_names[i], index=False)

    # Sauvegarder le fichier Excel
    writer.close()
    print(f"Fichier '{file_name}' sauvegardé avec succès.")

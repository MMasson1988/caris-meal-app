#!/usr/bin/env python
# coding: utf-8

# In[2]:


# Standard library imports
import os
import re
import time
import warnings
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse

# Third-party imports
import pandas as pd
import numpy as np
import openpyxl
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import xlsxwriter
import pymysql
from sqlalchemy import create_engine
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv('dot.env')
pd.set_option('display.float_format', '{:.2f}'.format)  # Set float format

# Suppress warnings
warnings.filterwarnings('ignore')

# import personal functions
from utils import get_commcare_odata
from ptme_fonction import creer_colonne_match_conditional

# configure date
start_date = pd.to_datetime('2024-06-17')
end_date = pd.to_datetime('today')

# In[3]:

def plot_monthly_data(df, date_column, plot_title):
    """
    Generates a horizontal bar chart showing monthly counts of cases.
    Args:
        df: The pandas DataFrame containing the data.
        date_column: The name of the date column in the DataFrame.
        plot_title: The title of the plot.
    """
    df[date_column] = pd.to_datetime(df[date_column])
    df['Month'] = df[date_column].dt.strftime('%B %Y')
    monthly_counts = df.groupby('Month')['case_id'].count().reset_index()
    months_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    monthly_counts['Month'] = pd.Categorical(monthly_counts['Month'], categories=[f'{month} {year}' for year in sorted(monthly_counts['Month'].str.split(' ').str[1].unique()) for month in months_order if f'{month} {year}' in monthly_counts['Month'].unique()], ordered=True)
    monthly_counts = monthly_counts.sort_values(by='Month')
    plt.figure(figsize=(14, 10))
    colors = list(mcolors.TABLEAU_COLORS.values())
    bars = plt.barh(monthly_counts['Month'], monthly_counts['case_id'], color=colors[:len(monthly_counts)])
    for bar in bars:
        width = bar.get_width()
        label_x_pos = width + 0.5
        label_y_pos = bar.get_y() + bar.get_height() / 2
        plt.text(label_x_pos, label_y_pos, int(width), va='center', ha='left', fontsize=12, weight='bold') # Set fontsize and weight

    plt.title(plot_title)
    plt.tight_layout()
    plt.gca().grid(False) # Remove gridlines
    plt.show()


# In[4]:

def plot_beneficiaries_by_categorie(df, lo_department, set_title, set_xlabel, set_ylabel):
    # Configurer le style et la taille du graphique
    sns.set(rc={'figure.figsize': (18.27, 11.7)})  # Taille du graphique
    sns.set_style("whitegrid")                     # Style de Seaborn
    sns.set_context("talk")                        # Contexte adapté pour les présentations

    # Trier les données par nombre de bénéficiaires actifs en ordre décroissant
    sorted_data = df.groupby(lo_department).size().sort_values(ascending=False)
    sorted_df = sorted_data.reset_index(name='count')  # Réinitialiser l'index pour un tracé correct

    # Calculer le total des patients actifs
    total_active_patients = sorted_df['count'].sum()

    # Créer une palette de couleurs personnalisée
    n_colors = len(sorted_df)
    palette = sns.color_palette("husl", n_colors=n_colors) # Use husl for better color perception

    # Créer le graphique en barres avec la palette de couleurs
    ax = sns.barplot(y=lo_department, x='count', data=sorted_df, palette=palette)

    # Ajouter le titre et les étiquettes des axes
    ax.set_title(f"{set_title}\nTotal : {total_active_patients}")
    ax.set_xlabel(set_xlabel)
    ax.set_ylabel(set_ylabel)

    # Désactiver les lignes de la grille pour un rendu propre
    ax.grid(False)

    # Ajouter des étiquettes sur chaque barre
    for container in ax.containers:
        ax.bar_label(container)

    # Supprimer les bordures inutiles
    sns.despine()

    # Afficher le graphique
    plt.show()


# In[5]:

#Connecting to Commcare
load_dotenv('id_cc.env')
email = os.getenv('EMAIL')
password_cc = os.getenv('PASSWORD')
#Defining the driver
options = Options()
options.add_argument("start-maximized")
driver = webdriver.Chrome(options=options)
driver.implicitly_wait(1000)

#Creating login function
def commcare_login():
    driver.get(
        'https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/e557b6395b29e531d920e3dcd48028a4/'
    )
    driver.find_element("xpath", '//*[@id="id_auth-username"]').send_keys(email)
    driver.find_element("xpath", '//*[@id="id_auth-password"]').send_keys(password_cc)
    driver.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()

commcare_login()

#Download the database "Household child"
driver.find_element("xpath", '//*[@id="download-export-form"]/form/div[2]/div/div[2]/div[1]/button/span[1]').click()
driver.find_element("xpath", '//*[@id="download-progress"]/div/div/div[2]/div[1]/form/a/span[1]').click()

# wait for the download to complete and close the browser
time.sleep(10)
# Close the browser
driver.quit()


# In[10]:


#Connecting to Commcare
load_dotenv('id_cc.env')
email = os.getenv('EMAIL')
password_cc = os.getenv('PASSWORD')
#Defining the driver
options = Options()
options.add_argument("start-maximized")
driver = webdriver.Chrome(options=options)
driver.implicitly_wait(1000)

#Creating login function
def commcare_login():
    driver.get(
        'https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/a6a53d717d2d0bcb0724ae93a3cbfd9f/'
    )
    driver.find_element("xpath", '//*[@id="id_auth-username"]').send_keys(email)
    driver.find_element("xpath", '//*[@id="id_auth-password"]').send_keys(password_cc)
    driver.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()

commcare_login()

#Download the database "Household child"
driver.find_element("xpath", '//*[@id="download-export-form"]/form/div[2]/div/div[2]/div[1]/button/span[1]').click()
driver.find_element("xpath", '//*[@id="download-progress"]/div/div/div[2]/div[1]/form/a/span[1]').click()

# wait for the download to complete and close the browser
time.sleep(10)
# Close the browser
driver.quit()


# In[11]:


#Importing household nut file
h_nut_0 = pd.read_excel('~/Downloads/household_nutrition (created 2025-06-25) ' + str(datetime.today().strftime('%Y-%m-%d')) + '.xlsx', 
                    sheet_name = 'Cases'
                    , parse_dates = True)

# rename the column
h_nut_0['number_1'] = h_nut_0['number']
h_nut_0.rename(columns = {'number' : 'number_x'}, inplace = True)
#https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/a6a53d717d2d0bcb0724ae93a3cbfd9f/


# In[12]:


#Importing household nut file
h_nut_lookup = pd.read_excel('~/Downloads/household_nutrition (created 2025-06-25) ' + str(datetime.today().strftime('%Y-%m-%d')) + '.xlsx', 
                    sheet_name = 'Parent Cases'
                    , parse_dates = True)
# rename the column
h_nut_lookup['number'] = pd.to_numeric(h_nut_lookup['number'], errors='coerce').astype('Int64')
h_nut_lookup.rename(columns = {'number__0' : 'number_x'}, inplace = True)
h_nut_lookup.rename(columns = {'parent_case_id' : 'case_id'}, inplace = True)
# selected only 2 relevant columns
h_nut_lookup = h_nut_lookup [['number_x', 'case_id','number']]


# In[13]:


h_nut = h_nut_0.merge(h_nut_lookup, on = 'number_x', how = 'left')

# In[14]:

nutrition_case = pd.read_excel(f"~/Downloads/Nutrition (created 2025-04-25) {str(datetime.today().strftime('%Y-%m-%d'))}.xlsx", parse_dates = True)

# In[15]:

print(f'This nutrition case dataset has {nutrition_case.shape[0]} observations')

# In[16]:

#nut_depistage.rename(columns = {'sexe':'gender'}, inplace = True)
#Replacing code by true gender values
nutrition_case.loc[(nutrition_case.gender == 'M'), 'gender'] = 'Male'
nutrition_case.loc[(nutrition_case.gender == 'm'), 'gender'] = 'Male'
nutrition_case.loc[(nutrition_case.gender == 'f'), 'gender'] = 'Female'
nutrition_case.loc[(nutrition_case.gender == 'F'), 'gender'] = 'Female'
nutrition_case.loc[(nutrition_case.gender == 'Femelle'), 'gender'] = 'Female'
nutrition_case['gender'].value_counts()


# In[17]:


# Colonnes par type
date_columns = ['date_de_visite', 'date_de_depistage', 'date_admission', 'date_of_birth',
                'household_collection_date', 'death_date']
col_num = ['admission_muac', 'admission_weight_kg', 'admission_height_cm',
           'nbr_visit', 'nbr_visit_succeed', 'contrat_signe', 'household_number']
col_str = ['manutrition_type','name', 'eligible', 'admission_manutrition_type', 'site_code_id', 'phone_number',
           'gender', 'commune', 'departement', 'office', 'patient_code_2',
           'proposition_test_vih', 'refus_proposition_test_pourquoi',
           'has_household', 'opened_by_username', 'caseid']

# Conversions
nutrition_case[date_columns] = nutrition_case[date_columns].astype(str).apply(pd.to_datetime, errors='coerce')
nutrition_case[col_num] = nutrition_case[col_num].astype(str).apply(pd.to_numeric, errors='coerce')
nutrition_case[col_str] = nutrition_case[col_str].astype(str)

# Concaténer les colonnes nettoyées
nutrition_case = pd.concat([nutrition_case[date_columns], nutrition_case[col_num], nutrition_case[col_str]], axis=1)
nutrition_case.rename(columns={'caseid': 'case_id'}, inplace=True)

print(f'This combined dataset has {nutrition_case.shape[0]} observations')


# In[18]:


nutrition_case.to_excel("nutrition_case.xlsx",index=True)
#nutrition_case.to_excel(f"nutrition_case_{str(datetime.today().strftime('%Y-%m-%d'))}.xlsx", index = False)


# In[19]:


nutrition_depistage = nutrition_case[(nutrition_case['date_de_depistage'] >= start_date) & (nutrition_case['date_de_depistage'] <= end_date)]
print(f"Nombre de dépistages réalisés : {nutrition_depistage.shape[0]}")


# In[21]:


nutrition_depistage.to_excel("nutrition_depistage.xlsx",index=True)
#nutrition_depistage.to_excel(f"nutrition_depistage_{str(datetime.today().strftime('%Y-%m-%d'))}.xlsx", index = False)


# In[22]:


plot_monthly_data(nutrition_depistage, 'date_de_depistage',f'Nombre de dépistages réalisés par mois pour la periode\n Total Nombre de visite: {nutrition_depistage.shape[0]}')


# In[23]:


nutrition_depistage['gender'].value_counts()


# In[25]:


nutrition_visite = nutrition_case[(nutrition_case['date_de_visite'] >= start_date) & (nutrition_case['date_de_visite'] <= end_date)]
print(f"Nombre de visites réalisées : {nutrition_visite.shape[0]}")


# In[26]:


nutrition_visite.to_excel("nutrition_visite.xlsx",index=True)
#nutrition_visite.to_excel(f"nutrition_visite_{str(datetime.today().strftime('%Y-%m-%d'))}.xlsx", index = False)


# In[27]:


eligible = nutrition_visite[nutrition_visite['eligible']=='yes']
print(f"Nombre d'enfants éligibles : {eligible.shape[0]}")


# In[28]:


eligible.to_excel("eligible.xlsx",index=True)
#eligible.to_excel(f"eligible_{str(datetime.today().strftime('%Y-%m-%d'))}.xlsx", index = False)

# In[31]:


# Convertit proprement en numérique
eligible['nbr_visit'] = pd.to_numeric(eligible['nbr_visit'], errors='coerce')
# Garde les lignes où nbr_visit n'est pas NaN (donc ce ne sont pas des "---", vides, etc.)
enrole = eligible[eligible['nbr_visit'].notna()]
enrole = eligible[eligible['nbr_visit'] > 0]
print(f"Nombre de beneficiaires enrolés en nutrition : {enrole.shape[0]}")


# In[32]:


enrole.to_excel("enrole.xlsx",index=True)
#enrole.to_excel(f"enrole_{str(datetime.today().strftime('%Y-%m-%d'))}.xlsx", index = False)



def creer_colonne_match_conditional(df1, df2, on, nouvelle_colonne, mapping):
    """
    Crée une colonne dans df1 en fonction des correspondances avec df2, conditionnées par un mapping.

    :param df1: Le premier DataFrame
    :param df2: Le second DataFrame
    :param on: La colonne utilisée pour le merge
    :param nouvelle_colonne: Le nom de la nouvelle colonne à créer
    :param mapping: Un dictionnaire pour définir les valeurs de la colonne 'match'
    :return: df1 avec la nouvelle colonne ajoutée
    """
    # Merge gauche avec indicateur de correspondance
    merged_df = df1.merge(df2, on=on, how='left', indicator=True)

    # Création de la nouvelle colonne 'match' avec un mapping conditionnel
    merged_df[nouvelle_colonne] = merged_df['_merge'].map(mapping)

    # Suppression de la colonne '_merge'
    merged_df.drop(columns=['_merge'], inplace=True)

    # Retourner seulement les colonnes originales de df1 avec la nouvelle colonne
    return merged_df


# In[37]:


h_ovc_nut_j =enrole[['case_id','commune','office']]
mapping_p = {'both': 'yes', 'left_only': 'no'}
comptage = creer_colonne_match_conditional(enrole, h_nut, on='case_id', nouvelle_colonne='comptage', mapping=mapping_p).drop_duplicates('case_id', keep = 'first')
comptage.shape[0]
print(comptage['comptage'].value_counts())
# Filtrage des lignes où la colonne 'testing' vaut "yes"
nut_avec_comptage = comptage[comptage['comptage'] == "yes"]
print(f"Nombre de beneficiaires avec un comptage en nutrition : {nut_avec_comptage.shape[0]}")
nut_sans_comptage = comptage[comptage['comptage'] == "no"]
print(f"Nombre de beneficiaires sans aucun comptage en nutrition : {nut_sans_comptage.shape[0]}")

# In[38]:

nut_avec_comptage.to_excel("nut_avec_comptage.xlsx",index=True)
nut_sans_comptage.to_excel("nut_sans_comptage.xlsx",index=True)
#nut_avec_comptage.to_excel(f"nut_avec_comptage_{str(datetime.today().strftime('%Y-%m-%d'))}.xlsx", index = False)
#nut_sans_comptage.to_excel(f"nut_sans_comptage_{str(datetime.today().strftime('%Y-%m-%d'))}.xlsx", index = False)

# In[39]:

h_ovc_nut_j =enrole[['case_id','commune','office']]
mapping_p = {'both': 'yes', 'left_only': 'no'}
testing = creer_colonne_match_conditional(h_nut, enrole, on='case_id', nouvelle_colonne='testing', mapping=mapping_p)
testing.shape[0]
print(testing['testing'].value_counts())
# Filtrage des lignes où la colonne 'testing' vaut "yes"
testing_hh = testing[testing['testing'] == "yes"]
# Affiche le nombre total de lignes


# In[42]:



# In[44]:


columns = [
    "caseid", "first_name", "last_name", "age_in_year", "caregiver_yes_no", "dob",
    "full_code_patient_menage", "hiv_test", "hiv_test_date", "hiv_test_result",
    "infant_relationship", "is_refer_for_hiv_test", "main_infant_code",
    "st_code", "last_modified_by_user_username","last_modified_date",
    "opened_date", "owner_name", "case_id","commune","office","case_link"]
# Filtrage de colonnes dans le DataFrame
testing_hh = testing_hh[columns]
print(testing_hh.shape)


# In[45]:


testing_hh.to_excel('testing_hh.xlsx', index=False)
print(f"Nombre de menage en nutrition : {testing_hh.shape[0]}")
#testing_hh.to_excel(f"testing_hh_{str(datetime.today().strftime('%Y-%m-%d'))}.xlsx", index = False)


# In[46]:


condition_result = (
    (testing_hh['hiv_test_result'].isna()) |
    (testing_hh['hiv_test_result'] == "---") |
    (testing_hh['hiv_test_result'].astype(str).str.strip() == "")
)

condition_st_code = (
    (testing_hh['st_code'].isna()) |
    (testing_hh['st_code'] == "---") |
    (testing_hh['st_code'].astype(str).str.strip() == "")
)

# Filtrer les lignes où l'une des deux conditions est vraie
nut_sans_testing = testing_hh[condition_result & condition_st_code]

nut_sans_testing.to_excel('nut_sans_testing.xlsx', index=False)
print(f"Nombre de menage non encore dépisté : {nut_sans_testing.shape[0]}")

# Date de fin = aujourd’hui
end_date_week = pd.to_datetime('today')
# Date de début = 7 jours avant
start_date_week = end_date_week - timedelta(days=7)
depistage_nut_week = nutrition_depistage[(nutrition_depistage['date_de_depistage'] >= start_date_week) & (nutrition_depistage['date_de_depistage'] <= end_date_week)]
print(f"Nombre de dépistages pour la semaine : {depistage_nut_week.shape[0]}")


# In[58]:


# #### **4.2 Nombre de dépistage par agent pour la semaine**

# In[59]:


# #### **4.3 Nombre de visite par office pour la semaine**

# In[60]:


visite_nut_week = nutrition_visite[(nutrition_visite['date_de_visite'] >= start_date_week) & (nutrition_visite['date_de_visite'] <= end_date_week)]
print(f"Nombre de visites pour la semaine : {visite_nut_week.shape[0]}")


# In[61]:


"""plot_beneficiaries_by_categorie(
    df=visite_nut_week,
    lo_department='office',
    set_title='Nombre de visites réalisées pour la semaine par office',
    set_xlabel='Beneficiaires',
    set_ylabel='office'
)"""


# #### **4.4 Nombre de visite par agent pour la semaine**

# In[62]:


"""plot_beneficiaries_by_categorie(
    df=visite_nut_week,
    lo_department='opened_by_username',
    set_title='Nombre de visites réalisées pour la semaine par agent',
    set_xlabel='Beneficiaires',
    set_ylabel='agent'
)"""


# #### **4.5 Nombre de comptages réalisées pour la semaine**

# In[63]:


comptage_nut_week = nutrition_case[(nutrition_case['household_collection_date'] >= start_date_week) & (nutrition_case['household_collection_date'] <= end_date_week)]
print(f"Nombre de comptages pour la semaine : {comptage_nut_week.shape[0]}")


# In[64]:


"""if not comptage_nut_week.empty:
    plot_beneficiaries_by_categorie(
        df=visite_nut_week,
        lo_department='opened_by_username',
        set_title='Nombre de comptages réalisées pour la semaine par agent',
        set_xlabel='Bénéficiaires',
        set_ylabel='Agent'
    )
else:
    print("Pas d'activité")
"""

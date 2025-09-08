import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
import pandas as pd

def execute_sql_query(env_path: str, sql_file_path: str) -> pd.DataFrame:
    load_dotenv(env_path)
    user = os.getenv('MYSQL_USER')
    password = os.getenv('MYSQL_PASSWORD')
    host = os.getenv('MYSQL_HOST')
    db = os.getenv('MYSQL_DB')

    conn_text = f'mysql+pymysql://{user}:{password}@{host}/{db}'
    engine = create_engine(conn_text)

    with open(sql_file_path, 'r') as file:
        sql_query = file.read().replace('use caris_db;', '')

    df = pd.read_sql_query(sql_query, engine)
    engine.dispose()

    return df

#===========================================================================================================================
#========================================================================================================================= 
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
from datetime import datetime

def download_files():
    load_dotenv('id_cc.env')
    email = os.getenv('EMAIL')
    password_cc = os.getenv('PASSWORD')

    options = Options()
    options.add_argument("start-maximized")
    prefs = {"download.default_directory": "C:\\Users\\Moise\\Downloads\\REPORTS_MEAL\\OEV\\COMMCARE\\PTME"}
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(1000)

    def commcare_login():
        try:
            driver.get('https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/f6ddce2133f8d233d9fbd9341220ed6f/')
            driver.find_element(By.XPATH, '//*[@id="id_auth-username"]').send_keys(email)
            driver.find_element(By.XPATH, '//*[@id="id_auth-password"]').send_keys(password_cc)
            driver.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()
        except Exception as e:
            print(f"An error occurred during login: {e}")

    def download_report(download_url, button_xpath, progress_xpath):
        try:
            driver.get(download_url)
            driver.find_element(By.XPATH, button_xpath).click()
            time.sleep(80)  # wait for download to start
            driver.find_element(By.XPATH, progress_xpath).click()
        except Exception as e:
            print(f"An error occurred while downloading from {download_url}: {e}")

    commcare_login()

    # Get the current date in the format YYYY-MM-DD
    today_date = datetime.today().strftime('%Y-%m-%d')
    # Download the House mother reports from the server for the current date
    download_report(
        'https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/3eb9f92d8d82501ebe5c8cb89b83dbba/',
        '//*[@id="download-export-form"]/form/div[2]/div/div[2]/div[1]/button/span[1]',
        '//*[@id="download-progress"]/div/div/div[2]/div[1]/form/a/span[1]'
    )
    # Download the comptage de menage reports from the server for the current date
    download_report(
        'https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/269567f0b84da5a1767712e519ced62e/',
        '//*[@id="download-export-form"]/form/div[2]/div/div[2]/div[1]/button/span[1]',
        '//*[@id="download-progress"]/div/div/div[2]/div[1]/form/a/span[1]'
    )
    # Download the Appel PTME form reports from the server for the current date
    download_report(
        'https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/c1a3280f5e34a2b6078439f9b59ad72c/',
        '//*[@id="download-export-form"]/form/div[2]/div/div[2]/div[1]/button/span[1]',
        '//*[@id="download-progress"]/div/div/div[2]/div[1]/form/a/span[1]'
    )
    # Download the databse caseid form reports from the server for the current date
    download_report(
        'https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/af6c4186011182dfda68a84536231f68/',
        '//*[@id="download-export-form"]/form/div[2]/div/div[2]/div[1]/button/span[1]',
        '//*[@id="download-progress"]/div/div/div[2]/div[1]/form/a/span[1]'
    )

    # Check if the last file is completely downloaded before quitting
    last_file = f'household mother {today_date}.xlsx'
    download_path = os.path.join("C:\\Users\\Moise\\Downloads\\Reports_MEAL\\COMMCARE\\PTME", last_file)

    # Wait for the last file to appear in the download directory
    timeout = 300  # seconds
    start_time = time.time()
    while not os.path.isfile(download_path):
        if time.time() - start_time > timeout:
            print(f"Timed out waiting for the file {last_file} to download.")
            break
        time.sleep(5)

    driver.quit()

#===================================================================================================================
def check_files(files):
    path = "C:\\Users\\Moise\\Downloads\\Reports_MEAL\\OEV"
    missing_files = []

    for file in files:
        full_path = os.path.join(path, file)
        print(f"Checking for file: {full_path}")  # Debugging print
        if not os.path.isfile(full_path):
            missing_files.append(file)

    if not missing_files:
        print("All files are present.")
    else:
        print(f"The following files are missing: {missing_files}")

# Get the current date in the format YYYY-MM-DD
today_date = datetime.today().strftime('%Y-%m-%d')
#==================================================================================================================
import pandas as pd
def save_dataframe_to_excel(df, filename, output_path="C:\\Users\\Moise\\Downloads\\REPORTS_MEAL\\DATA\\PTME"):
    # Vérifier si le nom du fichier a l'extension .xlsx, sinon l'ajouter
    if not filename.endswith(".xlsx"):
        filename += ".xlsx"

    # Construire le chemin complet du fichier
    output_file_path = os.path.join(output_path, filename)

    # Sauvegarder le DataFrame dans un fichier Excel
    df.to_excel(output_file_path, index=False)

    print(f"DataFrame saved to {output_file_path}")
    return output_file_path

# Exemple d'utilisation :
#save_dataframe_to_excel(stat_ptme_index, "stat_ptme_index.xlsx")
#==================================================================================================================
import pandas as pd

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

#========================================Functions=========================================================
import plotly.express as px
import plotly.graph_objects as go

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
    
#========================================Functions=========================================================
import pandas as pd
import plotly.graph_objects as go

def plot_viral_load_summary2_plotly(df, age_min=0, age_max=19, start_date=None, end_date=None, title=None, output='plot'):
    df = df.copy()
    df['age'] = pd.to_numeric(df['age'], errors='coerce')
    df['last_viral_load_collection_date'] = pd.to_datetime(df['last_viral_load_collection_date'], errors='coerce')
    df['arv_start_date'] = pd.to_datetime(df['arv_start_date'], errors='coerce')

    # Filtrage par âge
    df = df[(df['age'] >= age_min) & (df['age'] <= age_max)]
    if df.empty:
        print(f"Aucune donnée pour les patients âgés de {age_min} à {age_max} ans.")
        return None

    # Dates
    end_date = pd.to_datetime('today')

    # Sous-ensembles
    on_arv = df[df['arv_start_date'] <= end_date - pd.DateOffset(months=2)]
    not_on_arv = df[~df.index.isin(on_arv.index)]

    vl_coverage = on_arv[on_arv['last_viral_load_collection_date'] >= end_date - pd.DateOffset(months=12)]
    not_covered = on_arv[~on_arv.index.isin(vl_coverage.index)]

    suppression_col = 'indetectable_ou_inf_1000'
    if df[suppression_col].dtype != 'O':
        df[suppression_col] = df[suppression_col].astype(str)

    vl_suppression = vl_coverage[vl_coverage[suppression_col].str.upper() == "OUI"]
    not_suppressed = vl_coverage[~vl_coverage.index.isin(vl_suppression.index)]

    # Gestion des sorties alternatives
    if output == 'on_arv':
        return on_arv
    elif output == 'not_on_arv':
        return not_on_arv
    elif output == 'vl_coverage':
        return vl_coverage
    elif output == 'not_covered':
        return not_covered
    elif output == 'vl_suppression':
        return vl_suppression
    elif output == 'not_suppressed':
        return not_suppressed
    elif output == 'TX_CURR':
        return df

    # Données pour le graphe
    Indicators = ['TX_CURR', 'On ARV ≥3mois', 'Viral Load Coverage', 'Viral Load Suppression']
    n_1 = [df.shape[0], on_arv.shape[0], vl_coverage.shape[0], vl_suppression.shape[0]]
    prop_impact1 = [
        1.0,
        on_arv.shape[0] / df.shape[0] if df.shape[0] > 0 else 0,
        vl_coverage.shape[0] / on_arv.shape[0] if on_arv.shape[0] > 0 else 0,
        vl_suppression.shape[0] / vl_coverage.shape[0] if vl_coverage.shape[0] > 0 else 0
    ]

    med = pd.DataFrame({
        'Indicators': Indicators,
        'n_1': n_1,
        'prop_impact1': [round(p * 100, 1) for p in prop_impact1]
    })

    # Couleurs personnalisées cohérentes
    color_map = {
        'TX_CURR': "#77198C",
        'On ARV ≥3mois': '#EF553B',
        'Viral Load Coverage': "#00C2CC",
        'Viral Load Suppression': "#F7FA63"
    }
    med['Color'] = med['Indicators'].map(color_map)
    med['Label'] = med.apply(lambda row: f"{row['n_1']:,} ({row['prop_impact1']}%)", axis=1)

    # Titre dynamique ou personnalisé
    if title is None:
        title = f"Cascade des OEV âgés de {age_min}-{age_max} ans"

    # Tracé Plotly
    fig = go.Figure()
    for _, row in med.iterrows():
        fig.add_trace(go.Bar(
            x=[row['Indicators']],
            y=[row['n_1']],
            name=row['Indicators'],
            marker_color=row['Color'],
            text=row['Label'],
            textposition='outside'
        ))

    fig.update_layout(
        title=title,
        xaxis_title="",
        yaxis_title="Fréquence",
        title_x=0.5,
        showlegend=False,
        template='plotly_white',
        margin=dict(t=60, b=60),
        annotations=[
            dict(
                text=f"Source: hivhaiti / {end_date.date()}",
                x=0.5,
                y=-0.2,
                showarrow=False,
                xref='paper',
                yref='paper',
                font=dict(size=11, color="gray")
            )
        ]
    )

    fig.show()
#=======================================Functions=========================================================
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def plot_age_pyramid(df, age_col='age', sex_col='sex', id_col='patient_code',
                     title='👥 TX_CURR - Pyramide des âges par sexe (0-17 ans)'):

    # Nettoyage
    df_clean = df[[age_col, sex_col, id_col]].dropna()
    df_clean[age_col] = pd.to_numeric(df_clean[age_col], errors='coerce')
    df_clean = df_clean[df_clean[age_col].between(0, 17)]  # max 17 ans

    # Bins avec dernier groupe 15-17
    bins = [0, 5, 10, 15, 18]
    labels = ['0-4', '5-9', '10-14', '15-17']
    df_clean['age_group'] = pd.cut(df_clean[age_col], bins=bins, labels=labels, right=False)

    # Comptage
    pyramid = df_clean.groupby(['age_group', sex_col])[id_col].count().unstack(fill_value=0)

    if 'F' not in pyramid.columns: pyramid['F'] = 0
    if 'M' not in pyramid.columns: pyramid['M'] = 0

    pyramid = pyramid.sort_index()

    # Traces Plotly
    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=pyramid.index.astype(str),
        x=-pyramid['M'],
        name='Hommes',
        orientation='h',
        marker_color='steelblue',
        text=pyramid['M'],
        textposition='inside',
        textfont=dict(color='white', size=13),
        width=0.9,
        hovertemplate='Âge: %{y}<br>Hommes: %{text}<extra></extra>'
    ))

    fig.add_trace(go.Bar(
        y=pyramid.index.astype(str),
        x=pyramid['F'],
        name='Femmes',
        orientation='h',
        marker_color='lightcoral',
        text=pyramid['F'],
        textposition='inside',
        textfont=dict(color='white', size=13),
        width=0.9,
        hovertemplate='Âge: %{y}<br>Femmes: %{text}<extra></extra>'
    ))

    # Axes dynamiques
    x_max = max(pyramid['M'].max(), pyramid['F'].max())
    step = int(np.ceil(x_max / 4.0 / 10.0)) * 10
    ticks = list(range(-x_max, x_max + step, step))
    ticktext = [abs(v) for v in ticks]

    fig.update_layout(
        title=dict(
            text=title,
            x=0.5,
            xanchor='center',
            font=dict(size=22)
        ),
        barmode='relative',
        xaxis=dict(
            title='Nombre de patients',
            tickvals=ticks,
            ticktext=ticktext,
            zeroline=True,
            showgrid=False
        ),
        yaxis=dict(
            title='Groupe d’âge',
            tickfont=dict(size=13),
            showgrid=False
        ),
        height=600,
        width=950,
        template='plotly_white',
        margin=dict(l=100, r=40, t=60, b=40)
    )

    fig.show()
#===========================================================================================================================
import pandas as pd

def filter_oev_data(
    df,
    excluded_offices=['BOM', 'PDP'],
    excluded_networks=['PIH', 'UGP', 'MSPP'],
    excluded_sites=['PAP/CHAP', 'PAP/OBCG', 'PAP/OGRE', 'PEG/HNDP', 'PAP/SMFO', 'LEG/HSCL', 'PAP/HAHD', 'ARC/SADA'],
    abandoned_flag=1,
    output_file='TX_CURR.xlsx'
):
    print(f"Initial dataset has {df.shape[0]} observations")

    df = df[~df['office'].isin(excluded_offices)]
    print(f"After excluding offices: {df.shape[0]} observations")

    df = df[~df['network'].isin(excluded_networks)]
    print(f"After excluding networks: {df.shape[0]} observations")

    df['age'] = pd.to_numeric(df['age'], errors='coerce')
    df = df[df['age'].between(0, 17)]
    print(f"After filtering age between 0-17: {df.shape[0]} observations")

    df = df[~df['site'].isin(excluded_sites)]
    print(f"After excluding sites: {df.shape[0]} observations")

    df['is_abandoned'] = pd.to_numeric(df['is_abandoned'], errors='coerce')
    df = df[df['is_abandoned'] != abandoned_flag]
    print(f"After excluding abandoned: {df.shape[0]} observations")

    next_appointment_date_max = pd.to_datetime('today')
    first_day_this_month = next_appointment_date_max.replace(day=1)
    next_appointment_date_min = first_day_this_month - pd.DateOffset(months=1)

    df['next_appointment_date'] = pd.to_datetime(df['next_appointment_date'], errors='coerce')
    df = df[df['next_appointment_date'] >= next_appointment_date_min]
    df = df.drop_duplicates(subset=['patient_code'], keep='last')
    print(f"After filtering by next appointment date ≥ {next_appointment_date_min.date()}: {df.shape[0]} observations")

    df.to_excel(output_file, index=False)
    print(f"Filtered data exported to {output_file}")

    return df


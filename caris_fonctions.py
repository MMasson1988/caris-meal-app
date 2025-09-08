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
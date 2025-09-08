#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAPPORT MUSO - Script Python exécutable
Converti depuis Tracking_Muso_Report.ipynb
"""

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

# Import functions
try:
    from utils import get_commcare_odata
    from caris_fonctions import execute_sql_query
except ImportError as e:
    print(f"Warning: Could not import some functions: {e}")

def main():
    """Fonction principale du rapport MUSO"""
    
    # Configuration
    load_dotenv('dot.env')
    pd.set_option('display.float_format', '{:.2f}'.format)
    warnings.filterwarnings('ignore')
    
    print("=== RAPPORT MUSO ===")
    print("0. DATABASE LOADING AND WRANGLING")
    
    try:
        # 1. CHARGEMENT DES DONNÉES
        print("Chargement des données...")
        today_str = datetime.today().strftime('%Y-%m-%d')
        
        # Chargement des fichiers Excel
        muso_group = pd.read_excel(
            f"~/Downloads/caris-meal-app/data/muso_groupes (created 2025-03-25) {today_str}.xlsx", 
            parse_dates=True
        )
        
        muso_ben = pd.read_excel(
            f"~/Downloads/caris-meal-app/data/muso_beneficiaries (created 2025-03-25) {today_str}.xlsx", 
            parse_dates=True
        )
        
        muso_household = pd.read_excel(
            f"~/Downloads/caris-meal-app/data/muso_household_2022 (created 2025-03-25) {today_str}.xlsx", 
            parse_dates=True
        )
        
        muso_ppi = pd.read_excel(
            f"~/Downloads/caris-meal-app/data/MUSO - Members - PPI Questionnaires (created 2025-04-23) {today_str}.xlsx", 
            parse_dates=True
        )
        
        muso_actif = pd.read_excel("./group_muso_actif.xlsx", parse_dates=True)
        
        print("✓ Données chargées avec succès")
        
        # 2. TRAITEMENT MUSO GROUPS
        print("\n1. TRAITEMENT DES GROUPES MUSO")
        
        muso_group_after = muso_group.copy(deep=True)
        muso_group_after = muso_group_after.rename(columns={"opened_by_username": "username"})
        
        colonnes = [
            "caseid", "is_graduated", "office", "graduation_date", "commune_name",
            "code", "creation_date", "officer_name", "gps_date", "gps", "office_name", "adress",
            "section_name", "departement_name", "name", "present", "credit", "balance", "absent",
            "cotisation", "date_suivi", "date_prochain_suivi", "closed", "closed_by_username",
            "last_modified_date", "username", "opened_date", "owner_name", "case_link"
        ]
        muso_group_after = muso_group_after[colonnes].reset_index(drop=True)
        
        # Filtrage des groupes actifs
        if 'caseid' in muso_actif.columns and 'caseid' in muso_group.columns:
            muso_group_caseids = muso_actif['caseid'].dropna().unique()
            muso_group_actif = muso_group[muso_group['caseid'].isin(muso_group_caseids)]
            print(f"Nombre de groupes actifs: {muso_group_actif.shape[0]}")
        else:
            print("Erreur : 'caseid' colonne manquante dans muso_actif ou muso_group")
            return
        
        # Remplacement et renommage
        muso_group_actif["opened_by_username"] = muso_group_actif["opened_by_username"].replace(
            "pierrerobentz.cassion@carisfoundationintl.org", "2estheve"
        )
        muso_group_actif = muso_group_actif.rename(columns={"opened_by_username": "username"})
        
        # Sélection des colonnes
        muso_group_actif = muso_group_actif[colonnes].reset_index(drop=True)
        
        print("Répartition par utilisateur:")
        print(muso_group_actif.value_counts("username"))
        
        # Conversion des dates et combinaison
        muso_group_actif["creation_date"] = pd.to_datetime(muso_group_actif["creation_date"], errors="coerce")
        muso_group_after["creation_date"] = pd.to_datetime(muso_group_after["creation_date"], errors="coerce")
        
        date_max_actif = muso_group_actif["creation_date"].max()
        print(f"Date maximale de création: {date_max_actif}")
        
        nouvelles_lignes = muso_group_after[muso_group_after["creation_date"] > date_max_actif]
        print(f"Nombre de nouveaux groupes ajoutés: {nouvelles_lignes.shape[0]}")
        
        muso_group_final = pd.concat([muso_group_actif, nouvelles_lignes], ignore_index=True)
        print(f"Nombre total de groupes Muso: {muso_group_final.shape[0]} lignes")
        # Renommage des colonnes
        muso_ben = muso_ben.rename(columns={"indices.muso_groupes": "caseid_group"})
        muso_group_final = muso_group_final.rename(columns={"caseid": "caseid_group"})
        print("Merge muso_ben_actif avec liste_muso...")
        liste_muso = pd.read_excel("liste_muso.xlsx", sheet_name=0)
        muso_group_final = muso_group_final.merge(
            liste_muso[["caseid_group", "officer_fullname", "officer_name"]],
            on="caseid_group",
            how="left"
        )
        # 3. TRAITEMENT MUSO BENEFICIARIES
        print("\n2. TRAITEMENT DES BÉNÉFICIAIRES MUSO")

        # Filtrage des bénéficiaires actifs
        if 'caseid_group' in muso_group_final.columns and 'caseid_group' in muso_ben.columns:
            muso_group_caseids = muso_group_final['caseid_group'].dropna().unique()
            muso_ben_actif = muso_ben[muso_ben['caseid_group'].isin(muso_group_caseids)]

            # Vérifier si la colonne removing_date existe avant de l'utiliser
            if "removing_date" in muso_ben_actif.columns:
                muso_ben_actif = muso_ben_actif[muso_ben_actif["removing_date"] == "---"]

            # 🔹 Ajout des colonnes officer_fullname et officer_name depuis liste_muso
            if "caseid_group" in liste_muso.columns:
                muso_ben_actif = muso_ben_actif.merge(
                    liste_muso[["caseid_group", "officer_fullname", "officer_name"]],
                    on="caseid_group",
                    how="left"
                )
            else:
                print("⚠️ Erreur : 'caseid_group' manquant dans liste_muso")

            print(f"Nombre de bénéficiaires muso: {muso_ben_actif.shape[0]}")
        else:
            print("Erreur : 'caseid_group' colonne manquante")
            return

        
        # PVVIH
        if "is_pvvih" in muso_ben_actif.columns:
            muso_pvvih = muso_ben_actif[muso_ben_actif["is_pvvih"] == "1"]
            print(f"Nombre de PVVIH dans muso: {muso_pvvih.shape[0]}")
        
        # Sélection des colonnes pour les bénéficiaires - SANS officer_fullname et officer_name
        columns = [
            "caseid", "household_number", "group_code", "dob", "patient_code",
            "first_name", "group_commune", "phone", "is_inactive", "group_departement",
            "inactive_date", "graduated", "abandoned_date", "is_abandoned", "last_name",
            "graduation_date", "gender", "rank", "group_name", "address",
            "is_pvvih", "is_caris_member", "name", "household_number_2022", "muso_start_date",
            "patient_code_pv", "date_enquete_ppi", "score_total_ppi", "close_reason", "test",
            "test_result", "date_du_test", "institution_ou_centre_hospitalier_qui_a_fait_le_test", 
            "est_sous_arv", "proche_decede_du_vih", "hospitalisation_dans_les_3_derniers_mois", 
            "lien_de_parent_avec_proche_decede_du_vih", "probleme_de_sante_regulier", "refere", 
            "owner_id", "caseid_group", "closed", "last_modified_by_user_username", 
            "last_modified_date", "opened_date", "owner_name"
        ]
        
        # Garder seulement les colonnes qui existent
        columns_existantes = [col for col in columns if col in muso_ben_actif.columns]
        
        if "last_modified_by_user_username" in muso_ben_actif.columns:
            muso_ben_actif["last_modified_by_user_username"] = muso_ben_actif["last_modified_by_user_username"].replace(
                "valentin.wichley@carisfoundationintl.org", "2estheve"
            )
        
        muso_ben_actif = muso_ben_actif[columns_existantes]
        print(f"Colonnes bénéficiaires conservées: {len(columns_existantes)}/{len(columns)}")
        
        # 4. LECTURE ET MERGE AVEC LISTE_MUSO
        print("\n3. LECTURE ET MERGE AVEC LISTE_MUSO")
        
        try:
            # Rechercher le fichier liste_muso dans le dossier
            import glob
            
            # Chercher tous les fichiers qui contiennent "liste_muso"
            liste_muso_files = glob.glob("*liste_muso*.xlsx") + glob.glob("*liste_muso*.xls")
            
            if not liste_muso_files:
                print("⚠️ Aucun fichier 'liste_muso' trouvé dans le dossier")
                liste_muso = None
                doublon = None
            else:
                # Prendre le premier fichier trouvé
                liste_muso_file = liste_muso_files[0]
                print(f"✓ Fichier trouvé: {liste_muso_file}")
                
                # SHEET 1 - Lire les données liste_muso
                try:
                    liste_muso = pd.read_excel(liste_muso_file, sheet_name=0)  # sheet1
                    print(f"Sheet1 - Dimensions liste_muso: {liste_muso.shape}")
                    
                    # Vérifier les colonnes nécessaires pour le merge
                    required_cols = ["caseid_group", "officer_fullname", "officer_name"]
                    missing_cols = [col for col in required_cols if col not in liste_muso.columns]
                    
                    if missing_cols:
                        print(f"⚠️ Colonnes manquantes dans liste_muso: {missing_cols}")
                        print(f"Colonnes disponibles: {list(liste_muso.columns)}")
                        
                        # Essayer de trouver des colonnes similaires
                        for missing_col in missing_cols:
                            similar_cols = [col for col in liste_muso.columns if missing_col.lower() in col.lower() or col.lower() in missing_col.lower()]
                            if similar_cols:
                                print(f"Colonnes similaires pour '{missing_col}': {similar_cols}")
                        liste_muso = None
                    else:
                        # Merge avec muso_ben_actif - GARDER TOUTES LES COLONNES DE muso_ben_actif
                        print("Merge muso_ben_actif avec liste_muso...")
                        muso_ben_actif = muso_ben_actif.merge(
                            liste_muso[["caseid_group", "officer_fullname", "officer_name"]],
                            on="caseid_group",
                            how="left"
                        )
                        
                        print(f"Résultat du merge: {muso_ben_actif.shape[0]} lignes")
                        print(f"Lignes avec données officer: {muso_ben_actif['officer_fullname'].notna().sum()}")
                        print(f"Colonnes dans muso_ben_actif après merge: {muso_ben_actif.shape[1]} colonnes")
                        
                        # Vérifier que les colonnes ont été ajoutées
                        if 'officer_fullname' in muso_ben_actif.columns and 'officer_name' in muso_ben_actif.columns:
                            print("✓ Colonnes officer_fullname et officer_name ajoutées avec succès")
                        else:
                            print("⚠️ Erreur: colonnes officer non ajoutées")
                        
                except Exception as e:
                    print(f"Erreur lors de la lecture du sheet1: {e}")
                    liste_muso = None
                
                # SHEET 2 - Lire les doublons et filtrer muso_ben_actif
                try:
                    doublon = pd.read_excel(liste_muso_file, sheet_name=1)  # sheet2
                    print(f"Sheet2 - Dimensions doublon: {doublon.shape}")
                    
                    # Vérifier si la colonne caseid existe dans doublon
                    if 'caseid' in doublon.columns:
                        # Obtenir les caseid des doublons
                        caseid_doublons = doublon['caseid'].dropna().unique()
                        print(f"Nombre de caseid doublons trouvés: {len(caseid_doublons)}")
                        
                        # Filtrer muso_ben_actif pour exclure les doublons
                        muso_ben_actif_avant = muso_ben_actif.shape[0]
                        muso_ben_actif = muso_ben_actif[~muso_ben_actif['caseid'].isin(caseid_doublons)]
                        muso_ben_actif_apres = muso_ben_actif.shape[0]
                        
                        print(f"Bénéficiaires avant filtrage: {muso_ben_actif_avant}")
                        print(f"Bénéficiaires après filtrage: {muso_ben_actif_apres}")
                        print(f"Doublons supprimés: {muso_ben_actif_avant - muso_ben_actif_apres}")
                        
                    else:
                        print("⚠️ Colonne 'caseid' non trouvée dans le sheet2 (doublons)")
                        print(f"Colonnes disponibles dans doublon: {list(doublon.columns)}")
                        
                except Exception as e:
                    print(f"Erreur lors de la lecture du sheet2: {e}")
                    doublon = None
                    
        except Exception as e:
            print(f"Erreur lors du traitement de liste_muso: {e}")
            liste_muso = None
            doublon = None
        
        # VÉRIFICATION FINALE DES COLONNES REQUISES
        required_final_cols = ['caseid_group', 'officer_fullname', 'officer_name', 'caseid']
        missing_final = [col for col in required_final_cols if col not in muso_ben_actif.columns]
        
        if missing_final:
            print(f"⚠️ Colonnes manquantes dans muso_ben_actif final: {missing_final}")
        else:
            print("✓ Toutes les colonnes requises sont présentes dans muso_ben_actif")
        
        # 5. TRAITEMENT MUSO PPI ET MERGE
        print("\n4. TRAITEMENT MUSO PPI ET MERGE")
        
        # Renommer la colonne dans muso_ppi
        if "form.case.@case_id" in muso_ppi.columns:
            muso_ppi = muso_ppi.rename(columns={"form.case.@case_id": "caseid", "form.form_type": "type_ppi", "form.general_info.date": "date_ppi"})
            print("✓ Colonne 'form.case.@case_id' renommée en 'caseid'")
        else:
            print("⚠️ Colonne 'form.case.@case_id' non trouvée dans muso_ppi")
        
        # Sélectionner les colonnes nécessaires de muso_ppi
        ppi_columns = ["form.form_type", "form.general_info.date", "username", "caseid"]
        
        # Vérifier que toutes les colonnes existent
        missing_cols = [col for col in ppi_columns if col not in muso_ppi.columns]
        if missing_cols:
            print(f"⚠️ Colonnes manquantes dans muso_ppi: {missing_cols}")
            # Garder seulement les colonnes qui existent
            ppi_columns = [col for col in ppi_columns if col in muso_ppi.columns]
        
        muso_ppi_selected = muso_ppi[ppi_columns].copy()
        print(f"Colonnes PPI sélectionnées: {ppi_columns}")
        print(f"Nombre de lignes PPI: {muso_ppi_selected.shape[0]}")
        
        # Merge avec muso_ben_actif (après filtrage des doublons)
        print("Merge muso_ben_actif avec muso_ppi...")
        muso_ben_with_ppi = muso_ben_actif.merge(
            muso_ppi, 
            on="caseid", 
            how="left"
        )
        muso_ben_with_ppi = muso_ben_with_ppi[muso_ben_with_ppi["caseid"].notna() & muso_ben_with_ppi["date_ppi"].notna()].drop_duplicates(subset=["caseid"])
        print(f"Résultat du merge: {muso_ben_with_ppi.shape[0]} lignes")
        if ppi_columns:
            print(f"Lignes avec données PPI: {muso_ben_with_ppi[ppi_columns[0]].notna().sum()}")
        
        # 6. SAUVEGARDE DES RÉSULTATS
        print("\n5. SAUVEGARDE DES FICHIERS")
        
        try:
            muso_group_actif.to_excel("muso_group_actif.xlsx", index=False)
            muso_group_final.to_excel("muso_group_final.xlsx", index=False)
            muso_ben_actif.to_excel("muso_ben_actif.xlsx", index=False)
            # Nouveau fichier avec le merge PPI
            muso_ben_with_ppi.to_excel("muso_ben_with_ppi.xlsx", index=False)
            print("✓ Fichiers sauvegardés avec succès")
            print(f"✓ Nouveau fichier créé: muso_ben_with_ppi.xlsx")
            
            if liste_muso is not None:
                print(f"✓ Données officer ajoutées à muso_ben_actif")
            
            if doublon is not None:
                print(f"✓ Doublons filtrés à partir du sheet2")
                # Optionnel: sauvegarder les doublons identifiés
                doublon.to_excel("doublons_identifies.xlsx", index=False)
                print(f"✓ Fichier doublons_identifies.xlsx créé")
                
        except Exception as e:
            print(f"Erreur lors de la sauvegarde: {e}")
        
        print("\n=== RAPPORT TERMINÉ ===")
        
    except FileNotFoundError as e:
        print(f"Erreur: Fichier non trouvé - {e}")
        print("Vérifiez que tous les fichiers de données sont présents")
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import os
from datetime import datetime

def main():
    # Étape 1 : Définir le nom du fichier
    
    today_str = datetime.today().strftime('%Y-%m-%d')
    # Nouveau chemin (correct)
    path = f"C:\\Users\\moise\\Downloads\\caris-meal-app\\data\\All Gardens {today_str}.xlsx"
    # Ou encore mieux, utiliser une structure plus flexible :
    base_path = "C:\\Users\\moise\\Downloads\\caris-meal-app\\data"
    path = f"{base_path}\\All Gardens {today_str}.xlsx"
    garden_path = os.path.expanduser(f"C:\\Users\\moise\\Downloads\\caris-meal-app\\data\\All Gardens {today_str}.xlsx")

    # Étape 2 : Vérifier l'existence du fichier principal
    if not os.path.exists(garden_path):
        print(f"❌ Fichier Garden introuvable : {garden_path}")
        return

    # Étape 3 : Lecture du fichier Garden
    df = pd.read_excel(garden_path)

    # Étape 4 : Renommer la colonne info.owner_name en username
    if 'info.owner_name' in df.columns:
        df = df.rename(columns={'info.owner_name': 'username'})
    else:
        print("❌ La colonne 'info.owner_name' est introuvable.")
        return

    # Étape 5 : Lecture du fichier site_info.xlsx
    if not os.path.exists("site_info.xlsx"):
        print("❌ Fichier site_info.xlsx introuvable dans le répertoire courant.")
        return

    infos = pd.read_excel('site_info.xlsx', usecols=['site', 'status', 'network', 'commune', 'departement', 'office'])
    infos['site'] = infos['site'].astype(str).str.strip()

    # Étape 6 : Nettoyage et préparation de df['site']
    if 'caris_site' not in df.columns:
        print("❌ Colonne 'caris_site' manquante dans le fichier Garden.")
        return

    df['site'] = df['caris_site'].astype(str).str.split('-').str[0].str.strip()

    # Étape 7 : Fusion avec infos
    df = pd.merge(df, infos, on='site', how='left')

    # Étape 8 : Vérification des colonnes nécessaires
    required_columns = ['username', 'info.last_modified_date', 'closed', 'cycle_4_start_date']
    if not all(col in df.columns for col in required_columns):
        print("❌ Colonnes nécessaires manquantes après fusion.")
        return

    # Étape 9 : Liste des usernames ciblés
    usernames = [
        "1mackenson", "6jkenson", "j6geniel", "j1james", "j1vincent",
        "j6emanise", "j6guerby", "j1napolean", "j1cepoudy", "j6benest"
    ]

    # Étape 10 : Conversion de la date
    df['info.last_modified_date'] = pd.to_datetime(df['info.last_modified_date'], errors='coerce')

    # Étape 11 : Bornes de date
    start_date = pd.Timestamp("2024-10-01")
    end_date = pd.Timestamp(datetime.today().date())

    # Étape 12 : Filtrage
    filtered_df = df[
        df['username'].isin(usernames) &
        df['info.last_modified_date'].between(start_date, end_date) &
        (df['closed'] == False) &
        (df['cycle_4_start_date'] == "---")
    ]
    filtered_df = filtered_df[filtered_df['address_department']!= "nord-ouest"]  # Filtrer sans le département nord-ouest

    # Étape 13 : Résultat
    print(f"✅ {len(filtered_df)} lignes sélectionnées après filtrage.")
    filtered_df.to_excel("all_gardens.xlsx", index=False)
    print(f"📁 Résultat exporté")

if __name__ == "__main__":
    main()

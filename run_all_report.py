#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'orchestration :
1. Exécute les pipelines Python (oev, ptme et muso) l'un après l'autre.
2. Génère les rapports Quarto (fichiers .qmd) correspondants.

Avant de lancer ce script, vérifiez que:
- Python est correctement installé et que les scripts sont présents
- Quarto est installé et accessible via la commande 'quarto'
- R est installé avec les packages requis
"""

import subprocess
import sys
import os
from pathlib import Path

# Liste des scripts Python à exécuter
pipelines = ["oev_pipeline.py", "ptme_pipeline.py", "muso_pipeline.py", "garden_pipeline.py"]

# Liste des fichiers Quarto à rendre
qmd_files = ["tracking-oev.qmd", "tracking-ptme.qmd", "tracking-muso.qmd","tracking-gardening.qmd"]

# Packages R requis pour les rapports
required_r_packages = [
    "gsubfn", "DBI", "dplyr", "ggplot2", "knitr", "rmarkdown", 
    "plotly", "DT", "lubridate", "stringr"
]

def check_r_packages():
    """Vérifie et installe les packages R manquants."""
    print("🔍 Vérification des packages R...")
    
    missing_packages = []
    
    for package in required_r_packages:
        try:
            # Vérifier si le package est installé
            result = subprocess.run([
                "Rscript", "-e", 
                f"if (!require('{package}', quietly = TRUE)) quit(status = 1)"
            ], capture_output=True, check=True)
            print(f"✅ Package R '{package}' trouvé")
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_packages.append(package)
            print(f"❌ Package R '{package}' manquant")
    
    # Installer les packages manquants
    if missing_packages:
        print(f"\n📦 Installation des packages R manquants: {missing_packages}")
        
        packages_str = "', '".join(missing_packages)
        install_cmd = f"install.packages(c('{packages_str}'), repos='https://cran.rstudio.com/')"
        
        try:
            subprocess.run([
                "Rscript", "-e", install_cmd
            ], check=True)
            print("✅ Packages R installés avec succès")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Erreur lors de l'installation des packages R: {e}")
            return False
    
    return True

def check_dependencies():
    """Vérifie toutes les dépendances."""
    print("🔍 Vérification des dépendances...\n")
    
    # Vérifier les fichiers Python
    for script in pipelines:
        if not Path(script).exists():
            print(f"❌ Script Python manquant: {script}")
            return False
    print("✅ Scripts Python trouvés")
    
    # Vérifier les fichiers Quarto
    for qmd in qmd_files:
        if not Path(qmd).exists():
            print(f"❌ Fichier Quarto manquant: {qmd}")
            return False
    print("✅ Fichiers Quarto trouvés")
    
    # Vérifier Quarto
    try:
        subprocess.run(["quarto", "--version"], capture_output=True, check=True)
        print("✅ Quarto installé")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Quarto non installé")
        return False
    
    # Vérifier R
    try:
        subprocess.run(["Rscript", "--version"], capture_output=True, check=True)
        print("✅ R installé")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ R non installé")
        return False
    
    # Vérifier et installer les packages R
    if not check_r_packages():
        return False
    
    print("\n✅ Toutes les dépendances sont satisfaites\n")
    return True

def run_command(cmd_list, description="", continue_on_error=False):
    """Exécute une commande avec gestion d'erreurs améliorée."""
    try:
        print(f"📌 {description}: {' '.join(cmd_list)}")
        
        result = subprocess.run(
            cmd_list, 
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        print("✅ Terminé avec succès")
        
        # Afficher la sortie si elle existe
        if result.stdout.strip():
            print(f"📄 Sortie: {result.stdout.strip()[:200]}...")
        
        print()
        return True
        
    except subprocess.CalledProcessError as err:
        print(f"❌ Erreur lors de l'exécution")
        print(f"   Code d'erreur: {err.returncode}")
        
        if err.stderr:
            print(f"   Erreur: {err.stderr.strip()[:500]}...")
        if err.stdout:
            print(f"   Sortie: {err.stdout.strip()[:500]}...")
        
        print()
        
        if continue_on_error:
            print("⚠️  Erreur ignorée, continuation...\n")
            return False
        else:
            sys.exit(err.returncode)
    
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        if not continue_on_error:
            sys.exit(1)
        return False

def run_quarto_with_retry(qmd_file):
    """Exécute Quarto avec retry en cas d'échec."""
    print(f"📊 Génération du rapport {qmd_file}")
    
    # Première tentative
    success = run_command(
        ["quarto", "render", qmd_file], 
        f"Génération de {qmd_file}",
        continue_on_error=True
    )
    
    if success:
        return True
    
    # Si échec et c'est le fichier PTME, essayer avec des options spéciales
    if "ptme" in qmd_file.lower():
        print(f"🔄 Retry pour {qmd_file} avec options spéciales...")
        
        # Essayer de forcer l'installation des packages dans le document
        try:
            # Créer un script R temporaire pour installer les packages
            temp_r_script = """
# Installation forcée des packages requis
packages <- c('gsubfn', 'DBI', 'dplyr', 'ggplot2', 'knitr', 'rmarkdown', 'plotly', 'DT', 'lubridate', 'stringr')
for(pkg in packages) {
  if(!require(pkg, character.only = TRUE, quietly = TRUE)) {
    install.packages(pkg, repos='https://cran.rstudio.com/')
    library(pkg, character.only = TRUE)
  }
}
"""
            
            with open("temp_install_packages.R", "w") as f:
                f.write(temp_r_script)
            
            print("📦 Installation forcée des packages R...")
            subprocess.run(["Rscript", "temp_install_packages.R"], check=True)
            
            # Nettoyer le fichier temporaire
            os.remove("temp_install_packages.R")
            
            # Retry Quarto
            return run_command(
                ["quarto", "render", qmd_file], 
                f"Retry génération de {qmd_file}",
                continue_on_error=True
            )
            
        except Exception as e:
            print(f"❌ Retry échoué: {e}")
            return False
    
    return False

def main():
    """Fonction principale."""
    print("🚀 Début de l'orchestration des pipelines et rapports")
    print(f"📁 Répertoire de travail: {os.getcwd()}\n")
    
    # Vérifier les dépendances
    if not check_dependencies():
        print("❌ Échec de la vérification des dépendances")
        sys.exit(1)
    
    # 1. Exécution des scripts Python
    print("=" * 60)
    print("🐍 PHASE 1: Exécution des pipelines Python")
    print("=" * 60)
    
    failed_pipelines = []
    
    for script in pipelines:
        success = run_command(
            [sys.executable, script], 
            f"Exécution du pipeline {script}",
            continue_on_error=True
        )
        
        if not success:
            failed_pipelines.append(script)
    
    # 2. Génération des rapports Quarto
    print("=" * 60)
    print("📊 PHASE 2: Génération des rapports Quarto")
    print("=" * 60)
    
    failed_reports = []
    
    for qmd in qmd_files:
        success = run_quarto_with_retry(qmd)
        
        if not success:
            failed_reports.append(qmd)
    
    # Résumé final
    print("=" * 60)
    print("📋 RÉSUMÉ FINAL")
    print("=" * 60)
    
    if failed_pipelines:
        print(f"❌ Pipelines échoués: {failed_pipelines}")
    else:
        print("✅ Tous les pipelines ont réussi")
    
    if failed_reports:
        print(f"❌ Rapports échoués: {failed_reports}")
    else:
        print("✅ Tous les rapports ont été générés")
    
    if failed_pipelines or failed_reports:
        print("\n⚠️  Exécution terminée avec des erreurs")
        sys.exit(1)
    else:
        print("\n🎉 Exécution terminée avec succès!")
        sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Interruption par l'utilisateur (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

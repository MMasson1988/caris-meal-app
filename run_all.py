#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'exécution de run_all.sh avec gestion des erreurs Quarto/R et Git
Auteur: CARIS Dashboard Team
Date: 2025
"""

import os
import sys
import subprocess
import platform
import time
import shutil
from pathlib import Path
from datetime import datetime

def check_quarto_installation():
    """Vérifie si Quarto est installé et accessible."""
    try:
        result = subprocess.run(['quarto', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Quarto installé: {result.stdout.strip()}")
            return True
        else:
            print("❌ Quarto non accessible")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Quarto non trouvé dans le PATH")
        return False

def check_r_installation():
    """Vérifie si R est installé et accessible."""
    try:
        result = subprocess.run(['R', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ R installé: {result.stdout.split(chr(10))[0]}")  # Fix: chr(10) au lieu de \\n
            return True
        else:
            print("❌ R non accessible")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ R non trouvé dans le PATH")
        return False

def check_git_installation():
    """Vérifie si Git est installé et accessible."""
    try:
        result = subprocess.run(['git', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Git installé: {result.stdout.strip()}")
            return True
        else:
            print("❌ Git non accessible")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Git non trouvé dans le PATH")
        return False

def check_git_repo():
    """Vérifie si le répertoire courant est un repo Git."""
    try:
        result = subprocess.run(['git', 'status'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Répertoire Git valide")
            return True
        else:
            print("❌ Pas un répertoire Git valide")
            return False
    except Exception as e:
        print(f"❌ Erreur lors de la vérification du repo Git: {e}")
        return False

def git_commit_site():
    """Exécute git add _site et git commit avec la date du jour."""
    try:
        # Obtenir la date du jour
        today = datetime.now().strftime('%Y-%m-%d')
        commit_message = f"Mon commit du {today}"
        
        print("📁 Ajout du répertoire _site à Git...")
        
        # Vérifier si le répertoire _site existe
        site_path = Path("_site")
        if not site_path.exists():
            print("⚠️ Le répertoire _site n'existe pas. Création d'un répertoire vide...")
            site_path.mkdir(exist_ok=True)
            # Créer un fichier .gitkeep pour permettre l'ajout du répertoire
            (site_path / ".gitkeep").touch()
        
        # Vérifier s'il y a des fichiers dans _site
        site_files = list(site_path.glob('*'))
        if not site_files:
            print("⚠️ Le répertoire _site est vide. Ajout d'un fichier .gitkeep")
            (site_path / ".gitkeep").touch()
        
        # Git add _site
        result_add = subprocess.run(['git', 'add', '_site'], 
                                  capture_output=True, text=True, timeout=30)
        
        if result_add.returncode != 0:
            print(f"❌ Erreur lors de git add: {result_add.stderr}")
            return False
        
        print("✅ git add _site réussi")
        
        # Vérifier s'il y a des changements à commiter
        result_status = subprocess.run(['git', 'status', '--porcelain'], 
                                     capture_output=True, text=True, timeout=10)
        
        if not result_status.stdout.strip():
            print("ℹ️ Aucun changement à commiter")
            return True
        
        print(f"💾 Commit avec le message: '{commit_message}'")
        
        # Git commit
        result_commit = subprocess.run(['git', 'commit', '-m', commit_message], 
                                     capture_output=True, text=True, timeout=30)
        
        if result_commit.returncode == 0:
            print("✅ Git commit réussi")
            print(f"📝 Message: {commit_message}")
            
            # Afficher un résumé du commit
            if result_commit.stdout:
                print(f"📊 Résumé: {result_commit.stdout.strip()}")
            
            return True
        else:
            print(f"❌ Erreur lors du commit: {result_commit.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Timeout lors des opérations Git")
        return False
    except Exception as e:
        print(f"❌ Erreur lors des opérations Git: {e}")
        return False

def find_r_executable():
    """Trouve l'exécutable R sur le système."""
    possible_paths = []
    
    if platform.system() == "Windows":
        # Chemins possibles pour R sur Windows
        possible_paths = [
            r"C:\Program Files\R\R-4.4.1\bin\R.exe",
            r"C:\Program Files\R\R-4.3.3\bin\R.exe",
            r"C:\Program Files\R\R-4.3.2\bin\R.exe",
            r"C:\Program Files\R\R-4.3.1\bin\R.exe",
            r"C:\Program Files\R\R-4.2.3\bin\R.exe",
        ]
        
        # Recherche automatique dans Program Files
        program_files = Path("C:/Program Files/R")
        if program_files.exists():
            for r_dir in sorted(program_files.glob("R-*"), reverse=True):  # Plus récent en premier
                r_exe = r_dir / "bin" / "R.exe"
                if r_exe.exists():
                    possible_paths.insert(0, str(r_exe))  # Ajouter en début de liste
    
    else:  # Linux/Mac
        possible_paths = [
            "/usr/bin/R",
            "/usr/local/bin/R",
            "/opt/R/bin/R"
        ]
    
    # Chercher R dans le PATH en premier
    r_in_path = shutil.which("R")
    if r_in_path:
        print(f"✅ R trouvé dans le PATH: {r_in_path}")
        return r_in_path
    
    # Sinon, chercher dans les chemins possibles
    for path in possible_paths:
        if Path(path).exists():
            print(f"✅ R trouvé à: {path}")
            return path
    
    print("❌ R non trouvé")
    return None

def configure_quarto_r():
    """Configure le chemin R pour Quarto."""
    print("🔧 Configuration de Quarto avec R...")
    
    r_path = find_r_executable()
    if not r_path:
        print("❌ Impossible de trouver l'installation R")
        return False
    
    try:
        # Définir la variable d'environnement QUARTO_R
        os.environ['QUARTO_R'] = r_path
        
        # Configurer Quarto (uniquement sur Windows)
        if platform.system() == "Windows":
            try:
                subprocess.run(['setx', 'QUARTO_R', r_path], 
                             capture_output=True, check=False, timeout=30)
            except subprocess.TimeoutExpired:
                print("⚠️ Timeout lors de setx, mais variable d'environnement définie")
        
        print(f"✅ QUARTO_R configuré: {r_path}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la configuration: {e}")
        return False

def run_python_pipelines():
    """Exécute les pipelines Python avant les rapports Quarto."""
    pipelines = [
        "oev_pipeline.py",
        "ptme_pipeline.py", 
        "muso_pipeline.py",
        "garden_pipeline.py"
    ]
    
    print("🐍 Exécution des pipelines Python...")
    
    for pipeline in pipelines:
        if Path(pipeline).exists():
            print(f"🔄 Exécution de {pipeline}...")
            try:
                result = subprocess.run(
                    [sys.executable, pipeline],
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minutes par pipeline
                )
                
                if result.returncode == 0:
                    print(f"✅ {pipeline} terminé avec succès")
                else:
                    print(f"⚠️ {pipeline} terminé avec des avertissements")
                    if result.stderr:
                        print(f"Erreurs: {result.stderr[:200]}...")
                        
            except subprocess.TimeoutExpired:
                print(f"⏰ Timeout pour {pipeline}")
                return False
            except Exception as e:
                print(f"❌ Erreur lors de l'exécution de {pipeline}: {e}")
                return False
        else:
            print(f"⚠️ Pipeline {pipeline} non trouvé")
    
    return True

def run_quarto_reports():
    """Exécute les rapports Quarto."""
    qmd_files = [
        "tracking-oev.qmd",
        "tracking-ptme.qmd",
        "tracking-muso.qmd",
        "tracking-gardening.qmd"
    ]
    
    print("📊 Génération des rapports Quarto...")
    
    for qmd_file in qmd_files:
        if Path(qmd_file).exists():
            print(f"📄 Rendu de {qmd_file}...")
            try:
                result = subprocess.run(
                    ['quarto', 'render', qmd_file],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes par rapport
                )
                
                if result.returncode == 0:
                    print(f"✅ {qmd_file} rendu avec succès")
                else:
                    print(f"❌ Erreur lors du rendu de {qmd_file}")
                    if result.stderr:
                        print(f"Erreurs: {result.stderr[:200]}...")
                    return False
                    
            except subprocess.TimeoutExpired:
                print(f"⏰ Timeout pour {qmd_file}")
                return False
            except Exception as e:
                print(f"❌ Erreur lors du rendu de {qmd_file}: {e}")
                return False
        else:
            print(f"⚠️ Fichier {qmd_file} non trouvé")
    
    return True

def run_shell_script():
    """Exécute le script run_all.sh selon le système d'exploitation."""
    script_path = "./run_all.sh"
    
    # Vérifier si le script existe
    if not Path(script_path).exists():
        print(f"❌ Script non trouvé: {script_path}")
        print("🔄 Exécution des étapes manuellement...")
        
        # Exécuter manuellement les étapes
        success = True
        success &= run_python_pipelines()
        if success:
            success &= run_quarto_reports()
        
        return success
    
    try:
        print("🚀 Exécution de run_all.sh...")
        print("=" * 50)
        
        if platform.system() == "Windows":
            # Sur Windows, utiliser Git Bash, WSL ou PowerShell
            commands_to_try = [
                ["bash", script_path],
                ["wsl", "bash", script_path],
                ["powershell", "-Command", f"& '{script_path}'"],
                ["cmd", "/c", script_path.replace('./run_all.sh', 'run_all.bat')]  # Au cas où il y aurait un .bat
            ]
            
            for cmd in commands_to_try:
                try:
                    print(f"Tentative avec: {' '.join(cmd)}")
                    result = subprocess.run(
                        cmd,
                        cwd=os.getcwd(),
                        capture_output=False,
                        text=True,
                        timeout=1800  # 30 minutes timeout
                    )
                    
                    if result.returncode == 0:
                        print("✅ Script exécuté avec succès!")
                        return True
                    else:
                        print(f"⚠️ Script terminé avec code: {result.returncode}")
                        continue
                        
                except FileNotFoundError:
                    print(f"❌ Commande non trouvée: {cmd[0]}")
                    continue
                except subprocess.TimeoutExpired:
                    print("⏰ Timeout - le script prend trop de temps")
                    return False
            
            print("❌ Impossible d'exécuter le script sur Windows")
            print("🔄 Tentative d'exécution manuelle...")
            success = True
            success &= run_python_pipelines()
            if success:
                success &= run_quarto_reports()
            return success
            
        else:  # Linux/Mac
            # Rendre le script exécutable
            subprocess.run(['chmod', '+x', script_path], check=False)
            
            result = subprocess.run(
                [script_path],
                cwd=os.getcwd(),
                capture_output=False,
                text=True,
                timeout=1800  # 30 minutes timeout
            )
            
            if result.returncode == 0:
                print("✅ Script exécuté avec succès!")
                return True
            else:
                print(f"❌ Script terminé avec code d'erreur: {result.returncode}")
                return False
                
    except subprocess.TimeoutExpired:
        print("⏰ Timeout - le script prend trop de temps à s'exécuter")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution: {e}")
        return False

def main():
    """Fonction principale."""
    print("🔄 CARIS Dashboard - Exécution complète avec Git")
    print("=" * 60)
    
    # Changer vers le répertoire du script
    script_dir = Path(__file__).parent
    original_dir = os.getcwd()
    
    try:
        os.chdir(script_dir)
        print(f"📁 Répertoire de travail: {os.getcwd()}")
        
        # Vérifications préliminaires
        print("\n🔍 Vérification des dépendances...")
        
        quarto_ok = check_quarto_installation()
        r_ok = check_r_installation()
        git_ok = check_git_installation()
        git_repo_ok = check_git_repo() if git_ok else False
        
        # Si R n'est pas accessible, essayer de le configurer
        if not r_ok:
            print("\n🔧 Tentative de configuration de R...")
            if not configure_quarto_r():
                print("❌ Impossible de configurer R. Veuillez installer R ou vérifier le PATH.")
                return 1
            # Revérifier R après configuration
            r_ok = check_r_installation()
        
        # Si Quarto n'est pas accessible, essayer de le configurer
        if not quarto_ok:
            print("\n🔧 Tentative de configuration de Quarto...")
            configure_quarto_r()
            
            # Vérifier à nouveau
            quarto_ok = check_quarto_installation()
            if not quarto_ok:
                print("❌ Impossible de configurer Quarto. Veuillez installer Quarto.")
                return 1
        
        if not git_ok:
            print("⚠️ Git n'est pas installé. Les opérations Git seront ignorées.")
        elif not git_repo_ok:
            print("⚠️ Ce répertoire n'est pas un repo Git. Les opérations Git seront ignorées.")
        
        print("\n✅ Vérifications terminées!")
        
        # Pause avant exécution
        print("\n⏳ Démarrage dans 3 secondes...")
        time.sleep(3)
        
        # Exécuter le script principal
        print("\n" + "="*60)
        print("🚀 ÉTAPE 1: Exécution des pipelines et rapports")
        print("="*60)
        
        success = run_shell_script()
        
        if not success:
            print("\n💥 Échec de l'exécution du script principal")
            print("🔧 Vérifiez les logs ci-dessus pour plus de détails.")
            return 1
        
        # Opérations Git
        if git_ok and git_repo_ok:
            print("\n" + "="*60)
            print("📝 ÉTAPE 2: Opérations Git")
            print("="*60)
            
            git_success = git_commit_site()
            
            if git_success:
                print("✅ Opérations Git terminées avec succès!")
            else:
                print("⚠️ Erreur lors des opérations Git (non critique)")
        else:
            print("\n⚠️ Opérations Git ignorées (Git non disponible ou repo invalide)")
        
        print("\n" + "="*60)
        print("🎉 PROCESSUS TERMINÉ AVEC SUCCÈS!")
        print("="*60)
        print("📊 Les rapports ont été générés dans le répertoire courant.")
        if git_ok and git_repo_ok:
            print("📝 Les changements ont été ajoutés au contrôle de version Git.")
        
        return 0
        
    finally:
        # Restaurer le répertoire original
        os.chdir(original_dir)

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⛔ Interruption par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
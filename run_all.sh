#!/bin/bash

# ================================
# 🚀 SCRIPT D'EXÉCUTION AUTOMATIQUE
# - 3 scripts Python
# - 3 fichiers Quarto
# - Opérations Git automatiques
# - Gestion des erreurs par fichier
# ================================

echo "🔁 Début de l'exécution globale"
echo "📅 Date : $(date)"
echo "-------------------------------"

# ========== PYTHON ==========
echo "🐍 [1/3] Exécution des scripts Python..."

PY_SCRIPTS=("oev_pipeline.py" "ptme_pipeline.py" "garden_pipeline.py" "muso_pipeline.py")
FAILED_PY=()

for file in "${PY_SCRIPTS[@]}"; do
    echo "⚙️ Exécution : $file"
    
    # Remplacer python3 par python (compatible Windows)
    python "$file"
    
    if [ $? -ne 0 ]; then
        echo "❌ Échec : $file"
        FAILED_PY+=("$file")
    else
        echo "✅ Succès : $file"
    fi
done

# ========== QUARTO ==========
echo ""
echo "📝 [2/3] Rendu des fichiers Quarto..."

QMD_FILES=("tracking-ptme.qmd" "tracking-oev.qmd" "tracking-gardening.qmd" "tracking-muso.qmd")
FAILED_QMD=()

for file in "${QMD_FILES[@]}"; do
    echo "📄 Rendu : $file"
    quarto render "$file"
    if [ $? -ne 0 ]; then
        echo "❌ Échec : $file"
        FAILED_QMD+=("$file")
    else
        echo "✅ Succès : $file"
    fi
done

# ========== GIT OPERATIONS ==========
echo ""
echo "📝 [3/3] Opérations Git..."

# Vérifier si on est dans un repository Git
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo "✅ Repository Git détecté"
    
    # Obtenir la date du jour
    DATE_TODAY=$(date +"%Y-%m-%d")
    COMMIT_MESSAGE="Mon commit du $DATE_TODAY"
    
    # Vérifier si le répertoire _site existe
    if [ ! -d "_site" ]; then
        echo "⚠️ Répertoire _site inexistant, création..."
        mkdir -p "_site"
        echo "# Generated site files" > "_site/.gitkeep"
    fi
    
    # Vérifier s'il y a des fichiers dans _site
    if [ -z "$(ls -A _site 2>/dev/null)" ]; then
        echo "⚠️ Répertoire _site vide, ajout d'un fichier .gitkeep"
        echo "# Generated site files" > "_site/.gitkeep"
    fi
    
    echo "📁 Ajout du répertoire _site à Git..."
    git add _site
    
    if [ $? -eq 0 ]; then
        echo "✅ git add _site réussi"
        
        # Vérifier s'il y a des changements à commiter
        if git diff --cached --quiet; then
            echo "ℹ️ Aucun changement à commiter dans _site"
        else
            echo "💾 Commit avec le message: '$COMMIT_MESSAGE'"
            git commit -m "$COMMIT_MESSAGE"
            
            if [ $? -eq 0 ]; then
                echo "✅ Git commit réussi"
                echo "📝 Message: $COMMIT_MESSAGE"
                
                # Afficher le hash du commit
                COMMIT_HASH=$(git rev-parse --short HEAD)
                echo "🔗 Hash du commit: $COMMIT_HASH"
                
                # Optionnel : proposer un push
                echo ""
                echo "💡 Pour pousser vers le repository distant, exécutez:"
                echo "   git push origin $(git branch --show-current)"
            else
                echo "❌ Échec du git commit"
                FAILED_GIT=true
            fi
        fi
    else
        echo "❌ Échec de git add _site"
        FAILED_GIT=true
    fi
else
    echo "⚠️ Pas un repository Git - opérations Git ignorées"
    echo "💡 Pour initialiser un repo Git, exécutez: git init"
    FAILED_GIT=false  # Pas une vraie erreur
fi

# ========== RAPPORT FINAL ==========
echo ""
echo "==============================="
echo "📋 RAPPORT D'EXÉCUTION FINALE"
echo "==============================="

# Compter les succès et échecs
TOTAL_SUCCESS=true

if [ ${#FAILED_PY[@]} -eq 0 ] && [ ${#FAILED_QMD[@]} -eq 0 ] && [ "$FAILED_GIT" != true ]; then
    echo "🎉 Tous les processus ont été exécutés avec succès!"
    echo ""
    echo "📊 Résumé:"
    echo "   ✅ Scripts Python: ${#PY_SCRIPTS[@]} réussis"
    echo "   ✅ Fichiers Quarto: ${#QMD_FILES[@]} rendus"
    echo "   ✅ Opérations Git: terminées"
else
    TOTAL_SUCCESS=false
    echo "⚠️ Certains processus ont échoué:"
    echo ""
    
    if [ ${#FAILED_PY[@]} -gt 0 ]; then
        echo "❌ Scripts Python échoués (${#FAILED_PY[@]}/${#PY_SCRIPTS[@]}):"
        for f in "${FAILED_PY[@]}"; do echo "   - $f"; done
        echo ""
    else
        echo "✅ Scripts Python: tous réussis (${#PY_SCRIPTS[@]}/${#PY_SCRIPTS[@]})"
    fi
    
    if [ ${#FAILED_QMD[@]} -gt 0 ]; then
        echo "❌ Fichiers Quarto échoués (${#FAILED_QMD[@]}/${#QMD_FILES[@]}):"
        for f in "${FAILED_QMD[@]}"; do echo "   - $f"; done
        echo ""
    else
        echo "✅ Fichiers Quarto: tous réussis (${#QMD_FILES[@]}/${#QMD_FILES[@]})"
    fi
    
    if [ "$FAILED_GIT" = true ]; then
        echo "❌ Opérations Git: échouées"
    else
        echo "✅ Opérations Git: réussies"
    fi
fi

echo ""
echo "📅 Fin d'exécution: $(date)"
echo "🔚 Script terminé."

# Code de sortie basé sur le succès global
if [ "$TOTAL_SUCCESS" = true ]; then
    exit 0
else
    exit 1
fi
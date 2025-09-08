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

    # ------ Corrections: commit & push fiables, sans créer _site ------
    # 1) Stager tous les changements (ajouts/suppressions/modifs)
    git add -A
    if [ $? -ne 0 ]; then
        echo "❌ Échec de 'git add -A'"
        FAILED_GIT=true
    else
        echo "✅ git add -A réussi"

        # 2) Commiter uniquement s'il y a des changements indexés
        if git diff --cached --quiet; then
            echo "ℹ️ Aucun changement à commiter"
            FAILED_GIT=false
        else
            echo "💾 Commit avec le message: '$COMMIT_MESSAGE'"
            if git commit -m "$COMMIT_MESSAGE"; then
                echo "✅ Git commit réussi"
                echo "📝 Message: $COMMIT_MESSAGE"
                COMMIT_HASH=$(git rev-parse --short HEAD)
                echo "🔗 Hash du commit: $COMMIT_HASH"

                # 3) Push automatique (avec -u si aucun upstream n'est défini)
                CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)
                if [ -z "$CURRENT_BRANCH" ]; then
                    CURRENT_BRANCH="main"
                fi

                if git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1; then
                    # Upstream existe déjà
                    if git push; then
                        echo "✅ git push réussi (upstream existant)"
                        FAILED_GIT=false
                    else
                        echo "❌ Échec de 'git push'"
                        FAILED_GIT=true
                    fi
                else
                    # Pas d'upstream → on le crée
                    if git push -u origin "$CURRENT_BRANCH"; then
                        echo "✅ git push réussi (upstream défini sur origin/$CURRENT_BRANCH)"
                        FAILED_GIT=false
                    else
                        echo "❌ Échec de 'git push -u origin $CURRENT_BRANCH'"
                        FAILED_GIT=true
                    fi
                fi
            else
                echo "❌ Échec du git commit"
                FAILED_GIT=true
            fi
        fi
    fi
    # ------ Fin corrections ------
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
        echo "❌ Fichiers Quarto échoués (${#FAILED_QMD[@]} / ${#QMD_FILES[@]}):"
        for f in "${FAILED_QMD[@]}"; do echo "   - $f"; done
        echo ""
    else
        echo "✅ Fichiers Quarto: tous réussis (${#QMD_FILES[@]} / ${#QMD_FILES[@]})"
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

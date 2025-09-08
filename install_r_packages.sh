#!/usr/bin/env bash

echo "📦 Installation des packages R..."

Rscript --vanilla -e '
packages <- c(
  "knitr", "RMySQL", "odbc", "DBI", "viridis", "ggrepel", "ggiraphExtra",
  "hrbrthemes", "plotly", "stringr", "RColorBrewer", "tidyverse",
  "lubridate", "scales", "extrafont", "DT", "data.table", "readxl",
  "forcats", "writexl", "reticulate", "anytime", "kableExtra", "tm",
  "stopwords", "wordcloud2"
)

install_if_missing <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    message(paste("🔧 Installation du package:", pkg))
    install.packages(pkg, dependencies = TRUE)
  }
}

invisible(sapply(packages, install_if_missing))

invisible(sapply(packages, function(pkg) {
  suppressPackageStartupMessages(library(pkg, character.only = TRUE))
}))

cat("\n✅ Tous les packages sont installés et chargés.\n")
'

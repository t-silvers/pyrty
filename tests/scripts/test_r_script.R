# Usage: Rscript test_r_script.R --c 3.14
options(warn=-1)
suppressPackageStartupMessages(library(optparse))
suppressPackageStartupMessages(library(tidyverse))
option_list <- list(make_option('--c', type = 'double'))
opt <- parse_args(OptionParser(option_list=option_list))
a <- 1:5
df <- tibble::tibble(a, b = a * 2, c = opt$c)
try(writeLines(readr::format_csv(df), stdout()), silent=TRUE)
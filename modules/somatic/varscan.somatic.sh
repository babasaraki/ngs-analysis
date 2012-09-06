#!/bin/bash
##
## DESCRIPTION:   Run varscan somatic on normal/tumor pair of mpileups
##
## USAGE:         varscan.somatic.sh
##                                   normal.mpileup
##                                   tumor.mpileup
##                                   sample_name
##                                   somatic_pval
##                                   tumor_purity 
##
## OUTPUT:        out_prefix.snp out_prefix.indel
##

# Load analysis config
source $NGS_ANALYSIS_CONFIG

# Check correct usage
usage 5 $# $0

PILEUP_NORM=$1
PILEUP_TUMOR=$2
SAMPLE_NAME=$3
SOMATIC_PVAL=$4
TUMOR_PURITY=$5

# Format output
OUT_PREFIX=$SAMPLE_NAME.varscan

# If output file already exists and has content, then don't run
assert_file_not_exists_w_content $OUT_PREFIX.snp

# Run tool
$VARSCAN                                \
  somatic                               \
  $PILEUP_NORM                          \
  $PILEUP_TUMOR                         \
  $OUT_PREFIX                           \
  --min-coverage-normal 10              \
  --min-coverage-tumor 6                \
  --min-var-freq 0.25                   \
  --min-freq-for-hom 0.80               \
  --normal-purity 1.00                  \
  --tumor-purity $TUMOR_PURITY          \
  --somatic-p-value $SOMATIC_PVAL       \
  --p-value 0.99                        \
  --strand-filter 1                     \
  &> $OUT_PREFIX.log


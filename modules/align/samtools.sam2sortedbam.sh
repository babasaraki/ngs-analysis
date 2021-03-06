#!/bin/bash
## 
## DESCRIPTION:   Covert sam to bam and sort the bam file using samtools
##
## USAGE:         samtools.sam2sortedbam.sh sample.sam.gz
##
## OUTPUT:        sample.sort.bam
##

# Load analysis config
source $NGS_ANALYSIS_CONFIG

# Check correct usage
usage 1 $# $0

INPUTSAM=$1
OUTPREFIX=`filter_ext $INPUTSAM 2`.sort
OUTPUTLOG=$OUTPREFIX.bam.log

$SAMTOOLS                    \
  view                       \
  -uS                        \
  $INPUTSAM                  \
  | samtools                 \
      sort                   \
      -                      \
      $OUTPREFIX             \
      &> $OUTPUTLOG

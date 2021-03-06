#!/bin/bash
##
## DESCRIPTION:   Assess sequence coverage in bam file(s)
##
## USAGE:         gatk.depthofcoverage.wes.sh
##                                            ref.fa
##                                            target_region
##                                            out_prefix
##                                            input1.bam
##                                            [input2.bam [...]]
##
## OUTPUT:        Coverage summaries
##

# Load analysis config
source $NGS_ANALYSIS_CONFIG

# Check correct usage
usage_min 4 $# $0

# Process input params
PARAMS=($@)
NUM_PARAMS=${#PARAMS[@]}
REF=${PARAMS[0]}
TARGET_REGION=${PARAMS[1]}
NUM_BAMFILES=$(($NUM_PARAMS - 3))
BAMFILES=${PARAMS[@]:3:$NUM_BAMFILES}

# Format output filenames
OUTPREFIX=${PARAMS[2]}.depthofcov.wes
OUTPUTLOG=$OUTPREFIX.log

# Format list of input bam files
INPUTBAM=''
for bamfile in $BAMFILES; do
  # Check if file exists
  assert_file_exists_w_content $bamfile
  INPUTBAM=$INPUTBAM' -I '$bamfile
done

# Run tool
`javajar 128g` $GATK            \
  -T DepthOfCoverage            \
  -R $REF                       \
  $INPUTBAM                     \
  -o $OUTPREFIX                 \
  -L $TARGET_REGION             \
  &> $OUTPUTLOG


# Arguments for DepthOfCoverage:
#  -o,--out <out>                                                        An output file created by the walker.  Will 
#                                                                        overwrite contents if file exists
#  -mmq,--minMappingQuality <minMappingQuality>                          Minimum mapping quality of reads to count towards 
#                                                                        depth. Defaults to -1.
#  --maxMappingQuality <maxMappingQuality>                               Maximum mapping quality of reads to count towards 
#                                                                        depth. Defaults to 2^31-1 (Integer.MAX_VALUE).
#  -mbq,--minBaseQuality <minBaseQuality>                                Minimum quality of bases to count towards depth. 
#                                                                        Defaults to -1.
#  --maxBaseQuality <maxBaseQuality>                                     Maximum quality of bases to count towards depth. 
#                                                                        Defaults to 127 (Byte.MAX_VALUE).
#  -baseCounts,--printBaseCounts                                         Will add base counts to per-locus output.
#  -omitLocusTable,--omitLocusTable                                      Will not calculate the per-sample per-depth 
#                                                                        counts of loci, which should result in speedup
#  -omitIntervals,--omitIntervalStatistics                               Will omit the per-interval statistics section, 
#                                                                        which should result in speedup
#  -omitBaseOutput,--omitDepthOutputAtEachBase                           Will omit the output of the depth of coverage at 
#                                                                        each base, which should result in speedup
#  -geneList,--calculateCoverageOverGenes <calculateCoverageOverGenes>   Calculate the coverage statistics over this list 
#                                                                        of genes. Currently accepts RefSeq.
#  --outputFormat <outputFormat>                                         the format of the output file (e.g. csv, table, 
#                                                                        rtable); defaults to r-readable table
#  --includeRefNSites                                                    If provided, sites with reference N bases but 
#                                                                        with coverage from neighboring reads will be 
#                                                                        included in DoC calculations.
#  --printBinEndpointsAndExit                                            Prints the bin values and exits immediately. Use 
#                                                                        to calibrate what bins you want before running on 
#                                                                        data.
#  --start <start>                                                       Starting (left endpoint) for granular binning
#  --stop <stop>                                                         Ending (right endpoint) for granular binning
#  --nBins <nBins>                                                       Number of bins to use for granular binning
#  -omitSampleSummary,--omitPerSampleStats                               Omits the summary files per-sample. These 
#                                                                        statistics are still calculated, so this argument 
#                                                                        will not improve runtime.
#  -pt,--partitionType <partitionType>                                   Partition type for depth of coverage. Defaults to 
#                                                                        sample. Can be any combination of sample, 
#                                                                        readgroup, library.
#  -dels,--includeDeletions                                              Include information on deletions
#  --ignoreDeletionSites                                                 Ignore sites consisting only of deletions
#  -ct,--summaryCoverageThreshold <summaryCoverageThreshold>             for summary file outputs, report the % of bases 
#                                                                        coverd to >= this number. Defaults to 15; can 
#                                                                        take multiple arguments.

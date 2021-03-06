#!/usr/bin/env python

import re
import sys
from collections import namedtuple

class VcfFile(file):
    '''
    Extension of the python File class to handle vcf formatted files
    '''
    
    # Column names described in header line
    column_names = None

#    def readline(self):
#        '''
#        Overloads the readline method of the File class
#        in order to remember the line that was read in
#        '''
#        self.last_line = file.readline(self)
#        return self.last_line

    def is_meta(self, line):
        '''
        Check to see if line is meta
        '''
        if line[0:2] == '##':
            return True
        return False

    def is_header(self, line):
        '''
        Check to see if line is header line
        '''
        if line[0:1] != '#':
            return False

        if line[0:2] == '##':
            return False
        
        la = line[1:].strip().split()
        # Just check the first 3 columns
        if la[0] != 'CHROM':
            return False
        if la[1] != 'POS':
            return False
        if la[2] != 'ID':
            return False
        return True

    def set_column_names(self, header_line):
        '''
        Parse the header line and set the column names
        '''
        # Check that the line is header line
        if not self.is_header(header_line):
            raise ValueError('This is not a header line:\n\t%s\n' % header_line)

        # Parse the line
        self.column_names = header_line[1:].strip().split()

    def jump2variants(self):
        '''
        Skip ahead to the variants section of the vcf file
        The column names in the header line will be set as an attribute
        The next readline() call will read the first variant line
        in the file
        Warning: should only be used once, at the beginning of the file
        '''
        while True:
            line = self.readline()
            if not self.is_meta(line):
                self.set_column_names(line)
                break

    def is_variant_line(self, line):
        '''
        Validate a variant line string
        '''
        if self.is_meta(line):
            return False
        if self.is_header(line):
            return False
        if len(line.strip().split()) != len(self.column_names):
            return False
        return True

    def read_variant(self):
        '''
        Parse the variant line, and call the parse_line method and return the
        resulting output
        NOTE:
          - This function will cause this iterator to move forward, since
            readline() will be called.
        '''
        # Read in the next variant line
        line = self.readline()

        # Check if end of file is reached
        if not line:
            raise StopIteration

        # Generate dictionary and return it
        return self.parse_line(line)

    def parse_line(self, line):
        '''
        Parse a line of vcf variant and return a dictionary mapping column names
        to variant values
        NOTE:
          - If the next line to read in is not a variant line, the function will
            raise an error.
        '''
        # Ensure that the line is a variant line
        if not self.is_variant_line(line):
            raise ValueError('This is not a variant line:\n\t%s\n' % line)

        return dict(zip(self.column_names, line.strip().split()))

    def parse_info(self, variant):
        '''
        For those field=val pairs in the info string that contain = sign,
        Generate a dictionary that maps the info column fields to their
        corresponding values and set it as an attribute of this object.
        Return the ones that do not have the = sign in a separate list.
        Input: variant dictionary returned by the read_variant() method
               or the parse_line(line) method
        '''
        # Separate the fields within the info string
        equal_sign = []
        no_equal_sign = []
        for val in variant['INFO'].split(';'):
            if re.search(r'=', val):
                equal_sign.append(val)
            else:
                no_equal_sign.append(val)

        # Check equal_sign empty
        if not equal_sign:
            return None, no_equal_sign

        # Generate the mapping dictionary
        return dict(map(lambda field_eq_val: field_eq_val.split('='),
                        equal_sign)), no_equal_sign

    def get_sample_names(self):
        '''
        Return the sample names as a list in the column order that they appear
        Note: The header line must have been read in.
        '''
        return self.column_names[9:]

    def parse_samples(self, variant):
        '''
        Generate a mapping from format fields to each sample\'s values
        Return a 2D dictionary mapping sample2formatfield2val

        Input: variant dictionary returned by the read_variant() method or the
               parse_line(line) method
        '''
        sample2field2val = {}
        formats = variant['FORMAT'].split(':')
        for sample in self.get_sample_names():
            sample2field2val[sample] = dict(zip(variant['FORMAT'].split(':'), variant[sample].split(':')))
        return sample2field2val

    def get_sample_gt(self, variant, sample, phased=False):
        '''
        Get a sample\'s genotype.
        The GT field shows alleles, not the actual nucleotide bases.
        Substitute the nucleotide bases into the numeric alleles.
        
        Given an allele string, convert to genotype string
        i.e.  0/0, 0/1, 1|1 => A/A, A/C, C|C
        Separator:
          /: unphased
          |: phased

        Input:
          variant: dictionary returned by the read_variant() or the parse_line(line) methods
          sample: sample name
          phased: True | False, default False
          
        '''
        # Set separator
        sep = '/'
        if phased:
            sep = '|'

        # Get sample GT value
        sample2field2val = self.parse_samples(variant)
        alleles_str = sample2field2val[sample]['GT']
        alleles = alleles_str.split(sep)

        possible_genotypes = [variant['REF']] +  variant['ALT'].split(',')

        # Get ref/alt alleles
        bases = []
        for a in alleles:
            # No Call
            if a == '.':
                bases.append('N')
            # Allele index
            else:
                bases.append(possible_genotypes[int(a)])

        # For unphased, sort the genotype bases
        if not phased:
            bases = sorted(bases)
        return sep.join(bases)


class VarscanVcfFile(VcfFile):
    '''
    Extension of the VcfFile class for parsing VarScan output vcf files
    '''
    SOMATIC_STATUS_CODE2TEXT = {'0': 'Reference', 
                                '1': 'Germline',
                                '2': 'Somatic',
                                '3': 'LOH',
                                '5': 'Unknown'}

class SnpEffVcfFile(VarscanVcfFile):
    '''
    Extension of the VarscanVcfFile for parsing SNPEff output vcf files
    '''
    IMPACT_EFFECTS = [('High','SPLICE_SITE_ACCEPTOR'),
                      ('High','SPLICE_SITE_DONOR'),
                      ('High','START_LOST'),
                      ('High','EXON_DELETED'),
                      ('High','FRAME_SHIFT'),
                      ('High','STOP_GAINED'),
                      ('High','STOP_LOST'),
                      ('Moderate','NON_SYNONYMOUS_CODING'),
                      ('Moderate','CODON_CHANGE'),
                      ('Moderate','CODON_INSERTION'),
                      ('Moderate','CODON_CHANGE_PLUS_CODON_INSERTION'),
                      ('Moderate','CODON_DELETION'),
                      ('Moderate','CODON_CHANGE_PLUS_CODON_DELETION'),
                      ('Moderate','UTR_5_DELETED'),
                      ('Moderate','UTR_3_DELETED'),
                      ('Low','SYNONYMOUS_START'),
                      ('Low','NON_SYNONYMOUS_START'),
                      ('Low','START_GAINED'),
                      ('Low','SYNONYMOUS_CODING'),
                      ('Low','SYNONYMOUS_STOP'),
                      ('Low','NON_SYNONYMOUS_STOP'),
                      ('Modifier','UTR_5_PRIME'),
                      ('Modifier','UTR_3_PRIME'),
                      ('Modifier','REGULATION'),
                      ('Modifier','UPSTREAM'),
                      ('Modifier','DOWNSTREAM'),
                      ('Modifier','GENE'),
                      ('Modifier','TRANSCRIPT'),
                      ('Modifier','EXON'),
                      ('Modifier','INTRON_CONSERVED'),
                      ('Modifier','INTRON'),
                      ('Modifier','INTRAGENIC'),
                      ('Modifier','INTERGENIC'),
                      ('Modifier','INTERGENIC_CONSERVED'),
                      ('Modifier','NONE'),
                      ('Modifier','CHROMOSOME'),
                      ('Modifier','CUSTOM'),
                      ('Modifier','CDS')]
    effects_prioritized = ['RARE_AMINO_ACID',
                           'SPLICE_SITE_ACCEPTOR',
                           'SPLICE_SITE_DONOR',
                           'START_LOST',
                           'EXON_DELETED',
                           'FRAME_SHIFT',
                           'STOP_GAINED',
                           'STOP_LOST',
                           'NON_SYNONYMOUS_CODING',
                           'CODON_CHANGE',
                           'CODON_INSERTION',
                           'CODON_CHANGE_PLUS_CODON_INSERTION',
                           'CODON_DELETION',
                           'CODON_CHANGE_PLUS_CODON_DELETION',
                           'UTR_5_DELETED',
                           'UTR_3_DELETED',
                           'SYNONYMOUS_START',
                           'NON_SYNONYMOUS_START',
                           'START_GAINED',
                           'SYNONYMOUS_CODING',
                           'SYNONYMOUS_STOP',
                           'NON_SYNONYMOUS_STOP',
                           'UTR_5_PRIME',
                           'UTR_3_PRIME',
                           'REGULATION',
                           'UPSTREAM',
                           'DOWNSTREAM',
                           'GENE',
                           'TRANSCRIPT',
                           'EXON',
                           'INTRON_CONSERVED',
                           'INTRON',
                           'INTRAGENIC',
                           'INTERGENIC',
                           'INTERGENIC_CONSERVED',
                           'NONE',
                           'CHROMOSOME',
                           'CUSTOM',
                           'CDS']
    effect2priority = None
    
    Effect = namedtuple('Effect', ['effect',
                                   'impact',
                                   'functional_class',
                                   'codon_change',
                                   'aa_change',
                                   'gene',
                                   'gene_biotype',
                                   'coding',
                                   'transcript',
                                   'exon']) # Errors, Warnings

    def _set_effect2priority(self):
        '''
        Set the dictionary mapping effect to its priority number
        Priority number is based on the index of each effect in
        the effects_prioritized attribute
        '''
        self.effect2priority = dict(zip(self.effects_prioritized, range(len(self.effects_prioritized))))
    
    def set_prioritized_effects(self, effectslist):
        '''
        Setter for effects_prioritized attribute
        Will also set the effects2priority variable
        Input:
          effectslist: list of effects
        '''
        self.effects_prioritized = effectslist
        self._set_effect2priority()

    def parse_effects(self, variant):
        '''
        Parse the info column string in the vcf file, and extract
        a list of Effects objects sorted by their priority
        Inputs
          variant: dictionary returned by the read_variant() or
                   the parse_line(line) method
        '''
        # If effect2priority is not set, set it
        if self.effect2priority is None:
            self._set_effect2priority()
        
        # Extract out the effects information string
        effect_info_str = re.search('EFF=(.*)', variant['INFO']).group(1)
        effect_strs = effect_info_str.split(',')
        effects = []
        for effect_str in effect_strs:
            effect_val = re.search('(.+)\(', effect_str).group(1)
            effect_attrs = [effect_val] + re.search('\((.+)\)', effect_str).group(1).split('|')
            
            # Skip annotations with errors and warnings
            if len(effect_attrs) > len(self.Effect._fields):
                continue

            # Create namedtuple object
            effect = self.Effect._make(effect_attrs[:len(self.Effect._fields)])
            effects.append(effect)
        return sorted(effects, key=lambda eff: self.effect2priority[eff.effect])

    def select_highest_priority_effect(self, variant):
        '''
        Parse the info column string in the vcf file, and extract the highest
        priority effect as defined by the effects_prioritized attribute

        Inputs
          variant: dictionary returned by the read_variant() or the
                   parse_line(line) method
        '''        
        # Parse the effects
        effects = self.parse_effects(variant)

        # If there were no valid effects, return None
        if not effects:
            return None

        # Return the first element, which has the highest priority
        return effects[0]

    def find_selected_transcript_effects(self, variant, g2t):
        '''
        Given a variant (output of parse_line) and a mapping from gene to selected transcripts (g2t)
        find all transcripts within the variant annotation that were selected for the annotated genes
        '''
        found_effects = []
        for effect in self.parse_effects(variant):
            if effect.gene in g2t:
                if effect.transcript == g2t[effect.gene]:
                    found_effects.append(effect)
        return found_effects

# ------------------------------------------------------------------------------------- #
# Classes to handle a list of vcf files

class VcfFiles(list):
    '''
    Class to manage multiple VcfFile objects
    '''
    pass

class SnpEffVcfFiles(VcfFiles):
    '''
    Class to manage multiple SnpEffVcfFile objects
    Generate gene2transcript2effect2counts (g2t2e2c)
    Also updates a dictionary of effects to impacts
    '''
#     g2t2e2c = None
#     eff2imp = None
#     transcript2len = None
    
    def count_transcript_effects_single(self, vcffile, g2t2e2c, effect2impact, highest_priority=False):
        '''
        For a single vcf file, update the counts of the total number of transcripts and their effects
        g2t2e2c is a dictionary of counts for the transcript effects counts.
        effect22impact is a dictionary mapping effect to their corresponding impact.
        If highest_priority is set to True, count only the highest priority effect per variant.
        By default, will count all the transcript effects for each variant.
        '''
        with vcffile:
            vcffile.jump2variants()
            for line in vcffile:
                variant = vcffile.parse_line(line)

                # Use single highest priority, or all the transcript effects for the variant
                if highest_priority:
                    effects = [vcffile.select_highest_priority_effect(variant)]
                else:
                    effects = vcffile.parse_effects(variant)
                    
                # Update the counts
                for eff in effects:
                    a = eff.gene
                    b = eff.transcript
                    c = eff.effect
                    g2t2e2c[a][b][c] = g2t2e2c.setdefault(a, {}).setdefault(b, {}).setdefault(c, 0) + 1
                    
                    # Update effect to impact mapping
                    if eff.effect not in effect2impact:
                        effect2impact[eff.effect] = eff.impact

                    # Impact already set for effect but does not match current impact
                    elif effect2impact[eff.effect] != eff.impact:
                        exit_message = 'Multiple impacts for effect %s: %s, %s\nExiting.'
                        sys.stderr.write(exit_message % (eff.effect, eff.impact, effect2impact[eff.effect]))
                        sys.exit(1)

        return g2t2e2c, effect2impact
        
    def count_transcript_effects_all(self, highest_priority=False):
        '''
        For all vcf files in the list, count the transcript effects.
        '''
        g2t2e2c = {}
        effect2impact = {}
        for vcffile in self:
            self.count_transcript_effects_single(vcffile, g2t2e2c, effect2impact, highest_priority=highest_priority)

        #self.register_transcript_counts(g2t2e2c, effect2impact, None)
        return g2t2e2c, effect2impact

    def select_transcript_for_gene(self, g2t2e2c, effect2impact, transcript2len):
        '''
        For a gene, select transcript with highest mutation count with effects that have
        "HIGH" impact.
        If multiple transcripts result, select one with the longest transcript.
        If selected transcripts have the same length, then select randomly.
        '''
        def get_high_impact_count(_e2c):
            '''
            Given an effect to count mapping, sum up the counts of effects that have HIGH impact
            '''
            high_impact_count = 0
            for _e,_c in _e2c.iteritems():
                if effect2impact[_e] == 'HIGH':
                    high_impact_count += int(_c)
            return high_impact_count

        def get_transcript_w_most_high_impact(_t2e2c, _transcript2len):
            '''
            Given a set of transcript to effect to counts mapping, return transcript with the
            highest HIGH impact effects.  If more than 1 transcript results, select the longest.
            If still more than 1 transcript results, select randomly
            If no transcript results, return False
            '''

            # Filter by transcript2len mapping.  Those that do not have length data cannot be used
            usable_t2e2c = {}
            for _t,_e2c in _t2e2c.iteritems():
                if _t in _transcript2len:
                    usable_t2e2c[_t] = _e2c
            if len(usable_t2e2c) == 0:
                return False
            
            # Generate tuples (transcript, count) sorted from highest to lowest counts
            t_counts = sorted([(_t, get_high_impact_count(_e2c)) for _t,_e2c in usable_t2e2c.iteritems()],
                              key=lambda x: x[1], reverse=True)

            # Select the transcripts that have equal highest counts (could be one or more)
            highest_count = t_counts[0][1]
            transcripts_w_most_high_impact = [_t_c for _t_c in t_counts if _t_c[1] == highest_count]
            if len(transcripts_w_most_high_impact) == 1:
                return transcripts_w_most_high_impact[0][0]
            
            # Select longer transcript
            return sorted([(_t_c[0], _transcript2len[_t_c[0]]) for _t_c in transcripts_w_most_high_impact],
                          key=lambda x: x[1], reverse=True)[0][0]

        g2highestt = {}
        for g in g2t2e2c:
            # Find total HIGH impact mutation counts
            t = get_transcript_w_most_high_impact(g2t2e2c[g], transcript2len)
            if not t:
                continue
            g2highestt[g] = t
        
        return g2highestt

#     def register_transcript_counts(self, g2t2e2c, eff2imp, transcript2len):
#         '''
#         Set the following as instance variables:
#         transcript effect counts
#         effect to impact mapping
#         transcript2length mapping
#         '''
#         self.g2t2e2c = g2t2e2c
#         self.eff2imp = eff2imp
#         self.transcript2len = transcript2len

#     def select_single_gene_transcript(self, effects):
#         '''
#         Select the gene transcript with the most variants using the transcript effect counts
#         g2t2e2c, eff2imp and transcript2len  must be set using the register_transcript_counts method.
#         Input must be the output of VcfFile.parse_effects method
#         '''
#         # If the necessary variables are not set, return 
#         if self.g2t2e2c is None or self.eff2imp is None or self.transcript2len is None:
#             raise Exception("g2t2e2c, eff2imp, and transcript2len are not set!")
        

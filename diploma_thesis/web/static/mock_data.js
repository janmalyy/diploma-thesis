export const MOCK_RESULT =
{
"narrative_summary": "BRCA1 p.Arg7Cys (c.19C>T) is a rare missense change located in the N\u2011terminal region of the protein. Functional assays, including saturation\u2011genome\u2011editing and multifactorial likelihood analysis, have shown no impact on protein function or splicing, leading to a reclassification as benign or likely benign in several studies [PMC7814423; PMC6772163; PMC7272326]. In contrast, computational predictions using the RPMDS framework indicate a high structural deviation (33.4\u202f%) and classify the variant as deleterious, with ClinVar entries reporting conflicting interpretations of pathogenicity [PMC10098510]. Population data are limited: the variant has been identified in a few Argentinean breast/ovarian cancer cases and in a single Chinese breast cancer patient, but also in healthy controls, and was reported as a driver mutation in a metastatic esophageal squamous cell carcinoma subregion, albeit with low evidential strength [PMC3725882; PMC10679972]. Overall, the preponderance of functional evidence supports a benign effect, while computational and isolated tumor reports suggest possible pathogenicity, leaving the variant\u2019s clinical significance uncertain.",
"structured_summary": {
    "overall_pathogenicity": "uncertain",
    "overall_confidence": "low",
    "pathogenicity_counts": {
        "uncertain": 3,
        "supports pathogenicity": 2,
        "supports benignity": 2
    },
    "conflicting_evidence": true
},
"article_mentions":
[
    {
        "mentions": [
            {
                "quoted_text": "HGVS :Protein: DNA BIC: Status N Carrier (%) Co-occurrence with deleterious PredictionSIFT GVGD grade refSNP BRCA1 p.**Arg7Cys**c**19C > T**CU 2(1.1) - NT C15 rs144792613 p. Cys61Gly c.181 T > G D 1 (1.1) - NT C65 - p. Arg71Gly c.211A > G D 1 (1.1) - NT C65 - p. Val122Asp c.365 T > A NR 5 (5.3) BRCA2 T C0 - p. Gln139Lys c.415C > A NR 6...",
                "mention_type": "population",
                "claim": "uncertain",
                "strength": "low"
            },
            {
                "quoted_text": "Five of the 28 missense variants (Table 4) (i.e., p.**Arg7Cys** p. Cys61Gly, p. Arg71Gly, p. Tyr179Cys, and p. Met1652Thr in BRCA1, p. Asp2723His in BRCA2) were predicted to have an impact on protein structure upon evaluation by SIFT and GVGD (Table 4). BRCA1 p.**Arg7Cys** differently from the other non-conservative variants, has a rather low prediction score and was found in two cases. The high prediction values for BRCA1 p. Cys61Gly and BRCA1 p. Arg71gly agree with their previously reported pathogenicity (Table 4). Few reported data are available for BRCA2 p. Asp2723His. BRCA1 p. Met1652Thr, located in the BRCT tandem repeat region is predicted to result in a large volume change in rigid neighbourhood but structural and functional assays show normal peptide binding specificity and transcriptional activity. Tyr179Cys is also located in a highly conserved region and is listed as clinically importance unknown (CU) in BIC. Notably BRCA1 Tyr179Cys co-occurred with two other missense mutations, i.e., Phe486Leu and Asn550His, in an FH patient affected with pagetoid BC (AB80). These 3 mutations, already reported to occur together, may constitute a rare haplotype brca.iarc.fr/LOVD].",
                "mention_type": "computational",
                "claim": "uncertain",
                "strength": "low"
            },
            {
                "quoted_text": "Column names:\nb\"\\r\\n\\r\\nTable S1: BRCA1 sequence variants identified in Argentinean breast/ovarian\\r\\ncancer cases\\r\\n|Location |Codon |HGVS: |\\r\\n|Exon\nRows:\ncod 39|\\r\\n| |6 | |\\r\\n|2 **R7C****p.Arg7Cys**|\\r\\n|I-7 |- |- |c.441+36C>T |IVS7+36C>T |CU |19 |BRCA1 (AB40, AB67, AB82) |rs45569|As [55] |\\r\\n| | | | | | | |\ncod 39|\\r\\n| |6 | |\\r\\n|2 **R7C****p.Arg7Cys**|\\r\\n|I-7 |- |- |c.441+36C>T |IVS7+36C>T |CU |19 |BRCA1 (AB40, AB67, AB82) |rs45569|As [55] |\\r\\n| | | | | | | | |832 |",
                "mention_type": "population",
                "claim": "uncertain",
                "strength": "low"
            }
        ],
        "overall_article_summary": "The article reports that the BRCA1 p.Arg7Cys (R7C) variant was identified in a small number of Argentinean breast/ovarian cancer patients, classified as a variant of uncertain significance with low computational prediction scores, indicating limited evidence for pathogenicity.",
        "uncertainties_or_limitations": null,
        "article_id": "PMC3725882",
        "title": "BRCA1 And BRCA2 analysis of Argentinean breast/ovarian cancer patients selected for age and family history highlights a role for novel mutations of putative south-American origin",
        "relevance_score": 1.0,
        "pub_year": 2012,
        "data_sources": [
            "suppl",
            "pmc"
        ]
    },
    {
        "mentions": [
            {
                "quoted_text": "Column names:\nb'\\r\\n Supplementary Table 5 55 VUS detected in our study\\r\\n with distinct status in the Findlay et al. study\\r\\n\\r\\n Gene |Chr:posi |ref>alt |Type |hgvs_c |hgvs_p |Number (BCs) |Number (HCs)\\r\\n |Annotation | |BRCA1\nRows:\net al. study\\r\\n\\r\\n Gene |Chr:posi |ref>alt |Type |hgvs_c |hgvs_p |Number (BCs) |Number (HCs)\\r\\n |Annotation | |BRCA1 |17:41276135 |T>C |splice_acceptor_variant |c.-19-3A>G\\r\\n | |0 |4 |Benign | |BRCA1 |17:41276095 |G>A |missense_variant **c.19C>T**r\\n **p.Arg7Cys**|1 |1 |Benign | |BRCA1 |17:41276064 |G>C |missense_variant\\r\\n |c.50C>G |p.Ala17Gly |0 |1 |Benign | |BRCA1 |17:41276065 |C>A\\r\\n |missense_variant |c.49G>T |p.Ala17Ser |0 |1 |Benign | |BRCA1 |17:41276061\\r\\n |A>T",
                "mention_type": "functional",
                "claim": "supports benignity",
                "strength": "moderate"
            }
        ],
        "overall_article_summary": "The study identified the BRCA1 p.Arg7Cys (r7c) variant in one breast cancer patient and one healthy control and reclassified it as benign using saturation genome editing functional data.",
        "uncertainties_or_limitations": null,
        "article_id": "PMC7814423",
        "title": "Prevalence and reclassification of BRCA1 and BRCA2 variants in a large, unselected Chinese Han breast cancer cohort",
        "relevance_score": 1.0,
        "pub_year": 2021,
        "data_sources": [
            "suppl"
        ]
    },
    {
        "mentions": [
            {
                "quoted_text": "Table title: Table S11. Prediction of unknown Asian missense variants in BRCA1 BRCT and RING and BRCA2 BRC4 domains by RPMDS\nColumn names:\ncDNA*|Protein**|ExonicFunc.refGene|ClinVar classification|Structural deviation (%)|Classification\nRows\n:**c.19C>T|**p.**Arg7Cys**|nonsynonymous SNV|Conflicting interpretations of pathogenicity|33.3984375|Deleterious",
                "mention_type": "computational",
                "claim": "supports pathogenicity",
                "strength": "moderate"
            }
        ],
        "overall_article_summary": "The article reports that the BRCA1 p.Arg7Cys (c.19C>T) variant identified in Asian populations is computationally predicted to be deleterious, with a structural deviation of 33.4% and conflicting ClinVar interpretations.",
        "uncertainties_or_limitations": null,
        "article_id": "PMC10098510",
        "title": "Ethnic-specificity, evolution origin and deleteriousness of Asian BRCA variation revealed by over 7500 BRCA variants derived from Asian population",
        "relevance_score": 0.35,
        "pub_year": 2022,
        "data_sources": [
            "suppl"
        ]
    },
    {
        "mentions": [
            {
                "quoted_text": "Column names:\nGene|HGVS Nucleotide|HGVS Protein|Legacy Description Nucleotide|Legacy Description Protein|Segregation LR|Pathology LR|Co-occurrence LR|Family History LR|Case-Control LR|Combined LR (Odds for Causality)|Prior Probability of Pathogenicity|Posterior Probability|IARC Class|Comment regarding class assignment|Suggested frequency rule strength derived from this study|Frequency Category Assigned for LR derivation|gnomAD Highest Minor Allele Frequency|gnomAD Population with Highest Minor Allele Frequency|Single Observation in gnomAD|Functional Paper/s|Functional Category Assigned|Findlay_Function|Findlay_RNAscore|Findlay_RNAclass|Starita Depleted|Mesman_Complementation|Mesman_HDR|Mesman_Cisplatin|Mesman_Class|Bouwman_Selection|Bouwman_FxnClass|Fernandes2019_fClass|Fernandes2019_fCategory|Petitalot2019_ControlGroup|Petitalot2019_Class|Hart2018_Functional Class|Hart2018_HDR ratio|Predicted Variant Consequence|Allele-Specific Splicing Result Summary|Coded Splicing Effect|Splicing Paper/s (First author)|Splicing Assay Method/s|Splicing Result/s|Splicing Reference/s|Allele Specific Assay|ClinVar Class Summary|ClinVar Class Details by Submitter|ClinVar Date|Allele Count (All Populations)|Allele Count African|Allele Number African|MAF_African|Allele Count Latino|Allele Number Latino|MAF_Latino|Allele Count East Asian|Allele Number East Asian|MAF_EastAsian|Allele Count European (non-Finnish)|Allele Number European (non-Finnish)|MAF_NFE|Allele Count South Asian|Allele Number South Asian|MAF_SouthAsian\nRows:\nBRCA1**c.19C>T**p.**Arg7Cys**|138C>T**R7C**|||||||||Combined LR is not <0.5 or >2|moderate in favour of benign|>0 & <0.0001||European (Non-Finnish)||Findlay|No functional impact|FUNC||Not Depleted||||||||||||||missense_variant||||||||Conflicting_interpretations_of_pathogenicity|likely_benign|uncertain_significance|2011-07-25|2002-05-29|2017-07-24|2015-08-31|2017-01-04|2013-06-10|2017-04-12|2017-04-20||||||||||||||||",
                "mention_type": "functional",
                "claim": "supports benignity",
                "strength": "moderate"
            }
        ],
        "overall_article_summary": "The article\u2019s multifactorial likelihood analysis classifies the BRCA1 c.19C>T (p.Arg7Cys) variant as likely benign, supported by functional data showing no impact on protein function and a moderate likelihood ratio favoring benign classification.",
        "uncertainties_or_limitations": null,
        "article_id": "PMC6772163",
        "title": "Large scale multifactorial likelihood quantitative analysis of BRCA1 and BRCA2 variants: An ENIGMA resource to support clinical variant classification",
        "relevance_score": 0.13,
        "pub_year": 2019,
        "data_sources": [
            "suppl"
        ]
    },
    {
        "mentions": [
            {
                "quoted_text": "Column names:\nSupplementary Table 8. Detailed information of driver mutations in tumor subregions of each patient. Sample Status Hugo_Symbol Chromosome Strand Variant_Classification Variant_Type Reference_Allele Tumor_Seq_Allele1 Tumor_Seq_Allele2\nRows:\nNM_004244.5 467 361 106 187 187 0 P848-LNmet Trunk TP53 17 + Nonsense_Mutation SNP T T A c.871A>T p.Lys291Ter p.K291* NM_000546.5 1347 1101 246 662 661 1 P848-LNmet Branch BRCA1 17 + Missense_Mutation SNP G G A**rs80356994**c**19C>T**p**Arg7Cys**p**R7C**NM_007294.4 1269 1240 29 812 809 3 P768-PTsup Trunk OBSCN 1 + Nonsense_Mutation SNP C C G novel c.24800C>G p.Ser8267Ter p.S8267* NM_001271223.2 712 622 89 253 253 0 P768-PTsup Trunk LRP1B 2\n467 361 106 187 187 0 P848-LNmet Trunk TP53 17 + Nonsense_Mutation SNP T T A c.871A>T p.Lys291Ter p.K291* NM_000546.5 1347 1101 246 662 661 1 P848-LNmet Branch BRCA1 17 + Missense_Mutation SNP G G A**rs80356994**c**19C>T**p**Arg7Cys**p**R7C**NM_007294.4 1269 1240 29 812 809 3 P768-PTsup Trunk OBSCN 1 + Nonsense_Mutation SNP C C G novel c.24800C>G p.Ser8267Ter p.S8267* NM_001271223.2 712 622 89 253 253 0 P768-PTsup Trunk LRP1B 2 +\n106 187 187 0 P848-LNmet Trunk TP53 17 + Nonsense_Mutation SNP T T A c.871A>T p.Lys291Ter p.K291* NM_000546.5 1347 1101 246 662 661 1 P848-LNmet Branch BRCA1 17 + Missense_Mutation SNP G G A**rs80356994**c**19C>T**p**Arg7Cys**p**R7C**NM_007294.4 1269 1240 29 812 809 3 P768-PTsup Trunk OBSCN 1 + Nonsense_Mutation SNP C C G novel c.24800C>G p.Ser8267Ter p.S8267* NM_001271223.2 712 622 89 253 253 0 P768-PTsup Trunk LRP1B 2 +\n187 0 P848-LNmet Trunk TP53 17 + Nonsense_Mutation SNP T T A c.871A>T p.Lys291Ter p.K291* NM_000546.5 1347 1101 246 662 661 1 P848-LNmet Branch BRCA1 17 + Missense_Mutation SNP G G A**rs80356994**c**19C>T**p**Arg7Cys**p**R7C**NM_007294.4 1269 1240 29 812 809 3 P768-PTsup Trunk OBSCN 1 + Nonsense_Mutation SNP C C G novel c.24800C>G p.Ser8267Ter p.S8267* NM_001271223.2 712 622 89 253 253 0 P768-PTsup Trunk LRP1B 2 + Missense_Mutation SNP",
                "mention_type": "population",
                "claim": "supports pathogenicity",
                "strength": "low"
            }
        ],
        "overall_article_summary": "The study identifies the BRCA1 p.Arg7Cys (c.19C>T) missense variant as a driver mutation in a lymph node metastasis subregion of an esophageal squamous cell carcinoma patient.",
        "uncertainties_or_limitations": null,
        "article_id": "PMC10679972",
        "title": "Multi-omics analyses reveal spatial heterogeneity in primary and metastatic oesophageal squamous cell carcinoma",
        "relevance_score": 0.11,
        "pub_year": 2023,
        "data_sources": [
            "suppl"
        ]
    },
    {
        "mentions": [
            {
                "quoted_text": "Column names:\nVariant no.|Gene|cDNA|Protein|RefSeq ID|chr|coordinates (b38)|strand|SNV position|Splicing result|RNA-seq|Splice abberration|ClinVar|dbSNP|Gtex TPM|HSF|SSF|MaxEnt|NNSPLICE|AccGain_DeltaScore_SpliceAI|AccLoss_DeltaScore_SpliceAI|DonGain_DeltaScore_SpliceAI|DonLoss_DeltaScore_SpliceAI|SpliceAI_max\nRows:\n|BRCA1**c.19C>T**p.**Arg7Cys**|NM_007294.3**c.19C>T**chr17||-|A+38|Normal|None|None|Likely benign/Uncertain significance**rs80356994**|NAS (+0.9)|No effect to NSS|No effect to NSS|No effect to NSS|||||",
                "mention_type": "functional",
                "claim": "no claim",
                "strength": "moderate"
            }
        ],
        "overall_article_summary": "Blood RNA analysis identified that the BRCA1 c.19C>T (p.Arg7Cys) variant does not affect splicing, providing functional evidence against a pathogenic effect.",
        "uncertainties_or_limitations": null,
        "article_id": "PMC7272326",
        "title": "Blood RNA analysis can increase clinical diagnostic rate and resolve variants of uncertain significance",
        "relevance_score": 0.11,
        "pub_year": 2020,
        "data_sources": [
            "suppl"
        ]
    }
]
}


export const MOCK_EVENTS = [
    { status: 'Recognizing the variant (SynVar)' },
    { status: 'Fetching literature mentions' },
    { status: 'Annotation', article_count: 4 },
    { total_calls: 6 },
    { status: 'Updating Fulltext & Suppl Data'},
    { status: 'Analysis and Extraction', completed_calls: 1 },
    { status: 'Analysis and Extraction', completed_calls: 2 },
    { status: 'Analysis and Extraction', completed_calls: 3 },
    { status: 'Analysis and Extraction', completed_calls: 4 },
    { status: 'Analysis and Extraction', completed_calls: 5 },
    { status: 'Aggregation', completed_calls: 6},
    { completed_calls: 6 },
    { result: MOCK_RESULT }
];

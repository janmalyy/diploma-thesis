export const MOCK_RESULT = {
    "narrative_summary": "The BRCA1 missense variant p.Arg7Cys (R7C, c.19C>T) has been reported in a handful of individuals across several ethnic groups but remains rare. In an Argentinean cohort it was found in three breast/ovarian cancer patients and classified as clinically uncertain (CU) in the BIC database [PMC3725882]. A Chinese Han study identified the same change in one breast\u2011cancer case and one healthy control, and the authors deemed it benign based on the functional assay of Findlay et\u202fal. [PMC7814423]. The variant was also reported as a novel germline mutation in a single Iranian breast\u2011cancer patient among 85 screened individuals [21918854].\n\nComputational predictions are contradictory. Low\u2011impact scores from SIFT/GVGD were reported for the Argentinean cases, suggesting little effect on protein structure, whereas a separate Asian\u2010focused analysis predicted a deleterious structural deviation of 33.4% [PMC10098510]. A large\u2011scale multifactorial likelihood analysis provided moderate evidence favoring a benign classification (combined likelihood ratio between 0.5 and 2, low population frequency <0.0001 in non\u2011Finnish Europeans, no functional impact in the Findlay saturation\u2011genome\u2011editing assay, and no depletion in the Starita assay), although ClinVar entries remain conflicting (likely benign vs uncertain significance) [PMC6772163]. Further functional work showed no abnormal splicing in blood RNA and negative splicing predictions, supporting a lack of impact on RNA processing [PMC7272326].\n\nClinically, the variant has been observed sporadically in cancer patients, including a single somatic occurrence described as a subclonal driver mutation in a lymph\u2011node metastasis of oesophageal squamous cell carcinoma [PMC10679972]. However, there is no segregation data, no large case\u2011control studies, and functional assays beyond splicing and saturation editing are lacking. Several reviews and drug\u2011prescription supplements list p.Arg7Cys among many BRCA1 mutations without any interpretation [PMC3838820; PMC9763624]. Overall, the preponderance of evidence (low population frequency, benign functional assay results, and moderate likelihood\u2011ratio support) tilts toward a likely benign classification, but conflicting computational predictions and isolated somatic reports generate uncertainty, leaving the variant formally classified as of uncertain significance pending further functional or epidemiologic data.",
    "structured_summary": {
        "overall_pathogenicity": "uncertain",
        "overall_confidence": "low",
        "pathogenicity_counts": {
            "uncertain": 6,
            "supports pathogenicity": 2,
            "supports benignity": 0
        },
        "conflicting_evidence": false
    },
    "article_evidences": [
        {
            "reason": "The article discusses the BRCA1 missense variant p.Arg7Cys (R7C), providing observations of its occurrence in Argentinean breast/ovarian cancer patients and computational prediction scores, thus containing relevant evidence for interpretation.",
            "is_relevant": true,
            "evidence": [
                {
                    "quoted_text": "Five of the 28 missense variants (Table 4) (i.e., p.Arg7Cys, p.Cys61Gly, p.Arg71Gly, p.Tyr179Cys, and p.Met1652Thr in BRCA1, p.Asp2723His in BRCA2) were predicted to have an impact on protein structure upon evaluation by SIFT and GVGD (Table 4).",
                    "description": "p.Arg7Cys was among the 28 missense variants evaluated by SIFT and GVGD for predicted impact on protein structure.",
                    "evidence_type": "computational",
                    "claim": "uncertain",
                    "strength": "low",
                    "source": null
                },
                {
                    "quoted_text": "BRCA1 p.Arg7Cys, differently from the other non-conservative variants, has a rather low prediction score and was found in two cases.",
                    "description": "The variant p.Arg7Cys has a rather low SIFT/GVGD prediction score and was observed in two Argentinean breast/ovarian cancer cases.",
                    "evidence_type": "computational",
                    "claim": "uncertain",
                    "strength": "low",
                    "source": null
                },
                {
                    "quoted_text": "p.Arg7Cys ... CU ...",
                    "description": "The p.Arg7Cys variant is listed as \"CU\" (clinically uncertain) in the BIC database, indicating unknown clinical significance.",
                    "evidence_type": "clinical",
                    "claim": "uncertain",
                    "strength": "low",
                    "source": null
                },
                {
                    "quoted_text": "Table S1: BRCA1 sequence variants identified in Argentinean breast/ovarian cancer cases ... R7C p.Arg7Cys ... AB40, AB67, AB82",
                    "description": "Supplementary Table S1 reports the p.Arg7Cys (R7C) variant in three Argentinean breast/ovarian cancer cases (AB40, AB67, AB82).",
                    "evidence_type": "population",
                    "claim": "uncertain",
                    "strength": "low",
                    "source": null
                }
            ],
            "uncertainties_or_limitations": "The article provides only observational and computational data without functional assays, and the variant is reported in a very small number of patients, leaving its pathogenicity uncertain.",
            "overall_article_summary": "The study identifies the BRCA1 p.Arg7Cys (R7C) missense variant in a few Argentinean breast/ovarian cancer patients, notes its low computational prediction scores, and classifies it as clinically uncertain, offering limited evidence for its interpretation.",
            "article_id": "PMC3725882",
            "title": "BRCA1 And BRCA2 analysis of Argentinean breast/ovarian cancer patients selected for age and family history highlights a role for novel mutations of putative south-American origin",
            "relevance_score": 1.0,
            "pub_year": 2012
        },
        {
            "reason": "The article mentions the BRCA1 p.Arg7Cys (c.19C>T) variant in Supplementary Table\u00a05, providing population occurrence data (1 breast cancer case,\u00a01 healthy control) and a benign classification from the Findlay et al. functional assay, thus it contains variant\u2011specific evidence.",
            "is_relevant": true,
            "evidence": [
                {
                    "quoted_text": "BRCA1\u00a0|17:41276095\u00a0|\u00a0G>A\u00a0|missense_variant\u00a0|c.19C>T\u00a0|p.Arg7Cys\u00a0|1\u00a0|1\u00a0|Benign",
                    "description": "The BRCA1 missense variant c.19C>T (p.Arg7Cys) was observed in 1 breast cancer patient and 1 healthy control in the Chinese cohort and was classified as Benign according to the functional assay reported by Findlay et\u202fal. (Supplementary Table\u00a05).",
                    "evidence_type": "population",
                    "claim": "uncertain",
                    "strength": "low",
                    "source": null
                }
            ],
            "uncertainties_or_limitations": "Evidence is limited to a single case and control observation and relies on an external functional assay classification; no independent functional validation or larger prevalence data are provided.",
            "overall_article_summary": "The study reports that the BRCA1 p.Arg7Cys variant appears in one case and one control and is classified as benign, suggesting it is likely not pathogenic in this Chinese population.",
            "article_id": "PMC7814423",
            "title": "Prevalence and reclassification of BRCA1 and BRCA2 variants in a large, unselected Chinese Han breast cancer cohort",
            "relevance_score": 1.0,
            "pub_year": 2021
        },
        {
            "reason": "The article mentions the BRCA1 Arg7Cys (c.19C>T) variant in supplemental Table S11 with a computational deleterious prediction, which meets relevance criteria.",
            "is_relevant": true,
            "evidence": [
                {
                    "quoted_text": "c.19C>T|p.(Arg7Cys)|nonsynonymous SNV|Conflicting interpretations of pathogenicity|33.3984375|Deleterious",
                    "description": "Table S11 lists c.19C>T|p.(Arg7Cys)|nonsynonymous SNV|Conflicting interpretations of pathogenicity|33.3984375|Deleterious, indicating a computationally predicted structural deviation of 33.4% and classification as deleterious.",
                    "evidence_type": "computational",
                    "claim": "no claim",
                    "strength": "moderate",
                    "source": null
                }
            ],
            "uncertainties_or_limitations": "The evidence is based solely on computational prediction and a conflicting ClinVar classification, with no functional or clinical data provided.",
            "overall_article_summary": "The article provides a computational structural prediction that the BRCA1 p.Arg7Cys variant is deleterious, but acknowledges conflicting ClinVar evidence and does not present experimental validation.",
            "article_id": "PMC10098510",
            "title": "Ethnic-specificity, evolution origin and deleteriousness of Asian BRCA variation revealed by over 7500 BRCA variants derived from Asian population",
            "relevance_score": 0.35,
            "pub_year": 2022
        },
        {
            "reason": "The article mentions BRCA1 mutations in several cases but does not specify the r7c variant, still providing potentially relevant gene-level information.",
            "is_relevant": true,
            "evidence": [
                {
                    "quoted_text": "[Gene: LRP1B], [Gene: KRAS], [Gene: ERBB3], [Gene: BRCA1], [Gene: NF1] and AR showed mutations in 3 cases each (10%).",
                    "description": "BRCA1 mutations were observed in 3 of 30 ITAC tumors (10% of cases).",
                    "evidence_type": "population",
                    "claim": "supports pathogenicity",
                    "strength": "low",
                    "source": null
                }
            ],
            "uncertainties_or_limitations": "The article does not provide details on the specific BRCA1 variant(s) observed, including whether the r7c variant is present, nor any functional or clinical interpretation.",
            "overall_article_summary": "The study reports that BRCA1 was mutated in a subset of sinonasal intestinal-type adenocarcinoma cases, but offers no variant-level data for r7c.",
            "article_id": "PMC8507674",
            "title": "Aberrant Signaling Pathways in Sinonasal Intestinal-Type Adenocarcinoma",
            "relevance_score": 0.29,
            "pub_year": 2021
        },
        {
            "reason": "The article mentions the BRCA1 p.Arg7Cys variant among reported mutations, providing evidence of its observation in the global mutation spectrum.",
            "is_relevant": true,
            "evidence": [
                {
                    "quoted_text": "[ProteinMutation: p.Arg7Cys]",
                    "description": "The article includes the mutation [ProteinMutation: p.Arg7Cys] among a list of BRCA1 protein mutations.",
                    "evidence_type": "population",
                    "claim": "no claim",
                    "strength": "low",
                    "source": null
                }
            ],
            "uncertainties_or_limitations": "The article only lists p.Arg7Cys without providing functional, clinical, frequency, or pathogenicity data, limiting its interpretative value.",
            "overall_article_summary": "This review lists the BRCA1 p.Arg7Cys variant among many reported mutations but does not provide further data on its functional impact or clinical significance.",
            "article_id": "PMC3838820",
            "title": "A Comprehensive Focus on Global Spectrum of BRCA1 and BRCA2 Mutations in Breast Cancer",
            "relevance_score": 0.29,
            "pub_year": 2013
        },
        {
            "reason": "The article mentions the BRCA1 p.Arg7Cys (r7c) variant as a novel mutation detected in its patient cohort, making it relevant to the specified variant.",
            "is_relevant": true,
            "evidence": [
                {
                    "quoted_text": "In the present study, we could detect the novel following mutations: ... [ProteinMutation: p.Arg7Cys] ... in [Gene: BRCA1] ...",
                    "description": "The study identified the BRCA1 p.Arg7Cys (r7c) variant as a novel mutation among 85 Iranian breast cancer patients.",
                    "evidence_type": "clinical",
                    "claim": "no claim",
                    "strength": "low",
                    "source": null
                }
            ],
            "uncertainties_or_limitations": "The article provides only the detection of the variant without functional assays, segregation analysis, population frequency data, or explicit pathogenicity classification for p.Arg7Cys.",
            "overall_article_summary": "The article reports the identification of the BRCA1 p.Arg7Cys variant as a novel mutation in an Iranian breast cancer cohort but does not offer interpretation of its clinical significance.",
            "article_id": "21918854",
            "title": "BRCA1 and BRCA2 germline mutations in 85 Iranian breast cancer patients.",
            "relevance_score": 0.24,
            "pub_year": 2012
        },
        {
            "reason": "The article does not explicitly mention the BRCA1 r7c variant, but it provides functional assay data covering 96.5% of all possible SNVs in 13 BRCA1 exons, which could potentially include r7c, making the article potentially relevant.",
            "is_relevant": true,
            "evidence": [],
            "uncertainties_or_limitations": "The study does not provide any specific functional, clinical, population, or computational evidence for the r7c variant, so its applicability to this variant is uncertain.",
            "overall_article_summary": "The paper reports saturation genome editing of most possible SNVs in 13 BRCA1 exons, offering a functional classification resource, but it does not specifically discuss the r7c variant.",
            "article_id": "PMC6181777",
            "title": "Accurate classification of BRCA1 variants with saturation genome editing",
            "relevance_score": 0.22,
            "pub_year": 2018
        },
        {
            "reason": "The article lists BRCA1 R7C in a supplementary table of mutations, providing a mention of the variant even though no functional, clinical, or pathogenicity interpretation is given, so it is conservatively considered relevant.",
            "is_relevant": true,
            "evidence": [
                {
                    "quoted_text": "BRCA1 MUT (R7C)",
                    "description": "BRCA1 R7C is listed among BRCA1 mutations in Supplementary Table 3 (Details of drugs prescribed for respective SNPs by OncoKB) of the article, but no functional, clinical, or computational interpretation is provided for this variant.",
                    "evidence_type": "computational",
                    "claim": "no claim",
                    "strength": "low",
                    "source": "Supplementary Table 3 (article PMC9763624)"
                }
            ],
            "uncertainties_or_limitations": "The article only mentions the variant without providing any functional, clinical, population, or computational evidence, limiting its usefulness for variant interpretation.",
            "overall_article_summary": "The article includes BRCA1 R7C in a list of BRCA1 mutations in a supplementary table, but does not discuss its effect or classification.",
            "article_id": "PMC9763624",
            "title": "Analysis of single-nucleotide polymorphisms in genes associated with triple-negative breast cancer",
            "relevance_score": 0.15,
            "pub_year": 2022
        },
        {
            "reason": "The article\u2019s supplementary table contains a specific entry for the BRCA1 c.19C>T (p.Arg7Cys) variant, including a combined likelihood ratio, evidence strength, population frequency, functional assay result, and ClinVar classification, which directly pertains to the interpretation of this variant.",
            "is_relevant": true,
            "evidence": [
                {
                    "quoted_text": "BRCA1|c.19C>T|p.(Arg7Cys)|138C>T|R7C||||||||||Combined LR is not <0.5 or >2|moderate in favour of benign|>0 & <0.0001||European (Non-Finnish)||Findlay|No functional impact|FUNC||Not Depleted||||||||||||||missense_variant||||||||Conflicting_interpretations_of_pathogenicity|likely_benign|uncertain_significance|2011-07-25|2002-05-29|2017-07-24|2015-08-31|2017-01-04|2013-06-10|2017-04-12|2017-04-20",
                    "description": "The BRCA1 c.19C>T (p.Arg7Cys) variant is listed in the supplementary table with a combined likelihood ratio that is neither <0.5 nor >2, indicating moderate evidence in favour of a benign classification; the variant has a reported population frequency greater than 0 and less than 0.0001 in the European (non\u2011Finnish) gnomAD cohort; functional assessment from the Findlay assay indicates no functional impact (FUNC); it is noted as not depleted in the Starita depletion assay; ClinVar entries show conflicting interpretations of pathogenicity, including likely benign and uncertain significance submissions.",
                    "evidence_type": "computational",
                    "claim": "uncertain",
                    "strength": "moderate",
                    "source": null
                }
            ],
            "uncertainties_or_limitations": "The evidence is limited to a single table entry without detailed discussion in the article text; the combined likelihood ratio does not reach thresholds for a definitive classification, and the ClinVar entries are conflicting, leaving uncertainty about the clinical significance of the variant.",
            "overall_article_summary": "The article provides a supplementary table entry for BRCA1 c.19C>T (p.Arg7Cys) indicating moderate evidence toward a benign interpretation, no functional impact in the Findlay assay, low population frequency, and conflicting ClinVar classifications, but lacks comprehensive functional or clinical data to conclusively determine pathogenicity.",
            "article_id": "PMC6772163",
            "title": "Large scale multifactorial likelihood quantitative analysis of BRCA1 and BRCA2 variants: An ENIGMA resource to support clinical variant classification",
            "relevance_score": 0.13,
            "pub_year": 2019
        },
        {
            "reason": "The article lists BRCA1 p.Arg7Cys (c.19C>T, rs80356994) as a missense driver mutation detected in the branch subregion of a lymph node metastasis sample (P848-LNmet), providing direct evidence of the variant.",
            "is_relevant": true,
            "evidence": [
                {
                    "quoted_text": "BRCA1 17 + Missense_Mutation SNP G G A rs80356994 c.19C>T p.Arg7Cys p.R7C ... P848-LNmet Branch",
                    "description": "BRCA1 p.Arg7Cys (c.19C>T, rs80356994) was identified as a missense mutation in the branch subregion of lymph node metastasis (LNmet) sample P848, listed among driver mutations in Supplementary Table\u202f8.",
                    "evidence_type": "clinical",
                    "claim": "supports pathogenicity",
                    "strength": "moderate",
                    "source": null
                }
            ],
            "uncertainties_or_limitations": "Only a single somatic occurrence is reported without functional assays, clinical outcome data, or population frequency analysis, limiting conclusions about pathogenicity.",
            "overall_article_summary": "The study characterizes spatial heterogeneity in oesophageal squamous cell carcinoma and reports the BRCA1 p.Arg7Cys missense variant as a subclonal driver mutation in a lymph node metastasis sample.",
            "article_id": "PMC10679972",
            "title": "Multi-omics analyses reveal spatial heterogeneity in primary and metastatic oesophageal squamous cell carcinoma",
            "relevance_score": 0.11,
            "pub_year": 2023
        },
        {
            "reason": "The article's supplementary table lists the BRCA1 c.19C>T (p.Arg7Cys) variant and provides splicing analysis results, prediction scores, and ClinVar classification, indicating explicit evidence relevant to its functional interpretation.",
            "is_relevant": true,
            "evidence": [
                {
                    "quoted_text": "|BRCA1|c.19C>T|p.(Arg7Cys)|NM_007294.3:c.19C>T|chr17||-|A+38|Normal|None|None|Likely benign/Uncertain significance|rs80356994||NAS (+0.9)|No effect to NSS|No effect to NSS|No effect to NSS|||||",
                    "description": "Blood RNA splicing analysis for BRCA1 c.19C>T (p.Arg7Cys) reported a normal splicing result, indicating no abnormal splicing observed.",
                    "evidence_type": "functional",
                    "claim": "no claim",
                    "strength": "moderate",
                    "source": null
                },
                {
                    "quoted_text": "|BRCA1|c.19C>T|p.(Arg7Cys)|...|NAS (+0.9)|No effect to NSS|No effect to NSS|No effect to NSS|",
                    "description": "In silico splicing prediction tools (HSF, SSF, MaxEnt, NNSPLICE) all indicated no effect on splicing for the variant.",
                    "evidence_type": "computational",
                    "claim": "no claim",
                    "strength": "moderate",
                    "source": null
                },
                {
                    "quoted_text": "|BRCA1|c.19C>T|p.(Arg7Cys)|...|Likely benign/Uncertain significance|",
                    "description": "ClinVar entry classifies the variant as 'Likely benign/Uncertain significance', reflecting an ambiguous clinical interpretation.",
                    "evidence_type": "clinical",
                    "claim": "no claim",
                    "strength": "low",
                    "source": null
                }
            ],
            "uncertainties_or_limitations": "The assessment is limited to splicing effects in blood RNA and does not address potential impacts on protein function or other disease mechanisms; the ClinVar classification remains uncertain.",
            "overall_article_summary": "The article provides functional RNA splicing evidence showing the BRCA1 p.Arg7Cys variant does not alter splicing, supported by computational predictions, but the variant's clinical significance remains ambiguous.",
            "article_id": "PMC7272326",
            "title": "Blood RNA analysis can increase clinical diagnostic rate and resolve variants of uncertain significance",
            "relevance_score": 0.11,
            "pub_year": 2020
        },
        {
            "reason": "The article mentions the BRCA1 p.Arg7Cys (R7C) variant as a novel mutation identified in one of the 85 Iranian breast cancer patients screened, providing a case observation without functional or pathogenicity interpretation.",
            "is_relevant": true,
            "evidence": [
                {
                    "quoted_text": "In the present study, we could detect the novel following mutations: ... [ProteinMutation: p.Arg7Cys] ... in [Gene: BRCA1] ...",
                    "description": "The BRCA1 p.Arg7Cys (R7C) variant was reported as a novel mutation detected in an Iranian breast cancer patient among 85 screened individuals.",
                    "evidence_type": "clinical",
                    "claim": "no claim",
                    "strength": "low",
                    "source": null
                }
            ],
            "uncertainties_or_limitations": "The article does not provide any functional data, segregation analysis, population frequency, or explicit pathogenicity classification for the p.Arg7Cys variant, limiting the ability to assess its clinical significance.",
            "overall_article_summary": "The study identifies p.Arg7Cys as a novel BRCA1 mutation in a breast cancer cohort but offers no further interpretation regarding its impact or disease relevance.",
            "article_id": "21918854",
            "title": "BRCA1 and BRCA2 germline mutations in 85 Iranian breast cancer patients.",
            "relevance_score": 0.24,
            "pub_year": 2012
        }
    ]
};


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

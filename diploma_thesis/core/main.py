"""
todo ve variomes mají advanced filtry, ty bych taky asi mohl využít...

Workflow:
1. Normalise variant input. - SynVar
2. Fetch relevant literature data and fulltext_snippets from SIBiLS Variomes.        TODO improve check text for fulltext_snippets
    - if snippet not found, it is added to paragraphs as is
# TODO brát pmc ids aji z litvar2, ne jen z variomes
3. Retrieve full-text annotations from PubTator 3.
4. Fallback to BiodiversityPMC access if PubTator data is missing.
5. Intelligently shorten and filter context based on relevance (mocked).    TODO
6. Generate a concise summary using a LLM.

Output:
- Article-level attributes: Study type, quality, disease.
- Comprehensive variant summary.
"""
import asyncio
import time
from pprint import pprint

from diploma_thesis.api.variomes import (fetch_variomes_data,
                                         parse_variomes_data)
from diploma_thesis.core.models import (Variant, prune_articles,
                                        remove_articles_with_no_match)
from diploma_thesis.core.run_llm import run_pipeline
from diploma_thesis.core.update_article_fulltext import \
    update_articles_fulltext
from diploma_thesis.core.update_suppl_data import update_suppl_data
from diploma_thesis.settings import DATA_DIR, logger


async def main():
    # with open(DATA_DIR / "brca_variants.txt", "r", encoding="utf-8") as f:
    #     text = f.read()
    # variants = text.split("\n")
    #
    # for i, variant in enumerate(variants[:1]):
    #     start_time = time.time()
    #
    #     # 1. Initialize Variant (handles normalisation)
    #     # variant = Variant("BRCA1", "V11A", "protein", fetch_data=False)
    #     variant = Variant("NOP10", "D12H", "protein", fetch_data=True)
    #     # variant = Variant(variant.split(" ")[0], variant.split(" ")[1], "protein")
    #     # logger.info(f"Processing variant: {variant}")
    #
    #     # 2. Fetch Data from Variomes
    #     logger.info("Fetching data from SIBiLS Variomes...")
    #     data = fetch_variomes_data(variant)
    #
    #     # 2b. Parse Data from Variomes
    #     articles = parse_variomes_data(data, variant)
    #     if not articles:
    #         logger.info("No articles found for this variant.")
    #         return
    #     # logger.info(f"Found {len(articles)} articles. IDs: {[a.pmcid if a.pmcid != "" else a.pmid for a in articles]}")
    #
    #     variant.fetch_synvar_data()
    #
    #     articles = prune_articles(articles)
    #
    #     # 3. Fetch and Parse Data from PubTator and BiodiversityPMC
    #     # logger.info("Fetching data from PubTator and BiodiversityPMC...")
    #     update_articles_fulltext(articles, variant)
    #
    #     # 4. Parse Suppl. Data
    #     update_suppl_data(articles, variant)
    #
    #     # 5. Remove Articles with no match
    #     articles = remove_articles_with_no_match(articles)
    #
    #     print("\n" + "="*50)
    #     print("ARTICLE DETAILS")
    #     print("="*50)
    #     for article in articles:
    #         print(article.get_context())
    #         print("Annotation source:", article.annotation_source)
    #         print("\n")
    #
    #     # 6. Generate Summary
    #     final_result = await run_pipeline(variant, articles)

    final_result = """
{'article_evidences': [{'article_id': 'PMC8794197',
    'data_sources': ['suppl', 'pmc'],
    'mentions': [{'claim': <Claim.no_claim: 'no claim'>,
                  'mention_type': <MentionType.population: 'population'>,
                  'quoted_text': '...melanocyte, DNA '
                                 'repair, cell cycle, '
                                 'telomeres 8 70 35% 3 '
                                 'rs143789597 c.242G>A '
                                 'p.Arg81Gln 0.001112 '
                                 'NOP10 Cancer, skin '
                                 'pigmentation, '
                                 'melanocyte, DNA repair, '
                                 'cell cycle, telomeres 6 '
                                 '52 66% 1 **rs146261631** '
                                 '**c.34G>C** '
                                 '**p.Asp12His** 0.009744 '
                                 'PTPN22 Cancer, cancer '
                                 'susceptibility, '
                                 'melanoma, skin '
                                 'pigmentation, '
                                 'melanocyte, cell cycle, '
                                 'telomeres 7 40 29% 1 '
                                 'rs72650671 c.1108C>A '
                                 'p.His370Asn 0.002273 '
                                 'MCM3 Cancer, cancer '
                                 'susceptibility,...',
                  'strength': <MentionStrength.low: 'low'>},
                 {'claim': <Claim.supports_pathogenicity: 'supports pathogenicity'>,
                  'mention_type': <MentionType.clinical: 'clinical'>,
                  'quoted_text': 'Lastly, we identified a '
                                 'rare variant in the '
                                 'NOP10 gene (NOP10 '
                                 'Ribonucleoprotein), '
                                 'which interacts directly '
                                 'with TERT gene. NOP10 is '
                                 'a member of the '
                                 'telomerase '
                                 'ribonucleoprotein '
                                 'complex that is '
                                 'responsible for telomere '
                                 'maintenance, thus '
                                 'preserving chromosomal '
                                 'integrity and genome '
                                 'stability. Telomere '
                                 'maintenance genes such '
                                 'as TERT, ACD, POT1 and '
                                 'TERF2IP were associated '
                                 'to melanoma '
                                 'predisposition '
                                 'previously. The mutant '
                                 'residue that we found '
                                 '(**c.34G>C**; '
                                 '**p.Asp12His**) was '
                                 'described previously in '
                                 'a study of congenital '
                                 'dyskeratosis.',
                  'strength': <MentionStrength.low: 'low'>},
                 {'claim': <Claim.supports_pathogenicity: 'supports pathogenicity'>,
                  'mention_type': <MentionType.computational: 'computational'>,
                  'quoted_text': 'Column names: Family '
                                 '|Genes|dbSNP|Predicted '
                                 'Damaging '
                                 'Algorithms|Genomic '
                                 'pos.|Transcript '
                                 'Name|Type of '
                                 'variant|Ref/Alt|HGVS '
                                 'c.|HGVS p.|ExAC '
                                 'Frequency\n'
                                 'Rows:\n'
                                 'Family '
                                 '1|NOP10|**rs146261631**|4 '
                                 'of 6 Predicted as '
                                 'Damaging|15:34635241|NM_018648|Missense|C/G|**c.34G>C**|**p.Asp12His**|0.009744',
                  'strength': <MentionStrength.moderate: 'moderate'>}],
    'overall_article_summary': 'The study reports a rare '
                               'NOP10 missense variant '
                               '(c.34G>C; p.Asp12His; '
                               'rs146261631) identified in '
                               'a melanoma‑prone family, '
                               'provides computational '
                               'predictions of damage and '
                               'population frequency data, '
                               'and proposes it as a '
                               'candidate gene for '
                               'melanoma susceptibility, '
                               'but offers no functional '
                               'or segregation evidence.',
    'pub_year': 2022,
    'relevance_score': 1.0,
    'title': 'Family-based whole-exome sequencing '
             'identifies rare variants potentially related '
             'to cutaneous melanoma predisposition in '
             'Brazilian melanoma-prone families',
    'uncertainties_or_limitations': None},
   {'article_id': 'PMC11160413',
    'data_sources': ['pmc'],
    'mentions': [{'claim': <Claim.supports_pathogenicity: 'supports pathogenicity'>,
                  'mention_type': <MentionType.clinical: 'clinical'>,
                  'quoted_text': 'In total, we found 138 '
                                 'variants not targeted by '
                                 'the LDT (see Table E3). '
                                 'Interestingly, four of '
                                 'them were predicted as '
                                 'potentially damaging or '
                                 'probably damaging by '
                                 'PolyPhen-2 and as '
                                 'deleterious on the basis '
                                 'of a CADD score >20 '
                                 '(Table 3). These include '
                                 '**D12H** in NOP10 and '
                                 'E322D in NAF1, each '
                                 'identified in one '
                                 'patient, and F559I in '
                                 'RTEL1 and L59F in ACD, '
                                 'identified in the same '
                                 'patient. Note that T138N '
                                 'in SFTPC, identified in '
                                 '25 patients, was also '
                                 'considered putatively '
                                 'damaging on the basis of '
                                 'pathogenicity scores '
                                 '(PolyPhen-2: possibly '
                                 'damaging; CADD score = '
                                 '22.1). However, this is '
                                 'a common variant with a '
                                 'similar minor allele '
                                 'frequency (MAF) in the '
                                 'Quebec City IPF cohort '
                                 '(MAF = 22%) compared '
                                 'with the reference '
                                 'populations (MAF = 26% '
                                 'in the 1000 Genomes '
                                 'Project and MAF = 21% in '
                                 'TOPMed). The four '
                                 'putatively deleterious '
                                 'variants, in '
                                 'well-characterized genes '
                                 'known to cause IPF, '
                                 'suggest that we may have '
                                 'identified new '
                                 'pathogenic variants of '
                                 'IPF that might be '
                                 'specific to the French '
                                 'Canadian population.',
                  'strength': <MentionStrength.low: 'low'>},
                 {'claim': <Claim.uncertain: 'uncertain'>,
                  'mention_type': <MentionType.population: 'population'>,
                  'quoted_text': 'Gene Variant Chr '
                                 'Position hg38 Exon mRNA '
                                 'Protein MAF '
                                 'Pathogenicity IPF Cohort '
                                 '1000G TOPMed PolyPhen-2 '
                                 'CADD Score ACMGG RTEL1 '
                                 'rs747497376 20 '
                                 '63,688,339 20 c.1675T>A '
                                 'F559I 0.008 0 9.9 x 10-6 '
                                 '1.0 26.1 VUS ACD '
                                 'rs368387402 16 '
                                 '67,659,970 2 c.175C>T '
                                 'L59F 0.008 0 6.6 x 10-6 '
                                 '0.969 25 VUS NAF1 '
                                 'rs146474502 14 '
                                 '163,133,221 7 c.966A>C '
                                 'E322D 0.008 0 0.00051 '
                                 '0.906 24.2 VUS NOP10 '
                                 '**rs146261631** 15 '
                                 '34,343,040 1 **c.34G>C** '
                                 '**D12H** 0.008 0.007 '
                                 '0.00586 0.629 27.3 VUS',
                  'strength': <MentionStrength.moderate: 'moderate'>}],
    'overall_article_summary': 'The article reports NOP10 '
                               'D12H as a rare missense '
                               'variant observed in one '
                               'IPF patient, predicted '
                               'deleterious by '
                               'computational tools '
                               '(PolyPhen‑2, CADD) and '
                               'classified as a variant of '
                               'uncertain significance, '
                               'suggesting it could be a '
                               'novel pathogenic '
                               'contributor to familial '
                               'pulmonary fibrosis but '
                               'lacking definitive '
                               'functional or segregation '
                               'evidence.',
    'pub_year': 2024,
    'relevance_score': 0.89,
    'title': 'A Test to Comprehensively Capture the Known '
             'Genetic Component of Familial Pulmonary '
             'Fibrosis',
    'uncertainties_or_limitations': 'The evidence for '
                                    'NOP10 D12H is limited '
                                    'to a single case and '
                                    'in‑silico '
                                    'predictions; no '
                                    'functional assays or '
                                    'segregation data are '
                                    'provided, and the '
                                    'variant remains '
                                    'classified as VUS.'},
   {'article_id': 'PMC2882227',
    'data_sources': ['pmc'],
    'mentions': [{'claim': <Claim.no_claim: 'no claim'>,
                  'mention_type': <MentionType.population: 'population'>,
                  'quoted_text': 'Homozygosity at marker '
                                 'D15S1007 was not seen in '
                                 'any of the other '
                                 'families in the initial '
                                 'homozygosity screen '
                                 'suggesting that this '
                                 'mutation is a rare cause '
                                 'of AR-DC (Fig. 1B). To '
                                 'determine if this p.R34W '
                                 'or any other mutation is '
                                 'present in any other '
                                 'family, we sequenced '
                                 'samples from the index '
                                 'case of 171 '
                                 'uncharacterized families '
                                 '(the majority being '
                                 'sporadic cases) on the '
                                 'DCR. A total of nine '
                                 'different sequence '
                                 'variations were seen in '
                                 'this group of patients, '
                                 'six of which (c.34G> C, '
                                 'IVS1 + 21G> A, IVS1-15C> '
                                 'G, c.* 30A> G, c.*31C> '
                                 'T, c.*45G> T, where IVS1 '
                                 'is intron 1 and asterisk '
                                 'indicates after the stop '
                                 'codon) have been '
                                 'described previously as '
                                 'polymorphisms. c.34G> C '
                                 'causes an aspartic acid '
                                 'to histidine '
                                 'substitution at amino '
                                 'acid 12 and was observed '
                                 'as a heterozygous change '
                                 'in one individual but '
                                 'has also been reported '
                                 'by Yamaguchi et al. in a '
                                 'screen of 282 healthy '
                                 'subjects. Three sequence '
                                 'variations are novel '
                                 '(IVS1 + 192 C> A, '
                                 'c.*136T> C, c.*149G> A). '
                                 'These changes are also '
                                 'thought to be '
                                 'non-pathogenic due to '
                                 'their frequency '
                                 '(frequency of the minor '
                                 'allele in each case, '
                                 '0.306, 0.121 and 0.064, '
                                 'respectively) and due to '
                                 'their location, in the '
                                 'middle of an intron or '
                                 "in the 3'-UTR. It was "
                                 'interesting to note that '
                                 'the genetic background '
                                 'for the p.R34W mutation '
                                 'had a unique haplotype '
                                 'compared with all the '
                                 'other individuals typed '
                                 '(data not shown). The '
                                 'p.R34W substitution was '
                                 'not detected in a screen '
                                 'of 56 ethnically matched '
                                 'healthy individuals '
                                 'indicating that this '
                                 'change is not present at '
                                 'a polymorphic frequency '
                                 'in this population.',
                  'strength': <MentionStrength.low: 'low'>}],
    'overall_article_summary': 'While the article '
                               'demonstrates NOP10 '
                               'mutations cause an '
                               'autosomal recessive '
                               'dyskeratosis congenita '
                               'subtype, it reports the '
                               'specific D12H (c.34G>C) '
                               'variant as a known '
                               'polymorphism observed in '
                               'healthy individuals, '
                               'suggesting it is likely '
                               'benign rather than '
                               'pathogenic.',
    'pub_year': 2007,
    'relevance_score': 0.79,
    'title': 'Genetic heterogeneity in autosomal recessive '
             'dyskeratosis congenita with one subtype due '
             'to mutations in the telomerase-associated '
             'protein NOP10',
    'uncertainties_or_limitations': None},
   {'article_id': 'PMC7870655',
    'data_sources': ['suppl'],
    'mentions': [{'claim': None,
                  'mention_type': <MentionType.clinical: 'clinical'>,
                  'quoted_text': 'Table title: 0|0|Count\n'
                                 'Column names: 0|3|Other '
                                 'Variants (cDNA & protein '
                                 ')\n'
                                 'Rows:\n'
                                 '73|4|NOP10 **c.34G>C** '
                                 '**p.Asp12His** B/LB',
                  'strength': None}],
    'overall_article_summary': 'The article reports NOP10 '
                               'D12H (p.Asp12His) as '
                               'benign/likely benign, '
                               'indicating it is not '
                               'considered pathogenic in '
                               'this Armenian breast '
                               'cancer cohort.',
    'pub_year': 2021,
    'relevance_score': 0.49,
    'title': 'Germline mutational spectrum in Armenian '
             'breast cancer patients suspected of '
             'hereditary breast and ovarian cancer',
    'uncertainties_or_limitations': None},
   {'article_id': 'PMC6742646',
    'data_sources': ['suppl'],
    'mentions': [{'claim': <Claim.supports_pathogenicity: 'supports pathogenicity'>,
                  'mention_type': <MentionType.functional: 'functional'>,
                  'quoted_text': 'Column names: Gene '
                                 'name|Chrom|Pos|Mutation|HGVS_cDNA|Uniprot|dbSNP_id|Enzyme|Drug '
                                 'enzyme|Drug target|Drug '
                                 'transporter|Disruptive\n'
                                 'Rows:\n'
                                 'NOP10|||C>G|NM_018648.3:**c.34G>C**|Q9NPE3,**D12H**|**rs146261631**|||||',
                  'strength': <MentionStrength.low: 'low'>}],
    'overall_article_summary': 'The article lists NOP10 '
                               'D12H among the missense '
                               'variants examined for '
                               'protein‑protein '
                               'interaction disruption, '
                               'but does not provide a '
                               'specific functional or '
                               'pathogenicity result for '
                               "this variant.', ",
    'pub_year': 2019,
    'relevance_score': 0.08,
    'title': 'Extensive disruption of protein interactions '
             'by genetic variants across the allele '
             'frequency spectrum in human populations',
    'uncertainties_or_limitations': None},
   {'article_id': 'PMC9006286',
    'data_sources': ['suppl'],
    'mentions': [{'claim': <Claim.no_claim: 'no claim'>,
                  'mention_type': <MentionType.clinical: 'clinical'>,
                  'quoted_text': 'Table title: '
                                 'SUPPLEMENTARY '
                                 'INFORMATION\n'
                                 'Rows:\n'
                                 '**c.G34C**',
                  'strength': <MentionStrength.moderate: 'moderate'>}],
    'overall_article_summary': 'The article reports '
                               'detection of the NOP10 '
                               'D12H (c.34G>C) variant in '
                               'its supplementary data, '
                               'but provides no further '
                               'interpretation or evidence '
                               'regarding its effect or '
                               'clinical significance.',
    'pub_year': 2022,
    'relevance_score': 0.03,
    'title': 'Genomic profiling of a randomized trial of '
             'interferon-alpha vs hydroxyurea in MPN '
             'reveals mutation-specific responses',
    'uncertainties_or_limitations': None}],
'narrative_summary': 'The NOP10 missense change c.34G>C (p.Asp12His, also '
  'noted as D12H) is a rare variant that has been reported '
  'in several disease‑focused sequencing studies. In a '
  'Brazilian melanoma‑prone family it was identified as a '
  'candidate susceptibility allele, showed multiple '
  'in‑silico predictions of damage, and was highlighted '
  'because NOP10 interacts with telomerase components such '
  'as TERT; however, functional or segregation data were '
  'not provided [PMC8794197]. A similar observation was '
  'made in a cohort of familial pulmonary fibrosis '
  'patients, where the same variant was found in one case, '
  'received deleterious scores from PolyPhen‑2 and CADD '
  '(>20), and was classified as a variant of uncertain '
  'significance (VUS) pending further evidence '
  '[PMC11160413]. An additional catalogue of '
  'protein‑protein interaction disruptions listed the '
  'variant among those potentially affecting NOP10 '
  'function, albeit without experimental validation '
  '[PMC6742646].\n'
  '\n'
  'Contrastingly, the variant has also been reported as a '
  'common polymorphism in healthy individuals. In a study '
  'of autosomal recessive dyskeratosis congenita the '
  'c.34G>C change was observed heterozygously in a single '
  'subject and had been previously detected in a screen of '
  '282 unaffected donors, leading the authors to regard it '
  'as likely benign rather than disease‑causing '
  '[PMC2882227]. A breast‑cancer‑focused germline screen '
  'in an Armenian cohort classified the same allele as '
  'benign/likely benign (B/LB) based on population data '
  '[PMC7870655]. A supplementary report from a '
  'myeloproliferative neoplasm trial merely listed the '
  'variant without any interpretation [PMC9006286].\n'
  '\n'
  'Overall, the evidence for NOP10 D12H is conflicted. '
  'Computational predictions and its presence in '
  'telomere‑related disease cohorts suggest a possible '
  'deleterious role, yet population surveys and '
  'cancer‑genetics screenings consistently label it as a '
  'benign polymorphism. No functional assays, segregation '
  'analyses, or robust case‑control studies have been '
  'presented to resolve this discrepancy, leaving the '
  'clinical significance of NOP10 p.Asp12His uncertain.',
'structured_summary': {'conflicting_evidence': False,
    'overall_confidence': <ConfidenceLevel.LOW: 'low'>,
    'overall_pathogenicity': <Pathogenicity.PATHOGENIC: 'pathogenic'>,
    'pathogenicity_counts': {'supports benignity': 0,
                             'supports pathogenicity': 4,
                             'uncertain': 1}}}
        """

    pprint(final_result)
    end_time = time.time()
    # logger.info(f"\nWorkflow completed in {round(end_time - start_time, 2)}s")


if __name__ == '__main__':
    asyncio.run(main())

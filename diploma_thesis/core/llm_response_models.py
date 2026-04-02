from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    functional = "functional"
    clinical = "clinical"
    population = "population"
    computational = "computational"
    other = "other"


class EvidenceStrength(str, Enum):
    low = "low"
    moderate = "moderate"
    high = "high"


class Claim(str, Enum):
    no_claim = "no claim"
    uncertain = "uncertain"
    supports_pathogenicity = "supports pathogenicity"
    supports_benignity = "supports benignity"


class EvidenceItem(BaseModel):
    quoted_text: str = Field(
        description="The FULL, verbatim sentence or complete table row from the original text. "
                    "Do NOT extract fragments or single words. "
                    "MUST be exactly the same as the text in the original article and CAN NOT be modified."
    )
    description: str = Field(
        description="A concise summary of the evidence. If a sentence contains multiple findings, "
                    "synthesize them here into a single cohesive description."
    )
    evidence_type: Annotated[
        EvidenceType,
        Field(description=(
            "functional: In vitro/vivo assays; "
            "clinical: Case reports/segregation; "
            "population: Allele frequency (e.g., data from gnomAD or 1000G); "
            "computational: In silico predictions (e.g., data from PolyPhen or SIFT); "
            "other: Other types of evidence;"
        ))
    ]

    claim: Annotated[
        Claim,
        Field(description=(
            "uncertain: Conflicting/insufficient; "
            "supports pathogenicity: Evidence for disease-causing; "
            "supports benignity: Evidence for harmlessness; "
            "no claim: Mentioned only without interpretation;"

        ))
    ]
    strength: EvidenceStrength


class ArticleAnalysis(BaseModel):
    reason: str = Field(description="1 sentence explaining relevance decision")
    is_relevant: bool
    evidence: list[EvidenceItem] = Field(default_factory=list)
    uncertainties_or_limitations: str | None = Field(default=None, description="1 sentence summary of the uncertainties or limitations of the article")
    overall_article_summary: str | None = Field(default=None, description="1 sentence summary of the article based on the evidences")


# --------------------------------------------------
class Pathogenicity(str, Enum):
    PATHOGENIC = "pathogenic"
    LIKELY_PATHOGENIC = "likely pathogenic"
    BENIGN = "benign"
    LIKELY_BENIGN = "likely benign"
    UNCERTAIN = "uncertain"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class AggregatedSummary(BaseModel):
    narrative_summary: str = Field(description="A natural language synthesis of the findings long from one to three paragraphs.")

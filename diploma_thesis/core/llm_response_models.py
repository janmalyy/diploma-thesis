from enum import Enum

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
    supports_pathogenicity = "supports pathogenicity"
    supports_benignity = "supports benignity"
    conflicting = "conflicting"
    unclear = "unclear"
    no_claim = "no claim"


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


class EvidenceItem(BaseModel):
    quoted_text: str = Field(description="The exact reference to the original text.")
    description: str = Field(description="Your description of the quoted text.")
    evidence_type: EvidenceType
    claim: Claim
    strength: EvidenceStrength


class ArticleAnalysis(BaseModel):
    reason: str = Field(description="1 sentence explaining relevance decision")
    is_relevant: bool
    evidence: list[EvidenceItem] = Field(default_factory=list)
    overall_article_conclusion: str | None = None
    uncertainties_or_limitations: str | None = None


class StructuredSummary(BaseModel):
    overall_pathogenicity: Pathogenicity
    conflicting_evidence: bool
    overall_confidence: ConfidenceLevel


class AggregatedSummary(BaseModel):
    narrative_summary: str = Field(description="A natural language synthesis of the findings.")
    structured_summary: StructuredSummary

from enum import Enum

from pydantic import BaseModel, Field


class MentionType(str, Enum):
    functional = "functional"
    clinical = "clinical"
    population = "population"
    computational = "computational"
    other = "other"


class Claim(str, Enum):
    no_claim = "no claim"
    uncertain = "uncertain"
    supports_pathogenicity = "supports pathogenicity"
    supports_benignity = "supports benignity"


class Mention(BaseModel):
    mention_id: int = Field(description="The ID of the mention", default=0)
    reason: str = Field(description="1 sentence explaining relevance decision")
    is_relevant: bool

    mention_type: MentionType = Field(
        description=(
            "functional: In vitro/vivo assays;"
            "clinical: Case reports/segregation;"
            "population: Allele frequency (e.g., data from gnomAD or 1000G);"
            "computational: In silico predictions (e.g., data from PolyPhen or SIFT);"
            "other: Other types of evidence;"
        ),
        default=None)

    claim: Claim = Field(
        description=(
            "uncertain: VUS/uncertain significance/conflicting/insufficient/; "
            "supports pathogenicity: Evidence for disease-causing; "
            "supports benignity: Evidence for harmlessness; "
            "no claim: Mentioned only without interpretation;"
        ),
        default=None)


class ArticleAnalysis(BaseModel):
    mentions: list[Mention] = Field(default_factory=list)
    uncertainties_or_limitations: str | None = Field(default=None, description="1 sentence summary of the uncertainties or limitations of the article")
    overall_article_summary: str | None = Field(default=None, description="1 sentence summary of the article based on the mentions")


class AggregatedSummary(BaseModel):
    narrative_summary: str = Field(description="A natural language synthesis of the findings.")


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

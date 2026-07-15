"""Automated, source-backed opportunity scouting."""

from __future__ import annotations

from dataclasses import dataclass

from src.ingestion.manual import IngestionError
from src.ingestion.schemas import SourceSubmission
from src.ingestion.web import (
    PAIN_SIGNALS,
    WebEvidenceCandidate,
    candidate_from_search_result,
)
from src.research.competitor_search import SearchProvider, canonical_url


SCOUT_FOCUS_LABELS: dict[str, str] = {
    "all": "Any market",
    "healthcare": "Healthcare operations",
    "professional_services": "Professional services",
    "field_services": "Property & field services",
    "commerce": "Commerce & supply chain",
    "people_ops": "Hiring & people operations",
}

SCOUT_SOURCE_FILTER = (
    "(site:news.ycombinator.com OR site:indiehackers.com OR "
    "site:stackoverflow.com OR site:github.com OR site:g2.com OR "
    "site:capterra.com OR site:trustpilot.com)"
)


@dataclass(frozen=True)
class OpportunityTheme:
    """A concrete customer workflow worth testing against public evidence."""

    key: str
    title: str
    topic: str
    target_customer: str
    focus: str


OPPORTUNITY_THEMES: tuple[OpportunityTheme, ...] = (
    OpportunityTheme(
        key="clinic-referrals",
        title="Patient referral follow-up",
        topic="patient referral follow-up and status tracking",
        target_customer="independent clinics",
        focus="healthcare",
    ),
    OpportunityTheme(
        key="client-documents",
        title="Client document collection",
        topic="collecting missing client documents and reminders",
        target_customer="small accounting firms",
        focus="professional_services",
    ),
    OpportunityTheme(
        key="property-maintenance",
        title="Maintenance request coordination",
        topic="maintenance request intake updates and vendor coordination",
        target_customer="property managers",
        focus="field_services",
    ),
    OpportunityTheme(
        key="returns-exceptions",
        title="Returns exception handling",
        topic="customer return exceptions refunds and warehouse handoffs",
        target_customer="ecommerce operations teams",
        focus="commerce",
    ),
    OpportunityTheme(
        key="interview-feedback",
        title="Interview feedback collection",
        topic="collecting interview feedback and hiring approvals",
        target_customer="small recruiting teams",
        focus="people_ops",
    ),
    OpportunityTheme(
        key="prior-authorization",
        title="Prior authorization documentation",
        topic="prior authorization document collection and status follow-up",
        target_customer="outpatient medical practices",
        focus="healthcare",
    ),
    OpportunityTheme(
        key="client-approvals",
        title="Client approval tracking",
        topic="client content approval reminders and revision tracking",
        target_customer="marketing agencies",
        focus="professional_services",
    ),
    OpportunityTheme(
        key="change-orders",
        title="Construction change-order tracking",
        topic="change order approval tracking and subcontractor updates",
        target_customer="small construction subcontractors",
        focus="field_services",
    ),
    OpportunityTheme(
        key="inventory-reconciliation",
        title="Inventory reconciliation",
        topic="inventory discrepancies and spreadsheet reconciliation",
        target_customer="small distributors",
        focus="commerce",
    ),
    OpportunityTheme(
        key="employee-onboarding",
        title="Employee onboarding handoffs",
        topic="employee onboarding document collection and task handoffs",
        target_customer="small HR teams",
        focus="people_ops",
    ),
    OpportunityTheme(
        key="patient-intake",
        title="Patient intake handoffs",
        topic="patient intake forms and duplicate data entry",
        target_customer="independent therapy practices",
        focus="healthcare",
    ),
    OpportunityTheme(
        key="vendor-renewals",
        title="Vendor renewal tracking",
        topic="vendor contract renewal dates approvals and reminders",
        target_customer="small finance and operations teams",
        focus="professional_services",
    ),
    OpportunityTheme(
        key="technician-dispatch",
        title="Technician dispatch updates",
        topic="field technician scheduling status updates and customer notifications",
        target_customer="local service businesses",
        focus="field_services",
    ),
    OpportunityTheme(
        key="purchase-order-matching",
        title="Purchase-order matching",
        topic="purchase order invoice matching and discrepancy resolution",
        target_customer="small manufacturers",
        focus="commerce",
    ),
    OpportunityTheme(
        key="compliance-evidence",
        title="Compliance evidence collection",
        topic="employee compliance training evidence and reminder tracking",
        target_customer="regulated small businesses",
        focus="people_ops",
    ),
)


@dataclass(frozen=True)
class ScoutedEvidenceCandidate:
    """A web candidate paired with the workflow that surfaced it."""

    evidence: WebEvidenceCandidate
    theme: OpportunityTheme

    @property
    def title(self) -> str:
        return self.evidence.title

    @property
    def url(self) -> str:
        return self.evidence.url

    @property
    def domain(self) -> str:
        return self.evidence.domain

    @property
    def score(self) -> float:
        return self.evidence.score

    @property
    def preview(self) -> str:
        return self.evidence.preview

    def to_submission(self) -> SourceSubmission:
        """Add scout context while preserving the source's original evidence text."""

        submission = self.evidence.to_submission()
        metadata = {
            **submission.metadata_json,
            "opportunity_theme": self.theme.key,
            "opportunity_theme_title": self.theme.title,
            "scouted_target_customer": self.theme.target_customer,
        }
        return submission.copy(update={"metadata_json": metadata})


@dataclass(frozen=True)
class ScoutedOpportunity:
    """A workflow hypothesis paired with its attributable public evidence."""

    theme: OpportunityTheme
    candidates: tuple[ScoutedEvidenceCandidate, ...]


def build_scout_query(theme: OpportunityTheme) -> str:
    """Build a broad, pain-oriented query without restrictive exact phrases."""

    query = (
        f"{theme.topic} {theme.target_customer} customer complaint discussion "
        f"({PAIN_SIGNALS}) {SCOUT_SOURCE_FILTER}"
    )
    return " ".join(query.split())


def select_opportunity_themes(
    focus: str = "all",
    *,
    limit: int = 4,
    offset: int = 0,
) -> tuple[OpportunityTheme, ...]:
    """Select a rotating, bounded set of concrete opportunity hypotheses."""

    if focus not in SCOUT_FOCUS_LABELS:
        raise IngestionError("Select a supported market focus.")
    if not 1 <= limit <= 8:
        raise IngestionError("Opportunity scans must include between 1 and 8 themes.")
    themes = [
        theme for theme in OPPORTUNITY_THEMES if focus == "all" or theme.focus == focus
    ]
    if not themes:
        return ()
    start = offset % len(themes)
    rotated = themes[start:] + themes[:start]
    return tuple(rotated[:limit])


class AutomatedOpportunityScout:
    """Discover sourced opportunity leads without requiring a user-supplied idea."""

    def __init__(
        self,
        provider: SearchProvider,
        *,
        search_depth: str = "basic",
    ) -> None:
        self.provider = provider
        self.search_depth = search_depth

    def scan(
        self,
        *,
        focus: str = "all",
        theme_limit: int = 4,
        results_per_theme: int = 3,
        offset: int = 0,
    ) -> list[ScoutedOpportunity]:
        """Search several customer workflows and group unique evidence by lead."""

        if not 1 <= results_per_theme <= 10:
            raise IngestionError("Results per opportunity must be between 1 and 10.")
        themes = select_opportunity_themes(
            focus,
            limit=theme_limit,
            offset=offset,
        )
        seen_urls: set[str] = set()
        leads: list[ScoutedOpportunity] = []
        for theme in themes:
            query = build_scout_query(theme)
            candidates: list[ScoutedEvidenceCandidate] = []
            for result in self.provider.search(
                query,
                max_results=results_per_theme,
                search_depth=self.search_depth,
            ):
                evidence = candidate_from_search_result(result, query=query)
                if evidence is None:
                    continue
                url_key = canonical_url(evidence.url)
                if url_key in seen_urls:
                    continue
                seen_urls.add(url_key)
                candidates.append(
                    ScoutedEvidenceCandidate(evidence=evidence, theme=theme)
                )
            candidates.sort(key=lambda item: item.score, reverse=True)
            if candidates:
                leads.append(
                    ScoutedOpportunity(
                        theme=theme,
                        candidates=tuple(candidates),
                    )
                )
        return leads

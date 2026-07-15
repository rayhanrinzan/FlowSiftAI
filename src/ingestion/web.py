"""Public web evidence discovery and normalization."""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import ceil
from urllib.parse import urlsplit

from src.ingestion.manual import IngestionError, build_source_external_id
from src.ingestion.schemas import SourceSubmission
from src.research.competitor_search import SearchProvider, canonical_url
from src.research.schemas import SearchResult


MAX_EVIDENCE_TEXT_CHARS = 20_000

WEB_SOURCE_LABELS: dict[str, str] = {
    "forums": "Forums & communities",
    "issues": "Issue trackers",
    "reviews": "Product reviews",
    "web": "Broad web",
}

SOURCE_FILTERS: dict[str, str] = {
    "forums": (
        "(site:news.ycombinator.com OR site:indiehackers.com OR "
        "site:stackoverflow.com OR site:discourse.org)"
    ),
    "issues": "site:github.com/issues",
    "reviews": "(site:g2.com OR site:capterra.com OR site:trustpilot.com)",
    "web": "",
    "discussions": (
        "(site:news.ycombinator.com OR site:indiehackers.com OR "
        "site:stackoverflow.com OR site:github.com OR site:g2.com OR "
        "site:capterra.com OR site:trustpilot.com)"
    ),
}

PAIN_SIGNALS = (
    '"manual process" OR "takes hours" OR frustrating OR expensive OR '
    'workaround OR repetitive OR "wish there was"'
)

SCOUT_FOCUS_LABELS: dict[str, str] = {
    "all": "Any market",
    "healthcare": "Healthcare operations",
    "professional_services": "Professional services",
    "field_services": "Property & field services",
    "commerce": "Commerce & supply chain",
    "people_ops": "Hiring & people operations",
}


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
class WebEvidenceCandidate:
    """One attributable public result that can be reviewed before ingestion."""

    title: str
    url: str
    domain: str
    raw_text: str
    snippet: str
    score: float
    source_queries: tuple[str, ...]
    theme_key: str | None = None
    theme_title: str | None = None
    target_customer: str | None = None

    @property
    def preview(self) -> str:
        """Return a concise result excerpt for the review UI."""

        text = self.snippet or self.raw_text
        return " ".join(text.split())[:600]

    def to_submission(self) -> SourceSubmission:
        """Normalize this candidate for the shared discovery pipeline."""

        metadata = {
            "ingestion_method": "web_search",
            "search_queries": list(self.source_queries),
            "search_score": self.score,
            "search_snippet": self.snippet[:1_000],
        }
        if self.theme_key:
            metadata["opportunity_theme"] = self.theme_key
            metadata["opportunity_theme_title"] = self.theme_title
            metadata["scouted_target_customer"] = self.target_customer
        return SourceSubmission(
            platform="web",
            raw_text=self.raw_text,
            source_url=self.url,
            source_external_id=build_source_external_id(self.raw_text, self.url),
            community=self.domain,
            title=self.title,
            engagement_score=self.score,
            metadata_json=metadata,
        )


@dataclass(frozen=True)
class ScoutedOpportunity:
    """A workflow hypothesis paired with its attributable public evidence."""

    theme: OpportunityTheme
    candidates: tuple[WebEvidenceCandidate, ...]


def generate_evidence_queries(
    topic: str,
    *,
    target_customer: str | None = None,
    source_types: tuple[str, ...] = ("forums", "issues", "reviews"),
    quote_terms: bool = True,
) -> list[str]:
    """Build bounded queries aimed at first-hand pain and workaround evidence."""

    cleaned_topic = " ".join(topic.strip().split()).replace('"', "")
    cleaned_customer = " ".join((target_customer or "").strip().split()).replace(
        '"', ""
    )
    if not cleaned_topic:
        raise IngestionError("Enter a market, workflow, or problem to search.")
    if len(cleaned_topic) > 300 or len(cleaned_customer) > 200:
        raise IngestionError("Search topic or target customer is too long.")
    if not source_types:
        raise IngestionError("Select at least one source type.")

    unknown = set(source_types) - set(SOURCE_FILTERS)
    if unknown:
        raise IngestionError(f"Unsupported web source type: {sorted(unknown)[0]}.")

    topic_expression = f'"{cleaned_topic}"' if quote_terms else cleaned_topic
    if cleaned_customer:
        audience = f' "{cleaned_customer}"' if quote_terms else f" {cleaned_customer}"
    else:
        audience = ""
    queries: list[str] = []
    for source_type in source_types:
        source_filter = SOURCE_FILTERS[source_type]
        query = (
            f"{topic_expression}{audience} customer complaint discussion "
            f"({PAIN_SIGNALS}) {source_filter}"
        )
        queries.append(" ".join(query.split()))
    return queries


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


class WebEvidenceDiscoveryService:
    """Search, deduplicate, and rank public evidence candidates."""

    def __init__(
        self,
        provider: SearchProvider,
        *,
        search_depth: str = "basic",
    ) -> None:
        self.provider = provider
        self.search_depth = search_depth

    def discover(
        self,
        topic: str,
        *,
        target_customer: str | None = None,
        source_types: tuple[str, ...] = ("forums", "issues", "reviews"),
        max_results: int = 15,
        quote_terms: bool = True,
    ) -> list[WebEvidenceCandidate]:
        """Return a bounded set of unique, attributable search results."""

        if not 1 <= max_results <= 100:
            raise IngestionError("Maximum web results must be between 1 and 100.")
        queries = generate_evidence_queries(
            topic,
            target_customer=target_customer,
            source_types=source_types,
            quote_terms=quote_terms,
        )
        per_query = min(10, max(3, ceil(max_results / len(queries))))
        candidates: dict[str, WebEvidenceCandidate] = {}

        for query in queries:
            for result in self.provider.search(
                query,
                max_results=per_query,
                search_depth=self.search_depth,
            ):
                candidate = candidate_from_search_result(result, query=query)
                if candidate is None:
                    continue
                key = canonical_url(candidate.url)
                existing = candidates.get(key)
                if existing is None:
                    candidates[key] = candidate
                    continue
                queries_seen = tuple(
                    dict.fromkeys((*existing.source_queries, *candidate.source_queries))
                )
                preferred = (
                    candidate
                    if (candidate.score, len(candidate.raw_text))
                    > (existing.score, len(existing.raw_text))
                    else existing
                )
                candidates[key] = replace(preferred, source_queries=queries_seen)

        return sorted(
            candidates.values(),
            key=lambda item: (item.score, len(item.raw_text)),
            reverse=True,
        )[:max_results]


class AutomatedOpportunityScout:
    """Discover sourced opportunity leads without requiring a user-supplied idea."""

    def __init__(
        self,
        provider: SearchProvider,
        *,
        search_depth: str = "basic",
    ) -> None:
        self.discovery = WebEvidenceDiscoveryService(
            provider,
            search_depth=search_depth,
        )

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
            candidates = self.discovery.discover(
                theme.topic,
                target_customer=theme.target_customer,
                source_types=("discussions",),
                max_results=results_per_theme,
                quote_terms=False,
            )
            unique_candidates: list[WebEvidenceCandidate] = []
            for candidate in candidates:
                url_key = canonical_url(candidate.url)
                if url_key in seen_urls:
                    continue
                seen_urls.add(url_key)
                unique_candidates.append(
                    replace(
                        candidate,
                        theme_key=theme.key,
                        theme_title=theme.title,
                        target_customer=theme.target_customer,
                    )
                )
            if unique_candidates:
                leads.append(
                    ScoutedOpportunity(
                        theme=theme,
                        candidates=tuple(unique_candidates),
                    )
                )
        return leads


def candidate_from_search_result(
    result: SearchResult,
    *,
    query: str,
) -> WebEvidenceCandidate | None:
    """Convert one search result into a reviewable evidence candidate."""

    url = result.url.strip()
    if not url.startswith(("http://", "https://")):
        return None
    raw_text = (result.content or result.snippet).strip()
    if not raw_text:
        return None
    raw_text = raw_text[:MAX_EVIDENCE_TEXT_CHARS].rstrip()
    domain = urlsplit(url).netloc.lower().removeprefix("www.")
    if not domain:
        return None
    return WebEvidenceCandidate(
        title=result.title.strip() or "Untitled public discussion",
        url=url,
        domain=domain,
        raw_text=raw_text,
        snippet=result.snippet.strip(),
        score=float(result.score),
        source_queries=(query,),
    )

from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
import logging
from typing import Dict, Iterable, List, Mapping, Optional

import requests

from ..models import RawArticle
from .base import BaseProvider

SEC_BASE = "https://data.sec.gov"
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"


logger = logging.getLogger(__name__)


class SECClient:
    """Lightweight helper to interact with the SEC EDGAR datasets."""

    def __init__(self, user_agent: str) -> None:
        if not user_agent or "@" not in user_agent:
            raise ValueError("SEC user agent must include a contact email per SEC guidelines")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate",
            }
        )

    def get_json(self, path: str) -> Mapping[str, object]:
        response = self._session.get(f"{SEC_BASE}{path}", timeout=15)
        response.raise_for_status()
        return response.json()

    @lru_cache(maxsize=1)
    def ticker_map(self) -> Dict[str, Dict[str, str]]:
        try:
            response = self._session.get(TICKER_MAP_URL, timeout=15)
            response.raise_for_status()
            payload = response.json()
        except requests.HTTPError as exc:
            logger.warning("SEC ticker map fetch failed: %s", exc)
            return {}
        mapping: Dict[str, Dict[str, str]] = {}
        for item in payload.values():
            ticker = item.get("ticker")
            cik = item.get("cik_str")
            title = item.get("title")
            if isinstance(ticker, str) and isinstance(cik, int):
                mapping[ticker.upper()] = {
                    "cik": f"{cik:010d}",
                    "title": title or ticker.upper(),
                }
        return mapping

    def resolve_cik(self, query: str) -> Optional[Dict[str, str]]:
        normalized = query.strip().upper()
        if not normalized:
            return None
        if normalized.isdigit():
            return {"cik": normalized.zfill(10), "title": normalized}
        mapping = self.ticker_map()
        if normalized in mapping:
            return mapping[normalized]
        # Fallback: fuzzy title match (simple substring)
        for entry in mapping.values():
            title = entry.get("title", "").upper()
            if normalized in title:
                return entry
        return None

    def company_submissions(self, cik: str) -> Mapping[str, object]:
        return self.get_json(f"/submissions/CIK{cik}.json")

    def supplemental_submissions(self, filename: str) -> Mapping[str, object]:
        return self.get_json(f"/submissions/{filename}")

    def company_facts(self, cik: str) -> Mapping[str, object]:
        return self.get_json(f"/api/xbrl/companyfacts/CIK{cik}.json")


class SECFilingsProvider(BaseProvider):
    """Fetches Form 10-K filings from the SEC with basic financial highlights."""

    MAX_AGE_YEARS = 10
    _FINANCIAL_CONCEPTS: Dict[str, List[str]] = {
        "revenue": [
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "SalesRevenueNet",
        ],
        "net_income": ["NetIncomeLoss"],
        "assets": ["Assets"],
        "liabilities": ["Liabilities"],
        "cash": [
            "CashAndCashEquivalentsAtCarryingValue",
            "CashAndCashEquivalentsPeriodIncreaseDecrease",
        ],
    }

    def __init__(self, user_agent: str, max_years: int = MAX_AGE_YEARS) -> None:
        self._client = SECClient(user_agent)
        self._max_years = max(1, max_years)

    def fetch(self, query: str, limit: int = 10, **kwargs: Mapping[str, object]) -> Iterable[RawArticle]:
        identity = self._client.resolve_cik(query)
        if identity is None:
            return []
        cik = identity["cik"]
        company_name = identity.get("title", query.upper())
        cutoff = datetime.utcnow() - timedelta(days=365 * self._max_years)
        filings = self._collect_filings(cik, cutoff)
        if not filings:
            return []
        facts = self._safe_company_facts(cik)
        items: List[RawArticle] = []
        for filing in filings[:limit]:
            summary = self._compose_summary(filing, facts)
            title = f"{company_name} Form 10-K ({filing['filing_date'].year})"
            source = f"SEC 10-K FY{filing.get('fy') or filing['filing_date'].year}"
            items.append(
                RawArticle(
                    title=title,
                    url=filing["url"],
                    source=source,
                    published_at=filing["filing_date"],
                    content=summary,
                    description=summary,
                )
            )
        return items

    def _collect_filings(self, cik: str, cutoff: datetime) -> List[Dict[str, object]]:
        aggregated: Dict[str, Dict[str, object]] = {}
        datasets = []
        submissions = self._safe_company_submissions(cik)
        if submissions:
            datasets.append(submissions)
        if not datasets:
            return []
        extra_files = submissions.get("filings", {}).get("files", []) if isinstance(submissions, Mapping) else []
        for extra in extra_files:
            name = extra.get("name") if isinstance(extra, Mapping) else None
            if isinstance(name, str):
                supplemental = self._safe_supplemental(name)
                if supplemental:
                    datasets.append(supplemental)
        for dataset in datasets:
            records = self._iter_records(dataset)
            for record in records:
                if record.get("form") not in {"10-K", "10-K/A"}:
                    continue
                filing_date = self._parse_date(record.get("filingDate"))
                if filing_date is None or filing_date < cutoff:
                    continue
                accession = record.get("accessionNumber")
                if not accession:
                    continue
                if accession in aggregated:
                    continue
                url = self._build_filing_url(cik, accession, record.get("primaryDocument"))
                aggregated[accession] = {
                    "accession": accession,
                    "filing_date": filing_date,
                    "report_date": self._parse_date(record.get("reportDate")),
                    "fy": record.get("fy"),
                    "form": record.get("form"),
                    "url": url,
                }
        ordered = sorted(aggregated.values(), key=lambda item: item["filing_date"], reverse=True)
        return ordered

    def _safe_company_submissions(self, cik: str) -> Optional[Mapping[str, object]]:
        try:
            return self._client.company_submissions(cik)
        except requests.HTTPError as exc:
            logger.warning("SEC submissions fetch failed for %s: %s", cik, exc)
            return None

    def _safe_supplemental(self, filename: str) -> Optional[Mapping[str, object]]:
        try:
            return self._client.supplemental_submissions(filename)
        except requests.HTTPError as exc:
            logger.warning("SEC supplemental fetch failed for %s: %s", filename, exc)
            return None

    def _iter_records(self, dataset: Mapping[str, object]) -> List[Dict[str, object]]:
        if not isinstance(dataset, Mapping):
            return []
        if "filings" in dataset and isinstance(dataset["filings"], Mapping):
            recent = dataset["filings"].get("recent")
            if isinstance(recent, Mapping):
                return self._normalize_rows(recent)
        return self._normalize_rows(dataset)

    def _normalize_rows(self, payload: Mapping[str, object]) -> List[Dict[str, object]]:
        forms = payload.get("form")
        if not isinstance(forms, list):
            return []
        length = len(forms)
        rows: List[Dict[str, object]] = []
        for idx in range(length):
            row: Dict[str, object] = {}
            for key, value in payload.items():
                if isinstance(value, list) and len(value) > idx:
                    row[key] = value[idx]
            rows.append(row)
        return rows

    def _build_filing_url(self, cik: str, accession: str, primary: Optional[str]) -> str:
        stripped_cik = str(int(cik))  # removes leading zeros
        accession_no_dashes = accession.replace("-", "")
        document = primary or "index.htm"
        return f"https://www.sec.gov/Archives/edgar/data/{stripped_cik}/{accession_no_dashes}/{document}"

    def _parse_date(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            if "T" in value:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None

    def _safe_company_facts(self, cik: str) -> Mapping[str, object]:
        try:
            return self._client.company_facts(cik)
        except requests.HTTPError:
            return {}

    def _compose_summary(self, filing: Mapping[str, object], facts: Mapping[str, object]) -> str:
        accession = filing.get("accession")
        fy = filing.get("fy")
        report_date = filing.get("report_date")
        metrics = self._extract_financials(accession, facts)
        parts = [f"Form {filing.get('form')} filed on {filing['filing_date'].date()}."]
        if fy:
            parts.append(f"Fiscal year: {fy}.")
        if report_date:
            parts.append(f"Period end: {report_date.date()}.")
        if metrics:
            formatted = ", ".join(
                f"{label}: {value}" for label, value in metrics.items()
            )
            parts.append(formatted)
        else:
            parts.append("Financial highlights unavailable from XBRL dataset.")
        return " ".join(parts)

    def _extract_financials(self, accession: Optional[str], facts: Mapping[str, object]) -> Dict[str, str]:
        if not accession or not isinstance(facts, Mapping):
            return {}
        fact_root = facts.get("facts")
        if not isinstance(fact_root, Mapping):
            return {}
        us_gaap = fact_root.get("us-gaap")
        if not isinstance(us_gaap, Mapping):
            return {}
        results: Dict[str, str] = {}
        for label, concepts in self._FINANCIAL_CONCEPTS.items():
            value = self._find_fact_value(us_gaap, concepts, accession)
            if value is not None:
                results[self._label_for(label)] = self._format_currency(value)
        return results

    def _find_fact_value(self, us_gaap: Mapping[str, object], concepts: List[str], accession: str) -> Optional[float]:
        for concept in concepts:
            concept_payload = us_gaap.get(concept)
            if not isinstance(concept_payload, Mapping):
                continue
            units = concept_payload.get("units")
            if not isinstance(units, Mapping):
                continue
            for series in units.values():
                if not isinstance(series, list):
                    continue
                for entry in series:
                    if not isinstance(entry, Mapping):
                        continue
                    if entry.get("accn") == accession and entry.get("form") in {"10-K", "10-K/A"}:
                        val = entry.get("val")
                        if isinstance(val, (int, float)):
                            return float(val)
        return None

    def _label_for(self, key: str) -> str:
        mapping = {
            "revenue": "Revenue",
            "net_income": "Net income",
            "assets": "Total assets",
            "liabilities": "Total liabilities",
            "cash": "Cash & cash equivalents",
        }
        return mapping.get(key, key.title())

    def _format_currency(self, value: float) -> str:
        suffixes = [
            (1e12, "T"),
            (1e9, "B"),
            (1e6, "M"),
        ]
        sign = "-" if value < 0 else ""
        magnitude = abs(value)
        for threshold, suffix in suffixes:
            if magnitude >= threshold:
                return f"{sign}${magnitude / threshold:.2f}{suffix}"
        return f"{sign}${magnitude:,.0f}"

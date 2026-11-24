"""
Ingest the UPS IPO Harvard Business School case into the knowledge base.

Place the zip file (with financial CSVs and any supporting files) into:
    cases/past/ups-ipo/

Then run: python seed_ups_ipo.py

Expected files in cases/past/ups-ipo/:
    brief.md
    outcome.md
    ups_financials.csv
    fedex_financials.csv
    market_data.csv
    (optional) UPS_s_IPO_hbscase.pdf
    (optional) any .zip file — will be auto-extracted
"""

import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace") if hasattr(sys.stdout, "buffer") else sys.stdout

from rich.console import Console
console = Console(file=sys.stdout)

CASE_DIR = Path("cases/past/ups-ipo-case")

BASE_META = {
    "case_name": "UPS IPO Valuation",
    "industry": "logistics/transportation",
    "case_type": "ipo_valuation",
    "date": "1999-11",
    "source": "Harvard Business School Case 9-103-015",
    "author": "Professor Paul Healy",
    "outcome": "ipo_successful_long_term_mixed",
    "company_size": "large_cap",
    "revenue": "$25B",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _id(label: str) -> str:
    return hashlib.md5(f"ups_ipo_{label}".encode()).hexdigest()


def _chunk(label: str, text: str, chunk_type: str, extra_meta: dict = None) -> dict:
    meta = {**BASE_META, "chunk_type": chunk_type}
    if extra_meta:
        meta.update(extra_meta)
    return {
        "id": _id(label),
        "text": text.strip()[:3000],
        "metadata": meta,
    }


def _extract_zips():
    """Auto-extract any zip files found in the case directory."""
    for zf in CASE_DIR.glob("*.zip"):
        console.print(f"  [cyan]Extracting {zf.name}...[/cyan]")
        with zipfile.ZipFile(zf, "r") as z:
            z.extractall(CASE_DIR)
        console.print(f"  [green]Extracted {zf.name}[/green]")


def _split_markdown_sections(text: str) -> dict[str, str]:
    """Split markdown into {header: body} dict using ## or ### as section boundaries."""
    sections = {}
    current_header = "__preamble__"
    current_body = []
    for line in text.splitlines():
        if line.startswith("## ") or line.startswith("### "):
            if current_body:
                sections[current_header] = "\n".join(current_body).strip()
            current_header = line.lstrip("#").strip()
            current_body = []
        else:
            current_body.append(line)
    if current_body:
        sections[current_header] = "\n".join(current_body).strip()
    return sections


def _fuzzy_match(sections: dict, *keywords) -> str | None:
    """Find the first section whose header contains any of the keywords (case-insensitive)."""
    for header, body in sections.items():
        h = header.lower()
        if any(kw.lower() in h for kw in keywords):
            return body
    return None


# ── Brief.md chunking ─────────────────────────────────────────────────────────

def chunks_from_brief(path: Path) -> list:
    text = path.read_text(encoding="utf-8", errors="replace")
    sections = _split_markdown_sections(text)
    chunks = []

    # Full brief as one searchable blob (truncated)
    chunks.append(_chunk(
        "brief_full",
        f"UPS IPO CASE BRIEF (HBS 9-103-015):\n{text[:3000]}",
        "context",
    ))

    # Client overview + current situation
    overview = _fuzzy_match(sections, "client overview", "overview", "current situation", "situation")
    if overview:
        chunks.append(_chunk("brief_overview", f"UPS CLIENT OVERVIEW & SITUATION:\n{overview}", "context"))

    # Industry context
    industry = _fuzzy_match(sections, "industry", "market context", "package delivery")
    if industry:
        chunks.append(_chunk("brief_industry", f"UPS INDUSTRY CONTEXT ($43B Package Delivery Market):\n{industry}", "context"))

    # Strategic questions — each as its own chunk
    strat = _fuzzy_match(sections, "strategic question", "key question", "strategic challenge")
    if strat:
        # Try to split into individual questions
        questions = re.split(r"\n(?=\d+\.|\*|\-)", strat)
        for i, q in enumerate(questions):
            q = q.strip()
            if len(q) > 50:
                chunks.append(_chunk(
                    f"brief_strategic_q_{i}",
                    f"UPS IPO STRATEGIC QUESTION:\n{q}",
                    "problem_statement",
                ))

    # Stakeholder perspectives — each as its own chunk
    stakeholder_section = _fuzzy_match(sections, "stakeholder", "perspective", "ceo", "morgan stanley")
    if stakeholder_section:
        # Split by sub-headers or dashes indicating individual stakeholders
        stakeholder_parts = re.split(r"\n(?=###|\*\*[A-Z])", stakeholder_section)
        for i, part in enumerate(stakeholder_parts):
            part = part.strip()
            if len(part) > 80:
                chunks.append(_chunk(
                    f"brief_stakeholder_{i}",
                    f"UPS IPO STAKEHOLDER PERSPECTIVE:\n{part}",
                    "stakeholder_input",
                ))
    else:
        # Try individual stakeholder-named sections
        for name in ["james kelly", "morgan stanley", "fedex", "employee", "analyst"]:
            match = _fuzzy_match(sections, name)
            if match:
                chunks.append(_chunk(
                    f"brief_stakeholder_{name.replace(' ', '_')}",
                    f"UPS IPO STAKEHOLDER — {name.title()}:\n{match}",
                    "stakeholder_input",
                ))

    # Financial highlights
    financials = _fuzzy_match(sections, "financial highlight", "financial summary", "financials")
    if financials:
        chunks.append(_chunk("brief_financials", f"UPS IPO FINANCIAL HIGHLIGHTS:\n{financials}", "financial_data"))

    # Operating advantages
    ops = _fuzzy_match(sections, "operating advantage", "competitive advantage", "operations")
    if ops:
        chunks.append(_chunk("brief_ops_advantages", f"UPS OPERATING ADVANTAGES:\n{ops}", "finding"))

    # Growth vectors
    growth = _fuzzy_match(sections, "growth vector", "growth opportunit", "globalization", "e-commerce", "supply chain")
    if growth:
        chunks.append(_chunk("brief_growth_vectors", f"UPS GROWTH VECTORS (1999):\n{growth}", "context"))

    # Valuation benchmarks
    valuation = _fuzzy_match(sections, "valuation", "benchmark", "best of breed", "comparable", "multiple")
    if valuation:
        chunks.append(_chunk("brief_valuation", f"UPS IPO VALUATION BENCHMARKS:\n{valuation}", "financial_data"))

    console.print(f"  → brief.md: {len(chunks)} chunks")
    return chunks


# ── CSV chunking ──────────────────────────────────────────────────────────────

def chunks_from_financials(ups_path: Path, fedex_path: Path) -> list:
    chunks = []

    def _read_csv(p: Path) -> str:
        try:
            return p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    ups_raw = _read_csv(ups_path) if ups_path.exists() else ""
    fedex_raw = _read_csv(fedex_path) if fedex_path.exists() else ""

    # Natural language summary of UPS financials
    ups_summary = """UPS FINANCIAL PERFORMANCE (1994-1998):
Revenue grew from $19.6B (1994) to $24.8B (1998) — a 6% CAGR over 5 years.
Net income margins expanded from 4.8% (1994) to 7.0% (1998), showing improving operational leverage.
Return on equity (ROE) of 25.2% — exceptional for a capital-intensive logistics company.
Capital expenditure ran at ~$1.5-2B annually, reflecting heavy investment in fleet, technology, and hubs.
Daily package volume: ~12-13M ground packages and ~1.2M air packages per day by 1998.
Revenue per piece (ground): modest growth as pricing remained competitive vs. FedEx.
Revenue per piece (air): premium pricing maintained due to time-definite delivery reliability.
Operating ratio (costs as % of revenue): consistently below industry average, demonstrating efficiency advantage.
The integrated ground/air network created structural cost advantages that FedEx, operating two separate networks, could not easily replicate.

Raw CSV data available: """ + (ups_raw[:500] if ups_raw else "File not found")

    chunks.append(_chunk("financials_ups", ups_summary, "financial_data"))

    # FedEx comparison
    fedex_summary = """FEDEX FINANCIAL COMPARISON vs. UPS (Late 1990s):
FedEx revenue: approximately $10-12B — roughly half of UPS's $24.8B.
FedEx net margins: ~3.8% — significantly below UPS's 7.0%, reflecting separate ground/air network inefficiency.
FedEx ROE: 10.6% — less than half of UPS's 25.2%, indicating UPS's superior capital efficiency.
FedEx P/E ratio: 19.8x at time of UPS IPO analysis.
FedEx Price/Revenue: 0.74x.
FedEx Market/Book: 2.68x.
FedEx Beta: 1.16 — indicating higher market risk perception than UPS.
FedEx operating lease obligations: $13.1B — significant off-balance-sheet liability reflecting aircraft/vehicle leases.
The financial gap between UPS and FedEx supported the argument that UPS deserved a premium multiple.
However, FedEx's separate air network gave it flexibility to serve international express markets that UPS was still building.

Raw CSV data available: """ + (fedex_raw[:500] if fedex_raw else "File not found")

    chunks.append(_chunk("financials_fedex", fedex_summary, "financial_data"))

    # Comparative summary
    comparison = """UPS vs. FedEx COMPARATIVE ANALYSIS (1999 IPO Context):
The core valuation question: should UPS be priced like FedEx (logistics peer) or like "best of breed" consumer/retail companies?

UPS financial superiority over FedEx:
- Revenue: UPS $24.8B vs. FedEx ~$11B (2.2x larger)
- Net margin: UPS 7.0% vs. FedEx 3.8% (84% higher margins)
- ROE: UPS 25.2% vs. FedEx 10.6% (2.4x more efficient)
- Network density advantage: UPS's integrated ground/air network had lower cost-per-package than FedEx's parallel networks

Implication for IPO pricing:
- Using FedEx multiples (P/E ~19.8x) as the floor, UPS's superior financials justified a premium
- The "best of breed" argument (Coca-Cola, Walmart comparables at 30-40x P/E) was aggressive but not unreasonable given UPS's dominant market position
- Actual IPO priced at $50/share, implying ~25-27x P/E — between FedEx and best-of-breed
- 25-year retrospective: FedEx multiples proved more appropriate than best-of-breed, as logistics companies face capital intensity and labor cost constraints that consumer brands do not"""

    chunks.append(_chunk("financials_comparison", comparison, "financial_data"))

    console.print(f"  → financials: {len(chunks)} chunks")
    return chunks


def chunks_from_market_data(path: Path) -> list:
    chunks = []
    raw = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""

    market_summary = """UPS IPO MARKET CONTEXT — Package Delivery Industry (1999):
Total US package delivery market: approximately $43B in 1999.
Market growth: industry had grown at ~7-8% annually through the 1990s, driven by business-to-business shipping.
E-commerce (1999): nascent but explosive growth projected — Amazon, eBay, and other online retailers were just beginning to drive B2C parcel volume.
Projections for 2005: analysts expected e-commerce to dramatically accelerate package volumes, particularly last-mile delivery.

Market share (approximate, 1999):
- UPS: ~60% of ground package market, ~30% of air express
- FedEx: dominant in overnight air express (~45%), growing in ground
- Airborne Express: ~15-20% of air express
- USPS: significant in first-class/parcel post, non-competitor in express

Key competitive dynamics:
- UPS's integrated network (same trucks do ground and air pickup) created cost advantage
- FedEx acquired Caliber Systems (1998) to build a ground network to compete with UPS — threat to UPS's core business
- International: both UPS and FedEx were investing heavily to build global networks; neither had dominant international position yet

Raw CSV data available: """ + (raw[:500] if raw else "File not found")

    chunks.append(_chunk("market_size_and_share", market_summary, "context"))

    best_of_breed = """UPS IPO "BEST OF BREED" COMPARABLE VALUATION ANALYSIS:
The Morgan Stanley deal team argued UPS should be valued not just against logistics peers (FedEx) but against "best of breed" market leaders in their respective industries.

Best-of-breed comparables (approximate 1999 multiples):
- Coca-Cola: ~35-40x P/E, ~8x revenue — dominant brand, pricing power, global distribution
- Walmart: ~30-35x P/E — dominant market position, logistics excellence, scale
- Home Depot: ~25-30x P/E — dominant in its category, growth retailer

The best-of-breed argument for UPS:
1. UPS had 60%+ market share in ground delivery — comparable dominance to Coca-Cola in beverages
2. Network effects: the more packages UPS carries, the more efficient the network becomes (density advantage)
3. Brand: "Brown" had near-100% brand recognition, associated with reliability
4. Pricing power: UPS had historically been a price leader, not follower

Why best-of-breed multiples were ultimately too aggressive (25-year retrospective):
- Logistics is capital-intensive; consumer brands are not — Coca-Cola doesn't need to buy $2B in trucks annually
- Labor costs: UPS's Teamsters union contracts created structural wage inflation that consumer brands avoid
- Amazon dependency risk: in 1999, Amazon was a customer. By 2024, Amazon became a competitor.
- Asset-light businesses (Coca-Cola, Walmart relative to logistics) deserve higher multiples than asset-heavy ones"""

    chunks.append(_chunk("market_best_of_breed_comparables", best_of_breed, "financial_data"))

    console.print(f"  → market_data: {len(chunks)} chunks")
    return chunks


# ── Outcome.md chunking ───────────────────────────────────────────────────────

def chunks_from_outcome(path: Path) -> list:
    text = path.read_text(encoding="utf-8", errors="replace")
    sections = _split_markdown_sections(text)
    chunks = []

    # IPO pricing and first-day results
    ipo_result = _fuzzy_match(sections, "ipo pricing", "first day", "priced", "november 1999", "ipo result")
    if ipo_result:
        chunks.append(_chunk("outcome_ipo_day", f"UPS IPO RESULT:\n{ipo_result}", "recommendation"))
    else:
        # Use beginning of outcome text
        chunks.append(_chunk(
            "outcome_ipo_day",
            f"UPS IPO RESULT:\nIPO priced at $50/share on November 9, 1999. Raised $5.47 billion — the largest US IPO ever at the time. Stock opened at $64.40, a 29% first-day pop, closing near $66. Implied market cap of approximately $80-90B at peak first-day trading.\n\n{text[:500]}",
            "recommendation",
        ))

    # Post-IPO eras
    for era_keyword, era_label, era_slug in [
        (["2000", "2001", "2002", "early 2000", "dot-com"], "Post-IPO Early Years (2000-2007)", "outcome_era_early"),
        (["2008", "2009", "financial crisis", "recession"], "Financial Crisis Era", "outcome_era_crisis"),
        (["2020", "2021", "covid", "pandemic"], "COVID Era Peak", "outcome_era_covid"),
        (["amazon", "2022", "2023", "2024", "decline", "long-term"], "Amazon Threat and Long-Term Performance", "outcome_era_amazon"),
    ]:
        match = _fuzzy_match(sections, *era_keyword)
        if match:
            chunks.append(_chunk(era_slug, f"UPS {era_label.upper()}:\n{match}", "finding"))

    # What worked
    worked = _fuzzy_match(sections, "what worked", "success", "worked well", "positive")
    if worked:
        chunks.append(_chunk("outcome_what_worked", f"UPS IPO — WHAT WORKED:\n{worked}", "recommendation"))

    # What didn't work
    didnt = _fuzzy_match(sections, "what didn't", "what failed", "downside", "didn't work", "lessons learned", "what went wrong")
    if didnt:
        chunks.append(_chunk("outcome_what_failed", f"UPS IPO — WHAT DIDN'T WORK / LESSONS:\n{didnt}", "recommendation"))

    # Amazon lesson specifically — flag prominently
    amazon = _fuzzy_match(sections, "amazon")
    if amazon:
        chunks.append(_chunk(
            "outcome_amazon_lesson",
            f"UPS AMAZON CUSTOMER CONCENTRATION RISK (Critical Pattern for Future Cases):\n{amazon}\n\nPattern: In 1999, Amazon was seen as a growth opportunity for UPS — a major e-commerce customer driving volume. By 2024, Amazon built its own delivery network (Amazon Logistics) and became UPS's biggest competitive threat. This is a powerful warning pattern: a customer who represents 10%+ of revenue and has the scale and motivation to vertically integrate is a strategic risk, not just a customer. Always ask: 'Could this customer become a competitor?'",
            "finding",
            {"special_pattern": "customer_becomes_competitor"},
        ))

    # General lessons chunk
    lessons = _fuzzy_match(sections, "lesson", "key lesson", "takeaway", "implication")
    if lessons:
        chunks.append(_chunk("outcome_lessons", f"UPS IPO KEY LESSONS FOR KNOWLEDGE BASE:\n{lessons}", "finding"))
    else:
        # Write a synthesized lessons chunk
        chunks.append(_chunk(
            "outcome_lessons_synthesized",
            """UPS IPO SYNTHESIZED LESSONS (HBS Case 9-103-015):

1. VALUATION METHODOLOGY: "Best of breed" comparables (Coca-Cola, Walmart multiples) overvalued UPS. FedEx multiples were more appropriate because logistics companies face capital intensity and union labor cost constraints that asset-light consumer brands do not. The lesson: peer comparables should share the same fundamental economics, not just the same market dominance.

2. IPO AS ACQUISITION CURRENCY: The IPO was strategically correct — UPS used public equity to acquire Mailboxes Etc., Fritz Companies, and other logistics players in the 2000s. The primary IPO value was strategic, not just financial.

3. CULTURE PRESERVATION: The employee-owner culture (all employees owned stock pre-IPO) was partially preserved through the IPO structure but eroded over time as new employees joined without the same ownership mentality. Going public changes organizational culture in ways that are difficult to prevent.

4. E-COMMERCE POSITIONING: The 1999 analysis correctly identified e-commerce as a major growth driver. UPS was well-positioned for B2C parcel growth. The forecast was right; what wasn't anticipated was that the largest e-commerce player would eventually become a direct competitor.

5. CUSTOMER CONCENTRATION RISK: Amazon grew to represent ~13% of UPS revenue by the early 2020s. When Amazon built its own delivery network, UPS had to restructure volumes and pricing significantly. Any customer representing 10%+ of revenue who has the scale and motivation to vertically integrate is a strategic risk.

6. S&P 500 UNDERPERFORMANCE: Despite steady business fundamentals, UPS underperformed the S&P 500 over the 25 years post-IPO — a reminder that a good business at an expensive price is still a poor investment.""",
            "finding",
        ))

    console.print(f"  → outcome.md: {len(chunks)} chunks")
    return chunks


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    console.print("\n[bold cyan]Ingesting UPS IPO HBS Case into knowledge base...[/bold cyan]\n")

    if not CASE_DIR.exists():
        CASE_DIR.mkdir(parents=True, exist_ok=True)
        console.print(f"  [yellow]Created {CASE_DIR} — place your files there and re-run.[/yellow]")
        return

    # Extract any zip files first
    _extract_zips()

    # Check what files we have
    brief_path = CASE_DIR / "brief.md"
    outcome_path = CASE_DIR / "outcome.md"
    ups_csv = CASE_DIR / "ups_financials.csv"
    fedex_csv = CASE_DIR / "fedex_financials.csv"
    market_csv = CASE_DIR / "market_data.csv"

    missing = [p.name for p in [brief_path, outcome_path] if not p.exists()]
    if missing:
        console.print(f"  [red]Missing required files: {', '.join(missing)}[/red]")
        console.print(f"  [dim]Place files in: {CASE_DIR.resolve()}[/dim]")
        # List what we do have
        found = list(CASE_DIR.rglob("*"))
        if found:
            console.print(f"  [dim]Found: {', '.join(f.name for f in found if f.is_file())}[/dim]")
        return

    # Build all chunks
    all_chunks = []
    all_chunks.extend(chunks_from_brief(brief_path))
    all_chunks.extend(chunks_from_financials(ups_csv, fedex_csv))
    all_chunks.extend(chunks_from_market_data(market_csv))
    all_chunks.extend(chunks_from_outcome(outcome_path))

    # Write metadata.json for the cases list command
    metadata = {
        "case_name": "UPS IPO Valuation",
        "date_analyzed": "1999-11",
        "n_agents": 0,
        "n_rounds": 0,
        "total_tokens": 0,
        "total_cost_usd": 0,
        "top_recommendations": [
            "Price between FedEx peer multiples and best-of-breed — FedEx floor, brand premium justified",
            "Use IPO proceeds as acquisition currency for strategic logistics acquisitions",
            "Preserve employee ownership culture through structured equity programs post-IPO",
            "Assess customer concentration risk — any 10%+ customer who can vertically integrate is a strategic threat",
        ],
        "bottom_line": "IPO at $50 raised $5.47B (largest US IPO ever). 25-year arc: steady growth through 2015, COVID peak at $192, then Amazon-driven decline to ~$100.",
        "industry": "logistics/transportation",
        "case_type": "ipo_valuation",
        "source": "Harvard Business School Case 9-103-015",
    }
    (CASE_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # Embed
    console.print(f"\n[bold cyan]Embedding {len(all_chunks)} chunks into ChromaDB...[/bold cyan]")
    try:
        from knowledge.vectorstore import store_chunks
        store_chunks(all_chunks)
        console.print(f"\n[bold green]Done! {len(all_chunks)} chunks embedded for UPS IPO case.[/bold green]")
        console.print("[dim]Run: python main.py cases  — to verify[/dim]\n")
    except Exception as e:
        console.print(f"\n[red]Embedding failed: {e}[/red]")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

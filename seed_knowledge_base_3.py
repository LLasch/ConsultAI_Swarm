"""
Seed the knowledge base with 10 more real-world business cases (Cases 21-30).
Creates cases/past/ directories and embeds all chunks into ChromaDB.

Run: python seed_knowledge_base_3.py
"""

import hashlib
import json
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace") if hasattr(sys.stdout, "buffer") else sys.stdout

from rich.console import Console
console = Console(file=sys.stdout)


CASES = [
    {
        "name": "Spotify Freemium Music Streaming",
        "slug": "spotify-freemium-model",
        "industry": "technology",
        "case_type": "digital_transformation",
        "date": "2008-10-01",
        "problem": """Music Industry Revenue Collapse and Piracy Crisis (2008)

In 2008, the music industry was in freefall. Revenue had dropped from $23.3B (1999) to $14.6B (2008) due to piracy (Napster, LimeWire, BitTorrent). Apple's iTunes had proven people would pay for digital music per-song, but there was no recurring revenue model. Artists and labels were desperate for monetization but deeply skeptical of anything that looked like "giving music away for free." """,

        "decision": """Freemium Streaming Strategy with Label Equity Alignment

Daniel Ek launched Spotify in Sweden (2008), expanding to the US in 2011:
1. Free tier with ads — unlimited streaming deliberately "good enough" to kill piracy but annoying enough to nudge users toward paying
2. Premium tier at $9.99/month — no ads, offline downloads, higher audio quality
3. Negotiated licensing deals with all major labels — gave labels equity stakes in Spotify as part of licensing agreements, aligning their incentives with Spotify's growth
4. Invested heavily in algorithmic discovery — Discover Weekly, Release Radar, personalized playlists. This became the core retention mechanism.
5. Expanded into podcasts — acquired Gimlet Media ($230M), Anchor ($150M), Joe Rogan exclusive deal ($200M) between 2019-2020 to diversify beyond music
6. Direct listing on NYSE (2018) — bypassed traditional IPO, letting existing shareholders sell directly""",

        "outcome": """Results (2008-2024):

- Grew from 0 to 600M+ users (including 240M+ paying subscribers) by 2024
- Became world's largest music streaming platform — 31% global market share
- Music industry revenue recovered from $14.6B (2008) to $28.6B (2023), with streaming at 67% — Spotify almost single-handedly reversed the industry's decline
- Free tier conversion rate: ~45% — one of the best freemium conversion rates in tech
- Gross margins stuck at 25-28% because ~70% of music revenue goes to labels — Spotify didn't report meaningful profit until Q3 2023, 15 years after launch
- Podcast investments largely written down — Gimlet restructured, Joe Rogan deal went non-exclusive
- Stock: peaked $364 (2021), dropped to $70 (late 2022), recovered to $300+ (2024) after profitability through cost cutting
- Average per-stream artist payout of $0.003-0.005 became a cultural flashpoint

Key Lesson: Freemium can grow a market, not just capture one. Spotify converted pirates into paying customers by offering a legal alternative easier than piracy. But being the distribution platform doesn't guarantee profits when content owners (labels) hold the pricing power.""",

        "top_recommendations": [
            "Align content owners' incentives with platform growth through equity stakes, not just licensing fees",
            "Design free tier to be genuinely useful (kills piracy) but friction-filled enough to drive premium conversion",
            "Invest in algorithmic discovery as the primary retention mechanism — recommendations keep users longer than catalog size",
            "Recognize that platform margins are capped by content owner leverage — pursue non-music revenue (podcasts) to escape the constraint",
        ],
        "bottom_line": "Reversed a dying industry by converting pirates to subscribers, but content owner leverage caps profitability — 15 years to first meaningful profit.",
    },

    {
        "name": "Blockbuster Declined Netflix Acquisition",
        "slug": "blockbuster-netflix-decline",
        "industry": "retail",
        "case_type": "digital_transformation",
        "date": "2000-01-01",
        "problem": """Blockbuster DVD Rental Empire vs. Netflix Threat (2000)

In 2000, Blockbuster was a $6 billion revenue empire with 9,000+ stores worldwide. Netflix, a tiny DVD-by-mail startup with 300,000 subscribers and $57M in revenue, was bleeding cash. Netflix co-founder Reed Hastings flew to Dallas and offered to sell Netflix to Blockbuster for $50 million. CEO John Antioco reportedly laughed them out of the room. Late fees alone generated $800M/year for Blockbuster. This is the most famous missed acquisition in business history.""",

        "decision": """Series of Strategic Errors Culminating in Bankruptcy — CAUTIONARY TALE

1. Declined the Netflix acquisition in 2000 for $50M
2. Eventually launched Blockbuster Online (2004) — which was actually gaining traction and threatening Netflix
3. CEO Antioco proposed eliminating late fees ($200M revenue hit) and investing aggressively in online — the board and activist investor Carl Icahn opposed as too costly
4. Antioco forced out in 2007, replaced by Jim Keyes (former 7-Eleven CEO) who believed physical retail was Blockbuster's strength
5. Under Keyes, Blockbuster tried to compete with Redbox (DVD kiosks) instead of Netflix streaming — completely misreading which competitor mattered
6. Filed for Chapter 11 bankruptcy in September 2010 with $900M in debt""",

        "outcome": """Results — COMPLETE DESTRUCTION OF VALUE:

- Blockbuster: $6B revenue → bankruptcy in 10 years. Last corporate-owned store closed in 2014. One franchise location in Bend, Oregon remains open as a tourist attraction.
- Netflix: $50M acquisition offer → worth $160B+ by 2023
- The $50M acquisition declined would have been worth approximately 320,000x that amount
- Ironically, Antioco was the CEO who understood the threat — his online strategy was working. The board and Icahn, focused on quarterly profits, killed the one person trying to save the company.
- Carl Icahn's activist investment in Blockbuster is widely considered one of the worst activist campaigns in corporate history

Key Lesson: The biggest strategic errors aren't always made by clueless executives — sometimes the right person sees the threat, proposes the right response, and gets overruled by shareholders focused on short-term profits. Also: the $50M Netflix acquisition would be the single greatest missed deal in business history.""",

        "top_recommendations": [
            "Never decline an acquisition of a direct competitor at a price that represents less than 1% of your own revenue",
            "When an activist investor forces out the CEO pursuing digital transformation, the activist is usually wrong",
            "Identify which competitor actually threatens your existence vs. which is a distraction — Blockbuster fought Redbox while Netflix killed them",
            "Late fees as a revenue line ($800M/year) were a strategic liability — they created customer resentment that drove adoption of alternatives",
        ],
        "bottom_line": "FAILURE CASE: Declined $50M Netflix acquisition → $6B company went bankrupt. Board overruled the CEO who had the right strategy.",
    },

    {
        "name": "Airbnb COVID Pivot to Rural and Long-Term Stays",
        "slug": "airbnb-covid-pivot",
        "industry": "technology",
        "case_type": "turnaround",
        "date": "2020-03-01",
        "problem": """Airbnb COVID-19 Existential Crisis (2020)

In February 2020, Airbnb was preparing for a blockbuster IPO. By April 2020, bookings had collapsed 72% year-over-year as global travel stopped. Revenue dropped from $1.2B (Q1 2020 estimate) to $335M (Q2 2020). The company's entire business model — strangers sleeping in other people's homes in popular urban destinations — seemed incompatible with a pandemic. Airbnb laid off 25% of its workforce (1,900 employees). The IPO was shelved indefinitely.""",

        "decision": """Data-Driven Pivot to Rural, Domestic, and Long-Term Stays

1. Cut $800M in costs in 8 weeks — halted all marketing spend, froze hiring, cut executive salaries, suspended projects
2. Noticed a signal in the data: while urban bookings cratered, searches for rural and domestic getaways were spiking
3. Completely redesigned the homepage — shifted from city search to flexible search and curated categories: Cabins, Lakefront, Countryside, Unique Stays, Tiny Homes
4. Launched "Go Near" campaign — promoted local and domestic travel within driving distance
5. Leaned into long-term stays (28+ days) — remote work enabled people to work from anywhere. Added features for monthly stays and negotiated lower rates.
6. Simplified the product — cut 50% of internal projects and features to focus on the core booking experience
7. Went public in December 2020 — IPO priced at $68, opened at $146 on first trade""",

        "outcome": """Results (2020-2022):

- Revenue: $3.4B (2019) → $6.0B (2021) → $8.4B (2022) — fully recovered and surpassed pre-pandemic levels
- Stock opened at $146 on IPO day (December 2020) — more than 2x the $68 IPO price. Market cap hit $100B+.
- Long-term stays (28+ days) became the fastest-growing segment — 20%+ of total bookings by 2022
- Category-based search (Cabins, Treehouses) drove a permanent shift in how people use Airbnb
- Airbnb became profitable for the first time in its history in 2022 — $1.9B net income
- Marketing spend was permanently reduced from ~$1.6B/year to ~$400M — proving the brand was strong enough to grow without heavy paid advertising
- Chesky's letter to laid-off employees became a widely-cited model for humane layoffs

Key Lesson: Crisis is a filter — it forces you to see what actually matters. Airbnb's pre-pandemic business was bloated with projects and features. The 72% revenue drop forced a clarity that voluntary strategy reviews never achieve. The pivot to rural/domestic/long-term stays wasn't a prediction — it was reading real-time demand data and responding in weeks rather than quarters.""",

        "top_recommendations": [
            "Watch for demand signals in your own data during a crisis — Airbnb found the rural/domestic opportunity by reading search behavior",
            "Product simplification during crisis often reveals what the product should have always been",
            "Long-term/subscription-style usage (monthly stays) creates more predictable revenue than pure transactional bookings",
            "Cutting marketing spend dramatically can be the right call when brand recognition is high — test before assuming paid acquisition is necessary",
        ],
        "bottom_line": "72% revenue collapse forced product clarity and a pivot to rural/long-term stays that made the company more profitable than before.",
    },

    {
        "name": "Nokia Mobile Phone Collapse",
        "slug": "nokia-smartphone-collapse",
        "industry": "technology",
        "case_type": "digital_transformation",
        "date": "2007-01-01",
        "problem": """Nokia Market Leadership vs. iPhone and Android Disruption (2007)

In 2007, Nokia had 49.4% global mobile phone market share — selling more phones than Samsung, Motorola, Sony Ericsson, and LG combined. Nokia's Symbian OS powered the majority of smartphones on Earth. But Nokia's smartphones were designed for a pre-touch era: physical keyboards, resistive touchscreens, complex menus, and an OS increasingly difficult for developers to build apps for. The iPhone (2007) and Android (2008) represented a fundamentally different vision of what a phone could be.""",

        "decision": """Fragmented Response Ending in Microsoft Partnership — CAUTIONARY TALE

1. Dismissed the iPhone as a niche product — Nokia's head of smartphones said "we have nothing to worry about"
2. Continued investing in Symbian despite internal engineering teams warning it was architecturally outdated
3. Experimented with multiple alternative OS projects simultaneously (Maemo, MeeGo) — fragmenting R&D resources without fully committing to any
4. Hired Stephen Elop as CEO (2010) — first non-Finnish CEO, former Microsoft executive. Issued the famous "Burning Platform" memo comparing Nokia to a man on a burning oil platform.
5. Partnered exclusively with Microsoft Windows Phone (February 2011) — abandoning Symbian and MeeGo. Bet the entire smartphone future on a third-place mobile OS.
6. Released the Lumia series — well-designed hardware running Windows Phone, but the app ecosystem was a fraction of iOS/Android""",

        "outcome": """Results — CATASTROPHIC MARKET SHARE COLLAPSE:

- Market share: 49.4% (2007) → 24.7% (2011) → 3.4% (2013)
- Revenue: €51B (2007) → €25.5B (2012)
- Stock dropped 90%+ from 2007 peak
- Windows Phone never exceeded 3.6% global smartphone market share — the app gap was insurmountable
- The "Burning Platform" memo accurately described the problem but the chosen solution (Windows Phone) made things worse
- Microsoft acquired Nokia's phone division for $7.2B in September 2013
- Microsoft wrote off the entire acquisition as a loss in 2015 — laying off 18,000 former Nokia employees
- Nokia pivoted to telecommunications infrastructure (5G networks) — a completely different business

Key Lesson: The "Burning Platform" memo was right about the diagnosis but the treatment killed the patient. By publicly declaring Symbian dead before Windows Phone was ready, Elop cratered existing Nokia sales immediately while the replacement product was months away. Also: betting on a third-place platform in a platform war is almost always fatal — app ecosystem winner-take-most dynamics make catching up nearly impossible.""",

        "top_recommendations": [
            "Never publicly declare your existing platform dead until the replacement is ready to ship — you will crater sales of both",
            "In platform wars with network effects, third place is effectively last place — the app ecosystem gap is insurmountable",
            "Fragmented R&D across multiple competing OS projects (Symbian, Maemo, MeeGo) produces nothing — commit fully to one",
            "When a competitor redefines the category, your technical superiority in the old category definition becomes irrelevant",
        ],
        "bottom_line": "FAILURE CASE: 49% market share to 3.4% in 6 years. Right diagnosis (Burning Platform), wrong treatment (Windows Phone partnership).",
    },

    {
        "name": "IKEA Flat Pack Supply Chain Revolution",
        "slug": "ikea-flat-pack-model",
        "industry": "retail",
        "case_type": "growth_strategy",
        "date": "1956-01-01",
        "problem": """IKEA Supplier Boycott and Forced Reinvention (1950s)

In the 1950s, IKEA founder Ingvar Kamprad faced a boycott. Swedish furniture manufacturers, threatened by IKEA's low-price catalog business, pressured suppliers to stop selling to IKEA. The Swedish furniture industry association banned IKEA from trade fairs. Kamprad suddenly couldn't source furniture for his catalog. The company's existence was threatened.""",

        "decision": """Constraint-Driven Business Model Innovation

The supplier boycott forced IKEA to reinvent its entire model:
1. Designed its own furniture — since no one would sell to IKEA, it started designing in-house. Born from necessity, not strategy.
2. Invented flat-pack shipping — removing table legs to fit in a car revealed that unassembled furniture was dramatically cheaper to transport and store. Customers would assemble it themselves.
3. Sourced from Poland and other low-cost countries — circumvented the Swedish supplier boycott by going international. Reduced production costs by 50%+.
4. Built massive warehouse-style stores — customers browse a showroom, then pick up flat-packed boxes from a warehouse section
5. Added restaurant, childcare, and "experience" — turned furniture shopping from a chore into a destination
6. Created a complex Dutch foundation ownership structure — making it effectively impossible to acquire and minimizing taxes. Provides extraordinary strategic patience.
7. Maintained uniform design language globally — same stores, same products, same experience in 62 countries""",

        "outcome": """Results (1956-2023):

- Revenue: ~€50B (2023) — the world's largest furniture retailer by a massive margin
- 460+ stores in 62 countries, with 775 million store visits per year
- IKEA serves approximately 1 billion meals per year in its restaurants — one of the world's largest restaurant chains
- Flat-pack model reduced shipping costs by ~80% vs. assembled furniture, enabling retail prices 30-50% below competitors
- BILLY bookcase: 110M+ units sold since 1979 — roughly one for every 70 humans on Earth
- Foundation ownership structure means IKEA never faces quarterly earnings pressure — can invest in decades-long bets
- Online sales only ~20% of revenue by 2023 — deliberately slower to e-commerce than most retailers

Key Lesson: Constraints breed innovation. Every defining feature of IKEA's model — in-house design, flat-pack, international sourcing, warehouse stores — was a response to being boycotted by the existing industry. The supplier boycott that was meant to destroy IKEA instead forced it to create the most disruptive retail model in furniture history. Private/foundation ownership structures provide strategic patience that public companies can't match.""",

        "top_recommendations": [
            "Vertical integration forced by external constraints (supplier boycott) can create durable competitive advantages",
            "Transferring assembly labor to customers (flat-pack) dramatically reduces costs and enables lower retail prices — but requires design quality to compensate",
            "Foundation/private ownership structures provide multi-decade strategic patience unavailable to publicly traded companies",
            "The in-store experience (restaurant, childcare) drives destination visits and longer dwell time — adjacencies that seem unrelated to core business can be strategic",
        ],
        "bottom_line": "Supplier boycott forced in-house design, flat-pack, and international sourcing — constraints that created the world's most disruptive furniture retailer.",
    },

    {
        "name": "Theranos Blood Testing Fraud",
        "slug": "theranos-fraud",
        "industry": "healthcare",
        "case_type": "general_strategy",
        "date": "2003-01-01",
        "problem": """Theranos Blood Testing Vision vs. Reality (2003-2015)

Elizabeth Holmes founded Theranos in 2003 with a compelling vision: a device that could run hundreds of blood tests from a single finger prick. If real, this would have transformed diagnostics — faster, cheaper, less painful testing available at pharmacies rather than labs. The market was real and enormous. The technology was not.""",

        "decision": """Fraudulent Scaling of Unproven Technology — CAUTIONARY / FRAUD CASE

1. Raised $700M+ in venture capital on the basis of vision, celebrity board members (Henry Kissinger, George Shultz, James Mattis), and charismatic storytelling — without allowing technical due diligence
2. Launched partnership with Walgreens (2013) — opened Wellness Centers in 40+ stores in Arizona, running real patient blood tests
3. The technology never actually worked — the proprietary "Edison" device could only perform a small fraction of claimed tests with unreliable results. Theranos secretly used conventional Siemens machines for most tests, running diluted samples that produced inaccurate results.
4. Built a culture of secrecy and intimidation — employees who raised concerns were threatened with lawsuits; departments were siloed so no one could see the full picture
5. Faked demonstrations for investors and partners — rigged demo devices to show predetermined results
6. Peak valuation reached $9 billion — making Holmes the youngest self-made female billionaire on paper""",

        "outcome": """Results — FRAUD, CRIMINAL CONVICTION, DESTROYED VALUE:

- In October 2015, Wall Street Journal investigative reporter John Carreyrou published an exposé revealing the technology didn't work
- CMS inspected Theranos's lab and found results that posed "immediate jeopardy to patient health and safety"
- Walgreens terminated the partnership and sued Theranos for $140M
- Theranos voided two years of blood test results — tens of thousands of patients received potentially inaccurate results
- The company dissolved in 2018
- Holmes convicted of four counts of wire fraud in January 2022, sentenced to 11 years in prison
- Former president Sunny Balwani convicted on 12 counts, sentenced to nearly 13 years
- $700M+ in investor capital destroyed; the fraud set back legitimate blood testing innovation by years

Key Lesson: A compelling narrative is not a substitute for a working product. The consulting frameworks (market sizing, competitive positioning, TAM analysis) all showed Theranos was addressing a massive market — and they were right about the market. They were wrong about the product. Always distinguish between "is this a good market?" and "can this company actually deliver?" Investor due diligence must include technical validation, not just market analysis.""",

        "top_recommendations": [
            "Always perform technical due diligence separately from market due diligence — a real market does not validate an unproven product",
            "Celebrity board members and charismatic founders are not substitutes for audited technology validation",
            "Any company that refuses technical due diligence is hiding something — treat refusal as disqualifying",
            "Culture of secrecy and legal intimidation of employees raising product concerns is a critical red flag",
        ],
        "bottom_line": "FRAUD CASE: Right market analysis, fraudulent product. $700M destroyed, criminal convictions. Due diligence must validate technology, not just market size.",
    },

    {
        "name": "Zara Fast Fashion Supply Chain",
        "slug": "zara-fast-fashion-supply-chain",
        "industry": "retail",
        "case_type": "growth_strategy",
        "date": "1990-01-01",
        "problem": """Traditional Fashion Retail's 6-Month Inventory Problem (1990s)

Traditional fashion retail operated on a 6-month cycle: designers created collections, manufacturers produced them, and retailers ordered inventory months before the selling season. This meant retailers were essentially guessing which styles would sell. The result: 30-40% of inventory typically sold at markdowns, and hot trends were missed because the supply chain couldn't respond quickly enough. H&M, Gap, and others were locked into this slow cycle.""",

        "decision": """Vertically Integrated Speed-as-Strategy Supply Chain

Amancio Ortega built Zara (under parent Inditex) around a radically different supply chain:
1. Design to store in 2-3 weeks — versus 6 months for competitors. ~700 designers constantly monitor runway shows, street fashion, and store-level sales data.
2. Manufactured 60%+ in Europe (Spain, Portugal, Morocco, Turkey) — deliberately paying higher labor costs for speed. Competitors shipped from China/Bangladesh (cheaper but 3-5 month lead times).
3. Small batch production — each style produced in limited quantities. If it sells, more is made. If it doesn't, it's pulled and replaced within 2 weeks. Creates artificial scarcity.
4. No advertising — Zara spends less than 0.3% of revenue on advertising vs. 3-4% for competitors. The constantly rotating inventory IS the marketing.
5. Centralized distribution — all inventory flows through a massive logistics center in Arteixo, Spain, then to stores worldwide within 48 hours. Ships 2.5 million items per week.
6. Store managers have real authority — they report daily on what's selling and what customers are asking for. This flows to the design team within hours.""",

        "outcome": """Results (1990-2023):

- Inditex revenue grew from ~€2B (1998) to €36B (2023)
- Amancio Ortega became one of the richest people in the world — net worth $90B+
- Zara produces ~65,000 new items per year vs. ~24,000 for H&M — nearly 3x the product velocity
- Inventory markdown rate: ~15% vs. 30-40% for competitors — small-batch, quickly replaced
- Zara's inventory turnover is 2-3x higher than H&M's
- The model has been copied by many but rarely matched — the vertically integrated, Europe-based supply chain is extremely expensive to replicate
- Inditex has been one of the best-performing European stocks of the 21st century
- COVID impact: stores closed but online sales surged 77% in 2020. Online now ~25% of sales.

Key Lesson: Speed is a strategy, not just a capability. Zara doesn't compete on price, brand, or quality — it competes on responsiveness. The fastest feedback loop between customer desire and product availability wins. This is the supply chain equivalent of the OODA loop in military strategy: observe, orient, decide, act — faster than your competitor.""",

        "top_recommendations": [
            "Pay premium for proximity in your supply chain when speed-to-market is the competitive advantage — nearshoring beats offshoring when responsiveness is the strategy",
            "Small batch production with rapid restocking eliminates markdown risk and creates scarcity-driven urgency",
            "Eliminate advertising budget when product freshness creates its own store traffic — Zara's 0.3% vs. industry's 3-4%",
            "Real-time sales data flowing from stores to designers is worth more than months of trend forecasting",
        ],
        "bottom_line": "Speed as strategy: 2-3 week design-to-store cycle vs. 6-month industry standard. 15% markdown rate vs. 30-40%. €36B revenue.",
    },

    {
        "name": "WeWork $47 Billion Valuation Collapse",
        "slug": "wework-valuation-collapse",
        "industry": "retail",
        "case_type": "general_strategy",
        "date": "2019-01-01",
        "problem": """WeWork Real Estate Business Disguised as Tech Company (2019)

WeWork, founded by Adam Neumann in 2010, was a co-working space company that signed long-term leases on office buildings and rented desks on flexible short-term agreements. The core business model — long-term lease obligations funded by short-term rental income — carried inherent risk but was functional. The problem was that WeWork and its investors (primarily SoftBank's Vision Fund) convinced themselves and the market that WeWork was a technology company worth a tech-company valuation, not a real estate company.""",

        "decision": """Narrative-Driven Overexpansion Without Governance — CAUTIONARY TALE

1. Raised $12.8B in total funding at a peak valuation of $47 billion (January 2019)
2. Expanded at breakneck speed — from 1 location to 800+ globally, signing long-term leases worth billions in future obligations
3. CEO Adam Neumann engaged in significant self-dealing — purchased buildings and leased them back to WeWork, trademarked "We" and charged WeWork $5.9M for the naming rights
4. Filed S-1 for IPO in August 2019 — revealed staggering losses ($1.9B in 2018 on $1.8B revenue), Neumann's self-dealing, and governance issues. Used the phrase "our mission is to elevate the world's consciousness."
5. SoftBank's Vision Fund provided a reality-distortion field enabling the overvaluation
6. Pulled the IPO in September 2019 after intense public scrutiny. Valuation slashed from $47B to ~$10B overnight.
7. Neumann forced out as CEO with a $1.7B exit package (later reduced)""",

        "outcome": """Results — COMPLETE VALUE DESTRUCTION:

- Valuation: $47B (Jan 2019) → ~$9B (Oct 2019) → public via SPAC at $9B (2021) → stock declined 98% → filed for bankruptcy November 2023
- Total investor losses: estimated $14B+ including SoftBank's ~$11.5B write-down
- SoftBank's Masayoshi Son called WeWork his "biggest mistake"
- Neumann personally received hundreds of millions despite the company's failure
- The co-working model itself wasn't wrong — IWG (Regus) operates a similar business profitably. WeWork's failure was execution and governance, not concept.
- The term "WeWork-style" entered business vocabulary as shorthand for: mundane business model disguised as a tech company to justify an inflated valuation

Key Lesson: Narrative does not equal value. WeWork's pitch disguised straightforward real estate arbitrage as "community" and "consciousness." When analyzing a company, always ask: if you stripped away the mission statement and buzzwords, what do the unit economics actually look like? WeWork's unit economics were: sign a 15-year lease, fill it with tenants on 1-year agreements, and pray there's never a recession.""",

        "top_recommendations": [
            "Always analyze unit economics beneath the narrative — what are the actual lease obligations vs. contracted revenue?",
            "A real estate company calling itself a tech company to justify tech multiples is a governance and valuation red flag",
            "Unchecked founder power (Neumann's voting shares, self-dealing) is a structural risk factor independent of business quality",
            "Long-term liability / short-term revenue mismatches are inherently fragile in recessions — WeWork's model required perpetual occupancy",
        ],
        "bottom_line": "FAILURE CASE: $47B valuation → bankruptcy. Real estate arbitrage disguised as tech. Self-dealing CEO. Governance failures destroyed $14B+.",
    },

    {
        "name": "Toyota Production System Manufacturing Revolution",
        "slug": "toyota-production-system",
        "industry": "manufacturing",
        "case_type": "growth_strategy",
        "date": "1950-01-01",
        "problem": """Toyota Post-War Manufacturing Disadvantage vs. Ford (1950)

In 1950, Toyota was a tiny, nearly bankrupt Japanese automaker producing 2,685 cars per year. Ford's Rouge River plant alone produced 7,000 cars per day. Toyota couldn't compete on scale, couldn't afford large inventories of parts, and couldn't access the capital that American automakers had. Toyota engineer Taiichi Ohno visited Ford's factories and saw massive waste: mountains of inventory, workers waiting for parts, defects caught only at the end of the line.""",

        "decision": """Toyota Production System (TPS) — 30-Year Systematic Development

Ohno spent 30 years developing what became TPS:
1. Just-in-Time manufacturing — parts arrive at the assembly line exactly when needed, not before. Eliminates inventory costs but requires extreme coordination with suppliers.
2. Jidoka (autonomation) — machines automatically stop when a defect is detected. Any worker can pull the "andon cord" to halt the entire production line if they see a problem. Revolutionary — in American factories, the line never stopped.
3. Kaizen (continuous improvement) — every employee, from line workers to executives, is expected to identify and implement small improvements constantly. Thousands of tiny optimizations that compound over decades.
4. Kanban system — visual cards that signal when more parts are needed, creating a "pull" system (make only what's demanded) rather than a "push" system
5. Respect for people — workers aren't replaceable cogs; they're the source of improvement ideas. Toyota invested heavily in training, gave line workers authority to stop production, and maintained employment stability.
6. Supplier partnerships — long-term relationships with suppliers who adopt TPS principles, rather than adversarial lowest-bidder procurement""",

        "outcome": """Results (1950-2023):

- Toyota grew from 2,685 cars/year (1950) to the world's largest automaker by volume (2008), producing 10M+ vehicles annually
- Revenue: $275B+ (2023)
- By the 1980s, Toyota cars had 60% fewer defects than GM cars
- Toyota operated with days of inventory vs. weeks or months for competitors
- The 1980s "Japanese quality revolution" was largely driven by TPS adoption across Japanese industry
- Every major manufacturer on Earth eventually adopted TPS principles (renamed "lean manufacturing" by MIT researchers in 1990)
- The principles spread far beyond manufacturing: lean startup, agile software development, lean healthcare all trace directly to TPS
- Toyota's market cap consistently exceeds the combined value of GM, Ford, and Stellantis

VULNERABILITY: The 2011 Japan earthquake and tsunami exposed the fragility of just-in-time — halted production worldwide, showing that minimal inventory means minimal buffer in catastrophic supply chain disruptions.

Key Lesson: The most powerful competitive advantage is a system, not a product. Toyota didn't win with better car designs — it won with a fundamentally better way of making cars. Systems advantages are almost impossible to copy because they're not a single decision but thousands of interconnected practices, culture, and relationships refined over decades.""",

        "top_recommendations": [
            "Build a system advantage, not just a product advantage — systems are 10x harder to copy than features",
            "Give front-line employees the authority to stop the line — they see problems executives can't and will optimize if trusted to do so",
            "Just-in-time supply chains require extreme supplier relationships — they only work with partnership-level trust, not adversarial procurement",
            "Kaizen (continuous improvement culture) compounds over decades — hundreds of tiny improvements create an insurmountable cumulative advantage",
        ],
        "bottom_line": "System advantage beats product advantage. Just-in-time + continuous improvement + worker authority created 60% fewer defects than competitors.",
    },

    {
        "name": "Adobe Perpetual License to Subscription Transformation",
        "slug": "adobe-subscription-transformation",
        "industry": "technology",
        "case_type": "digital_transformation",
        "date": "2012-01-01",
        "problem": """Adobe Creative Suite Revenue Plateau and Piracy Problem (2012)

In 2012, Adobe was a mature software company selling Creative Suite as boxed software for $1,299-$2,599 per license. The business model had several problems: revenue was "lumpy" (big spikes at launch, then decline), piracy was rampant (an estimated 60%+ of Photoshop installs were pirated), upgrade cycles were lengthening, and the high price locked out students, freelancers, and emerging markets. Revenue had plateaued around $4B. Wall Street was skeptical of growth.""",

        "decision": """Full Commitment to Subscription — No Hybrid, No Retreat

CEO Shantanu Narayen executed one of the most decisive pivots in software history:
1. Killed the perpetual license entirely — stopped selling Creative Suite as boxed software. Cold turkey. No more $2,599 one-time purchases.
2. Launched Creative Cloud (2013) — all Adobe apps for $49.99/month (full suite) or $9.99/month (single app). A 75-95% price reduction for new customers.
3. Made the transition mandatory — after Creative Suite 6, there would be no more standalone versions. If you wanted Photoshop, you subscribed. Period.
4. Accepted a short-term revenue decline — converting $2,599 one-time purchases to $50/month means 4+ years to recoup the same revenue per customer. Wall Street punished the stock initially.
5. Used subscription model to dramatically increase update frequency — instead of one major release every 18-24 months, shipped continuous updates
6. Expanded addressable market — the $10/month Photoshop plan converted millions of pirates into paying customers
7. Added new products to the bundle — Adobe XD, Adobe Spark, Lightroom CC — increasing subscription value without proportional price increases""",

        "outcome": """Results (2012-2023):

- Revenue: $4.4B (2012) → $19.4B (2023) — 4.4x growth in 11 years
- Recurring revenue: ~15% of total (2012) → 93% of total (2023)
- ARR from Creative Cloud alone: $12B+
- Subscribers: 0 (2012) → 30M+ Creative Cloud subscribers by 2023
- Stock: $33 (2012) → $570+ (2023) — a 17x return
- Piracy dropped dramatically — at $10/month, the hassle of pirating Photoshop exceeds the cost of paying for it
- Gross margins expanded from ~85% to ~88% — subscription model even more profitable at scale
- Adobe became the poster child for "subscription transformation" — Microsoft, Autodesk, and every enterprise software company followed the same playbook
- The initial backlash was fierce — petitions with tens of thousands of signatures. Adobe held firm, and the backlash faded.

Key Lesson: Subscription transitions work if you commit fully and survive the valley. Adobe's revenue dipped for 2-3 quarters during the transition — this is where most companies lose nerve and offer a "hybrid" option that undermines the migration. Killing the cash cow entirely (no perpetual licenses, period) was what made it work. Half-measures result in the worst of both worlds. Also: dramatically lowering price can grow total revenue if the addressable market expands enough.""",

        "top_recommendations": [
            "Execute subscription transitions completely — hybrid models (perpetual + subscription) undermine the migration and produce the worst of both worlds",
            "Accept the revenue valley: 2-3 quarters of decline during subscription transition is the price of a 10x revenue business",
            "Dramatically lower price can increase total revenue if it converts a large piracy or non-consumption market into paying customers",
            "Continuous product updates (enabled by subscription) are a retention mechanism — customers on subscription receive constant value vs. waiting years for a new version",
        ],
        "bottom_line": "Full commitment to subscription (no hybrid) drove 4.4x revenue growth and 17x stock return. The transition valley was 2-3 quarters; the payoff was a decade.",
    },
]


CROSS_CASE_PATTERNS_3 = """CROSS-CASE PATTERNS — Cases 21-30

1. CONSTRAINT-DRIVEN INNOVATION IS THE MOST DURABLE KIND: IKEA's entire model came from a supplier boycott. Toyota's system came from having no capital for inventory. Airbnb's best product decisions came from a 72% revenue collapse. The best strategies often emerge from the worst circumstances.

2. PLATFORM/ECOSYSTEM DYNAMICS CREATE WINNER-TAKE-MOST OUTCOMES: Spotify vs. other streaming (network effects in playlists and discovery), Nokia's Symbian vs. iOS/Android (app ecosystems), Blockbuster vs. Netflix (content library). Once a platform reaches critical mass, catching up is nearly impossible.

3. THE DIFFERENCE BETWEEN A GOOD MARKET AND A GOOD COMPANY: Theranos addressed a real, massive market (blood testing). WeWork addressed a real need (flexible office space). Both were right about the market and catastrophically wrong about their ability to serve it. Never confuse market analysis with company analysis.

4. FULL COMMITMENT BEATS HEDGING: Adobe killed perpetual licenses entirely. Airbnb pivoted to rural/long-term stays completely. Nokia's fatal error was hedging between Symbian, MeeGo, and Windows Phone. When the right strategy is identified, partial execution is worse than no execution.

5. SPEED AS STRATEGY: Zara (2-week design cycle), Airbnb (redesigned homepage in weeks during COVID), Adobe (continuous updates vs. 18-month cycles). The company with the fastest feedback loop usually wins, not the company with the best plan.

6. CORPORATE GOVERNANCE MATTERS AS MUCH AS STRATEGY: Blockbuster's Antioco had the right strategy — the board killed it. WeWork's Neumann had unchecked power — no one stopped the excess. Nokia hired an outsider CEO who made a $7.2B mistake. The quality of the decision-making structure is as important as the quality of the decisions.

7. SYSTEMS ADVANTAGES VS. PRODUCT ADVANTAGES: Toyota's TPS, IKEA's flat-pack logistics, and Zara's supply chain are all system advantages that took decades to build and are nearly impossible to copy. Product features can be replicated in months; operating systems take decades.

8. SUBSCRIPTION AND FREEMIUM TRANSITIONS: Adobe (full subscription commitment), Spotify (freemium to premium funnel). Both required accepting short-term revenue pain for long-term recurring revenue. The companies that hedged (offering both perpetual and subscription) failed; the ones who committed fully succeeded.

Cases covered: Spotify (2008-2024), Blockbuster (2000-2010 — FAILURE), Airbnb COVID pivot (2020-2022), Nokia collapse (2007-2014 — FAILURE), IKEA supply chain revolution (1956-present), Theranos fraud (2003-2018 — FRAUD/FAILURE), Zara fast fashion (1990-2023), WeWork valuation collapse (2019-2023 — FAILURE), Toyota Production System (1950-present), Adobe subscription transformation (2012-2023)."""


def _id(case_slug, chunk_type, idx=0):
    raw = f"{case_slug}_{chunk_type}_{idx}"
    return hashlib.md5(raw.encode()).hexdigest()


def _write_files(case: dict) -> Path:
    case_dir = Path("cases/past") / case["slug"]
    materials_dir = case_dir / "materials"
    materials_dir.mkdir(parents=True, exist_ok=True)

    brief = f"""# Case Brief: {case['name']}

**Industry:** {case['industry']}
**Case Type:** {case['case_type'].replace('_', ' ').title()}
**Date:** {case['date']}

## The Problem

{case['problem']}

## The Decision

{case['decision']}
"""
    (materials_dir / "case_brief.md").write_text(brief, encoding="utf-8")
    (case_dir / "outcome.md").write_text(f"# Outcome — {case['name']}\n\n{case['outcome']}\n", encoding="utf-8")

    metadata = {
        "case_name": case["name"],
        "date_analyzed": case["date"],
        "n_agents": 0,
        "n_rounds": 0,
        "total_tokens": 0,
        "total_cost_usd": 0,
        "top_recommendations": case["top_recommendations"],
        "bottom_line": case["bottom_line"],
        "industry": case["industry"],
        "case_type": case["case_type"],
        "source": "real_world_case_study",
    }
    (case_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return case_dir


def _build_chunks(case: dict) -> list:
    slug = case["slug"]
    base_meta = {
        "case_name": case["name"],
        "industry": case["industry"],
        "case_type": case["case_type"],
        "date": case["date"],
        "source": "real_world_case_study",
    }
    chunks = []

    chunks.append({"id": _id(slug, "problem_statement"), "text": f"PROBLEM STATEMENT ({case['name']}):\n{case['problem']}", "metadata": {**base_meta, "chunk_type": "problem_statement"}})
    chunks.append({"id": _id(slug, "decision"), "text": f"STRATEGY AND DECISION ({case['name']}):\n{case['decision']}", "metadata": {**base_meta, "chunk_type": "finding"}})
    chunks.append({"id": _id(slug, "outcome"), "text": f"OUTCOME ({case['name']}):\n{case['outcome']}", "metadata": {**base_meta, "chunk_type": "outcome"}})
    chunks.append({"id": _id(slug, "exec_summary"), "text": f"EXECUTIVE SUMMARY ({case['name']}):\n{case['bottom_line']}", "metadata": {**base_meta, "chunk_type": "exec_summary"}})

    for i, rec_title in enumerate(case["top_recommendations"]):
        chunks.append({"id": _id(slug, "recommendation", i), "text": f"RECOMMENDATION ({case['name']}): {rec_title}", "metadata": {**base_meta, "chunk_type": "recommendation", "recommendation_title": rec_title}})

    return chunks


def main():
    console.print("\n[bold cyan]Seeding knowledge base with 10 more real-world business cases (21-30)...[/bold cyan]\n")

    from knowledge.vectorstore import store_chunks

    all_chunks = []
    total_files = 0

    for case in CASES:
        case_dir = _write_files(case)
        total_files += 1
        console.print(f"  [green]Created[/green] {case_dir}")
        all_chunks.extend(_build_chunks(case))

    all_chunks.append({
        "id": hashlib.md5("cross_case_patterns_batch3_0".encode()).hexdigest(),
        "text": CROSS_CASE_PATTERNS_3,
        "metadata": {"case_name": "Cross-Case Patterns (Cases 21-30)", "chunk_type": "finding", "industry": "general", "case_type": "general_strategy", "source": "real_world_case_study"},
    })

    console.print(f"\n[bold cyan]Embedding {len(all_chunks)} chunks into ChromaDB...[/bold cyan]")
    try:
        store_chunks(all_chunks)
        console.print(f"\n[bold green]Done! {total_files} cases created, {len(all_chunks)} chunks embedded.[/bold green]")
        console.print("[dim]Run: python main.py cases  — to verify[/dim]\n")
    except Exception as e:
        console.print(f"\n[red]Embedding failed: {e}[/red]")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

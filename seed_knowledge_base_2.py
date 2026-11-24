"""
Seed the knowledge base with 10 more real-world business cases (Cases 11-20).
Creates cases/past/ directories and embeds all chunks into ChromaDB.

Run: python seed_knowledge_base_2.py
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
        "name": "Chipotle Food Safety Crisis and Digital Turnaround",
        "slug": "chipotle-food-safety-turnaround",
        "industry": "retail",
        "case_type": "turnaround",
        "date": "2015-12-01",
        "problem": """Chipotle E. Coli Crisis (2015-2016)

Between July and December 2015, Chipotle experienced five separate foodborne illness outbreaks — E. coli across 11 states (55+ sick), norovirus (234 sick at one location), and salmonella (64 sick). For a brand built entirely on "Food with Integrity" and fresh, high-quality ingredients, this was existential. Same-store sales dropped 29% in Q1 2016. Stock cratered from $758 to below $400. Net income collapsed from $475M (2015) to $22.9M (2016). The company's initial response made things worse — the CFO blamed the CDC and media, and founder Chip Wilson offered no public apology for weeks.""",

        "decision": """Two-Phase Recovery Strategy

Phase 1 — Crisis Response (2016-2017):
1. Closed all 2,000+ restaurants on February 8, 2016 for a company-wide food safety meeting — unprecedented in the industry
2. Hired a new head of food safety and implemented protocols claimed to be "10-15 years ahead of industry standard"
3. Mandated employees wash hands every 30 minutes, blanch produce in hot water, DNA-test ingredients before shipping
4. Offered paid sick leave to discourage sick employees from working
5. Flooded the market with free burrito coupons worth $62M+ to drive customers back
6. Heavy national TV advertising for the first time in 5 years

Phase 2 — Reinvention under Brian Niccol (2018-2021):
7. Hired Brian Niccol (from Taco Bell) as CEO in March 2018 after both co-CEOs departed
8. Built digital ordering infrastructure — app, delivery partnerships with DoorDash, "Chipotlanes" (drive-through for digital orders only)
9. Launched culturally relevant marketing: "For Real" campaign, TikTok challenges, influencer partnerships
10. Added new menu items (queso, carne asada, cauliflower rice) for the first time in years
11. Raised wages to $15/hour average in 2021 — positioned as employer of choice in fast food""",

        "outcome": """Results (2016-2021):

- Recovery took 4 full years — didn't regain pre-crisis stock price until mid-2019
- Under Niccol, stock went from ~$300 (2018) to $1,900+ (2021) — a 6x return
- Digital sales went from near-zero to 50%+ of revenue
- Revenue grew from $4.5B (2016) to $7.5B (2021)
- Chipotlanes became the default new restaurant format — digital-first design
- The crisis permanently changed the brand's operational DNA — food safety became a genuine core competency
- Niccol was later poached by Starbucks in 2024 as their CEO — a testament to the turnaround's reputation

Key Lesson: A food safety crisis doesn't kill a restaurant brand — a poor response does. Chipotle's initial deflection and blame-shifting extended the damage by years. The real turnaround came with new leadership, genuine operational changes, and a forward-looking digital strategy rather than backward-looking apologies.""",

        "top_recommendations": [
            "Replace leadership whose credibility is tied to the crisis — new CEO signals clean break",
            "Close operations for symbolic retraining — the cost is less than the trust it rebuilds",
            "Build digital ordering as a permanent operational advantage, not a crisis response",
            "Turn the crisis into a capability — Chipotle's food safety became genuinely industry-leading post-outbreak",
        ],
        "bottom_line": "New leadership plus genuine operational investment — not apologies alone — drove the 6x recovery.",
    },

    {
        "name": "Lululemon Sheer Pants to Men's Expansion",
        "slug": "lululemon-brand-expansion",
        "industry": "retail",
        "case_type": "growth_strategy",
        "date": "2013-03-01",
        "problem": """Lululemon Product Recall and Founder Crisis (2013)

In March 2013, Lululemon pulled 17% of its black yoga pants from stores because they were too sheer. The recall cost $67M in lost sales. Then founder Chip Wilson made it catastrophically worse on Bloomberg TV, saying "quite frankly, some women's bodies just actually don't work" for the pants — blaming customers for the defective product. Stock dropped 17.5%. CEO Christine Day resigned. Wilson stepped down as chairman. Sales growth decelerated from 30%+ to low teens. The brand's core demographic — affluent women — felt personally insulted.""",

        "decision": """"Power of Three x2" Growth Strategy (2018)

After Wilson fully departed (2015) and a period of stabilization:
1. Calvin McDonald hired as CEO in 2018 — launched "Power of Three x2": double men's revenue, double digital revenue, double international revenue within 5 years
2. Massive investment in men's line — previously an afterthought, repositioned as core growth pillar with dedicated marketing, product development, and retail space
3. Expanded beyond yoga into running, training, hiking, and casual wear — "from the studio to the street"
4. Built out digital commerce and the MIRROR acquisition ($500M, 2020) for connected fitness
5. Aggressive international expansion, especially China
6. Maintained premium pricing ($98-128 leggings) while competitors undercut on price""",

        "outcome": """Results (2018-2023) — and the MIRROR Failure:

- Revenue exploded from $2.6B (2018) to $9.6B (2023) — 24% annual growth rate
- Men's business grew from ~$800M to $2.5B+ — exceeded the "double" target
- Digital revenue went from 26% to 44% of total
- International revenue tripled
- McDonald achieved the "Power of Three x2" goal in 3 years instead of 5
- Stock went from ~$130 (2018) to $490+ (2023)
- Lululemon became the third-largest athletic apparel brand globally, behind only Nike and Adidas

MIRROR FAILURE: The $500M acquisition of connected fitness company MIRROR was a complete failure — wrote down $443M in 2023 and discontinued the product.

By 2025, the brand faced new challenges: growth slowed, stock dropped 50%, and ironically, another sheer pants controversy emerged.

Key Lesson: A brand crisis can become a strategic reset if leadership changes are real, not cosmetic. Lululemon's turnaround was about building an entirely new growth engine that made the company less dependent on the original market. But the MIRROR disaster shows that even successful turnaround CEOs can make expensive mistakes chasing trends.""",

        "top_recommendations": [
            "Use a crisis as a forcing function to pursue growth vectors the brand had deprioritized (men's, international)",
            "Set audacious multi-year goals with clear metrics — 'double three things in five years' creates alignment",
            "Maintain premium pricing discipline even under competitive pressure",
            "Be cautious with trend-driven acquisitions (connected fitness) — they often fail to integrate with core business",
        ],
        "bottom_line": "Crisis forced a strategic reset that unlocked 4x revenue growth by building new categories alongside the core.",
    },

    {
        "name": "LEGO Ideas Crowdsourced Product Development",
        "slug": "lego-ideas-crowdsourcing",
        "industry": "manufacturing",
        "case_type": "growth_strategy",
        "date": "2008-01-01",
        "problem": """LEGO Product Development Cost and Relevance Problem (2008)

Even after LEGO's 2004 turnaround, the company faced an ongoing challenge: how to consistently develop sets that consumers actually want to buy. Traditional corporate product development was expensive, slow, and often disconnected from what fans cared about. LEGO designers, working internally, sometimes produced sets that underperformed commercially. Meanwhile, the company's most passionate adult fans (AFOLs — Adult Fans of LEGO) were designing incredibly creative custom builds and sharing them online — for free.""",

        "decision": """LEGO Ideas Crowdsourcing Platform

1. Launched LEGO Ideas (originally LEGO Cuusoo in 2008, rebranded 2014) — a platform where anyone can submit a set design
2. If a design gets 10,000 community votes, LEGO's internal review board evaluates it for production feasibility, licensing requirements, and commercial viability
3. If approved, LEGO produces and sells the set. The original designer gets 1% of global net sales — typically $10K-50K+ for successful sets
4. LEGO maintains full creative control of the final product — the community submission is a concept, not a finished design
5. The platform serves as market research — LEGO can see which concepts generate enthusiasm before committing any R&D budget""",

        "outcome": """Results (2008-present):

- Over 40 Ideas sets produced since launch, including massive commercial hits
- The NASA Saturn V rocket (fan-designed) became one of LEGO's all-time best sellers at $119.99
- The Ship in a Bottle, Treehouse, and Friends Central Perk sets all originated from Ideas
- Over 1.8 million registered members submitting designs
- LEGO gets free product development — fans do the creative work, LEGO only invests in sets with proven demand (10,000+ votes)
- The 1% royalty model is far cheaper than internal design costs while keeping fans deeply engaged
- Ideas sets have higher average margin than standard sets because demand is pre-validated
- The platform creates emotional investment — fans feel ownership of the brand, making them evangelists
- Other companies have copied the model (Starbucks, Dell) but none as successfully

Key Lesson: Your most passionate customers are also your best product developers. Crowdsourcing doesn't replace internal R&D — it de-risks it. By letting the community vote before you invest in production, you're running free market research at scale.""",

        "top_recommendations": [
            "Create a community submission platform that turns superfans into unpaid product developers",
            "Use community voting as pre-production demand validation — only build what's already proven popular",
            "Pay creators a small royalty (1%) — it's far cheaper than internal R&D and generates evangelists",
            "Maintain editorial control over the final product — community provides the concept, company controls execution",
        ],
        "bottom_line": "Crowdsourced product development from superfans delivers higher-margin, pre-validated products at lower R&D cost.",
    },

    {
        "name": "JCPenney Ron Johnson Transformation Failure",
        "slug": "jcpenney-ron-johnson-failure",
        "industry": "retail",
        "case_type": "organizational_change",
        "date": "2011-11-01",
        "problem": """JCPenney Mid-Market Department Store Stagnation (2011)

JCPenney was a struggling but stable mid-market department store with $17.3B in revenue in 2011. Same-store sales were flat but the company was profitable. The board, wanting transformation, hired Ron Johnson — the mastermind behind Apple Retail Stores — as CEO in November 2011. Johnson arrived with a vision to transform JCPenney from a coupon-driven discount retailer into a hip, Apple-like shopping experience. This is a cautionary case of a "brilliant" strategy that destroyed a company.""",

        "decision": """Sweeping Transformation Without Testing — CAUTIONARY TALE

Johnson implemented sweeping changes, almost all at once:
1. Eliminated all coupons, sales, and promotions — replaced with "everyday low pricing." No more weekly sales, no clearance, no coupons.
2. Redesigned stores into "store-within-a-store" boutiques (Martha Stewart, Joe Fresh, Levi's) — reminiscent of Apple's Genius Bar layout
3. Killed JCPenney's private label brands that loyal customers knew, replaced with trendy brands
4. Launched new logo, marketing, and brand identity — targeting younger consumers rather than JCPenney's existing middle-aged, middle-income core customer
5. Refused to test any changes — when asked about focus groups, Johnson reportedly said "We didn't test at Apple." Rolled out nationwide immediately.
6. Alienated existing customers while failing to attract new ones — young consumers didn't see JCPenney as a destination regardless of redesign

NOTE: Every one of these decisions was a strategic error.""",

        "outcome": """Results — CATASTROPHIC FAILURE:

- Revenue collapsed from $17.3B (2011) to $13.0B (2012) — a 25% decline in one year
- Same-store sales dropped 25% — worst performance by a major US retailer in modern history
- The company lost $985M in 2012 (vs. $152M profit in 2011)
- Stock dropped from $43 to $15
- JCPenney's core customers (coupon-loving, deal-seeking middle-income women) abandoned the brand en masse
- Johnson was fired after just 17 months, in April 2013
- Previous CEO Myron Ullman was brought back to restore coupons and sales — but damage was permanent
- JCPenney never recovered to pre-Johnson revenue levels
- Company filed for bankruptcy in May 2020

Key Lesson: What works at Apple doesn't work at JCPenney. Johnson's fatal error was contempt for his existing customer. He tried to replace them with a customer who didn't exist. Never roll out radical changes without testing. Also: Apple Stores worked because Apple had products people were desperate to buy. JCPenney was selling Dockers and bedsheets.""",

        "top_recommendations": [
            "Always test radical changes before nationwide rollout — never deploy untested transformation at scale",
            "Understand your existing customer before trying to replace them — JCPenney's coupon users were the business",
            "Distinguish between strategy that works for one context (Apple) versus another (mid-market retail)",
            "A new CEO's background is not a strategy — Johnson's Apple success did not transfer to JCPenney's context",
        ],
        "bottom_line": "FAILURE CASE: Nationwide rollout of untested strategy destroyed the existing customer base without creating a new one.",
    },

    {
        "name": "Slack from Failed Video Game to $27.7B Acquisition",
        "slug": "slack-pivot-to-enterprise",
        "industry": "technology",
        "case_type": "digital_transformation",
        "date": "2012-11-01",
        "problem": """Tiny Speck / Glitch Game Failure and Pivot (2012)

In 2012, a Vancouver-based company called Tiny Speck was running out of money. Their product, a massively multiplayer online game called Glitch, had failed to attract a sustainable player base despite $17M in venture funding. The game shut down in November 2012, and the team of ~45 people faced layoffs and dissolution. But during Glitch's development, the team had built an internal communication tool to coordinate their distributed workforce — a searchable, channel-based messaging system that replaced email for day-to-day work.""",

        "decision": """Pivot from Gaming to Enterprise Communication

CEO Stewart Butterfield (who had previously co-founded Flickr after a similar pivot from a failed game):
1. Pivoted entirely from gaming to enterprise communication software
2. Named the product Slack (Searchable Log of All Communication and Knowledge)
3. Launched a private beta in August 2013 — invited specific companies and communities to try it
4. Grew through word-of-mouth within teams — viral spread within organizations. No sales team needed initially.
5. Priced on freemium model — free for small teams, paid plans for advanced features, search history, compliance
6. Built extensive integration ecosystem — connected to every other business tool (GitHub, Google Drive, Trello, Salesforce)
7. Raised $340M in VC by 2018 to fuel growth before profitability
8. Chose a direct listing on NYSE in June 2019 rather than a traditional IPO""",

        "outcome": """Results (2013-2021):

- 8,000 companies signed up in the first 24 hours of the beta launch
- Within 2 weeks: 15,000 users. Within 6 months: 500,000 daily active users
- Slack became the fastest enterprise software company to reach $100M in annual recurring revenue — in under 2 years
- By 2020: 12.5 million daily active users, 750,000+ organizations, $900M+ in annual revenue
- Changed how millions of people work — "Slack" became a verb ("just Slack me")
- In December 2020, Salesforce announced acquisition of Slack for $27.7 billion
- Butterfield went from shutting down a failed game to a $27.7B exit in 8 years
- The failed game Glitch was eventually open-sourced — nobody cared

Key Lesson: The most valuable product might be the one you built for yourself. Slack wasn't designed to be a product — it was an internal tool solving a real problem the team had. When your team builds something they can't live without, that's the strongest possible product-market fit signal. Pivot fast and completely — Butterfield didn't try to save Glitch and do Slack on the side.""",

        "top_recommendations": [
            "When a pivot is necessary, pivot completely — don't run the old business and new business simultaneously",
            "Internal tools solving genuine pain points are the strongest product-market fit signal",
            "Use viral bottom-up adoption (individual users pulling in their teams) rather than top-down enterprise sales",
            "Build an integration ecosystem early — connecting to existing tools reduces switching friction",
        ],
        "bottom_line": "Complete pivot from failed gaming to internal tool-turned-product achieved $27.7B exit in 8 years.",
    },

    {
        "name": "BlackBerry Disruption Denial",
        "slug": "blackberry-disruption-denial",
        "industry": "technology",
        "case_type": "turnaround",
        "date": "2007-01-01",
        "problem": """BlackBerry iPhone Threat Denial (2007)

In 2007, BlackBerry (then Research in Motion) was the dominant smartphone company with 50% US market share, $6B in annual revenue, and synonymous with professional communication. When Steve Jobs unveiled the iPhone in January 2007, BlackBerry's co-CEO Mike Lazaridis reportedly watched the demo and said "it's OK, we'll be fine." Internally, BlackBerry engineers dismissed the iPhone because it had no physical keyboard, poor battery life, and couldn't do email as well as BlackBerry. They were right about all three points — in 2007. This is a cautionary case of incumbents rationalizing disruption away.""",

        "decision": """Incremental Response While the Market Moved — CAUTIONARY TALE

1. Dismissed the iPhone threat for 2+ years — continued investing in physical keyboard devices
2. Launched BlackBerry Storm (2008) — a hastily developed touchscreen phone widely panned as buggy. Had a "clickable" screen that was neither fish nor fowl.
3. Doubled down on enterprise — believed corporate IT departments would keep choosing BlackBerry for security and email. Ignored the consumerization of IT.
4. Refused to open an app ecosystem — the iPhone App Store (2008) transformed phones into platforms. BlackBerry was slow to create a comparable marketplace.
5. Launched BlackBerry 10 OS (2013) — a completely new operating system, years too late. iOS and Android had already locked up the developer ecosystem.
6. Explored a sale in 2013 but no buyer materialized at an acceptable price""",

        "outcome": """Results — CATASTROPHIC DECLINE:

- Market share: 50% (2007) to 0.3% (2016)
- Revenue: $19.9B peak (2011) to $3.4B (2014) to under $1B by 2016
- Stock: $140+ (2008) to under $8 (2013)
- Lost 5,000+ employees through layoffs between 2011-2015
- The company eventually exited smartphone hardware entirely in 2016
- Pivoted to enterprise software and cybersecurity — a much smaller but sustainable business
- BlackBerry's patents remain valuable — generates hundreds of millions in licensing revenue
- The BlackBerry brand was licensed to other manufacturers for low-end Android phones — a shadow of its former self

Key Lesson: Incumbents die not because they can't see the threat, but because they rationalize why the threat doesn't apply to them. BlackBerry's engineers were technically correct that the iPhone was worse at email — but they completely missed that "smartphone" was being redefined. When your competitor redefines the category, your existing advantages become irrelevant.""",

        "top_recommendations": [
            "When a competitor redefines the category, your technical superiority in the old category is irrelevant",
            "Build an app ecosystem — platforms beat products in any market with network effects",
            "Consumer adoption precedes enterprise adoption — ignoring consumer market is not 'enterprise focus', it's blindness",
            "An honest strategic assessment must ask 'what if we're wrong?' — BlackBerry never seriously modeled the downside",
        ],
        "bottom_line": "FAILURE CASE: Technical superiority in the old category (email) was irrelevant when the category was redefined (pocket computer).",
    },

    {
        "name": "Patagonia Anti-Growth Purpose-Driven Brand",
        "slug": "patagonia-purpose-driven-brand",
        "industry": "retail",
        "case_type": "growth_strategy",
        "date": "2011-11-01",
        "problem": """Patagonia Philosophical Mission-Commerce Tension (2011)

Patagonia was profitable and growing, but founder Yvon Chouinard was increasingly troubled by the environmental impact of consumption — including consumption of Patagonia products. The outdoor apparel industry produces enormous waste: the average American throws away 81 pounds of clothing per year. Patagonia's core customer cared about environmentalism but was still buying new jackets every season. Chouinard wanted to align the company's business model with its environmental mission — even if that meant telling customers to buy less.""",

        "decision": """Radical Purpose-Driven Business Model

1. Ran a full-page Black Friday ad in the New York Times (2011) with the headline "Don't Buy This Jacket" — urged consumers to think before purchasing and to repair, reuse, and recycle clothing
2. Launched Worn Wear — program to repair, trade in, and resell used Patagonia clothing. The company fixes any Patagonia garment for free or low cost, regardless of age.
3. Offered a lifetime guarantee on all products — if it breaks, Patagonia repairs or replaces it
4. Made Worn Wear a standalone e-commerce platform selling refurbished Patagonia gear at 30-50% off
5. Invested 1% of all sales (not profits — sales) to environmental causes through "1% for the Planet"
6. Switched to recycled and organic materials across the product line — by 2025, 98% of fabrics were recycled
7. In September 2022, Chouinard transferred ownership to a trust and nonprofit, ensuring all profits (~$100M/year) go to fighting climate change. "Earth is now our only shareholder." """,

        "outcome": """Results (2011-2022):

- The "Don't Buy This Jacket" ad increased sales by 30% in the following year — the opposite of the intended effect
- Revenue grew from $400M (2011) to $1.5B+ (2022) — nearly 4x growth while telling people to buy less
- Worn Wear became a significant business line — creates customer loyalty, reduces returns, attracts environmentally conscious consumers
- The company's environmental stance became its primary competitive moat — customers pay premium prices ($200+ jackets) partly because of brand values
- The 2022 ownership transfer was global front-page news, generating billions in earned media
- Patagonia proved that "purpose-driven" business isn't just CSR window dressing — it can be the actual strategy
- Critics note the paradox: telling people not to buy drove more buying. The anti-consumption message became a consumption signal.

Key Lesson: Authenticity is the ultimate brand strategy — but only if it's real. Patagonia's environmental commitment isn't marketing; it's the actual operating model (recycled materials, free repairs, 1% of sales donated, and ultimately giving the entire company away). People trust brands that don't seem desperate for their money.""",

        "top_recommendations": [
            "Build a resale/repair program — Worn Wear creates loyalty, revenue, and competitive differentiation simultaneously",
            "Environmental and social commitments must be operational (recycled materials, free repairs), not just marketing",
            "Anti-marketing can outperform traditional marketing when the audience is skeptical of corporate messaging",
            "Premium pricing is sustainable when justified by authentic values, not just product quality",
        ],
        "bottom_line": "Authentic purpose-driven model — including giving the company away — drove 4x revenue growth while telling people to buy less.",
    },

    {
        "name": "Zoom Pandemic Growth and Post-Pandemic Correction",
        "slug": "zoom-pandemic-growth",
        "industry": "technology",
        "case_type": "growth_strategy",
        "date": "2019-12-01",
        "problem": """Zoom Pre-Pandemic Niche Position (2019)

In late 2019, Zoom was a moderately successful but niche B2B video conferencing tool with 10 million daily meeting participants, $623M in annual revenue, and brand recognition mainly among tech companies and remote workers. The market was dominated by Cisco WebEx, Microsoft Teams (bundled with Office 365), and Google Meet. Then COVID-19 hit in March 2020, and billions of people suddenly needed video calling for work, school, healthcare, family gatherings, and everything else.""",

        "decision": """Pandemic Scaling Strategy (2020)

CEO Eric Yuan made critical calls in a compressed timeframe:
1. Removed the 40-minute limit on free accounts for K-12 schools worldwide — making Zoom the default education platform overnight
2. Scaled infrastructure from 10M to 300M daily participants in 3 months — a 30x increase requiring emergency cloud infrastructure deals with Oracle and AWS
3. Addressed the "Zoombombing" security crisis head-on — added default passwords, waiting rooms, and end-to-end encryption within weeks. Hired a CISO and security advisory board.
4. Launched Zoom Phone, Zoom Rooms, Zoom Events — expanded from video meetings into a full unified communications platform
5. Kept the product dead simple — resisted the urge to add complexity. "Join meeting" with one click remained the core experience.
6. Attempted a $14.7B acquisition of Five9 (cloud contact center) in 2021 — fell apart due to regulatory and shareholder opposition""",

        "outcome": """Results — Explosive Growth and Brutal Correction:

- Daily meeting participants: 10M (Dec 2019) to 300M (April 2020) — 30x in 4 months
- Revenue: $623M (FY2020) to $2.65B (FY2021) to $4.1B (FY2022) — 6.5x in 2 years
- Stock: $68 (Jan 2020) to $568 (Oct 2020) — an 8x return in 10 months
- "Zoom" became a generic verb for video calling, like "Google" for search
- Free school program onboarded 125,000+ schools in 25 countries

THE CORRECTION WAS BRUTAL:
- Stock crashed from $568 (Oct 2020) to $70 (Nov 2022) — an 88% decline as pandemic demand normalized
- Growth rate slowed dramatically as offices reopened and Microsoft Teams (bundled free with Office 365) captured enterprise share
- The Five9 acquisition failure left Zoom without a clear diversification path
- By 2023, Zoom settled into a stable ~$4.5B revenue business and pivoted messaging to "AI-first"

Key Lesson: Being in the right place at the right time is only the beginning — you still have to execute. Zoom's 30x scaling without catastrophic failure is one of the great engineering achievements in tech history. But the case shows the danger of pandemic-driven demand: a company built on a once-in-a-century tailwind needs a plan for when that tailwind disappears.""",

        "top_recommendations": [
            "When a market inflection point arrives, scale infrastructure before you lose the window — Zoom's 30x scaling was non-negotiable",
            "Free tiers for high-impact users (K-12 schools) drive mass adoption and goodwill that outlasts the promotion",
            "Address security crises immediately and publicly — Zoombombing was fixed in weeks, not months",
            "Pandemic-driven growth requires a post-pandemic strategy — plan for the tailwind ending before it does",
        ],
        "bottom_line": "30x scaling during pandemic created a generic verb and lasting platform, but demand normalization required a new growth thesis.",
    },

    {
        "name": "Kodak Digital Photography Invention and Self-Destruction",
        "slug": "kodak-disruption-failure",
        "industry": "manufacturing",
        "case_type": "digital_transformation",
        "date": "1975-01-01",
        "problem": """Kodak Film Business vs. Digital Photography Threat (1975-2000s)

Kodak is the canonical case of disruption denial. In 1975, Kodak engineer Steve Sasson invented the first digital camera. He presented it to executives, who told him the invention was "cute" but to keep it quiet — because digital photography would destroy Kodak's enormously profitable film business. Kodak's film and printing division had 80%+ gross margins. The entire company was built on the "razor and blades" model: sell cameras cheap, make money on film and development. Digital eliminated the recurring revenue. For decades, Kodak sat on digital technology patents while competitors built the digital photography market.""",

        "decision": """Protecting Film Business Over Digital Future — CAUTIONARY TALE

1. Suppressed digital photography internally through the 1980s and 1990s — protecting the film business
2. Eventually launched digital cameras in the late 1990s, but positioned them as a complement to film, not a replacement
3. Invested in a "hybrid" strategy — digital cameras that produced prints (Kodak EasyShare) — trying to preserve the printing revenue model
4. Attempted to pivot to digital printing — commercial and consumer printing solutions
5. Sold off non-core assets in the 2000s — health imaging, camera sensor business
6. Filed 1,100+ digital photography patents — some of the most foundational IP in the industry — but relied on patent licensing revenue rather than building digital products
7. Filed for Chapter 11 bankruptcy in January 2012""",

        "outcome": """Results — CATASTROPHIC DECLINE:

- Revenue: $16B peak (1996) to $6.2B (2008) to $2.2B (2011)
- Employees: 145,000 (peak, 1988) to 17,000 (2012)
- Stock: $94 (1997) to $0.36 (2012)
- Filed for bankruptcy January 2012, emerged September 2013 as a much smaller commercial printing company
- Lost $14B in market value over 15 years
- Kodak's patents were sold for $525M in 2013 — a fraction of their potential value if commercialized internally
- Meanwhile, Instagram (founded 2010) sold for $1B in 2012 — a company built entirely on digital photography, Kodak's own invention
- Kodak exists today as a small commercial printing and chemicals company — unrecognizable from its former self

Key Lesson: Inventing the future doesn't save you if you refuse to use it. Kodak had every advantage — the technology, the patents, the brand, the distribution — and still lost because the film business was too profitable to cannibalize. The Kodak story is the inverse of Netflix: same diagnosis (our core business is going to be disrupted by digital), opposite decisions (protect vs. cannibalize), opposite outcomes.""",

        "top_recommendations": [
            "When you invent a disruptive technology, use it yourself — don't suppress it to protect an existing revenue model",
            "Patents without products are not a strategy — Kodak's IP was worth billions as products but only millions as licenses",
            "High-margin legacy businesses are the greatest risk factor for disruption — the more profitable the incumbent model, the harder it is to cannibalize",
            "Compare to Netflix: same diagnosis, opposite response, opposite outcome — this is the fork-in-the-road moment every incumbent faces",
        ],
        "bottom_line": "FAILURE CASE: Invented digital photography, then suppressed it to protect film margins. Instagram sold for $1B in 2012 — built on Kodak's own technology.",
    },

    {
        "name": "Under Armour Overexpansion and Founder Problem",
        "slug": "under-armour-overexpansion",
        "industry": "retail",
        "case_type": "turnaround",
        "date": "2015-01-01",
        "problem": """Under Armour Growth Addiction (2015)

Under Armour was the hottest brand in athletic apparel from 2010-2015. Revenue grew from $1B to $4B in five years. Stock was up 1,500% from its IPO. The company had overtaken Adidas as the #2 athletic brand in the US. Then everything unraveled. Founder Kevin Plank had invested aggressively in "connected fitness" technology — acquiring MapMyFitness ($150M), MyFitnessPal ($475M), and Endomondo ($85M). These were app companies with huge user bases but no clear path to selling shoes and shirts. Meanwhile, the core apparel business was losing its edge: wholesale partners were oversaturated, the fashion cycle moved toward retro/lifestyle (favoring Nike and Adidas), and Under Armour had no credible women's line.""",

        "decision": """Growth at All Costs — CAUTIONARY TALE

1. Spent $710M on connected fitness acquisitions (2013-2015) with no integration strategy
2. Continued aggressive revenue growth targets — pushed excess inventory into off-price channels (TJ Maxx, Marshalls), diluting the premium brand
3. Over-invested in DTC retail — opened expensive Brand House stores that underperformed
4. Failed to invest in lifestyle/fashion — remained stuck in the "performance athlete" niche while competitors expanded into athleisure
5. Plank made politically controversial comments supporting Donald Trump (2017), alienating key endorsers — Steph Curry publicly criticized him
6. Accounting practices came under SEC and DOJ investigation (2019) — accused of pulling forward revenue from future quarters to hit growth targets
7. Plank eventually stepped down as CEO in October 2019, replaced by Patrik Frisk (who lasted 2 years), then by Stephanie Linnartz (who lasted 11 months)""",

        "outcome": """Results — CATASTROPHIC DECLINE:

- Revenue plateaued at ~$5B and then declined — lost 10 straight quarters of growth
- Stock collapsed from $50 (2015) to under $7 (2020) — an 86% decline
- Connected fitness apps (MyFitnessPal, MapMyFitness, Endomondo) were all eventually sold — for a combined price far below acquisition cost. MyFitnessPal alone was sold for $345M in 2020 after being acquired for $475M.
- Under Armour dropped from #2 to #4 in US athletic market, behind Nike, Adidas, and New Balance
- SEC investigation resulted in a $9M settlement in 2021 — small fine but massive reputational damage
- Plank returned as CEO in April 2024, attempting a second act, but stock remains depressed
- The brand's core problem remains unresolved: perceived as a performance brand in a lifestyle-driven market

Key Lesson: Growth addiction is a disease. Under Armour's core business was healthy — they made great performance apparel. But the obsession with maintaining 20%+ growth rates led to bad acquisitions, channel dilution, and accounting games. Contrast with Patagonia: Patagonia said "buy less" and grew 4x; Under Armour said "grow at all costs" and shrank. Also: founder-CEOs who can't evolve from scrappy entrepreneur to scaled executive often become the company's biggest liability.""",

        "top_recommendations": [
            "Do not acquire technology companies to solve a brand problem — MyFitnessPal users don't automatically buy shoes",
            "Resist the temptation to push excess inventory into off-price channels — short-term revenue kills long-term brand equity",
            "A founder who cannot adapt from startup mode to scaled executive often becomes the company's primary risk factor",
            "Revenue growth is not a strategy — a company with 20%+ growth targets will eventually manufacture that growth through accounting",
        ],
        "bottom_line": "FAILURE CASE: Growth addiction led to $710M in failed acquisitions, channel dilution, accounting investigation, and 86% stock decline.",
    },
]


CROSS_CASE_PATTERNS_2 = """CROSS-CASE PATTERNS — Cases 11-20 (Niche Edition)

1. LEADERSHIP TRANSITIONS ARE THE REAL TURNING POINT: Chipotle recovered under Niccol, not the founders. Lululemon recovered under McDonald, not Wilson. Under Armour declined under Plank. The right leader at the right moment matters more than the right strategy.

2. YOUR WORST CRISIS CAN BECOME YOUR STRONGEST CAPABILITY: Chipotle's food safety is now industry-leading BECAUSE of the outbreak. Lululemon's quality control is stronger because of the sheer pants recall. Post-crisis investment often creates durable competitive advantages.

3. TECHNOLOGY PIVOTS WORK WHEN THE PRODUCT SOLVES A REAL PROBLEM YOU EXPERIENCED YOURSELF: Slack was built to solve the team's own communication problem. Zoom was built because Eric Yuan was frustrated with Cisco WebEx. Internal pain is the best product-market fit validator.

4. IGNORING DISRUPTION BECAUSE YOUR CURRENT BUSINESS IS TOO PROFITABLE IS THE #1 KILLER: Kodak (film margins), BlackBerry (enterprise email lock-in), Under Armour (performance apparel). The more profitable your legacy business, the harder it is to cannibalize it.

5. SPEED WITHOUT STRATEGIC CLARITY DESTROYS VALUE: JCPenney (nationwide rollout with no testing), Under Armour (3 app acquisitions in 2 years with no integration). Fast execution of the wrong strategy is worse than slow execution of the right one.

6. PARADOX OF AUTHENTICITY: Patagonia's "buy less" increased sales. Domino's "our pizza sucks" increased sales. Transparency and anti-marketing often outperform traditional marketing because modern consumers are deeply skeptical of corporate messaging.

7. FOUNDER-CEO TRANSITIONS: Chipotle (Brian Niccol), Lululemon (Calvin McDonald), Best Buy (Hubert Joly). Outside CEOs with fresh context often outperform founders in turnaround situations.

8. CROWDSOURCING AND COMMUNITY: LEGO Ideas turned superfans into product developers. Slack grew through bottom-up word-of-mouth within teams. Community-driven growth is the most capital-efficient acquisition strategy.

Cases covered: Chipotle (2015-2021), Lululemon (2013-2023), LEGO Ideas (2008-present), JCPenney (2011-2013 — FAILURE), Slack (2012-2021), BlackBerry (2007-2016 — FAILURE), Patagonia (2011-present), Zoom (2019-2022), Kodak (1975-2012 — FAILURE), Under Armour (2015-2020 — FAILURE)."""


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

    outcome_text = f"# Outcome — {case['name']}\n\n{case['outcome']}\n"
    (case_dir / "outcome.md").write_text(outcome_text, encoding="utf-8")

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
    (case_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

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

    chunks.append({
        "id": _id(slug, "problem_statement"),
        "text": f"PROBLEM STATEMENT ({case['name']}):\n{case['problem']}",
        "metadata": {**base_meta, "chunk_type": "problem_statement"},
    })

    chunks.append({
        "id": _id(slug, "decision"),
        "text": f"STRATEGY AND DECISION ({case['name']}):\n{case['decision']}",
        "metadata": {**base_meta, "chunk_type": "finding"},
    })

    chunks.append({
        "id": _id(slug, "outcome"),
        "text": f"OUTCOME ({case['name']}):\n{case['outcome']}",
        "metadata": {**base_meta, "chunk_type": "outcome"},
    })

    chunks.append({
        "id": _id(slug, "exec_summary"),
        "text": f"EXECUTIVE SUMMARY ({case['name']}):\n{case['bottom_line']}",
        "metadata": {**base_meta, "chunk_type": "exec_summary"},
    })

    for i, rec_title in enumerate(case["top_recommendations"]):
        chunks.append({
            "id": _id(slug, "recommendation", i),
            "text": f"RECOMMENDATION ({case['name']}): {rec_title}",
            "metadata": {**base_meta, "chunk_type": "recommendation", "recommendation_title": rec_title},
        })

    return chunks


def main():
    console.print("\n[bold cyan]Seeding knowledge base with 10 more real-world business cases (11-20)...[/bold cyan]\n")

    from knowledge.vectorstore import store_chunks

    all_chunks = []
    total_files = 0

    for case in CASES:
        case_dir = _write_files(case)
        total_files += 1
        console.print(f"  [green]Created[/green] {case_dir}")

        chunks = _build_chunks(case)
        all_chunks.extend(chunks)

    all_chunks.append({
        "id": hashlib.md5("cross_case_patterns_batch2_0".encode()).hexdigest(),
        "text": CROSS_CASE_PATTERNS_2,
        "metadata": {
            "case_name": "Cross-Case Patterns (Cases 11-20)",
            "chunk_type": "finding",
            "industry": "general",
            "case_type": "general_strategy",
            "source": "real_world_case_study",
        },
    })

    console.print(f"\n[bold cyan]Embedding {len(all_chunks)} chunks into ChromaDB...[/bold cyan]")
    try:
        from knowledge.vectorstore import store_chunks
        store_chunks(all_chunks)
        console.print(f"\n[bold green]Done! {total_files} cases created, {len(all_chunks)} chunks embedded.[/bold green]")
        console.print("[dim]Run: python main.py cases  — to verify[/dim]\n")
    except Exception as e:
        console.print(f"\n[red]Embedding failed: {e}[/red]")
        console.print("[dim]Files were created in cases/past/ — run 'python main.py learn <path>' manually if needed.[/dim]")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

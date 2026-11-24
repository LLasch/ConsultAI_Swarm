"""
Seed the knowledge base with 10 real-world corporate business cases.
Creates cases/past/ directories and embeds all chunks into ChromaDB.

Run: python seed_knowledge_base.py
"""

import hashlib
import json
import sys
import io
from datetime import date
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace") if hasattr(sys.stdout, "buffer") else sys.stdout

from rich.console import Console
console = Console(file=sys.stdout)


# ── Case data ─────────────────────────────────────────────────────────────────

CASES = [
    {
        "name": "LEGO Turnaround",
        "slug": "lego-turnaround",
        "industry": "manufacturing",
        "case_type": "turnaround",
        "date": "2004-01-01",
        "problem": """LEGO Near-Bankruptcy Crisis (2003)

By 2003, LEGO was losing $1 million per day, had accumulated $800 million in debt, and sales had dropped 30% in two years. Operating margins collapsed from 18% in the late 1990s to 2.4%. The company had overexpanded into theme parks, clothing lines, video games, TV shows, and jewelry — none of which played to its core strength. Product complexity had exploded to 13,000 SKUs with many sets being sold at a loss. Video games and digital entertainment were pulling children away from physical toys. Analysts predicted bankruptcy within 18 months.""",

        "decision": """Turnaround Strategy: Radical Simplification (2004)

CEO Jørgen Vig Knudstorp (former McKinsey) executed radical simplification:

- Cut SKUs from 13,000 to 7,000 — eliminated unprofitable sets and redundant brick types
- Sold the LEGOLAND theme parks to Merlin Entertainments, retaining licensing rights
- Exited non-core businesses — shut down clothing, jewelry, in-house video game development
- Aligned design to manufacturing cost — discovered some sets were being sold at a loss and fixed pricing
- Refocused R&D on the core brick system — structured, data-informed design framework
- Invested in franchise partnerships — Star Wars, Harry Potter, Marvel licensing deals
- Launched LEGO Ideas — crowdsourcing platform where fans submit and vote on new set designs
- Cut 1,000 jobs and outsourced non-core manufacturing""",

        "outcome": """Results (2006–2023):

- Operating margin recovered to 15.6% (from 2.4% in 2003) by 2006
- Annual sales exceeded $2 billion by 2014 — a 900% increase over a decade
- In 2015, LEGO overtook Mattel to become the world's largest toy company
- Star Wars sets alone increased revenue by 35%
- The LEGO Movie (2014) grossed $468M globally, functioning as a massive brand advertisement
- By 2023, LEGO was a $9.7 billion global powerhouse
- During the 2008 recession, while competitors suffered, LEGO's profits quadrupled
- Brand Finance named LEGO the world's most powerful brand in 2015, dethroning Ferrari

Key Lesson: The problem wasn't lack of innovation — it was lack of focus. Cutting back was the boldest growth strategy. "Companies don't die from starvation; they die from indigestion." — Knudstorp""",

        "top_recommendations": [
            "Cut product portfolio radically (from 13,000 to 7,000 SKUs)",
            "Exit all non-core businesses (theme parks, clothing, jewelry)",
            "Invest in franchise licensing partnerships (Star Wars, Harry Potter)",
            "Launch fan-driven product development (LEGO Ideas)",
        ],
        "bottom_line": "Radical simplification and return to core competency saved LEGO from bankruptcy.",
    },

    {
        "name": "Netflix DVD to Streaming Pivot",
        "slug": "netflix-streaming-pivot",
        "industry": "technology",
        "case_type": "digital_transformation",
        "date": "2007-01-01",
        "problem": """Netflix DVD Business Disruption Risk (2007)

In 2007, Netflix was a successful DVD-by-mail rental company with 7.5 million subscribers and $1.2 billion in revenue. But CEO Reed Hastings saw the writing on the wall: physical media was dying. Broadband internet penetration was crossing 50% of US households. YouTube (launched 2005) was proving consumers wanted on-demand video. The challenge: cannibalize your own profitable DVD business before someone else does.""",

        "decision": """Streaming Pivot Strategy (2007–2013)

1. Launched streaming service in 2007 as an add-on to existing DVD plans — no extra charge for small initial content library
2. Invested aggressively in streaming content licenses — $40M in 2008, growing to $2B+ by 2012
3. Separated DVD and streaming into distinct plans (2011) — pricing effectively increased 60% for customers who wanted both
4. Began producing original content — House of Cards (2013) was a $100M bet ordered two seasons sight unseen based on data analytics
5. Expanded internationally — Canada (2010), then Latin America, UK, Nordics by 2012
6. Built proprietary content delivery network (Open Connect) to reduce CDN dependence

The Qwikster mistake (2011): attempted to spin off DVD business entirely. Lost 800,000 subscribers in one quarter, stock dropped 77%. Hastings publicly apologized and reversed the branding but kept the price separation.""",

        "outcome": """Results (2013–2023):

- By Q1 2013, Netflix had recovered to 36 million streaming subscribers
- House of Cards (Feb 2013) proved streaming services could produce prestige television
- By 2017, Netflix had 100 million subscribers globally
- By 2020, Netflix had 200 million subscribers and a market cap exceeding $200 billion
- The DVD business wound down from $1.2B revenue (2007) to being shut down entirely in 2023
- Netflix fundamentally disrupted the entire entertainment industry — Blockbuster filed for bankruptcy in 2010
- Traditional TV networks launched their own streaming services years too late

Key Lesson: The willingness to cannibalize your own profitable business is the hardest strategic decision but sometimes the only path to survival. The Qwikster mistake showed that execution matters as much as strategy — the right decision was nearly fatal because of poor communication.""",

        "top_recommendations": [
            "Cannibalize profitable legacy business before external disruption forces it",
            "Invest heavily in original content as a defensible differentiator",
            "Expand internationally early to build scale advantages",
            "Build proprietary technology infrastructure rather than relying on third parties",
        ],
        "bottom_line": "Self-disruption of the DVD business was existentially necessary; execution errors (Qwikster) nearly derailed it.",
    },

    {
        "name": "Apple Return from Near-Death",
        "slug": "apple-1997-turnaround",
        "industry": "technology",
        "case_type": "turnaround",
        "date": "1997-09-01",
        "problem": """Apple Near-Bankruptcy (1997)

In 1997, Apple was 90 days from bankruptcy. The company had lost $1.6 billion over two years, market share had collapsed to 3.3%, and the product line was bloated with dozens of confusing, overlapping Macintosh models. Apple had wasted hundreds of millions on failed products: Newton PDA, Copland OS, Pippin gaming console, eWorld online service, and multiple printer lines. Michael Dell publicly suggested Apple should "shut down and give the money back to shareholders." """,

        "decision": """Ruthless Simplification Strategy (1997–2003)

Steve Jobs returned as interim CEO in September 1997:

1. Cut product line from 15+ models to 4 — simple 2x2 grid: Consumer/Pro x Desktop/Portable (iMac, iBook, Power Mac, PowerBook)
2. Killed Newton, Copland, Pippin, printers, and dozens of other products — eliminated 70% of the product line
3. Negotiated a $150M investment from Microsoft (controversial but existentially necessary)
4. Launched the iMac (1998) — radically redesigned all-in-one in translucent colored plastic, first mass-market computer designed as lifestyle product
5. Launched Apple Retail Stores (2001) — critics called it insane to open retail during the dot-com bust
6. Launched iPod + iTunes (2001–2003) — entered music player market, then created iTunes Store as killer ecosystem
7. Elevated Jony Ive to SVP of Design, making industrial design a strategic function rather than cost center""",

        "outcome": """Results (1998–2007):

- iMac sold 800,000 units in first 5 months (1998) — 32% were first-time computer buyers
- Apple returned to profitability in Q1 1998 ($45M profit, first in years)
- iPod: Windows compatibility added 2003, sales exploded — 100M iPods sold by 2007
- iTunes Store launched April 2003, sold 1 million songs in first week
- Apple Retail Stores became the highest-revenue-per-square-foot retail operation in the world
- Revenue grew from $7.1B (1997) to $13.9B (2005)
- Stock: $3.19 (Dec 1997, split-adjusted) to $75 (Dec 2007) — 23x return before iPhone even launched
- iPod/iTunes ecosystem laid the foundation for the iPhone (2007), which made Apple the world's most valuable company

Key Lesson: Saying no is as important as saying yes. Jobs killed more products than he launched. Focus and simplification were the turnaround — not a single breakthrough product, but a strategy of doing fewer things at dramatically higher quality.""",

        "top_recommendations": [
            "Ruthlessly cut product line to a 2x2 matrix (consumer/pro x desktop/portable)",
            "Invest in design as a core strategic function, not a cost center",
            "Create an ecosystem (iTunes + iPod) rather than a standalone product",
            "Open direct retail to control brand experience and customer relationship",
        ],
        "bottom_line": "Saying no to 70% of the product line — not any single new product — was the turnaround.",
    },

    {
        "name": "Domino's Pizza Turnaround",
        "slug": "dominos-pizza-turnaround",
        "industry": "retail",
        "case_type": "turnaround",
        "date": "2009-01-01",
        "problem": """Domino's Brand and Product Crisis (2009)

By 2009, Domino's stock had hit $3 per share (down from $32 at IPO). Consumers rated Domino's pizza as tasting "like cardboard" and "like ketchup on a cracker" in viral brand perception surveys. In blind taste tests, Domino's finished dead last among national pizza chains. The 50-year-old recipe had never been meaningfully updated. Same-store sales had been flat or declining for years. The brand was synonymous with cheap, low-quality delivery pizza in an era when consumers were gravitating toward fast-casual and premium options.""",

        "decision": """Radical Honesty and Product Reformulation Strategy

CEO Patrick Doyle made one of the most unusual moves in corporate marketing history:

1. Launched the "Pizza Turnaround" campaign — TV ads showing real focus group footage of people trashing Domino's pizza, followed by chefs pledging to fix it. Publicly admitted the product was terrible.
2. Completely reformulated the pizza — new crust, new sauce, new cheese. Every component changed. Not incremental.
3. Invested heavily in digital/mobile ordering — built best-in-class app. By 2015, over 50% of orders through digital channels.
4. Created the "Pizza Tracker" — real-time order tracking that turned commodity delivery into something engaging
5. Launched "Domino's AnyWare" — ordering via text, tweet, smart TV, Amazon Echo, Slack, zero-click ordering
6. "Paving for Pizza" program — Domino's filled potholes in cities to protect pizza during delivery. Brilliant PR stunt.""",

        "outcome": """Results (2010–2021):

- Same-store sales jumped 14.3% in the first quarter after new recipe launch — largest quarterly increase in fast-food history
- Stock: $3 (2009) to $135 (2017) to $430+ (2021) — a 140x return, outperforming Google, Amazon, and Apple over same period
- By 2018, Domino's surpassed Pizza Hut as #1 pizza chain globally by revenue
- Digital sales went from near-zero to over 75% of total orders
- Revenue grew from $1.4B (2009) to $4.4B (2021)
- The transparent "we screwed up" marketing became a Harvard Business School case study in brand authenticity
- Domino's became as much a tech company as a pizza company

Key Lesson: Radical honesty can be a competitive advantage. Rather than defending a bad product, Domino's weaponized their weakness into a turnaround narrative. But the honesty only worked because they actually fixed the product — the reformulation was real, not just marketing.""",

        "top_recommendations": [
            "Acknowledge product failures publicly to build turnaround credibility",
            "Fully reformulate core product — incremental improvement won't reset brand perception",
            "Invest in digital ordering as primary channel (50%+ of orders)",
            "Create engaging operational transparency (Pizza Tracker) to differentiate commodity delivery",
        ],
        "bottom_line": "Radical public honesty about product failure, backed by genuine product reformulation, drove the turnaround.",
    },

    {
        "name": "Best Buy Amazon Survival",
        "slug": "best-buy-amazon-survival",
        "industry": "retail",
        "case_type": "digital_transformation",
        "date": "2012-01-01",
        "problem": """Best Buy "Amazon Showroom" Crisis (2012)

By 2012, Best Buy appeared to be the next Blockbuster. Consumers were openly using Best Buy stores as showrooms — examining products in-store, then buying from Amazon at lower prices. Stock had dropped 50% in a year. Comparable-store sales were declining. The CEO had resigned due to a personal conduct investigation. Amazon was growing 30%+ per year. Circuit City had already gone bankrupt in 2009. Industry consensus was that big-box electronics retail was dead.""",

        "decision": """"Renew Blue" Turnaround Strategy (2012)

New CEO Hubert Joly launched "Renew Blue" in late 2012:

1. Price-matched Amazon and all major online competitors — eliminated the #1 reason customers left stores empty-handed
2. Cut $1 billion in costs over two years — closed underperforming stores, reduced corporate overhead, renegotiated vendor contracts
3. Transformed stores into "experience centers" — created branded store-within-a-store partnerships with Samsung, Apple, Microsoft, Sony. Vendors paid for buildout and staffing.
4. Invested in employee training and engagement — Joly personally visited stores, reintroduced employee discounts. Employee engagement scores rose from 33rd to 75th+ percentile.
5. Built ship-from-store capabilities — turned 1,000+ stores into mini-fulfillment centers for same-day delivery
6. Launched Total Tech Support and Geek Squad subscriptions — recurring revenue from services
7. Created Best Buy Health — moved into aging-at-home technology, acquired GreatCall for $800M""",

        "outcome": """Results (2013–2019):

- Stock: $11.29 (December 2012) to $100+ (2019) — a 9x return
- Revenue stabilized at ~$43B (had been declining toward $36B)
- Online sales grew from 7% to 33% of total revenue
- Comparable-store sales growth turned positive and remained positive for 6 consecutive years
- Store-within-a-store program generated hundreds of millions in vendor payments
- Best Buy Health grew to $600M+ in revenue
- Employee turnover decreased significantly; customer satisfaction reached record highs
- While Amazon killed Circuit City, RadioShack, Toys R Us, and Sears — Best Buy thrived

Key Lesson: Physical retail isn't dead — boring retail is dead. Best Buy survived by making stores useful in ways Amazon couldn't replicate: you can't try on headphones on a website or get someone to install your home theater from a warehouse.""",

        "top_recommendations": [
            "Price-match competitors immediately to stop showrooming (short-term margin sacrifice for traffic retention)",
            "Convert stores to vendor-funded experience centers — shift cost burden while improving experience",
            "Build ship-from-store to compete on last-mile delivery speed",
            "Develop subscription services (Total Tech Support) for recurring revenue",
        ],
        "bottom_line": "Physical retail survived by becoming an experience and service center that Amazon cannot replicate.",
    },

    {
        "name": "Marvel Bankruptcy to Disney Acquisition",
        "slug": "marvel-bankruptcy-to-disney",
        "industry": "general",
        "case_type": "growth_strategy",
        "date": "1998-01-01",
        "problem": """Marvel Entertainment Bankruptcy (1996)

In 1996, Marvel Entertainment filed for Chapter 11 bankruptcy. The comic book speculator bubble burst. Marvel had overleveraged itself under corporate raider Ron Perelman, taking on $700M in junk bond debt. Comic book sales collapsed industry-wide. Marvel's stock went from $35 to nearly zero. The company's most valuable IP (Spider-Man, X-Men) had been licensed to other studios for minimal upfront fees — Sony had Spider-Man film rights, Fox had X-Men and Fantastic Four.""",

        "decision": """Marvel Studios Self-Production Strategy (2005)

After emerging from bankruptcy in 1998, Marvel made a radical bet:

1. Created Marvel Studios (2005) to produce their own films instead of licensing characters
2. Secured a $525M credit facility from Merrill Lynch using film rights to 10 characters (Iron Man, Captain America, Thor) as collateral — if films flopped, Marvel would lose its own characters
3. Chose Iron Man as the first film — a B-list character Marvel controlled outright. Cast Robert Downey Jr. (considered a major risk)
4. Designed a connected universe — planned individual character films building toward team-up movies (The Avengers), creating unprecedented narrative arc across multiple films
5. Hired Kevin Feige to oversee coherent creative vision across all properties""",

        "outcome": """Results (2008–2019):

- Iron Man (2008) grossed $585M globally on a $140M budget — massive hit
- The connected universe approach created unprecedented audience investment — each film marketed the next
- The Avengers (2012) grossed $1.52 billion — validating the entire MCU strategy
- Disney acquired Marvel for $4 billion in 2009 — at the time many analysts called it overpriced
- By 2019, the MCU had generated over $22.5 billion in global box office revenue
- Avengers: Endgame (2019) grossed $2.8 billion — became the highest-grossing film ever (at the time)
- Disney's $4B acquisition is now considered one of the greatest deals in entertainment history — the MCU alone generated 10x+ the purchase price
- The "cinematic universe" model was copied by every major studio (DC, Universal, MonsterVerse)

Key Lesson: Your most undervalued assets are often the ones you're not using yourself. Marvel's characters were worth billions as self-produced films but only millions as licenses to other studios. Vertical integration — owning production rather than licensing — was the unlock.""",

        "top_recommendations": [
            "Vertically integrate — produce directly rather than licensing IP to others",
            "Design a connected narrative universe to create compounding audience engagement across properties",
            "Use B-list assets first to prove the model before risking A-list IP",
            "Hire a single creative executive (Feige) to maintain coherent vision across a large portfolio",
        ],
        "bottom_line": "Vertical integration from licensing to self-production unlocked 10x+ value from existing IP.",
    },

    {
        "name": "Starbucks Schultz Returns Turnaround",
        "slug": "starbucks-schultz-turnaround",
        "industry": "retail",
        "case_type": "turnaround",
        "date": "2008-01-01",
        "problem": """Starbucks Over-Expansion Crisis (2008)

By 2008, Starbucks was in crisis. The company had over-expanded from 10,000 to 16,000 stores in just 5 years, prioritizing growth over quality. Same-store sales were declining for the first time in company history. Stock had lost 50% of its value. An internal memo from founder Howard Schultz leaked, lamenting that stores had lost their soul — felt "sterile" and "cookie-cutter," automated espresso machines eliminated barista craft, breakfast sandwich smells overpowered coffee aromas. McDonald's McCafé was aggressively competing on price. The financial crisis was about to make consumers rethink $5 lattes.""",

        "decision": """Quality-First Turnaround Strategy (2008–2012)

Howard Schultz returned as CEO in January 2008:

1. Closed all 7,100 US stores for 3.5 hours on February 26, 2008 to retrain every barista on espresso technique. Cost: ~$6M in lost revenue. Message: quality matters more than sales.
2. Closed 600 underperforming US stores and stopped opening new ones — reversed growth-at-all-costs
3. Eliminated breakfast sandwiches temporarily until reformulated to not overpower coffee smell
4. Replaced automated espresso machines with semi-automatic Mastrena machines requiring barista skill
5. Launched Pike Place Roast — a high-quality everyday drip coffee to compete with McDonald's
6. Invested heavily in digital — Starbucks app with mobile payments, My Starbucks Rewards loyalty program, free in-store WiFi
7. Created Starbucks Reserve and Roastery concept — premium immersive coffee experiences
8. Diversified revenue — K-Cups partnership with Keurig, bottled Frappuccinos, Starbucks VIA instant coffee""",

        "outcome": """Results (2010–2019):

- Same-store sales returned to positive growth by Q3 2010
- Stock: $7.83 (November 2008) to $57 (2013) — a 7x return in 5 years
- Revenue grew from $10.4B (2008) to $14.9B (2013)
- Starbucks Rewards became the most successful restaurant loyalty program in the US — 25M+ active members by 2019
- Mobile order-ahead (launched 2015) eventually drove 25% of all US transactions
- The Starbucks app at one point held more customer deposits than many mid-size banks ($1.6B in stored value)
- K-Cup partnership generated $1B+ in annual CPG revenue
- Reserve Roastery locations became tourist destinations, elevating the entire brand
- By 2019, Starbucks had 31,000 stores globally with a $100B+ market cap

Key Lesson: Growth can be the disease disguised as the cure. Schultz's counterintuitive move — slowing growth, closing stores, sacrificing short-term revenue for quality — rebuilt the brand's emotional connection. The 3.5-hour shutdown told employees, customers, and Wall Street that quality was non-negotiable.""",

        "top_recommendations": [
            "Make a dramatic symbolic gesture to signal the turnaround is real (mass retraining shutdown)",
            "Close underperforming locations — growth in store count is not the same as growth in brand strength",
            "Return to the craft and experience that made the brand valuable",
            "Build a loyalty program and digital ecosystem to own the customer relationship",
        ],
        "bottom_line": "Slowing expansion and investing in quality over quantity rebuilt brand trust and drove 7x stock return.",
    },

    {
        "name": "Target Canada Catastrophic Failure",
        "slug": "target-canada-failure",
        "industry": "retail",
        "case_type": "market_entry",
        "date": "2013-01-01",
        "problem": """Target Canada International Expansion (2013)

Target was one of the most successful retailers in the US, beloved for its "Cheap Chic" brand positioning. In 2011, Target announced a $1.8B acquisition of 220 former Zellers store leases in Canada. Canadian consumers were thrilled — Target had a cult following from cross-border shopping. Analysts projected $6B in Canadian revenue within a few years. The challenge: execute an unprecedented international expansion at speed while maintaining brand promise.""",

        "decision": """Aggressive Rapid Expansion Strategy — CAUTIONARY TALE

1. Acquired 220 Zellers leases across Canada for $1.8B
2. Opened 124 stores in just 10 months (March–December 2013) — unprecedented pace
3. Built a new supply chain from scratch rather than extending US system — implemented new SAP enterprise system for Canada
4. Set aggressive pricing targets — promised Canadian consumers "expect more, pay less" as in the US
5. Relied on existing Zellers locations rather than purpose-built Target stores

NOTE: This is a cautionary case — all five decisions were strategic errors.""",

        "outcome": """Results — CATASTROPHIC FAILURE ($5.4 Billion Loss):

- Opened to massive consumer excitement, then immediate and severe disappointment
- Supply chain disaster: new SAP system riddled with data errors. Store shelves empty 30-40% of the time. Products in warehouses but system didn't know how to route them to stores.
- Pricing failure: prices were 15-20% higher than US Target stores, violating the core brand promise. Canadian consumers could easily compare prices online.
- Location quality: former Zellers stores in B and C locations, poorly laid out, too small for the Target experience
- Speed killed quality: opening 124 stores in 10 months meant nothing was done well — staff undertrained, stores understocked, systems untested
- Same-store sales dramatically below projections — some stores generating less than 50% of expected revenue
- Total losses: $5.4 billion CAD over 2 years
- Target Canada filed for creditor protection in January 2015, just 2 years after launch
- All 133 stores closed, 17,600 employees lost their jobs
- The CEO who led the expansion was fired
- Target's US stock dropped; company has not attempted international expansion since

Key Lesson: Speed of execution cannot substitute for quality of execution. Target tried to do in 10 months what should have taken 3-4 years. Supply chain failure alone was fatal — you cannot run a retail operation if products don't reach shelves. Brand love doesn't translate automatically across borders.""",

        "top_recommendations": [
            "Never sacrifice supply chain readiness for speed of opening — empty shelves destroy brand promise",
            "Test new SAP or ERP systems thoroughly before relying on them at scale",
            "Phase international expansion over 3-4 years, not 10 months",
            "Audit location quality before committing — inherited real estate may not match brand requirements",
        ],
        "bottom_line": "FAILURE CASE: Speed without quality destroyed a beloved brand. $5.4B loss, 17,600 jobs, full exit.",
    },

    {
        "name": "Nintendo Wii Blue Ocean Strategy",
        "slug": "nintendo-wii-blue-ocean",
        "industry": "technology",
        "case_type": "growth_strategy",
        "date": "2005-01-01",
        "problem": """Nintendo Console Wars Losing Position (2005)

By 2005, Nintendo was losing the console wars badly. The GameCube (2001) had sold only 22 million units versus PlayStation 2's 155 million. The gaming industry was locked in a graphics arms race — Sony's PS3 and Microsoft's Xbox 360 competed on processing power and hard-core gamer appeal. Nintendo couldn't win this fight: less capital, weaker third-party developer relationships, and dismissed as a "kids' console." Conventional wisdom was that Nintendo would exit the home console market.""",

        "decision": """Blue Ocean Strategy — Competing by Not Competing (2006)

Under president Satoru Iwata, Nintendo pursued a Blue Ocean Strategy:

1. Designed the Wii with deliberately inferior graphics — technology roughly equivalent to original Xbox (one generation behind PS3/Xbox 360). This was intentional, not a budget limitation.
2. Invested in motion controls — the Wii Remote detected physical movement. Innovation was in the interface, not processing power.
3. Targeted non-gamers — designed for families, seniors, casual players, people who had never owned a console
4. Priced at $249 versus PS3's $499-$599 — impulse-accessible
5. Bundled Wii Sports — a simple, immediately fun game that showcased motion controls. Required zero gaming experience.
6. Prioritized "fun per dollar" over technical specs — Iwata: "the games industry is at risk of pursuing only hardware power, while ignoring the need for creative game design" """,

        "outcome": """Results (2006–2010) — and the Mixed Long-Term Story:

- Wii sold 101.6 million units lifetime — beat PS3 (87.4M) and Xbox 360 (84M)
- Wii Sports became the best-selling game of its generation (82.9 million copies)
- At peak (2008-2009), Wii was so popular retailers couldn't keep them in stock for over a year
- Nintendo's revenue tripled from ¥509B (2006) to ¥1.84T (2009)
- Wii expanded the total gaming market — reached women 25-55, seniors, and families
- Nintendo's market cap surged past Sony's
- Motion controls were so successful that Sony (PlayStation Move) and Microsoft (Kinect) released copycat products

LONGER-TERM MIXED RESULTS:
- Third-party developer support remained weak — hardware couldn't run most major games
- The casual audience largely didn't buy many additional games
- The follow-up console (Wii U, 2012) was a commercial disaster — only 13.5M units sold
- Nintendo found footing again with the Switch (2017), combining Wii accessibility with stronger hardware

Key Lesson: You don't have to win the game everyone else is playing. Blue Ocean strategies can create unsustainable markets if the audience you attract isn't deeply engaged.""",

        "top_recommendations": [
            "Redefine the competitive arena rather than competing on incumbent metrics (specs vs. accessibility)",
            "Target the non-customer — casual and lapsed consumers often represent a larger opportunity than core customers",
            "Bundle a killer demonstration product that makes the innovation immediately understandable",
            "Recognize that Blue Ocean markets need engagement depth, not just breadth, to sustain long-term",
        ],
        "bottom_line": "Won the console war by refusing to compete on the console war's terms — but casual audience had low engagement depth.",
    },

    {
        "name": "Burberry Brand Repositioning",
        "slug": "burberry-brand-repositioning",
        "industry": "retail",
        "case_type": "organizational_change",
        "date": "2006-01-01",
        "problem": """Burberry Brand Identity Crisis (2006)

By 2006, Burberry had a serious brand identity crisis. The iconic plaid pattern had been so widely counterfeited and adopted by British "chav" culture that it had become a cultural punchline. Some UK pubs and clubs banned Burberry caps. The brand was simultaneously too downmarket for luxury consumers and too expensive for the mass market. Licensing had spiraled out of control — the Burberry check appeared on everything from dog leashes to baby strollers, with 23 different licensees producing goods of varying quality. There was no coherent brand identity across markets.""",

        "decision": """Luxury Repositioning Strategy (2006–2014)

CEO Angela Ahrendts and Chief Creative Officer Christopher Bailey:

1. Terminated 23 of 35 product licenses — regained control of how the brand appeared. Killed low-end products diluting luxury positioning.
2. Reduced the visibility of the plaid pattern — shifted from check being the product to check being a subtle accent. Moved brand identity from "pattern" to "heritage British luxury."
3. Invested heavily in digital — first luxury brand to livestream runway shows (2009). Launched "Art of the Trench" — user-generated content platform for Burberry trench coat photos. Years ahead of competitors.
4. Unified global brand identity — consolidated from multiple regional brands into one coherent global luxury brand. Redesigned every store to a consistent concept.
5. Targeted younger luxury consumers — hired Emma Watson as brand ambassador, partnered with Apple Music, invested in social media when competitors dismissed it.
6. Elevated the trench coat as the brand's "hero product" — offered 12 million possible customization combinations through "Bespoke" trench program.
7. Invested in flagship retail experiences — Regent Street store featured 500+ speakers, 100 screens, RFID-tagged clothing that triggered personalized content in fitting rooms.""",

        "outcome": """Results (2006–2014):

- Revenue doubled from £743M (2006) to £1.57B (2012)
- Operating profit tripled from £135M to £354M over same period
- Stock: roughly £3 (2006) to £17+ (2013) — a 5x+ return
- "Art of the Trench" generated millions of social media impressions — repositioned Burberry as culturally relevant
- Burberry became the most followed luxury brand on all major social platforms
- The chav association faded as the brand consistently appeared in luxury contexts
- Burberry was named the fourth most valuable luxury brand globally by Interbrand
- Angela Ahrendts was hired by Apple in 2014 to lead retail — validation of Burberry's digital-first luxury strategy
- The digital strategy became a case study at Harvard, Stanford, and INSEAD

Key Lesson: You can't outrun a brand perception problem — you have to confront it. Kill the products creating the problem even if they generate revenue. And counterintuitively, the path to luxury repositioning was through digital and younger consumers, not by retreating to traditional luxury gatekeeping.""",

        "top_recommendations": [
            "Kill the licenses and products creating brand dilution, even if they generate revenue",
            "Identify and elevate one 'hero product' as the brand entry point and anchor",
            "Invest in digital and user-generated content to reach younger consumers — luxury brands cannot ignore social",
            "Unify global brand identity — regional variation creates brand incoherence at scale",
        ],
        "bottom_line": "Brand repositioning required killing the revenue sources causing the problem — and digital-first luxury reached younger consumers.",
    },
]

# ── Cross-case patterns chunk ─────────────────────────────────────────────────

CROSS_CASE_PATTERNS = """CROSS-CASE PATTERNS — 10 Major Corporate Turnarounds and Transformations

1. SIMPLIFICATION WINS: LEGO (cut SKUs 46%), Apple (cut to 4 products), Starbucks (closed 600 stores). Doing less, better, beats doing more, worse.

2. RADICAL HONESTY IS AN ASSET: Domino's "our pizza sucks," Starbucks closing for retraining, LEGO admitting "we are a burning platform." Acknowledging the problem publicly builds trust and creates a turnaround narrative.

3. CANNIBALIZE YOURSELF BEFORE SOMEONE ELSE DOES: Netflix killed its own DVD business. Apple's iPod killed the Walkman before iPhone killed the iPod. Companies that survived disruption were willing to disrupt themselves.

4. SPEED WITHOUT QUALITY KILLS: Target Canada is the clearest example — 124 stores in 10 months destroyed a beloved brand and cost $5.4B. Best Buy's deliberate, steady transformation over 7 years succeeded.

5. CORE IDENTITY MATTERS: LEGO returned to bricks. Starbucks returned to coffee craft. Burberry returned to the trench coat. Apple returned to elegant design. In every turnaround, the answer was in the company's DNA — they just had to rediscover it.

6. REDEFINE THE GAME: Nintendo didn't try to beat Sony on graphics — changed what "winning" meant. Best Buy didn't try to beat Amazon on price — became an experience center. Marvel didn't license better — produced themselves.

7. ONE KEY HIRE CHANGES EVERYTHING: Knudstorp at LEGO, Jobs at Apple, Schultz at Starbucks, Joly at Best Buy, Feige at Marvel. A single leader with the right vision and authority can transform an organization.

8. INVEST THROUGH THE CRISIS: Best Buy invested in digital while losing money. Netflix spent billions on content while burning cash. Starbucks invested in mobile tech while closing stores. Companies that invested through the downturn came out strongest.

Cases covered: LEGO (2003-2015), Netflix (2007-2020), Apple (1997-2007), Domino's (2009-2021), Best Buy (2012-2019), Marvel Entertainment (1996-2019), Starbucks (2008-2019), Target Canada (2013-2015 — FAILURE), Nintendo Wii (2005-2010), Burberry (2006-2014)."""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _id(case_slug, chunk_type, idx=0):
    raw = f"{case_slug}_{chunk_type}_{idx}"
    return hashlib.md5(raw.encode()).hexdigest()


def _write_files(case: dict) -> Path:
    """Create cases/past/<slug>/ directory structure."""
    case_dir = Path("cases/past") / case["slug"]
    materials_dir = case_dir / "materials"
    materials_dir.mkdir(parents=True, exist_ok=True)

    # case_brief.md — problem + decision
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

    # outcome.md
    outcome_text = f"# Outcome — {case['name']}\n\n{case['outcome']}\n"
    (case_dir / "outcome.md").write_text(outcome_text, encoding="utf-8")

    # metadata.json
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

    # Problem statement
    chunks.append({
        "id": _id(slug, "problem_statement"),
        "text": f"PROBLEM STATEMENT ({case['name']}):\n{case['problem']}",
        "metadata": {**base_meta, "chunk_type": "problem_statement"},
    })

    # Decision / strategy
    chunks.append({
        "id": _id(slug, "decision"),
        "text": f"STRATEGY AND DECISION ({case['name']}):\n{case['decision']}",
        "metadata": {**base_meta, "chunk_type": "finding"},
    })

    # Outcome
    chunks.append({
        "id": _id(slug, "outcome"),
        "text": f"OUTCOME ({case['name']}):\n{case['outcome']}",
        "metadata": {**base_meta, "chunk_type": "outcome"},
    })

    # Bottom line / exec summary
    chunks.append({
        "id": _id(slug, "exec_summary"),
        "text": f"EXECUTIVE SUMMARY ({case['name']}):\n{case['bottom_line']}",
        "metadata": {**base_meta, "chunk_type": "exec_summary"},
    })

    # Recommendations — one chunk per rec
    for i, rec_title in enumerate(case["top_recommendations"]):
        chunks.append({
            "id": _id(slug, "recommendation", i),
            "text": f"RECOMMENDATION ({case['name']}): {rec_title}",
            "metadata": {**base_meta, "chunk_type": "recommendation", "recommendation_title": rec_title},
        })

    return chunks


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    console.print("\n[bold cyan]Seeding knowledge base with 10 real-world business cases...[/bold cyan]\n")

    from knowledge.vectorstore import store_chunks

    all_chunks = []
    total_files = 0

    for case in CASES:
        # Write files
        case_dir = _write_files(case)
        total_files += 1
        console.print(f"  [green]Created[/green] {case_dir}")

        # Build chunks
        chunks = _build_chunks(case)
        all_chunks.extend(chunks)

    # Add cross-case patterns as a separate chunk
    all_chunks.append({
        "id": hashlib.md5("cross_case_patterns_0".encode()).hexdigest(),
        "text": CROSS_CASE_PATTERNS,
        "metadata": {
            "case_name": "Cross-Case Patterns",
            "chunk_type": "finding",
            "industry": "general",
            "case_type": "general_strategy",
            "source": "real_world_case_study",
        },
    })

    # Embed everything
    console.print(f"\n[bold cyan]Embedding {len(all_chunks)} chunks into ChromaDB...[/bold cyan]")
    try:
        store_chunks(all_chunks)
        console.print(f"\n[bold green]Done! {total_files} cases created, {len(all_chunks)} chunks embedded.[/bold green]")
        console.print("[dim]Run: python main.py cases  — to verify[/dim]\n")
    except Exception as e:
        console.print(f"\n[red]Embedding failed: {e}[/red]")
        console.print("[dim]Files were created in cases/past/ — run 'python main.py learn <path>' manually if needed.[/dim]")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

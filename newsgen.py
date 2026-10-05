"""Text and relationship data for the news: people, products, places, company stories and cross-company stories.

Everything here is data plus a few small pure functions, so the news engine in engine.py stays readable and
the pieces can be tested on their own.

Each company gets a persona (CEO, CFO, flagship product, headquarters city and a supplier, a customer and a
rival from other listed companies). Company stories are written as slot templates such as
"{ceo} faces board pressure over missed targets at {name}"; a story is only used if every slot it needs can be
filled for that company. When a CEO leaves, the persona changes, so later stories name the new CEO and
sometimes the former one.
"""
import hashlib
import random
import re
import string

FIRST = ["Alicia", "Marcus", "Priya", "Diego", "Hannah", "Tomasz", "Nadia", "Kwame", "Elena", "Rohan", "Sofia",
         "Liam", "Mei", "Ahmed", "Clara", "Jonas", "Ingrid", "Mateo", "Yuki", "Olga", "Samuel", "Leila", "Viktor",
         "Chloe", "Dmitri", "Aisha", "Henrik", "Camila", "Arjun", "Beatrice", "Felix", "Zainab", "Lars", "Nora",
         "Tariq", "Greta", "Emeka", "Paloma", "Stefan", "Wendy", "Rafael", "Maeve", "Hiroshi", "Fatima", "Oscar",
         "Zoe", "Kofi", "Annika", "Gustavo", "Ruth"]
LAST = ["Hartley", "Okafor", "Lindqvist", "Moreau", "Castellanos", "Nakamura", "Whitfield", "Banerjee", "Kowalski",
        "Abara", "Fontaine", "Ivanov", "Delacroix", "Sorensen", "Mwangi", "Petrov", "Hargreaves", "Vasquez", "Tanaka",
        "Olsen", "Rinaldi", "Haddad", "Brennan", "Kruger", "Almeida", "Osei", "Lombardi", "Yamamoto", "Draper",
        "Nilsson", "Bianchi", "Achebe", "Sterling", "Volkov", "Marlowe", "Quigley", "Adeyemi", "Falk", "Santoro",
        "Ashworth", "Zhou", "Lindgren", "Costa", "Mbeki", "Halloran", "Dubois", "Eriksen", "Navarro", "Pryce",
        "Takahashi", "Gallagher", "Oduya"]
CITIES = ["Rotterdam", "Austin", "Osaka", "Lyon", "Seattle", "Gdansk", "Monterrey", "Busan", "Leeds", "Denver",
          "Porto", "Chennai", "Lagos", "Krakow", "Tampa", "Hamburg", "Nagoya", "Calgary", "Valencia", "Pittsburgh",
          "Bergen", "Curitiba", "Dublin", "Phoenix", "Turin", "Shenzhen", "Detroit", "Aarhus", "Perth", "Nairobi",
          "Rotorua", "Hartford", "Antwerp", "Pune", "Tulsa", "Graz", "Recife", "Cork", "Boise", "Ghent", "Lahti",
          "Memphis", "Split", "Tacoma", "Brno", "Mumbai", "Oulu", "Savannah", "Basel", "Ottawa"]

# sector -> (adjectives, nouns) for flagship product names, e.g. "Atlas Core 7"
PRODUCTS = {
    "tech": (["Nova", "Atlas", "Pulse", "Vector", "Orion", "Helix", "Zenith", "Quantum", "Apex", "Nimbus"],
             ["Core", "Cloud", "Suite", "Chip", "Engine", "Stack", "Link", "Pro", "Cortex"]),
    "energy": (["Titan", "Prairie", "Granite", "Sunrise", "Harbor", "Ridge"], ["Drill", "Grid", "Turbine", "Array", "Field", "Plant"]),
    "pharma": (["Cura", "Vita", "Neo", "Gen", "Immuno", "Bio"], ["cept", "lex", "mab", "gen", "trol", "vir"]),
    "healthcare": (["Care", "Vital", "Clear", "Bright", "Pulse", "Anchor"], ["Plan", "Scan", "Link", "Clinic", "Shield", "Dial"]),
    "defense": (["Aegis", "Falcon", "Sentinel", "Iron", "Raven", "Bulwark"], ["Radar", "Shield", "Drone", "Array", "Guard", "Strike"]),
    "airlines": (["Skyline", "Horizon", "Jet", "Cirrus", "Aero", "Summit"], ["Express", "Connect", "Route", "Cabin", "Class", "Pass"]),
    "consumer": (["Golden", "Fresh", "Hearth", "Sunny", "Crisp", "Maple"], ["Bites", "Brew", "Blend", "Basket", "Table", "Harvest"]),
    "finance": (["Anchor", "Prime", "Keystone", "Harbor", "Summit", "Beacon"], ["Card", "Account", "Fund", "Loan", "Vault", "Plan"]),
    "retail": (["Value", "Urban", "Trail", "Maison", "Daily", "Nest"], ["Club", "Line", "Collection", "Box", "Market", "Rewards"]),
    "media": (["Silver", "Echo", "Pixel", "Spark", "Chatter", "Stream"], ["Originals", "Studio", "Live", "Arena", "Channel", "Quest"]),
    "autos": (["Volt", "Iron", "Crest", "Thunder", "Gear", "Auto"], ["Rider", "Haul", "Line", "Drive", "Cell", "Truck"]),
    "realestate": (["Skyline", "Hearth", "Plaza", "Crate", "Grand", "Keystone"], ["Tower", "Court", "Park", "Square", "Gate", "Residences"]),
    "crypto": (["Hash", "Block", "Coin", "Key", "Loop", "Pixel"], ["Wallet", "Pay", "Vault", "Chain", "Swap", "Ledger"]),
    "space": (["Launch", "Star", "Luna", "Red", "Astro", "Orbit"], ["Rocket", "Web", "Lander", "Habitat", "Lens", "Tug"]),
    "utilities": (["Bright", "Prairie", "Hydro", "Volt", "Clear", "Steady"], ["Grid", "Power", "Line", "Flow", "Supply", "Plan"]),
    "industrials": (["Iron", "Steel", "Prime", "Atlas", "Bridge", "Cargo"], ["Loader", "Bot", "Crane", "Line", "Works", "Hauler"]),
    "telecom": (["Tower", "Fiber", "Wave", "Link", "Signal", "Spectrum"], ["Net", "Plan", "Connect", "Cast", "Band", "Core"]),
    "materials": (["Stone", "Lithic", "Granite", "Alloy", "Quarry", "Terra"], ["Mix", "Cell", "Ore", "Block", "Metal", "Powder"]),
    "agriculture": (["Prairie", "Golden", "Green", "Harvest", "Field", "Sunrise"], ["Seed", "Yield", "Grain", "Feed", "Crop", "Mill"]),
    "meme": (["Moon", "Diamond", "Rocket", "Doge", "Ape", "Hype"], ["Coin", "Hands", "Club", "Pack", "Tokens", "Party"]),
}
# the imaginary industries of pack_fiction.json
PRODUCTS.update({
    "portals": (["Gate", "Jump", "Beam", "Relay", "Hop", "Warp"], ["Pass", "Link", "Pod", "Line", "Core", "Lane"]),
    "weather": (["Cloud", "Storm", "Rain", "Frost", "Gale", "Sun"], ["Seed", "Shield", "Maker", "Rig", "Veil", "Dial"]),
    "chrono": (["Chrono", "Epoch", "Aeon", "Tempo", "Moment", "Era"], ["Dial", "Vault", "Lens", "Chamber", "Loop", "Cell"]),
    "dreams": (["Lucid", "Dream", "Slumber", "Reverie", "Muse", "Haze"], ["Reel", "Pillow", "Vault", "Tide", "Loom", "Cast"]),
    "creatures": (["Ember", "Griffon", "Moon", "Frost", "Wild", "Amber"], ["Wing", "Herd", "Nest", "Saddle", "Brood", "Stable"]),
    "ocean": (["Abyss", "Pearl", "Coral", "Tide", "Deep", "Reef"], ["Tower", "Gate", "Dome", "Harvest", "Tube", "Station"]),
    "antigrav": (["Lift", "Float", "Hover", "Skim", "Aero", "Grav"], ["Plate", "Skiff", "Rail", "Cell", "Pad", "Crane"]),
    "alchemy": (["Gilded", "Rune", "Charm", "Elixir", "Spell", "Sage"], ["Alloy", "Thread", "Vial", "Lock", "Wand", "Draught"]),
})

def seeded(*parts):
    return random.Random(int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16))


def person(rng, avoid=()):
    for _ in range(50):
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        if name not in avoid:
            return name
    return name


def product(rng, sector):
    adj, noun = PRODUCTS.get(sector, PRODUCTS["tech"])
    # drug names are one word (Curamab); everything else is two (Atlas Core)
    name = f"{rng.choice(adj)}{rng.choice(noun)}" if sector == "pharma" else f"{rng.choice(adj)} {rng.choice(noun)}"
    return f"{name} {rng.randint(2, 9)}" if rng.random() < 0.4 else name


def make_persona(ticker, sector, others):
    """A company's people, flagship products and home city, deterministic per ticker. (Its suppliers, customers
    and rivals are not part of it any more: they live in relations.py.)"""
    rng = seeded("persona", ticker)
    ceo = person(rng)
    cfo = person(rng, (ceo,))
    p = {"ceo": ceo, "cfo": cfo, "product": product(rng, sector), "city": rng.choice(CITIES),
         "ex_ceos": []}
    p["product2"] = product(rng, sector)
    return p


_POSSESSIVE = re.compile(r"([A-Za-z]s)'s\b")      # "Therapeutics's" reads better as "Therapeutics'"


def slots_of(template):
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def fill(template, ctx):
    """Fill a template, or return None if it needs a slot that this company doesn't have."""
    need = slots_of(template)
    if any(ctx.get(k) in (None, "") for k in need):
        return None
    return _POSSESSIVE.sub(r"\1'", template.format(**ctx))


# ----------------------------------------------------------------------------------------------------------
# Company stories. sign: -1 bad news, +1 good. dm / dr / dd: effect on margin, revenue and debt at the next
# report; ds: change in shares outstanding (negative = buyback) for capital events. `why` names the cause in the
# earnings headline. A template is used only if every slot it mentions can be filled for the company.
# Slots: name ceo cfo product city supplier customer rival new_ceo ex_ceo pct
ISSUE_KINDS = [
    dict(key="mgmt", sign=-1, dm=-0.22, dr=-0.01, dd=0.0, why="management turmoil", texts=[
        "{ceo} faces board pressure over missed targets at {name}",
        "Activist investors demand {ceo}'s exit as {name} stumbles",
        "{name} reshuffles management after a leaked memo about {ceo}",
        "{cfo} clashes with {ceo} over {name}'s spending plans",
        "Board of {name} opens an inquiry into {ceo}'s pay and perks",
        "Senior executives quit {name} citing disputes with {ceo}",
        "{ex_ceo}, who left {name} last year, publicly criticises {ceo}'s strategy"]),
    dict(key="ceo_out", sign=-1, dm=-0.12, dr=-0.01, dd=0.0, why="a change of chief executive", new_ceo=True, texts=[
        "{ceo} steps down as chief executive of {name}; {new_ceo} takes over",
        "{name} ousts {ceo} after a string of weak quarters, naming {new_ceo} as CEO",
        "Shock at {name}: {ceo} resigns, {new_ceo} appointed to lead the company",
        "{ceo} leaves {name} with immediate effect; {cfo} praises the transition to {new_ceo}"]),
    dict(key="supply", sign=-1, dm=-0.18, dr=-0.04, dd=0.0, why="a supply-chain disruption", texts=[
        "{name} warns of delays at {supplier} that will hit {product} output",
        "{supplier} outage disrupts shipments to {name}",
        "Port congestion near {city} delays {name}'s {product} deliveries",
        "{ceo} says parts shortages will cap {name}'s {product} sales",
        "A fire at a {supplier} plant leaves {name} short of key parts",
        "{name} scrambles for alternatives after {supplier} misses deliveries",
        "Shortages force {name} to ration {product} orders"]),
    dict(key="recall", sign=-1, dm=-0.15, dr=-0.03, dd=0.06, why="a recall and regulatory probe", texts=[
        "{name} recalls {product} over safety concerns",
        "Regulators open a probe into {name}'s {product}",
        "{name} hit by class action over {product} defects",
        "{city} prosecutors investigate {name} over safety records",
        "{cfo} sets aside funds for {product} recall costs at {name}",
        "Watchdog flags problems with {product}; {name} promises fixes"]),
    dict(key="customer_loss", sign=-1, dm=-0.08, dr=-0.09, dd=0.0, why="the loss of a major customer", texts=[
        "{customer} drops {name} as a supplier",
        "{name} loses {customer}, one of its largest customers",
        "{customer} switches orders to {rival}, hurting {name}",
        "{name} warns that {customer} will cut its {product} orders"]),
    dict(key="debt", sign=-1, dm=-0.04, dr=0.0, dd=0.18, why="higher debt from its expansion", texts=[
        "{name} takes on new debt to fund {product} expansion",
        "{name} borrows heavily to build a plant in {city}",
        "Ratings agencies warn over {name}'s growing debt after its {product} push",
        "{cfo} defends {name}'s borrowing plans as debt climbs"]),
    dict(key="breach", sign=-1, dm=-0.10, dr=-0.05, dd=0.0, why="a data breach", texts=[
        "{name} reports a data breach affecting {product} customers",
        "Hackers hit {name}'s systems; {cfo} says an investigation is under way",
        "Customers review contracts after a security lapse at {name}",
        "{name} faces fines after personal data leaks from {product}"]),
    dict(key="strike", sign=-1, dm=-0.10, dr=-0.03, dd=0.0, why="a labour dispute", texts=[
        "Workers at {name}'s {city} plant walk out over pay",
        "Union rejects {name}'s offer; production of {product} slows",
        "{ceo} meets union leaders as strike at {name} enters a second week",
        "Strike in {city} leaves {name} struggling to fill {product} orders"]),
    dict(key="rival_launch", sign=-1, dm=-0.05, dr=-0.06, dd=0.0, why="a stronger rival product", texts=[
        "{rival} unveils a cheaper rival to {name}'s {product}",
        "{rival} grabs market share as {name}'s {product} lags",
        "Reviewers prefer {rival}'s new offering over {name}'s {product}",
        "{rival} poaches key engineers from {name}"]),
    dict(key="guidance", sign=-1, dm=-0.08, dr=-0.04, dd=0.0, why="a weaker outlook", texts=[
        "{name} cuts its outlook as {product} demand softens",
        "{cfo} warns {name}'s next quarter will be weaker than expected",
        "{name} trims forecasts, blaming slower orders in {city}",
        "{ceo} admits {name} will miss its own targets this year"]),
    dict(key="contract", sign=1, dm=0.10, dr=0.08, dd=0.0, why="a major contract win", texts=[
        "{name} wins a multi-year contract with {customer}",
        "{customer} signs a major order for {name}'s {product}",
        "{name} lands its biggest deal yet, says {ceo}",
        "{name} secures a long-term supply agreement for {product}",
        "{customer} picks {name} over {rival} for a landmark contract"]),
    dict(key="ceo_in", sign=1, dm=0.18, dr=0.01, dd=0.0, why="new management", new_ceo=True, texts=[
        "{name} appoints {new_ceo} as chief executive after {ceo}'s departure and unveils a turnaround plan",
        "{new_ceo} takes the helm at {name}, replacing {ceo}; investors cheer",
        "{name} names {new_ceo} as CEO and promises a fresh start",
        "Turnaround expert {new_ceo} replaces {ceo} at {name}"]),
    dict(key="launch", sign=1, dm=0.08, dr=0.06, dd=0.0, why="strong product demand", texts=[
        "{name}'s {product} sees strong early demand",
        "Reviews are glowing for {name}'s {product}",
        "Pre-orders for {name}'s {product} beat forecasts, says {cfo}",
        "{product} sells out in {city} on launch day, {name} reports",
        "{name} unveils {product2} to a warm reception"]),
    dict(key="cost_cut", sign=1, dm=0.20, dr=0.0, dd=0.0, why="cost savings", texts=[
        "{name} launches a cost-cutting programme under {ceo}",
        "{cfo} lifts margin guidance after a cost review at {name}",
        "{name} closes a costly {city} site and lifts its outlook",
        "Efficiency drive at {name} saves more than expected"]),
    dict(key="deleverage", sign=1, dm=0.03, dr=0.0, dd=-0.18, why="lower debt", texts=[
        "{name} pays down debt ahead of schedule",
        "{cfo} says {name} has cut debt after an asset sale in {city}",
        "{name} repays loans early, strengthening its balance sheet",
        "Ratings outlook improves as {name} reduces debt"]),
    dict(key="rival_stumble", sign=1, dm=0.02, dr=0.05, dd=0.0, why="gains from a rival's problems", texts=[
        "{rival} stumbles, handing {name} new customers",
        "{rival} recalls its flagship product, a boost for {name}'s {product}",
        "Customers defect from {rival} to {name}",
        "{name} gains share as {rival} struggles with delays"]),
    dict(key="expansion", sign=1, dm=0.03, dr=0.07, dd=0.05, why="expansion", texts=[
        "{name} opens a new {product} facility in {city}",
        "{name} expands into new markets with {product}",
        "{ceo} announces a hiring spree as {name} grows in {city}",
        "{name} breaks ground on a large new site near {city}"]),
    dict(key="award", sign=1, dm=0.03, dr=0.04, dd=0.0, why="industry recognition", texts=[
        "{name} wins a key patent for {product}",
        "{name}'s {product} takes the industry's top award",
        "{name} is named supplier of the year by {customer}",
        "A landmark ruling backs {name}'s patent on {product}"]),
    dict(key="outlook", sign=1, dm=0.08, dr=0.04, dd=0.0, why="a stronger outlook", texts=[
        "{name} raises its outlook as {product} sells out",
        "{ceo} tells investors orders are running ahead of plan at {name}",
        "{cfo} lifts full-year forecasts for {name}",
        "{name} says demand in {city} is stronger than expected"]),
    dict(key="buyback", sign=1, dm=0.0, dr=0.0, dd=0.0, ds=True, why="a share buyback", texts=[
        "{name} announces a buyback of {pct}% of its shares",
        "{cfo} unveils a buyback programme worth {pct}% of {name}",
        "{name} will retire {pct}% of its shares after a strong quarter",
        "Board of {name} approves a {pct}% share repurchase"]),
]
KINDS_BY_SIGN = {1: [k for k in ISSUE_KINDS if k["sign"] > 0], -1: [k for k in ISSUE_KINDS if k["sign"] < 0]}

# ----------------------------------------------------------------------------------------------------------
# Scheduled company events between earnings reports: a guidance update, an investor day, an analyst call, a product
# event. They are on the public calendar in advance (what and when, never how it will go), and the outcome is a coin
# tilted by the company's safety and the hidden mood, with the move scaled by 2 * (1 - p) like every other story, so
# the expected move is zero. `dm` / `dr` are the effect on the next report's margin and revenue (the sign is applied
# when the event fires). Slots: name ceo cfo product city.
COMPANY_EVENTS = [
    dict(key="guidance", label="Guidance update", dm=0.08, dr=0.05, why="updated guidance", texts_up=[
        "{name} raises its full-year outlook: {cfo} points to strong demand for {product}",
        "{name} lifts its forecasts after a better-than-planned stretch, says {cfo}",
        "{cfo} tells investors {name} now expects to beat its own targets this year"], texts_down=[
        "{name} lowers its full-year outlook: {cfo} cites weaker demand for {product}",
        "{name} trims its forecasts and warns of a tougher year ahead, says {cfo}",
        "{cfo} tells investors {name} will fall short of its own targets this year"]),
    dict(key="investor_day", label="Investor day", dm=0.05, dr=0.03, why="its investor day", texts_up=[
        "{name} wins over analysts at its investor day: {ceo} unveils a bold plan for {product}",
        "{ceo} lays out a five-year growth plan at {name}'s investor day and investors approve",
        "{name}'s investor day impresses: new targets for {product} beat expectations"], texts_down=[
        "{name}'s investor day disappoints: {ceo} offers few details on the plan for {product}",
        "Investors shrug at {name}'s investor day as {ceo} avoids setting new targets",
        "{ceo} stumbles through questions at {name}'s investor day and shares slip"]),
    dict(key="analyst_call", label="Analyst call", dm=0.03, dr=0.02, why="a call with analysts", texts_up=[
        "{name}'s call with analysts goes well: {cfo} reassures on margins and orders",
        "{ceo} sounds confident on {name}'s analyst call and takes questions on {product} in stride"], texts_down=[
        "{name}'s call with analysts goes badly: {cfo} struggles to explain a margin squeeze",
        "{ceo} is pressed on {product} sales during {name}'s analyst call and has few answers"]),
    dict(key="product_event", label="Product event", dm=0.02, dr=0.07, why="a product event", texts_up=[
        "{name}'s {product} event is a hit: the launch draws strong early orders",
        "{name} unveils {product} in {city} to a warm reception from reviewers"], texts_down=[
        "{name}'s {product} event falls flat: reviewers are unimpressed with the launch",
        "{name} unveils {product} in {city} but the launch is met with a shrug"]),
]
COMPANY_EVENT_KEYS = {k["key"]: k for k in COMPANY_EVENTS}

# ----------------------------------------------------------------------------------------------------------
# Cross-company stories: one template covers both directions (the "up" text is good for the target, the "down"
# text bad), and the weights say how the other company moves when the target does.
CROSS_KINDS = [
    dict(key="supply_chain", relation="customer", other_weight=0.5, why="a supplier relationship", texts_up=[
        "{other} signs a long-term supply deal with {name}",
        "{name} expands capacity so it can deliver more to {other}",
        "{name} and {other} agree on a bigger order for {product}"], texts_down=[
        "{name} halts shipments to {other} after a plant accident",
        "Outage at {name} leaves {other} short of parts",
        "{other} threatens to switch away from {name} over late deliveries"]),
    dict(key="rivalry", relation="rival", other_weight=-0.6, why="competition with a rival", texts_up=[
        "{name} wins a contract that {other} had been chasing",
        "{name} takes market share from {other} with a price cut",
        "{name}'s {product} outsells {other}'s offering in {city}"], texts_down=[
        "{other} lures a key customer away from {name}",
        "{other} unveils a rival product that outshines {name}'s {product}",
        "{other} undercuts {name} on price and wins a big deal"]),
    dict(key="partnership", relation="customer", other_weight=0.8, why="a partnership", texts_up=[
        "{name} and {other} announce a joint venture",
        "{name} to supply {other} under a landmark partnership",
        "{name} and {other} unveil a long-term alliance, says {ceo}"], texts_down=[
        "{name} and {other} scrap their partnership over a dispute",
        "Joint venture between {name} and {other} runs into trouble",
        "{other} sues {name} over a broken agreement"]),
    dict(key="acquisition", relation="rival", other_weight=-0.25, why="takeover talk", texts_up=[
        "{other} offers to buy {name} at a hefty premium",
        "Rumours swirl that {other} is preparing a bid for {name}",
        "{other} makes an approach for {name}, people familiar say"], texts_down=[
        "{other} abandons its bid for {name}",
        "Regulators move to block {other}'s takeover of {name}",
        "{name} rejects {other}'s approach as too low"]),
    dict(key="antitrust", relation="rival", other_weight=0.7, why="regulatory scrutiny", texts_up=[
        "Regulators clear {name} and {other} of wrongdoing",
        "Competition watchdog drops its case against {name} and {other}"], texts_down=[
        "Regulators open an antitrust probe into {name} and {other}",
        "Watchdog accuses {name} and {other} of price-fixing"]),
]

# ----------------------------------------------------------------------------------------------------------
# Wording variety for the sector/market templates: words that can be swapped for a synonym.
SYNONYMS = {
    "surges": ["jumps", "spikes", "leaps", "soars"], "surge": ["jump", "spike", "leap"],
    "slumps": ["tumbles", "sinks", "slides"], "falls": ["drops", "slips", "dips"], "rises": ["climbs", "gains", "edges up"],
    "announces": ["unveils", "declares", "reveals"], "wins": ["lands", "secures", "clinches"],
    "record": ["all-time high", "best-ever", "unprecedented"], "major": ["big", "significant", "large"],
    "warns": ["cautions", "signals", "flags"], "lifts": ["boosts", "raises", "propels"],
    "hit by": ["rocked by", "struck by", "shaken by"], "strong": ["robust", "solid", "firm"],
    "weak": ["soft", "feeble", "sluggish"], "new": ["fresh", "latest"], "shock": ["blow", "jolt"],
    "plans": ["intends", "prepares"], "cuts": ["slashes", "trims", "reduces"], "boost": ["lift", "fillip"],
    "crash": ["collapse", "rout"], "rally": ["surge", "advance"], "fears": ["worries", "concerns"],
    "approves": ["clears", "signs off on"], "rejects": ["turns down", "refuses"], "launches": ["rolls out", "debuts"],
}
_SYN_RE = re.compile(r"\b(" + "|".join(sorted((re.escape(k) for k in SYNONYMS), key=len, reverse=True)) + r")\b", re.I)


def paraphrase(text, rng, prob=0.5):
    """Swap some words for synonyms so the same template reads differently each time."""
    def swap(m):
        word = m.group(0)
        if rng.random() > prob:
            return word
        new = rng.choice(SYNONYMS[word.lower()])
        return new.capitalize() if word[0].isupper() else new
    return _SYN_RE.sub(swap, text)


SOURCES = ["Meme Wire", "Bourse Daily", "The Tape", "Street Ledger", "Market Pulse", "Ticker Post", "Floor Report",
           "Capital Courier"]
EARNINGS_QUOTES = {
    1: ["{ceo} called the quarter 'a step forward'", "{ceo} said results 'beat our own expectations'",
        "{cfo} said the numbers were 'ahead of plan'"],
    -1: ["{ceo} called the quarter 'disappointing'", "{ceo} admitted results 'fell short of what we wanted'",
         "{cfo} said the numbers were 'below plan'"],
    0: ["{ceo} called the quarter 'in line with expectations'", "{cfo} said results were 'steady'"],
}


# ----------------------------------------------------------------------------------------------------------
# Catalysts: rare news that moves a stock a LOT, even a calm one. Each is a two-outcome bet: the good outcome has
# probability `p` and a gain `up`; the bad outcome's loss is worked out as  -p * up / (1 - p),  so that
# p * up + (1 - p) * loss = 0 and the expected move is exactly zero. `up` is drawn from `up` (ordinary companies) or
# `up_moon` (moonshots), then capped so that the loss never takes more than 95% of the price.
CATALYSTS = [
    dict(key="trial", sectors=["pharma", "healthcare"], p=0.40, up=(0.30, 0.70), up_moon=(0.9, 1.7), weight=2.0,
         texts_up=["{name}'s Phase 3 trial hits its main goal: shares leap",
                   "{name} reports a clean sweep in its pivotal drug trial",
                   "Doctors call {name}'s trial data 'a turning point' for patients"],
         texts_down=["{name}'s lead drug fails its Phase 3 trial: shares collapse",
                     "Trial of {name}'s main treatment misses its goal",
                     "{name} halts its pivotal study after a safety scare"]),
    dict(key="approval", sectors=None, p=0.50, up=(0.25, 0.55), up_moon=(0.8, 1.6), weight=1.5,
         texts_up=["{name} wins approval for {product}", "Regulators clear {product}: a green light for {name}",
                   "{name} secures the licence it has waited years for"],
         texts_down=["Regulators reject {name}'s application for {product}", "{name} denied a licence for {product}",
                     "Approval for {product} postponed indefinitely: a blow to {name}"]),
    dict(key="buyout", sectors=None, p=0.30, up=(0.35, 0.80), up_moon=(1.0, 1.9), weight=1.0,
         texts_up=["A mystery bidder offers to buy {name} at a steep premium", "{name} receives a surprise takeover offer",
                   "A rival launches a hostile bid for {name}"],
         texts_down=["Buyout talks for {name} collapse and the shares tumble", "A suitor walks away from {name}",
                     "{name}'s takeover hopes vanish as the bidder withdraws"]),
    dict(key="audit", sectors=None, p=0.72, up=(0.15, 0.30), up_moon=(0.4, 0.9), weight=1.0,
         texts_up=["An independent audit clears {name} after a short-seller attack",
                   "{name} rebuts fraud claims and the shares snap back",
                   "Investigators find no wrongdoing at {name}"],
         texts_down=["{name} admits accounting errors; {cfo} resigns", "Regulators open a fraud probe into {name}",
                     "A short-seller report exposes problems at {name}: shares plunge"]),
    dict(key="contract", sectors=["defense", "industrials", "space", "tech", "energy", "utilities", "antigrav", "ocean", "portals"],
         p=0.45, up=(0.30, 0.65), up_moon=(0.9, 1.7), weight=1.0,
         texts_up=["{name} lands a mega-contract that doubles its order book", "{name} wins the biggest deal in its history",
                   "A government picks {name} for a landmark project"],
         texts_down=["{name} loses its biggest customer", "The contract that {name} was counting on goes to a rival",
                     "{name}'s flagship project is cancelled"]),
    dict(key="test", sectors=["space", "antigrav", "portals", "chrono", "ocean", "creatures", "weather", "alchemy", "tech", "energy"],
         p=0.40, up=(0.30, 0.70), up_moon=(0.9, 1.7), weight=1.5,
         texts_up=["{name}'s prototype works first time: investors cheer", "{name} completes a flawless full-scale test",
                   "A long-awaited demonstration by {name} exceeds every target"],
         texts_down=["{name}'s prototype fails in front of investors", "A full-scale test ends in disaster for {name}",
                     "{name} postpones its big demonstration after a failed rehearsal"]),
    dict(key="hype", sectors=["media", "retail", "crypto", "meme", "dreams", "consumer"], p=0.45, up=(0.25, 0.55),
         up_moon=(0.8, 1.5), weight=1.0,
         texts_up=["{name} goes viral overnight", "Social media piles into {name}", "A celebrity endorsement sends {name} soaring"],
         texts_down=["Backlash hits {name} as users abandon it", "{name} caught in a viral scandal",
                     "A hyped launch by {name} flops"]),
]


# ----------------------------------------------------------------------------------------------------------
# Industry-wide shocks: rare news that hits a whole sector at once (a ban, a collapse in demand, a probe, a
# disruptive technology), so an industry can crash while the wider market rises. Each is a fair two-outcome bet like
# a catalyst: the bad outcome (the "failure", drawn from `bad`) has probability 1 - p and the good one (a relief rally
# or a boom) has probability p and a gain of  (1 - p) * bad / p,  so  p * up + (1 - p) * (-bad) = 0  exactly.
# Every company in the sector moves the same way, each by that size times its own exposure (0.7 to 1.3, drawn
# without regard to the direction). The sizes are modest on purpose (a typical sector move is 5 to 10%, the rarest
# about 19%): an earlier version moved whole sectors 20 to 30% and 49% at the extreme, which was far too much.
INDUSTRY_SHOCKS = [
    dict(key="rules", p=0.45, bad=(0.05, 0.12), weight=2.0,
         texts_down=["Regulators unveil sweeping new rules for the {sector} sector: shares slump across the board",
                     "A tough new law lands on every {sector} company, and the whole sector sells off",
                     "Lawmakers vote to curb the {sector} industry: investors rush for the exits"],
         texts_up=["Regulators scrap burdensome rules for the {sector} sector: shares rally across the board",
                   "A new law clears the way for {sector} companies, and the whole sector jumps",
                   "Lawmakers back the {sector} industry with a generous package: shares surge"]),
    dict(key="demand", p=0.50, bad=(0.04, 0.10), weight=2.0,
         texts_down=["Demand for {sector} products collapses and the whole sector sells off",
                     "Customers abandon the {sector} industry: orders dry up across the board",
                     "A sudden slump in orders hammers every {sector} company"],
         texts_up=["Demand for {sector} products surges and the whole sector rallies",
                   "Customers pile into the {sector} industry: order books fill across the board",
                   "A rush of new orders lifts every {sector} company"]),
    dict(key="costs", p=0.50, bad=(0.04, 0.09), weight=1.0,
         texts_down=["A cost spike squeezes margins across the {sector} sector: shares fall together",
                     "A supply shortage hits the whole {sector} industry and profits are expected to suffer"],
         texts_up=["Costs plunge for {sector} companies: margins are expected to widen across the sector",
                   "A supply glut eases the squeeze on the whole {sector} industry and shares rise together"]),
    dict(key="probe", p=0.55, bad=(0.05, 0.13), weight=1.0,
         texts_down=["An industry-wide investigation shakes the {sector} sector: every company is named",
                     "Regulators open a sweeping probe into {sector} firms and the whole sector tumbles"],
         texts_up=["The industry-wide probe into {sector} firms ends with no charges: the sector rebounds",
                   "Investigators clear the {sector} industry and shares jump across the board"]),
    dict(key="disrupt", p=0.45, bad=(0.05, 0.12), weight=1.0,
         texts_down=["A breakthrough technology threatens to make the {sector} business obsolete: the sector sinks",
                     "A start-up shows a cheaper way to do what the whole {sector} industry does, and shares crash"],
         texts_up=["A breakthrough opens a vast new market for the {sector} industry: shares soar across the sector",
                   "A new discovery lowers costs for every {sector} company and the sector jumps"]),
    dict(key="credit", p=0.50, bad=(0.04, 0.09), weight=1.0,
         texts_down=["Lenders pull back from the {sector} sector: funding dries up and shares slide together",
                     "Banks cut credit lines to {sector} companies and the whole sector slumps"],
         texts_up=["Cheap funding floods back into the {sector} sector and shares rise together",
                   "Banks open the credit taps for {sector} companies and the sector rallies"]),
    dict(key="trade", p=0.50, bad=(0.04, 0.09), weight=1.0,
         texts_down=["New tariffs hit the {sector} sector: every exporter in the industry falls",
                     "A trade dispute closes key markets to {sector} companies and shares fall across the board"],
         texts_up=["A trade deal opens new markets to {sector} companies: the whole sector rises",
                   "Tariffs on the {sector} industry are lifted and shares jump together"]),
]


# ----------------------------------------------------------------------------------------------------------
# Moonshots: tiny, pre-revenue companies that join the market over time. They are extremely volatile (hundreds of
# per cent in a day is normal), they carry little liquidity, and they go bankrupt easily; the rare few that survive
# can multiply. Everything is generated, so there is always a fresh one to look at.
MOON_SYLLABLES = ["Nu", "Cy", "Ze", "Ae", "Lu", "Vy", "Or", "Ke", "Ma", "Xy", "Qu", "He", "Stra", "No", "Ar", "Ki", "Ta",
                  "Ve", "Ly", "Dro", "Fi", "Sy", "Ba", "Re", "Ono", "Zu", "Mi", "Pha", "Gen", "Tri", "Ul", "Vo"]
MOON_ENDS = ["vora", "tex", "lyn", "gen", "ora", "dyne", "ix", "ara", "pho", "mera", "tron", "vex", "sia", "nis", "lux"]
MOON_KINDS = [
    dict(key="biotech", sector="pharma", weight=5, suffixes=["Therapeutics", "Biosciences", "Pharma", "Genomics", "Oncology"],
         descs=["Developing a one-shot gene therapy for {condition}. Pre-revenue: one trial result decides everything.",
                "Testing an experimental pill for {condition}. No products yet; the whole value is one clinical trial.",
                "Building a vaccine for {condition}. Pre-revenue, with one late-stage study ahead.",
                "Growing replacement tissue for patients with {condition}. Years from a product, one breakthrough from a fortune."]),
    dict(key="space", sector="space", weight=2, suffixes=["Orbital", "Aerospace", "Launch", "Space"],
         descs=["Building a tiny rocket that it says will cut launch costs by 90%. One test flight away from the moon, or the scrapyard.",
                "Designing a lunar lander for the first private mission to {place}. Pre-revenue."]),
    dict(key="fusion", sector="energy", weight=2, suffixes=["Fusion", "Energy", "Power"],
         descs=["Promising a working fusion reactor 'within five years'. Pre-revenue, with a very expensive prototype."]),
    dict(key="quantum", sector="tech", weight=2, suffixes=["Quantum", "Labs", "Systems"],
         descs=["Building a quantum computer that it says will crack today's hardest problems. No customers yet.",
                "Developing a chip that runs AI a thousand times faster. Prototype stage."]),
    dict(key="crypto", sector="crypto", weight=1, suffixes=["Protocol", "Labs", "Chain"],
         descs=["Launching a new digital currency backed by 'something very clever'. Pre-revenue and pre-everything."]),
    dict(key="portals", sector="portals", weight=1, suffixes=["Gate", "Transit", "Jump"],
         descs=["Racing to build the first long-range teleport gate. Pre-revenue, one calibration away from the future."]),
    dict(key="chrono", sector="chrono", weight=1, suffixes=["Chrono", "Temporal", "Time"],
         descs=["Prototype time-dilation chamber in a garage lab. One working demonstration would change everything."]),
    dict(key="antigrav", sector="antigrav", weight=1, suffixes=["Lift", "Grav", "Hover"],
         descs=["Prototype antigravity plate that floats a person. Needs one more funding round and one more miracle."]),
]
CONDITIONS = ["a rare blood disorder", "type 1 diabetes", "a deadly lung disease", "inherited blindness", "Alzheimer's",
              "a common cancer", "chronic pain", "a childhood nerve disease", "heart failure", "a stubborn infection"]
PLACES = ["the Moon", "Mars orbit", "an asteroid", "the lunar south pole"]


def make_moonshot(rng, taken, sectors=None):
    """A new moonshot company config (a content-pack style dict, with its market profile merged in).
    `taken` is the set of tickers already used (listed or delisted); `sectors` limits it to industries that exist."""
    kinds = [k for k in MOON_KINDS if sectors is None or k["sector"] in sectors] or MOON_KINDS
    kind = rng.choices(kinds, weights=[k["weight"] for k in kinds])[0]
    for _ in range(200):
        stem = rng.choice(MOON_SYLLABLES) + rng.choice(MOON_ENDS)
        name = f"{stem} {rng.choice(kind['suffixes'])}"
        ticker = (stem[:3] + stem[-1]).upper()
        if len(ticker) == 4 and ticker.isalpha() and ticker not in taken:
            break
        ticker = "".join(rng.choice(string.ascii_uppercase) for _ in range(4))
        if ticker not in taken:
            break
    price = round(rng.uniform(0.6, 14.0), 2)
    cap = round(rng.uniform(0.004, 0.06), 4)               # billions of MB: small
    desc = rng.choice(kind["descs"]).format(condition=rng.choice(CONDITIONS), place=rng.choice(PLACES))
    return {"ticker": ticker, "name": name, "sector": kind["sector"], "beta": round(rng.uniform(2.5, 4.5), 2),
            "vol": round(rng.uniform(2.6, 5.5), 2), "sens": round(rng.uniform(1.4, 2.2), 2),
            "depth": int(rng.choice([2500, 3000, 3500, 4000, 5000])), "traits": ["moonshot"], "desc": desc,
            "initial_price": price, "market_cap": cap, "shares_outstanding": round(cap / price, 5), "revenue": 0.0,
            "margin": 0.0, "cash": round(cap * rng.uniform(0.2, 0.6), 4), "debt": 0.0, "dividend_yield": 0.0,
            "generated": True, "kind": kind["key"]}

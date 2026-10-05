"""Who supplies whom, who buys from whom and who competes with whom.

These links stay inside the engine: players never see them. They decide which companies appear together in
two-company stories, which names a company story uses for "a supplier", "a customer" or "a rival", and how a
move in one company spills over to its partners and rivals (a customer doing well helps its suppliers, a rival
doing well hurts you). Every spillover is a fixed fraction of a zero-mean move, so it has no expected effect.

The links for the companies that ship with the game are written by hand from what each company does, so they make
sense (a drug maker supplies hospitals, an oil company supplies airlines and power utilities, a chip foundry
supplies chip designers) and they are sparse: plenty of companies have no rival, or no customer, as in real life.
A company added later is linked by sector rules instead (a drug company can supply a hospital chain, a chip
designer can supply a carmaker), each rule with a probability, using a fixed pseudo-random draw for that pair of
companies, up to three links of each kind.

Adding a company links it into the companies that are already there, and each of those gets the matching link on
its side (a new drug company that supplies a hospital chain becomes a supplier of that hospital chain). Removing a
company (a bankruptcy) removes its links from everyone. The draws depend only on the two tickers, and a newcomer
never rearranges existing links.
"""
import hashlib
import math
import re

MAX_LINKS = 3          # a newcomer's rule-based links stop at this many suppliers, customers and rivals
MAX_TOTAL = 8          # and no company ever has more than this many of one kind

# The relationships between the companies that ship with the game, written by hand from what each one does (a drug
# maker supplies a hospital chain, an oil producer supplies an airline, a chip foundry supplies a chip designer).
# "A: B C" means A supplies B and C.
_SUPPLIES = """
NVXA: CLDR BYTE CRLN VLTR ROBO HSFG AEGX DRON
MEMR: CLDR BYTE
NNCF: NVXA MEMR VTDV
TRNC: NNCF CLST
LITH: CLST VLTR
CLST: VLTR CRLN IRHL SLRG
GRWK: CRLN IRHL VLTR TBMC
ATND: CRLN VLTR HAIL
SVSL: CLDR BYTE
CLDR: DTHV STFG CHBX DDIA
BYTE: DTHV ATND
CYBR: BNKR PNCL
DTHV: MGMT ADSP
RBVS: ROBO ATND CLSC DRON
OILX: SKYJ BLFL FRET
TRDL: OILX
KRKN: OILX
NUCL: GRID SVSL
SLRG: GRID
WIND: GRID
GALE: WIND GRID
TIDL: GRID
GRVN: GRID
SUNB: SLRG
GRID: HHRS SVSL HSFG
PHNX: HHRS
HYDR: IRHL FRET
ROBO: VLTR CRLN NVXA
FRET: MGMT VBRN CLCK
CRST: FRET CLCK
SAND: STBR KSBH ABYS
STNS: STBR LEVT
STBR: SBMR
LFTR: STBR KSBH
FIBR: SVSL CLDR STFG
LPDR: STWB ORSW ZNTH RDHB LNMN SUNB
STWB: ASLN
ASLN: FERT GRAI
AERO: SKYJ
GRAI: MUNC SNKW BRWH
FERT: GRAI
CLSD: GRAI SNWL
KELP: MUNC ENCH
MUNC: MGMT FRBK VBRN
SNKW: MGMT FRBK
BRWH: MGMT
UNCR: FRBK
YETI: FRBK
RWND: MUNC IRHL
ZIPD: CLCK
IRHL: FRET ZIPD
HOMR: MGMT CLCK
ENCH: TRLT QKST
GLDM: MSVR
CURA: CRXP MRHS DDIA
HLXB: MRHS
ONCX: MRHS
GNSP: MRHS
VTDV: MRHS
ELXR: CRXP
WAND: MRHS NNCF
RUNE: BNKR SKOF TMVT
SKOF: BNKR
PLZP: MGMT TRLT QKST
SLVR: STFG
ADSP: CHBX DLGM ECHN
SLPN: DRMW NGHT LCDL HNST
DRMW: STFG
QNTR: PHSJ GTWY BMLN VNSH
BMLN: CLCK
GTWY: PRTL
STRM: SFHB GMHT
EPCH: SKIP CHRN
TMVT: BNKR
PSTL: DLGM
CHRN: BNKR
BLKL: BNKR FRET
KYSF: CNHR
STDY: CNHR
HSFG: CNHR
TPPY: CLCK ZIPD
ANCH: KSBH
BNKR: HHRS SKOF
"""
# "A B" means A and B compete.
_RIVALS = """
BYTE RBVS
BYTE QLEF
CYBR RUNE
AEGX DRON
SKYJ GRFN
SKYJ SKIP
SKYJ SBMR
MOON LPDR
STWB TWRX
TWRX FIBR
OILX HYDR
PHNX BLFL
LITH TRNC
SAND STNS
LNMN TRNC
EMBR LFTR
GRFN FLTR
FRET PHSJ
FRET FLTR
VLTR CRLN
VLTR LEVT
CRLN LEVT
HAIL AIRY
HAIL GTWY
MGMT VBRN
MGMT FRBK
MGMT CLCK
HNST HOMR
QKST MSVR
ZIPD BMLN
MUNC SNKW
MUNC UNCR
KELP FERT
HLXB ONCX
HLXB CURA
ONCX GNSP
CURA ELXR
LCDL ERSE
MMBK ERSE
BNKR ANCH
BNKR CRED
CRED QKLN
TPPY CRED
LNLP QKLN
SFHB EPCH
STFG SDTD
ECHN SDTD
CHBX PUPZ
DOGO PUPZ
GMHT PRTL
GMHT PRLG
PRLG PRTL
ABYS KSBH
"""
CURATED_SUPPLY = [(a.strip(), b) for line in _SUPPLIES.strip().splitlines() for a, bs in [line.split(":")] for b in bs.split()]
CURATED_RIVALS = [tuple(line.split()) for line in _RIVALS.strip().splitlines()]
CURATED = {t for pair in CURATED_SUPPLY + CURATED_RIVALS for t in pair}

# Companies that are not in the lists above (added later, from a content pack) are linked by these sector rules.
# (supplier sector, customer sector, probability that a given pair is linked, and optionally a pattern the customer's
# name or description must match, so that a drug company supplies hospitals and pharmacies but not dentists)
SUPPLY = [
    # materials, energy and farming feed other industries
    ("materials", "industrials", .35), ("materials", "autos", .30, r"car|vehicle|motor|battery|batteries|truck"),
    ("materials", "tech", .25, r"chip|memory|circuit|semiconductor"), ("materials", "realestate", .30, r"build|home|construction"),
    ("materials", "space", .25), ("materials", "energy", .20),
    ("energy", "utilities", .35), ("energy", "airlines", .45), ("energy", "industrials", .25),
    ("agriculture", "consumer", .35, r"food|beverage|snack|drink"), ("agriculture", "retail", .25, r"grocer|supermarket|mart"),
    # industry and technology
    ("industrials", "autos", .30), ("industrials", "defense", .45), ("industrials", "space", .30),
    ("industrials", "realestate", .25, r"build|home|construction"), ("industrials", "energy", .25),
    ("industrials", "airlines", .30), ("industrials", "agriculture", .25), ("industrials", "utilities", .25),
    ("tech", "tech", .12), ("tech", "autos", .30), ("tech", "finance", .20), ("tech", "media", .25),
    ("tech", "healthcare", .25, r"hospital|medical|doctor|diagnostic|clinic"),
    ("tech", "retail", .15, r"online|marketplace|click"), ("tech", "telecom", .30), ("tech", "defense", .30),
    ("tech", "space", .25), ("tech", "crypto", .25), ("tech", "industrials", .20),
    # health, media, telecom, space and defence
    ("pharma", "healthcare", .50, r"hospital|clinic|pharmac|doctor|diagnostic"),
    ("telecom", "media", .40), ("telecom", "tech", .20), ("media", "retail", .30, r"online|marketplace|click|mart"),
    ("space", "defense", .35), ("space", "telecom", .35), ("defense", "space", .25),
    # consumer-facing, financial and property
    ("consumer", "retail", .40), ("finance", "realestate", .30), ("finance", "autos", .15), ("finance", "crypto", .20),
    ("crypto", "finance", .25), ("realestate", "retail", .30, r"store|mart|fashion|outdoor|furnishing"),
    ("utilities", "industrials", .25), ("utilities", "realestate", .30),
    # the imaginary industries
    ("portals", "retail", .35), ("portals", "industrials", .25), ("weather", "agriculture", .40),
    ("weather", "utilities", .30), ("chrono", "finance", .30), ("dreams", "media", .35),
    ("creatures", "retail", .30, r"grocer|supermarket|mart"), ("ocean", "realestate", .30),
    ("ocean", "utilities", .25), ("antigrav", "industrials", .25), ("alchemy", "retail", .30),
]
SUPPLY_P = {(r[0], r[1]): (r[2], re.compile(r[3]) if len(r) > 3 else None) for r in SUPPLY}

RIVAL_SAME_SECTOR = .55            # chance that two companies in the same sector compete directly
RIVAL_CROSS = {frozenset(("airlines", "portals")): .45,      # teleporting to work instead of flying there
               frozenset(("autos", "antigrav")): .45}         # hover-cars instead of cars

# how a move in one company spills over to its partners, as a fraction of that move
SPILL_TO_CUSTOMER = 0.10           # a supplier's news reaches the companies it supplies
SPILL_TO_SUPPLIER = 0.15           # a customer doing well means more orders for its suppliers
SPILL_TO_RIVAL = -0.12             # a rival doing well takes business from you


def _u(*parts):
    """A fixed pseudo-random number in [0, 1) that depends only on its arguments."""
    h = hashlib.sha256("|".join(parts).encode()).digest()
    return int.from_bytes(h[:6], "big") / 2 ** 48


class Relations:
    def __init__(self):
        self.sector = {}                 # ticker -> sector, for every company in the graph
        self.text = {}                   # ticker -> its name and description in lower case (for the rule filters)
        self.suppliers_of = {}           # ticker -> set of tickers that supply it
        self.customers_of = {}           # ticker -> set of tickers it supplies
        self.rivals_of = {}              # ticker -> set of tickers that compete with it

    # ---- reading
    def suppliers(self, ticker):
        return sorted(self.suppliers_of.get(ticker, ()))

    def customers(self, ticker):
        return sorted(self.customers_of.get(ticker, ()))

    def rivals(self, ticker):
        return sorted(self.rivals_of.get(ticker, ()))

    def partners(self, ticker, kind):
        """`kind` is 'supplier', 'customer' or 'rival'."""
        return {"supplier": self.suppliers, "customer": self.customers, "rival": self.rivals}[kind](ticker)

    def __contains__(self, ticker):
        return ticker in self.sector

    # ---- adding and removing companies
    def add(self, companies):
        """Link new companies into the graph. `companies` is a list of (ticker, sector) or (ticker, sector, text)
        where the text is the company's name and description; ones already in the graph are ignored. Existing links never change; each new company gets links to the companies already there and
        to the other newcomers, and those get the matching link back."""
        info = {c[0]: (c[1], (c[2] if len(c) > 2 else "").lower()) for c in companies}
        new = sorted(t for t in info if t not in self.sector)
        if not new:
            return
        for t in new:
            self.sector[t], self.text[t] = info[t]
            self.suppliers_of[t], self.customers_of[t], self.rivals_of[t] = set(), set(), set()
        fresh = set(new)
        for a, b in CURATED_SUPPLY:                      # the hand-written links, for any pair that is now present
            if a in self.sector and b in self.sector and (a in fresh or b in fresh):
                self.customers_of[a].add(b)
                self.suppliers_of[b].add(a)
        for a, b in CURATED_RIVALS:
            if a in self.sector and b in self.sector and (a in fresh or b in fresh):
                self.rivals_of[a].add(b)
                self.rivals_of[b].add(a)
        by_sector = {}
        for t in sorted(self.sector):
            by_sector.setdefault(self.sector[t], []).append(t)
        found = []                       # (random rank, kind, a, b): a supplies b, or a and b compete
        for (ss, cs), (p, pattern) in SUPPLY_P.items():
            for a in by_sector.get(ss, ()):
                for b in by_sector.get(cs, ()):
                    if (a != b and (a in fresh or b in fresh) and not (a in CURATED and b in CURATED)
                            and (pattern is None or pattern.search(self.text.get(b, "")))
                            and _u("supply", a, b) < p):
                        found.append((_u("rank", a, b), "supply", a, b))
        for ss, members in by_sector.items():
            for i, a in enumerate(members):
                for b in members[i + 1:]:
                    if ((a in fresh or b in fresh) and not (a in CURATED and b in CURATED)
                            and _u("rival", a, b) < RIVAL_SAME_SECTOR):
                        found.append((_u("rank", a, b), "rival", a, b))
        for pair, p in RIVAL_CROSS.items():
            s1, s2 = sorted(pair)
            for a in by_sector.get(s1, ()):
                for b in by_sector.get(s2, ()):
                    if ((a in fresh or b in fresh) and not (a in CURATED and b in CURATED)
                            and _u("rival", a, b) < p):
                        found.append((_u("rank", a, b), "rival", a, b))
        found.sort()                     # a random order, the same every time, so no company is favoured
        def room(node, links):
            return len(links[node]) < (MAX_LINKS if node in fresh else MAX_TOTAL)

        for _, kind, a, b in found:
            if kind == "supply":
                if room(a, self.customers_of) and room(b, self.suppliers_of) and b not in self.rivals_of[a]:
                    self.customers_of[a].add(b)
                    self.suppliers_of[b].add(a)
            elif (room(a, self.rivals_of) and room(b, self.rivals_of)
                  and b not in self.customers_of[a] and b not in self.suppliers_of[a]):
                self.rivals_of[a].add(b)
                self.rivals_of[b].add(a)

    def remove(self, ticker):
        """A company is gone (it went bankrupt): everyone loses the link to it."""
        if ticker not in self.sector:
            return
        for other in self.suppliers_of.pop(ticker, ()):
            self.customers_of[other].discard(ticker)
        for other in self.customers_of.pop(ticker, ()):
            self.suppliers_of[other].discard(ticker)
        for other in self.rivals_of.pop(ticker, ()):
            self.rivals_of[other].discard(ticker)
        del self.sector[ticker]
        self.text.pop(ticker, None)

    # ---- spillover
    def spill(self, returns, scale=1.0):
        """The extra move each company gets from the moves of its partners and rivals this tick. A company with
        several suppliers (or customers, or rivals) gets the average push of them, scaled by the square root of
        how many there are, so a company with many links is not made more volatile than one with a few."""
        suppliers_moved, customers_moved, rivals_moved = {}, {}, {}
        for tk, r in returns.items():
            if not r or tk not in self.sector:
                continue
            for c in self.customers_of[tk]:
                suppliers_moved[c] = suppliers_moved.get(c, 0.0) + r
            for s in self.suppliers_of[tk]:
                customers_moved[s] = customers_moved.get(s, 0.0) + r
            for v in self.rivals_of[tk]:
                rivals_moved[v] = rivals_moved.get(v, 0.0) + r
        out = {}
        for tk, moved in suppliers_moved.items():      # tk's suppliers moved: the news reaches the company they supply
            out[tk] = out.get(tk, 0.0) + SPILL_TO_CUSTOMER * scale * moved / math.sqrt(len(self.suppliers_of[tk]))
        for tk, moved in customers_moved.items():      # tk's customers moved: more or fewer orders for tk
            out[tk] = out.get(tk, 0.0) + SPILL_TO_SUPPLIER * scale * moved / math.sqrt(len(self.customers_of[tk]))
        for tk, moved in rivals_moved.items():         # tk's rivals moved: business shifts the other way
            out[tk] = out.get(tk, 0.0) + SPILL_TO_RIVAL * scale * moved / math.sqrt(len(self.rivals_of[tk]))
        return out

    # ---- saving
    def to_json(self):
        return {"sector": dict(self.sector), "text": dict(self.text),
                "supply": sorted([a, b] for a, bs in self.customers_of.items() for b in bs),
                "rival": sorted([a, b] for a, bs in self.rivals_of.items() for b in bs if a < b)}

    @classmethod
    def from_json(cls, d):
        r = cls()
        r.sector = dict(d.get("sector", {}))
        r.text = {k: v for k, v in d.get("text", {}).items() if k in r.sector}
        for t in r.sector:
            r.suppliers_of[t], r.customers_of[t], r.rivals_of[t] = set(), set(), set()
        for a, b in d.get("supply", []):
            if a in r.sector and b in r.sector:
                r.customers_of[a].add(b)
                r.suppliers_of[b].add(a)
        for a, b in d.get("rival", []):
            if a in r.sector and b in r.sector:
                r.rivals_of[a].add(b)
                r.rivals_of[b].add(a)
        return r

"""First-round pick ownership by draft year, for teams whose own pick was traded or protected.

Kinds:
  ("owed",)            pick belongs to another team: worth 0 to the original team
  ("protected", k)     team keeps the pick only if it lands at k or better
  ("rollover", k)      kept if at k or better; otherwise conveyed but the team keeps its next first
                       (valued at the average first-round pick), e.g. MIA 2027 -> 2028 unprotected
  ("lesser", partner)  team ends up with the less favorable of its own and partner's pick
                       (swap rights held by partner, or "more favorable of" deals going out)
  ("more", partner, k) team keeps the more favorable of its own and partner's pick; it also keeps the
                       less favorable one if that lands at k or better
Pair deals are valued exactly: each simulated season draws one lottery realization (sim.PickValues pools).

This is a selected own-pick/linked-rights map, not a complete portfolio ledger. Teams not listed are
assumed to own their pick; absence is not independent evidence of ownership. The two high-playoff-
probability omissions corrected below still matter for originating-first valuations. Incoming assets,
cash and second-round compensation are outside this metric unless explicitly modeled.
"""

OWNERSHIP = {
    # 2024 draft (2023-24 season). HoopsRumors, "Checking in on traded 2024 first-round picks" (March 2024).
    2024: {
        "WAS": ("protected", 12), "DET": ("protected", 18), "CHA": ("protected", 14),
        "POR": ("protected", 14), "TOR": ("protected", 6), "HOU": ("protected", 4),
        "UTA": ("protected", 10), "BKN": ("owed",),
        "SAC": ("protected", 14), "GSW": ("protected", 4), "IND": ("protected", 3), "DAL": ("protected", 10),
        # Unprotected originating first; NBA's dated December 2023 trade review:
        # https://www.nba.com/news/clippers-thunder-paul-george-shai-gilgeous-alexander-trade-review
        "LAC": ("owed",),
    },
    # 2025 draft (2024-25 season). CBS Sports, 2025 draft order and lottery odds; HoopsRumors, "Traded
    # first-round picks for 2025 NBA draft"; each checked against who actually picked (Draft Pick History).
    2025: {
        "PHI": ("protected", 6), "SAC": ("protected", 12), "PHX": ("owed",), "ATL": ("owed",),
        "POR": ("protected", 14), "MIA": ("protected", 14), "GSW": ("protected", 10),
        "LAC": ("lesser", "OKC"), "MIN": ("owed",), "UTA": ("protected", 10), "WAS": ("protected", 10),
    },
    # 2026 draft (2025-26 season). RotoWire 2026 lottery "what's at stake"; Third Apron (WAS);
    # 2026 draft order (ATL swap with SAS, ORL owed, POR top-14 to CHI, MIL keeps lesser of MIL/NOP).
    2026: {
        "IND": ("protected", 4), "UTA": ("protected", 8), "WAS": ("protected", 8),
        "NOP": ("owed",), "LAC": ("owed",), "ORL": ("owed",), "POR": ("protected", 14),
        "ATL": ("lesser", "SAS"), "MIL": ("lesser", "NOP"),
        # Current first only; fallback second/cash and downstream recipient pools are not valued here.
        # https://www.nba.com/news/oklahoma-city-acquires-chris-paul-houston-rockets-official-release
        "HOU": ("protected", 4),
    },
    # 2027 draft (2026-27 season). Third Apron, "NBA 3-2-1 lottery reform: 2027 draft".
    2027: {
        "MIL": ("owed",), "PHX": ("owed",), "ATL": ("owed",), "MIN": ("owed",), "CLE": ("owed",),
        "LAL": ("owed",), "NYK": ("owed",), "DEN": ("owed",), "SAS": ("owed",),
        "BKN": ("lesser", "HOU"), "LAC": ("lesser", "OKC"),
        # NOP holds MIL's 2027 first; ATL gets the less favorable of NOP/MIL, top-4 protected (Murray trade)
        "NOP": ("more", "MIL", 4),
        "DAL": ("protected", 2), "MIA": ("rollover", 14),
    },
}


def label(spec) -> str:
    if spec is None:
        return "yes"
    kind = spec[0]
    if kind == "owed":
        return "no"
    return {"protected": f"top-{spec[1]} protected", "rollover": f"top-{spec[1]} protected, rolls to 2028",
            "lesser": f"less favorable of own and {spec[1]}",
            "more": f"more favorable of own and {spec[1]}"}[kind]

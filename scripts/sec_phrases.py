"""
Small, auditable phrase allowlist + token hygiene helpers.

Goal: reduce "tokenization noise" (titles/names/boilerplate fragments) and
recover a handful of SEC-meaningful multiword phrases that executives recognize.

Keep this list intentionally short: it's better to be defensible than exhaustive.
"""

# Phrases (2-4 words). Store in lowercase.
SEC_PHRASE_ALLOWLIST: list[str] = [
    "artificial intelligence",
    "machine learning",
    "data security",
    "cyber security",
    "cybersecurity incident",
    "information security",
    "data privacy",
    "privacy regulation",
    "regulatory compliance",
    "government regulation",
    "trade restrictions",
    "export controls",
    "interest rates",
    "foreign exchange",
    "inflationary pressures",
    "supply chain",
    "supply disruption",
    "customer demand",
    "competitive landscape",
    "market share",
    "pricing pressure",
    "gross margin",
    "operating margin",
    "credit risk",
    "liquidity risk",
    "going concern",
    "material weakness",
    "internal controls",
    "financial reporting",
    "intellectual property",
    "patent infringement",
    "product liability",
    "class action",
    "litigation matters",
    "geopolitical tensions",
    "political instability",
    "climate change",
    "environmental regulation",
    "human capital",
    "talent retention",
    "labor shortages",
    "business continuity",
    "disaster recovery",
]

# Tokens we typically do not want in term shifts
HONORIFICS: set[str] = {
    "mr",
    "mrs",
    "ms",
    "miss",
    "dr",
    "prof",
    "sir",
    "madam",
}

# Common suffixes / corporate abbreviations that tend to create noise
NAME_SUFFIXES: set[str] = {
    "jr",
    "sr",
    "ii",
    "iii",
    "iv",
    "phd",
    "md",
}

# Boilerplate-y tokens that frequently surface as false positives in 10-K prose
NOISE_TOKENS: set[str] = {
    "inc",
    "corp",
    "ltd",
    "co",
    "company",
    "u",
    "s",
    "us",
    "usa",
}

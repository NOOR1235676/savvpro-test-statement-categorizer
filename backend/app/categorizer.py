import re
from dataclasses import dataclass

REVIEW_THRESHOLD = 0.75


@dataclass
class Txn:
    date: str
    description: str
    amount: float  # negative = money out, positive = money in


@dataclass
class Result:
    category: str
    confidence: float
    reason: str
    needs_review: bool


RULES = {
    "Software": ["ADOBE", "GITHUB", "FIGMA", "NOTION", "SLACK", "AWS", "DIGITALOCEAN", "OPENAI"],
    "Travel": ["UBER", "CAREEM", "PIA", "AIRBLUE", "BOLT"],
    "Meals": ["KFC", "MCDONALD", "STARBUCKS", "FOODPANDA", "CAFE"],
    "Office": ["DARAZ", "STAPLES", "OFFICE DEPOT"],
    "Fees": ["BANK FEE", "SERVICE CHARGE", "ANNUAL FEE"],
}
TRANSFER_WORDS = ["TRANSFER TO", "TRANSFER FROM", "OWN ACCOUNT", "SAVINGS", "CARD PAYMENT"]
INCOME_WORDS = ["PAYONEER", "FIVERR", "UPWORK", "INVOICE", "SALARY"]
REFUND_WORDS = ["REFUND", "REVERSAL", "CHARGEBACK"]


def normalize(desc: str) -> str:
    d = desc.upper()
    d = re.sub(r"[*#]", " ", d)
    d = re.sub(r"\d{3,}", " ", d)  # reference numbers
    return re.sub(r"\s+", " ", d).strip()


def merchant_key(desc: str) -> str:
    return " ".join(normalize(desc).split()[:2])


def _has(word: str, text: str) -> bool:
    # short keywords must match as whole words (PIA must not match PIANO)
    pattern = rf"\b{re.escape(word)}\b" if len(word) <= 4 else rf"\b{re.escape(word)}"
    return re.search(pattern, text) is not None


def categorize(txn: Txn, memory: dict[str, str] | None = None) -> Result:
    d = normalize(txn.description)

    # 1. user corrections win (learned memory)
    key = merchant_key(txn.description)
    if memory and key in memory:
        return Result(memory[key], 1.0, "Learned from your earlier correction", False)

    # 2. transfers are not spending
    if any(w in d for w in TRANSFER_WORDS):
        return Result("Transfer", 0.95, "Internal transfer, excluded from spending", False)

    # 3. refunds: money back, NOT income
    if txn.amount > 0 and any(w in d for w in REFUND_WORDS):
        return Result("Refund", 0.9, "Refund keyword on a credit", False)

    # 4. income
    if txn.amount > 0:
        if any(_has(w, d) for w in INCOME_WORDS):
            return Result("Income", 0.9, "Known income source", False)
        return Result("Needs Review", 0.4, "Unknown credit: could be income or refund", True)

    # 5. spending rules
    hits = {c: [k for k in kws if _has(k, d)] for c, kws in RULES.items()}
    hits = {c: h for c, h in hits.items() if h}
    if len(hits) == 1:
        cat, kw = next(iter(hits.items()))
        return Result(cat, 0.9, f"Matched '{kw[0]}'", False)
    if len(hits) > 1:
        return Result("Needs Review", 0.5, f"Ambiguous: matches {', '.join(hits)}", True)

    return Result("Needs Review", 0.2, "No rule matched", True)

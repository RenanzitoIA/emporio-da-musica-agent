"""Loading and cleaning of the store's operational data (CSV files).

The agent never reads the CSVs directly: every lookup goes through
`StoreData`, which holds clean pandas DataFrames plus a list of data-quality
issues found while loading (reported in the README and by `python -m emporio.audit`).
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

PRODUCT_STATUS = {"active", "discontinued", "coming_soon"}
ORDER_STATUS = {"pending", "confirmed", "shipped", "delivered", "cancelled"}


def normalize(text: str) -> str:
    """Lowercase, strip accents and collapse punctuation, for fuzzy matching."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return text.strip()


def digits(text: str) -> str:
    return re.sub(r"\D", "", str(text))


@dataclass
class StoreData:
    categories: pd.DataFrame
    products: pd.DataFrame
    promotions: pd.DataFrame
    customers: pd.DataFrame
    orders: pd.DataFrame
    order_items: pd.DataFrame
    issues: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, raw_dir: Path = RAW_DIR) -> "StoreData":
        read = lambda name: pd.read_csv(raw_dir / f"{name}.csv", encoding="utf-8")
        data = cls(
            categories=read("categories"),
            products=read("products"),
            promotions=read("promotions"),
            customers=read("customers"),
            orders=read("orders"),
            order_items=read("order_items"),
        )
        data._clean()
        data._audit()
        return data

    # ------------------------------------------------------------------ clean
    def _clean(self) -> None:
        p = self.products
        p["name"] = p["name"].str.strip()
        p["status"] = p["status"].str.strip().str.lower()
        p["stock_quantity"] = p["stock_quantity"].fillna(0).astype(int)
        p["price_brl"] = p["price_brl"].astype(float)
        p["specs"] = p["specs"].apply(_parse_specs)
        p["created_at"] = pd.to_datetime(p["created_at"], errors="coerce")
        p = p.merge(
            self.categories[["category_id", "name"]].rename(columns={"name": "category"}),
            on="category_id",
            how="left",
        )
        # Search key: name + category + spec values, accent-free.
        p["search_key"] = p.apply(
            lambda r: normalize(
                f"{r['name']} {r['category']} {' '.join(map(str, r['specs'].values()))}"
            ),
            axis=1,
        )
        self.products = p.sort_values("product_id").reset_index(drop=True)

        promo = self.promotions
        promo["is_active"] = promo["is_active"].astype(int).astype(bool)
        promo["discount_percent"] = promo["discount_percent"].astype(float)

        o = self.orders
        o["status"] = o["status"].str.strip().str.lower()
        for col in ("order_date", "estimated_delivery"):
            o[col] = pd.to_datetime(o[col], errors="coerce")
        o["tracking_code"] = o["tracking_code"].fillna("")
        o["notes"] = o["notes"].fillna("")

        c = self.customers
        c["phone_digits"] = c["phone"].map(digits)
        c["name_key"] = c["name"].map(normalize)

    # ------------------------------------------------------------------ audit
    def _audit(self) -> None:
        """Record inconsistencies instead of silently fixing them."""
        issues = self.issues
        p, o, oi, promo = self.products, self.orders, self.order_items, self.promotions

        for s in sorted(set(p["status"]) - PRODUCT_STATUS):
            issues.append(f"Unknown product status '{s}'.")
        for s in sorted(set(o["status"]) - ORDER_STATUS):
            issues.append(f"Unknown order status '{s}'.")

        out = p[(p["status"] == "active") & (p["stock_quantity"] == 0)]
        for _, r in out.iterrows():
            issues.append(f"Product {r.product_id} ({r['name']}) is active but out of stock.")
        disc = p[(p["status"] == "discontinued") & (p["stock_quantity"] > 0)]
        for _, r in disc.iterrows():
            issues.append(
                f"Product {r.product_id} ({r['name']}) is discontinued but still has "
                f"{r.stock_quantity} units in stock."
            )

        dup = promo[promo.duplicated("product_id", keep=False)]
        for pid, g in dup.groupby("product_id"):
            issues.append(
                f"Product {pid} has {len(g)} promotions "
                f"({g['is_active'].sum()} active); at most one active is assumed."
            )
        orphan = set(promo["product_id"]) - set(p["product_id"])
        if orphan:
            issues.append(f"Promotions reference unknown products: {sorted(orphan)}.")

        # Order totals vs. current catalog prices.
        merged = oi.merge(p[["product_id", "price_brl", "status"]], on="product_id", how="left")
        merged["line"] = merged["quantity"] * merged["price_brl"]
        totals = merged.groupby("order_id")["line"].sum()
        for _, r in o.iterrows():
            expected = totals.get(r.order_id)
            if expected is not None and abs(expected - r.total_brl) > 0.01:
                issues.append(
                    f"Order {r.order_id}: total R$ {r.total_brl:.2f} differs from current "
                    f"catalog prices (R$ {expected:.2f}); price changes or discounts may explain it."
                )
        for _, r in merged[merged["status"] == "coming_soon"].iterrows():
            issues.append(
                f"Order {r.order_id} contains product {r.product_id}, which is 'coming_soon'."
            )

        # Installment rules (store policy 3.1) vs. orders.
        for _, r in o.iterrows():
            m = re.fullmatch(r"credit_(\d+)x", str(r.payment_method))
            if not m:
                continue
            n = int(m.group(1))
            minimum = installment_minimum(n)
            if minimum and r.total_brl / n < minimum:
                issues.append(
                    f"Order {r.order_id}: {n}x of R$ {r.total_brl / n:.2f} is below the "
                    f"R$ {minimum:.2f} minimum installment for {n}x (policy 3.1)."
                )

        late = o[(o["status"] == "shipped") & o["estimated_delivery"].notna()]
        for _, r in late.iterrows():
            issues.append(
                f"Order {r.order_id} is still 'shipped' with estimated delivery "
                f"{r.estimated_delivery.date()} (check against the simulated date)."
            )


def installment_minimum(n: int) -> float:
    """Minimum installment value from policy 3.1 (0 = no minimum).

    Assumption: "up to 3x, no minimum (except below R$ 50.00)" is read as
    "2x-3x installments must be at least R$ 50.00". The section 3 table says
    "minimum R$ 100.00", but 3.1 is more specific, so 3.1 wins.
    """
    if n <= 1:
        return 0.0
    if n <= 3:
        return 50.0
    if n <= 6:
        return 80.0
    return 100.0


def _parse_specs(raw) -> dict:
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}

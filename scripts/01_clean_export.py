from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from _utils import (  # noqa: E402
    TableMeta,
    drop_mostly_empty_columns,
    excel_id_to_str,
    normalize_text,
    parse_datetime,
    parse_sla_to_timedelta,
    write_metadata,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "clean"


def _finalize(
    df: pd.DataFrame, table_name: str, *, dedup_ignore: set[str] | None = None
) -> tuple[pd.DataFrame, TableMeta]:
    rows_in = len(df)

    dedup_subset = None
    if dedup_ignore:
        dedup_subset = [c for c in df.columns if c not in dedup_ignore]

    exact_dup = int(df.duplicated(subset=dedup_subset).sum())
    if exact_dup:
        df = df.drop_duplicates(subset=dedup_subset)

    df, dropped = drop_mostly_empty_columns(df, threshold=0.999)

    meta = TableMeta(
        name=table_name,
        rows_in=rows_in,
        rows_out=len(df),
        dropped_columns=dropped,
        exact_duplicates_removed=exact_dup,
    )
    return df, meta


def clean_contacts(path: Path) -> tuple[pd.DataFrame, TableMeta]:
    df = pd.read_excel(path)
    df = df.rename(
        columns={
            "Id": "contact_id",
            "Contact Owner Name": "contact_owner_name",
            "Created Time": "created_time",
            "Modified Time": "modified_time",
        }
    )

    df["contact_id"] = df["contact_id"].map(excel_id_to_str)
    df["contact_id15"] = df["contact_id"].astype("string").str[:15]

    df["contact_owner_name"] = df["contact_owner_name"].map(normalize_text)
    df["created_time"] = parse_datetime(df["created_time"])
    df["modified_time"] = parse_datetime(df["modified_time"])

    return _finalize(df, "contacts")


def clean_calls(path: Path) -> tuple[pd.DataFrame, TableMeta]:
    df = pd.read_excel(path)
    df = df.rename(
        columns={
            "Id": "call_id",
            "Call Start Time": "call_start_time",
            "Call Owner Name": "call_owner_name",
            "CONTACTID": "contact_id_raw",
            "Call Type": "call_type",
            "Call Duration (in seconds)": "call_duration_seconds",
            "Call Status": "call_status",
            "Dialled Number": "dialled_number",
            "Outgoing Call Status": "outgoing_call_status",
            "Scheduled in CRM": "scheduled_in_crm",
            "Tag": "tag",
        }
    )

    df["call_id"] = df["call_id"].map(excel_id_to_str)
    df["call_start_time"] = parse_datetime(df["call_start_time"])
    df["call_owner_name"] = df["call_owner_name"].map(normalize_text)

    df["contact_id_str"] = df["contact_id_raw"].map(excel_id_to_str)
    df["contact_id15"] = df["contact_id_str"].astype("string").str[:15]

    for col in [
        "call_type",
        "call_status",
        "outgoing_call_status",
        "scheduled_in_crm",
    ]:
        if col in df.columns:
            df[col] = df[col].map(normalize_text)

    df["call_duration_seconds"] = pd.to_numeric(df["call_duration_seconds"], errors="coerce").round().astype("Int64")
    df["call_duration_minutes"] = (df["call_duration_seconds"].astype("float") / 60).round(2)

    return _finalize(df, "calls")


def clean_deals(path: Path) -> tuple[pd.DataFrame, TableMeta]:
    df = pd.read_excel(path)
    df = df.rename(
        columns={
            "Id": "deal_id_raw",
            "Deal Owner Name": "deal_owner_name",
            "Closing Date": "closing_date",
            "Quality": "quality",
            "Stage": "stage",
            "Lost Reason": "lost_reason",
            "Page": "page",
            "Campaign": "campaign",
            "SLA": "sla_raw",
            "Content": "content",
            "Term": "term",
            "Source": "source",
            "Payment Type": "payment_type",
            "Product": "product",
            "Education Type": "education_type",
            "Created Time": "created_time",
            "Course duration": "course_duration",
            "Months of study": "months_of_study",
            "Initial Amount Paid": "initial_amount_paid",
            "Offer Total Amount": "offer_total_amount",
            "Contact Name": "contact_id_raw",
            "City": "city",
            "Level of Deutsch": "level_of_deutsch",
        }
    )

    df.insert(0, "deal_row_id", np.arange(1, len(df) + 1, dtype=np.int64))

    df["deal_id_str"] = df["deal_id_raw"].map(excel_id_to_str)
    df["deal_id15"] = df["deal_id_str"].astype("string").str[:15]

    df["created_time"] = parse_datetime(df["created_time"])
    df["closing_date"] = parse_datetime(df["closing_date"])

    for col in [
        "deal_owner_name",
        "quality",
        "stage",
        "lost_reason",
        "page",
        "campaign",
        "content",
        "term",
        "source",
        "payment_type",
        "product",
        "education_type",
        "city",
        "level_of_deutsch",
    ]:
        if col in df.columns:
            df[col] = df[col].map(normalize_text)

    df["stage_norm"] = df["stage"].astype("string").str.strip().str.lower()
    df["is_paid"] = df["stage_norm"].eq("payment done").fillna(False)

    df["lost_reason_norm"] = df["lost_reason"].astype("string").str.strip().str.lower()
    df["is_duplicate_lost"] = (
        df["stage_norm"].eq("lost").fillna(False) & df["lost_reason_norm"].eq("duplicate").fillna(False)
    )

    df["contact_id_str"] = df["contact_id_raw"].map(excel_id_to_str)
    df["contact_id15"] = df["contact_id_str"].astype("string").str[:15]

    df["initial_amount_paid"] = pd.to_numeric(df["initial_amount_paid"], errors="coerce")
    df["offer_total_amount"] = pd.to_numeric(df["offer_total_amount"], errors="coerce")

    df["revenue_cash"] = np.where(df["is_paid"], df["initial_amount_paid"], 0.0)
    df["revenue_contract"] = np.where(df["is_paid"], df["offer_total_amount"], 0.0)

    df["sla_timedelta"] = df["sla_raw"].map(parse_sla_to_timedelta)
    df["sla_minutes"] = df["sla_timedelta"].dt.total_seconds() / 60
    df["sla_raw"] = df["sla_raw"].map(lambda v: pd.NA if pd.isna(v) else str(v)).map(normalize_text)

    df["course_duration"] = pd.to_numeric(df["course_duration"], errors="coerce")
    df["months_of_study"] = pd.to_numeric(df["months_of_study"], errors="coerce")

    df, meta = _finalize(df, "deals", dedup_ignore={"deal_row_id"})
    df["deal_row_id"] = np.arange(1, len(df) + 1, dtype=np.int64)
    return df, meta


def clean_spend(path: Path) -> tuple[pd.DataFrame, TableMeta]:
    df = pd.read_excel(path)
    df = df.rename(
        columns={
            "Date": "date",
            "Source": "source",
            "Campaign": "campaign",
            "Impressions": "impressions",
            "Spend": "spend",
            "Clicks": "clicks",
            "AdGroup": "ad_group",
            "Ad": "ad",
        }
    )

    df["date"] = parse_datetime(df["date"]).dt.date
    df["source"] = df["source"].map(normalize_text)
    df["campaign"] = df["campaign"].map(normalize_text)
    df["ad_group"] = df["ad_group"].map(normalize_text)
    df["ad"] = df["ad"].map(normalize_text)

    df["impressions"] = pd.to_numeric(df["impressions"], errors="coerce").round().astype("Int64")
    df["clicks"] = pd.to_numeric(df["clicks"], errors="coerce").round().astype("Int64")
    df["spend"] = pd.to_numeric(df["spend"], errors="coerce")

    return _finalize(df, "spend")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    tables: list[tuple[str, pd.DataFrame, TableMeta]] = []

    contacts, m_contacts = clean_contacts(ROOT / "Contacts (Done).xlsx")
    tables.append(("contacts", contacts, m_contacts))

    calls, m_calls = clean_calls(ROOT / "Calls (Done).xlsx")
    tables.append(("calls", calls, m_calls))

    deals, m_deals = clean_deals(ROOT / "Deals (Done).xlsx")
    tables.append(("deals", deals, m_deals))

    spend, m_spend = clean_spend(ROOT / "Spend (Done).xlsx")
    tables.append(("spend", spend, m_spend))

    meta_out: dict[str, object] = {
        "outputs": {},
        "notes": {
            "paid_definition": "Stage == 'Payment Done' (case-insensitive)",
            "closing_date_note": "По методичке Closing Date = дата оплаты, но в данных у paid может быть пустым.",
            "id_note": "Calls.CONTACTID / Deals.Contact Name потеряли точность в Excel; используйте contact_id15 как мягкий ключ.",
        },
    }

    for name, df, meta in tables:
        parquet_path = OUT_DIR / f"{name}.parquet"
        csv_path = OUT_DIR / f"{name}.csv"
        df.to_parquet(parquet_path, index=False)
        df.to_csv(csv_path, index=False, encoding="utf-8")

        meta_out["outputs"][name] = {
            "rows_in": meta.rows_in,
            "rows_out": meta.rows_out,
            "exact_duplicates_removed": meta.exact_duplicates_removed,
            "dropped_columns": meta.dropped_columns,
            "columns": list(df.columns),
        }

    write_metadata(OUT_DIR / "metadata.json", meta_out)
    print("OK: exported to data/clean")


if __name__ == "__main__":
    main()

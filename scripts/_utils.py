from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import time, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def normalize_text(value: Any) -> Any:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return pd.NA
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return pd.NA
    return re.sub(r"\s+", " ", text)


def parse_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", dayfirst=True)


def excel_id_to_str(value: Any) -> Any:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return pd.NA
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    if isinstance(value, (np.floating, float)):
        return f"{float(value):.0f}"
    text = str(value).strip()
    if text == "":
        return pd.NA
    text = re.sub(r"\.0$", "", text)
    try:
        f = float(text)
        return f"{f:.0f}"
    except Exception:
        return text


def drop_mostly_empty_columns(df: pd.DataFrame, threshold: float = 0.999) -> tuple[pd.DataFrame, list[str]]:
    missing_rate = df.isna().mean()
    to_drop = missing_rate[missing_rate >= threshold].index.tolist()
    if not to_drop:
        return df, []
    return df.drop(columns=to_drop), to_drop


def parse_sla_to_timedelta(value: Any) -> Any:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return pd.NaT

    if isinstance(value, timedelta):
        return pd.to_timedelta(value)

    if isinstance(value, time):
        return pd.to_timedelta(value.strftime("%H:%M:%S"))

    if isinstance(value, (np.integer, int)):
        # иногда Excel может хранить длительность как секунды
        return pd.to_timedelta(int(value), unit="s")

    if isinstance(value, (np.floating, float)):
        # если это доля дня (Excel duration), переведем в seconds
        # но это эвристика: большие числа уже не доля дня
        v = float(value)
        if 0 <= v < 10:
            return pd.to_timedelta(v, unit="D")
        return pd.NaT

    text = str(value).strip()
    if text == "":
        return pd.NaT
    try:
        return pd.to_timedelta(text)
    except Exception:
        return pd.NaT


@dataclass(frozen=True)
class TableMeta:
    name: str
    rows_in: int
    rows_out: int
    dropped_columns: list[str]
    exact_duplicates_removed: int


def write_metadata(path: Path, meta: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

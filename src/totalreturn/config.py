from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional
import yaml
from datetime import datetime, date


@dataclass
class StockConfig:
    code: str


@dataclass
class AppConfig:
    stocks: List[StockConfig]
    start_date: str  # YYYY-MM-DD
    end_date: Optional[str] = None  # YYYY-MM-DD or None

    @staticmethod
    def from_dict(d: dict) -> "AppConfig":
        stocks = [StockConfig(**item) if isinstance(item, dict) else StockConfig(code=str(item)) for item in d.get("stocks", [])]

        start_raw = d.get("start_date")
        end_raw = d.get("end_date")

        if not start_raw:
            raise ValueError("start_date is required in config.yaml")

        def _normalize_date(v):
            if v is None:
                return None
            if isinstance(v, str):
                # Validate format
                _ = datetime.strptime(v, "%Y-%m-%d")
                return v
            if isinstance(v, datetime):
                return v.strftime("%Y-%m-%d")
            if isinstance(v, date):
                return v.strftime("%Y-%m-%d")
            raise ValueError(f"Unsupported date type in config: {type(v)}")

        start_date = _normalize_date(start_raw)
        end_date = _normalize_date(end_raw) if end_raw is not None else None

        return AppConfig(stocks=stocks, start_date=start_date, end_date=end_date)


def load_config(path: str = None) -> AppConfig:
    """
    Load config.yaml. If path is None, resolve to project root's config.yaml using CWD.
    """
    if path is None:
        # Resolve relative to current working directory where main.py will be run
        path = os.path.join(os.getcwd(), "config.yaml")

    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return AppConfig.from_dict(data)

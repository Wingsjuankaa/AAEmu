#!/usr/bin/env python3

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from build_honor_store_runtime import (
    GLOBAL_OPEN_TYPE,
    HONOR_CURRENCY_ID,
    LEGACY_ITEM_IDS,
    MERCHANT_PACK_ID,
    STOCK,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    options = parser.parse_args()
    manifest = json.loads(options.manifest.read_text(encoding="utf-8"))
    assert manifest["output"]["sha256"] == sha256(options.runtime)

    with sqlite3.connect(options.runtime) as connection:
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        mapping = connection.execute(
            "SELECT merchant_pack_id FROM aaemu_global_merchant_packs "
            "WHERE open_type=? AND currency_id=?",
            (GLOBAL_OPEN_TYPE, HONOR_CURRENCY_ID),
        ).fetchone()
        assert mapping == (MERCHANT_PACK_ID,)
        goods = connection.execute(
            "SELECT item_id,grade_id,price,sort_order FROM merchant_goods "
            "WHERE merchant_pack_id=? ORDER BY sort_order",
            (MERCHANT_PACK_ID,),
        ).fetchall()
        assert goods == [
            (item_id, grade, price, order)
            for order, (item_id, grade, price, _) in enumerate(STOCK)
        ]
        ids = [row[0] for row in STOCK]
        assert connection.execute(
            f"SELECT COUNT(*) FROM items WHERE id IN ({','.join('?' for _ in ids)})",
            ids,
        ).fetchone()[0] == len(STOCK)
        assert connection.execute(
            f"SELECT COUNT(*) FROM aaemu_item_definition_coverage "
            f"WHERE item_id IN ({','.join('?' for _ in ids)}) AND coverage='complete'",
            ids,
        ).fetchone()[0] == len(STOCK)
        assert connection.execute(
            "SELECT COUNT(*) FROM items WHERE id IN (4740,4741,4742) "
            "AND use_skill_id IN (30944,30945,30946)"
        ).fetchone()[0] == len(LEGACY_ITEM_IDS)
    print("honor_store_runtime: ok")


if __name__ == "__main__":
    main()

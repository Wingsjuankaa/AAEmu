"""Idempotent AA10 upstream schema integration. Default: print the concrete SQL plan.
Run --apply only after a database/image backup and while Game is stopped.
Keeps native ArchePass/Bless schemas; never drops a table or rewrites item blobs.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "SQL/updates/2026-08-30_aaemu_game_item_detail_type.sql",
    "SQL/updates/2026-09-06_aaemu_game_account_attendances.sql",
    "SQL/updates/2026-09-06_aaemu_game_account_schedule_items.sql",
    "SQL/updates/2026-09-06_aaemu_game_housings_sell_public.sql",
    "SQL/updates/2026-09-08_aaemu_game_character_arche_pass_missions.sql",
    "SQL/updates/2026-09-08_aaemu_game_character_arche_passes.sql",
    "SQL/updates/2026-09-08_aaemu_game_character_bless_uthstin.sql",
    "SQL/updates/2026-09-08_aaemu_game_specialty_market.sql",
    "SQL/updates/2026-09-09_aaemu_game_specialty_stock_events.sql",
    "SQL/updates/2026-09-10_aaemu_game_mail_retention.sql",
    "SQL/updates/2026-09-11_aaemu_game_character_quest_cinema_end.sql",
    "SQL/updates/2026-09-12_aaemu_game_character_butlers.sql",
    "SQL/updates/2026-09-12_aaemu_game_farmhand_farming.sql",
    "SQL/updates/2026-09-13_aaemu_game_expedition_activities.sql",
    "SQL/updates/2026-09-13_aaemu_game_expedition_daily_exp.sql",
    "SQL/updates/2026-09-13_aaemu_game_expedition_descriptor_state.sql",
    "SQL/updates/2026-09-13_aaemu_game_expedition_instance_histories.sql",
    "SQL/updates/2026-09-13_aaemu_game_expedition_instance_history_type.sql",
    "SQL/updates/2026-09-13_aaemu_game_expedition_public_assignments.sql",
    "SQL/updates/2026-09-13_aaemu_game_expedition_recruitment.sql",
    "SQL/updates/2026-09-13_aaemu_game_expedition_renames.sql",
    "SQL/updates/2026-09-13_aaemu_game_expedition_weekly_contribution.sql",
    "SQL/updates/2026-09-13_aaemu_game_families.sql",
    "SQL/updates/2026-09-14_aaemu_game_character_recipes.sql"
]
MYSQL = ["docker", "exec", "-i", "aaemu10-db-1", "sh", "-c",
         'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -u root -N -B aaemu_game']
MARKER = 'upstream-20260916-8e71a37aa'

def sql(query):
    result = subprocess.run(MYSQL, input=query.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout.decode("utf-8")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    rows = sql("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema='aaemu_game';")
    columns = {}
    for row in rows.splitlines():
        table, col = row.split("\t")
        columns.setdefault(table, set()).add(col)
    if 'aa10_integration_migrations' in columns and sql(
            "SELECT 1 FROM aa10_integration_migrations WHERE id='" + MARKER + "';").strip():
        print(json.dumps({"already_applied": MARKER}))
        return
    # No silent reinterpretation of the fork's former per-level progression.
    for table in ('family_progress', 'expedition_quest_progress'):
        if table in columns and int(sql('SELECT COUNT(*) FROM `' + table + '`;').strip()):
            raise RuntimeError(table + ' requires an explicit progression conversion before integration')
    plan = []
    for filename in FILES:
        source = (ROOT / filename).read_text(encoding="utf-8-sig")
        source = re.sub(r"(?m)^\s*--.*$", "", source)
        for statement in source.split(';'):
            statement = statement.strip()
            if not statement or statement.upper().startswith('USE '):
                continue
            create = re.match(r'CREATE TABLE (?:IF NOT EXISTS )?`([^`]+)`', statement, re.I)
            alter = re.match(r'ALTER TABLE `([^`]+)`\s+(.+)', statement, re.I | re.S)
            if create:
                table = create[1]
                if table in columns:
                    continue
                columns[table] = set(re.findall(r'(?m)^\s*`([^`]+)`', statement))
            elif alter:
                table, body = alter.groups()
                if body.upper().startswith('ADD COLUMN'):
                    parts = re.split(r',\s*(?=ADD COLUMN)', body, flags=re.I)
                    for part in parts:
                        col = re.match(r'ADD COLUMN `([^`]+)`', part, re.I)[1]
                        if col not in columns.setdefault(table, set()):
                            plan.append('ALTER TABLE `' + table + '` ' + part + ';')
                            columns[table].add(col)
                    continue
                if body.upper().startswith('CHANGE COLUMN'):
                    old, new = re.match(r'CHANGE COLUMN `([^`]+)` `([^`]+)`', body, re.I).groups()
                    if new in columns[table]:
                        continue
                    columns[table].discard(old)
                    columns[table].add(new)
            plan.append(statement + ';')
    plan += [
        "SET time_zone = '+00:00';",
        "CREATE TABLE IF NOT EXISTS aa10_integration_migrations (id varchar(100) PRIMARY KEY, applied_at datetime NOT NULL);",
        "START TRANSACTION;",
        "INSERT IGNORE INTO account_attendances(account_id,year,month,day,attended_at,is_archelife) "
        "SELECT account_id,campaign_year,campaign_month,DAY(claim_day),UNIX_TIMESTAMP(claimed_at),is_archelife FROM account_attendance_claims;",
        "INSERT INTO aa10_integration_migrations(id,applied_at) VALUES ('" + MARKER + "',UTC_TIMESTAMP());",
        "COMMIT;"
    ]
    output = '\n\n'.join(plan) + '\n'
    if args.apply:
        sql(output)
        print(json.dumps({"applied": MARKER, "statements": len(plan)}))
    else:
        print(output)

if __name__ == '__main__':
    main()

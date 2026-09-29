"""No identity graph, persistence, revisions or release patches exist in v1."""

import csv
import hashlib
import hmac
import json
import re
from pathlib import Path


FIELDS = {
    "subjects": ("row_id", "tenant", "local_id", "name"),
    "visits": ("row_id", "tenant", "subject_id", "category"),
    "referrals": ("row_id", "from_tenant", "from_id", "to_tenant", "to_id", "note"),
}
SLUG = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")


def check_slug(value):
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        raise ValueError("invalid identifier/seed")


def token(seed, identity):
    check_slug(seed)
    tenant, local_id = identity
    check_slug(tenant)
    check_slug(local_id)
    message = b"person\0" + json.dumps(
        [tenant, local_id], ensure_ascii=True, separators=(",", ":")
    ).encode("ascii")
    return "ps_" + hmac.new(seed.encode("utf-8"), message, hashlib.sha256).hexdigest()


def read_tables(directory):
    tables = {}
    for table, fields in FIELDS.items():
        with (Path(directory) / (table + ".csv")).open(
            "r", encoding="utf-8", newline=""
        ) as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != list(fields):
                raise ValueError("incorrect {} header".format(table))
            rows = list(reader)
            if any(set(row) != set(fields) or None in row.values() for row in rows):
                raise ValueError("incorrect {} row width".format(table))
            tables[table] = rows
    validate_tables(tables)
    return tables


def validate_tables(tables):
    for table, fields in FIELDS.items():
        seen = set()
        for row in tables[table]:
            if set(row) != set(fields) or any(not isinstance(v, str) for v in row.values()):
                raise ValueError("incorrect row shape")
            for field, value in row.items():
                if field not in ("name", "note"):
                    check_slug(value)
            if row["row_id"] in seen:
                raise ValueError("duplicate row_id")
            seen.add(row["row_id"])
    identities = {(r["tenant"], r["local_id"]) for r in tables["subjects"]}
    if len(identities) != len(tables["subjects"]):
        raise ValueError("duplicate subject identity")
    for row in tables["visits"]:
        if (row["tenant"], row["subject_id"]) not in identities:
            raise ValueError("dangling visit")
    for row in tables["referrals"]:
        if any((row[prefix + "tenant"], row[prefix + "id"]) not in identities
               for prefix in ("from_", "to_")):
            raise ValueError("dangling referral")


def render_tables(tables, seed):
    """Render v1 independent identities; do not resolve identity equivalences."""
    check_slug(seed)
    result = {table: [] for table in FIELDS}
    for source in tables["subjects"]:
        row = dict(source)
        row["local_id"] = token(seed, (row["tenant"], row["local_id"]))
        row["name"] = ""
        result["subjects"].append(row)
    for source in tables["visits"]:
        row = dict(source)
        row["subject_id"] = token(seed, (row["tenant"], row["subject_id"]))
        result["visits"].append(row)
    for source in tables["referrals"]:
        row = dict(source)
        for prefix in ("from_", "to_"):
            row[prefix + "id"] = token(seed, (row[prefix + "tenant"], row[prefix + "id"]))
        row["note"] = ""
        result["referrals"].append(row)
    return result


def export_directory(input_directory, output_directory, seed):
    check_slug(seed)
    tables = read_tables(input_directory)
    rendered = render_tables(tables, seed)
    destination = Path(output_directory)
    destination.mkdir(parents=True, exist_ok=True)
    for table, fields in FIELDS.items():
        with (destination / (table + ".csv")).open(
            "w", encoding="utf-8", newline=""
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rendered[table])

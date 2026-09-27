"""
Generate deterministic mock data for the three MCP servers.

Writes one JSON file per system (CRM, Billing, App DB) plus a ground-truth file
that only the evaluation suite reads. The MCP servers never see the ground truth.

Usage (from the project root):
    python scripts/generate_mock_data.py
"""
import json
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MCP_DATA_DIR = PROJECT_ROOT / "mcp_servers" / "data"
GROUND_TRUTH_PATH = PROJECT_ROOT / "evals" / "entity_ground_truth.json"

# Each family shares a name root, so a query like "acme" legitimately returns
# several distinct companies. That is exactly the case the resolver must handle.
FAMILIES = [
    "Acme", "Globex", "Initech", "Hooli", "Vandelay", "Wonka", "Stark",
    "Wayne", "Cyberdyne", "Tyrell", "Oscorp", "Aperture", "Pied Piper",
    "Dunder Mifflin",
]
DIVISIONS = ["Logistics", "Labs", "Health", "Capital", "Energy", "Systems"]
US_SUFFIXES = ["Inc.", "LLC", "Corporation"]
UK_SUFFIXES = ["Ltd", "PLC"]
CRM_TIERS = ["Enterprise", "Mid-Market", "Startup"]
MRR_VALUES = [200, 500, 1200, 2500, 5000, 12000]
BILLING_ROLES = ["finance", "billing", "accounts"]
APP_DB_ROLES = ["admin", "ops", "founder", "dev"]
SYSTEMS = ["crm", "billing", "app_db"]

SUFFIX_CONFLICT_RATE = 0.25
LAST_LOGIN_START = date(2026, 1, 1)
LAST_LOGIN_WINDOW_DAYS = 240


def slugify(name: str) -> str:
    """'Pied Piper' -> 'piedpiper'. Used to build domains."""
    return "".join(ch for ch in name.lower() if ch.isalnum())


def build_variants(family: str, rng: random.Random) -> list:
    """Return the distinct companies that share one family name root."""
    variants = [{"name": family, "region": "US", "is_parent": True}]
    extra_count = rng.choices([0, 1, 2], weights=[40, 35, 25])[0]

    for _ in range(extra_count):
        has_uk = any(v["region"] == "UK" for v in variants)
        if not has_uk and rng.random() < 0.5:
            variants.append({"name": f"{family} UK", "region": "UK", "is_parent": False})
        else:
            taken = {v["name"] for v in variants}
            division = rng.choice([d for d in DIVISIONS if f"{family} {d}" not in taken])
            variants.append({"name": f"{family} {division}", "region": "US", "is_parent": False})

    return variants


def build_domain(variant: dict, family: str, rng: random.Random) -> str:
    """UK arms reuse the parent's root on .co.uk, which is the classic look-alike trap."""
    if variant["region"] == "UK":
        return f"{slugify(family)}.co.uk"
    return f"{slugify(variant['name'])}{rng.choice(['.com', '.io'])}"


def choose_systems(is_parent: bool, rng: random.Random) -> list:
    """Parents exist everywhere; divisions and regional arms have coverage gaps."""
    if is_parent:
        return list(SYSTEMS)
    count = rng.choices([3, 2, 1], weights=[50, 35, 15])[0]
    return sorted(rng.sample(SYSTEMS, count), key=SYSTEMS.index)


def build_entities(rng: random.Random) -> list:
    """Build the list of real-world companies that every system's records derive from."""
    entities = []
    for family in FAMILIES:
        for variant in build_variants(family, rng):
            suffixes = UK_SUFFIXES if variant["region"] == "UK" else US_SUFFIXES
            systems = choose_systems(variant["is_parent"], rng)
            suffix = rng.choice(suffixes)
            billing_suffix = suffix
            injected = []

            if "crm" in systems and "billing" in systems and rng.random() < SUFFIX_CONFLICT_RATE:
                billing_suffix = rng.choice([s for s in suffixes if s != suffix])
                injected.append("legal_suffix_conflict")

            entities.append({
                "entity_id": f"ent_{len(entities) + 1:03d}",
                "family": slugify(family),
                "name": variant["name"],
                "region": variant["region"],
                "domain": build_domain(variant, family, rng),
                "systems": systems,
                "suffix": suffix,
                "billing_suffix": billing_suffix,
                "injected_discrepancies": injected,
                "crm_ids": [],
                "stripe_ids": [],
                "user_ids": [],
            })
    return entities


def crm_record(entity: dict, rng: random.Random) -> dict:
    domain = entity["domain"]
    return {
        "company_name": f"{entity['name']} {entity['suffix']}",
        "website": rng.choice([domain, f"www.{domain}", f"https://www.{domain}"]),
        "tier": rng.choice(CRM_TIERS),
        "primary_contact": f"admin@{domain}",
    }


def billing_record(entity: dict, rng: random.Random) -> dict:
    return {
        "legal_name": f"{entity['name']} {entity['billing_suffix']}",
        "billing_email": f"{rng.choice(BILLING_ROLES)}@{entity['domain']}",
        "monthly_recurring_revenue": rng.choice(MRR_VALUES),
    }


def app_db_records(entity: dict, rng: random.Random) -> list:
    """An app database holds users, so one company can have several rows."""
    user_count = rng.choices([1, 2, 3], weights=[50, 35, 15])[0]
    roles = rng.sample(APP_DB_ROLES, user_count)
    return [
        {
            "company": entity["name"],
            "email": f"{role}@{entity['domain']}",
            "is_active": rng.random() < 0.8,
            "last_login": (LAST_LOGIN_START + timedelta(days=rng.randrange(LAST_LOGIN_WINDOW_DAYS))).isoformat(),
        }
        for role in roles
    ]


def assign_ids(pairs: list, id_field: str, ids_key: str, prefix: str, rng: random.Random) -> list:
    """Shuffle before numbering, so an ID never reveals which records belong together."""
    rng.shuffle(pairs)
    records = []
    for number, (entity, record) in enumerate(pairs, start=1001):
        record_id = f"{prefix}_{number}"
        records.append({id_field: record_id, **record})
        entity[ids_key].append(record_id)
    return records


def build_system_records(entities: list, rng: random.Random) -> tuple:
    crm_pairs, billing_pairs, app_db_pairs = [], [], []
    for entity in entities:
        if "crm" in entity["systems"]:
            crm_pairs.append((entity, crm_record(entity, rng)))
        if "billing" in entity["systems"]:
            billing_pairs.append((entity, billing_record(entity, rng)))
        if "app_db" in entity["systems"]:
            for record in app_db_records(entity, rng):
                app_db_pairs.append((entity, record))

    crm = assign_ids(crm_pairs, "crm_id", "crm_ids", "sf", rng)
    billing = assign_ids(billing_pairs, "stripe_id", "stripe_ids", "cus", rng)
    app_db = assign_ids(app_db_pairs, "user_id", "user_ids", "usr", rng)
    return crm, billing, app_db


def build_ground_truth(entities: list) -> dict:
    return {
        "seed": SEED,
        "entities": [
            {
                "entity_id": e["entity_id"],
                "family": e["family"],
                "name": e["name"],
                "region": e["region"],
                "domain": e["domain"],
                "crm_ids": sorted(e["crm_ids"]),
                "stripe_ids": sorted(e["stripe_ids"]),
                "user_ids": sorted(e["user_ids"]),
                "injected_discrepancies": e["injected_discrepancies"],
            }
            for e in entities
        ],
    }


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    rng = random.Random(SEED)
    entities = build_entities(rng)
    crm, billing, app_db = build_system_records(entities, rng)

    write_json(MCP_DATA_DIR / "crm_records.json", crm)
    write_json(MCP_DATA_DIR / "billing_records.json", billing)
    write_json(MCP_DATA_DIR / "app_db_records.json", app_db)
    write_json(GROUND_TRUTH_PATH, build_ground_truth(entities))

    print(f"Entities: {len(entities)} across {len(FAMILIES)} families")
    print(f"CRM: {len(crm)} | Billing: {len(billing)} | App DB: {len(app_db)}")


if __name__ == "__main__":
    main()

"""
Account-level research cache.

Postgres (Railway) when DATABASE_URL is set; in-memory dict fallback otherwise
so the app runs locally before Railway exists. Only ACCOUNT material is cached
(10-K, news, site, account LinkedIn). Contact work always runs fresh.
"""
import datetime
import json

from config import DATABASE_URL, CACHE_TTL_DAYS

_MEM = {}  # domain -> (material_dict, created_at)


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _dsn():
    # psycopg3 accepts postgresql://; normalize the older postgres:// scheme.
    return DATABASE_URL.replace("postgres://", "postgresql://", 1)


def _pg():
    return bool(DATABASE_URL)


def init():
    if not _pg():
        return
    import psycopg
    with psycopg.connect(_dsn()) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS research_cache (
                   domain TEXT PRIMARY KEY,
                   account_material JSONB NOT NULL,
                   created_at TIMESTAMPTZ NOT NULL DEFAULT now()
               )"""
        )
        conn.commit()


def get_account_material(domain):
    """Return cached material if younger than CACHE_TTL_DAYS, else None."""
    ttl = datetime.timedelta(days=CACHE_TTL_DAYS)
    if _pg():
        import psycopg
        with psycopg.connect(_dsn()) as conn:
            row = conn.execute(
                "SELECT account_material, created_at FROM research_cache WHERE domain=%s",
                (domain,),
            ).fetchone()
        if not row:
            return None
        material, created = row
        if _now() - created > ttl:
            return None
        return material
    # in-memory
    hit = _MEM.get(domain)
    if not hit:
        return None
    material, created = hit
    if _now() - created > ttl:
        return None
    return material


def set_account_material(domain, material):
    if _pg():
        import psycopg
        with psycopg.connect(_dsn()) as conn:
            conn.execute(
                """INSERT INTO research_cache (domain, account_material, created_at)
                   VALUES (%s, %s, now())
                   ON CONFLICT (domain) DO UPDATE
                     SET account_material = EXCLUDED.account_material,
                         created_at = now()""",
                (domain, json.dumps(material)),
            )
            conn.commit()
    else:
        _MEM[domain] = (material, _now())

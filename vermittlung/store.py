"""Persons, invitations, accesses and costs in SQLite (MIN-344).

Invitation codes and accesses are stored only as SHA-256 hashes: both are long random values, so a
plain hash is enough. The usage table holds person, model, tokens and cost of each call, never content.
Each access has a budget in CHF per calendar month in Swiss time (G98), taken from its code and raisable
per person; spending counts only the current month, nothing carries over. The column keeps its name
`credit_chf` from the one-time credit of G80, so databases from then go on as they are. Times are stored in
UTC; months are counted in Zurich (`months.py`).
"""
import dataclasses
import datetime
import hashlib
import re
import secrets
import sqlite3
import threading

import months
from pricing import Usage, cost_chf

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # without 0/O and 1/I, easy to type
CODE_LENGTH = 16  # 80 bits
CODE_GROUP = 4
INVITATION_DAYS = 45  # long enough for a round of applications
MAX_INVITATION_DAYS = 365
CONSENT_RECEIPT = re.compile(r"\d{4}-\d{2} [a-z]{1,20}")  # version and kind of search, nothing about the person
RETENTION_DAYS = 30  # cost logs go at the latest this long after the last access was revoked
MONTHLY_BUDGET_CHF = 5.0  # G98: what an access may spend per month unless raised
MAX_BUDGET_CHF = 100.0  # a typo in the admin command must not hand out a fortune
SCHEMA = f"""
CREATE TABLE IF NOT EXISTS people (name TEXT PRIMARY KEY, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS invitations (code_hash TEXT PRIMARY KEY, person TEXT NOT NULL REFERENCES people(name),
    created TEXT NOT NULL, expires TEXT NOT NULL, used TEXT, credit_chf REAL NOT NULL DEFAULT {MONTHLY_BUDGET_CHF});
CREATE TABLE IF NOT EXISTS accesses (id INTEGER PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL,
    person TEXT NOT NULL REFERENCES people(name), device TEXT NOT NULL, created TEXT NOT NULL,
    last_used TEXT, revoked TEXT, consent TEXT NOT NULL DEFAULT '',
    credit_chf REAL NOT NULL DEFAULT {MONTHLY_BUDGET_CHF});
CREATE TABLE IF NOT EXISTS usage (id INTEGER PRIMARY KEY, time TEXT NOT NULL, person TEXT NOT NULL,
    access_id INTEGER NOT NULL, model TEXT NOT NULL, input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
    cache_creation_input_tokens INTEGER NOT NULL, cache_read_input_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL, status INTEGER NOT NULL, request_id TEXT);
CREATE INDEX IF NOT EXISTS usage_person_time ON usage (person, time);
"""
PERSON_TABLES = ("usage", "accesses", "invitations")  # children of people, deleted first


class StoreError(ValueError):
    """Wrong input for an admin command or an invalid code; the message is meant for people."""


@dataclasses.dataclass(frozen=True)
class Access:
    id: int
    person: str
    budget_chf: float  # per calendar month


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_code(code: str) -> str:
    return "".join(c for c in str(code).upper() if c.isalnum())


def _iso(moment: datetime.datetime) -> str:
    return moment.astimezone(datetime.timezone.utc).isoformat(timespec="seconds")


def check_budget(budget_chf: float) -> None:
    if not 0 < budget_chf <= MAX_BUDGET_CHF:
        raise StoreError(f"Budget pro Monat: mehr als CHF 0 und höchstens CHF {MAX_BUDGET_CHF:.0f}.")


def _month_range(month: str) -> tuple[str, str]:
    """The month as stored times from its start up to, not including, the start of the next."""
    try:
        start, end = months.bounds(month)
    except ValueError as error:
        raise StoreError("Monat als JJJJ-MM angeben, z.B. 2026-11.") from error
    return _iso(start), _iso(end)


class Store:
    def __init__(self, path: str) -> None:
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._db.execute("PRAGMA foreign_keys = ON")
            self._db.executescript(SCHEMA)
            self._add_missing_columns()
            self._legacy_budget = "budget_usd" in self._columns("people")

    def _columns(self, table: str) -> set[str]:
        return {row["name"] for row in self._db.execute(f"PRAGMA table_info({table})")}

    def _add_missing_columns(self) -> None:
        """`CREATE TABLE IF NOT EXISTS` leaves a database from before MIN-401 or G80 as it is; the budget of its
        accesses and open codes starts at the default. A column `credit_since` from G80 stays, unread."""
        accesses = self._columns("accesses")
        if "consent" not in accesses:
            self._db.execute("ALTER TABLE accesses ADD COLUMN consent TEXT NOT NULL DEFAULT ''")
        if "credit_chf" not in accesses:
            self._db.execute(f"ALTER TABLE accesses ADD COLUMN credit_chf REAL NOT NULL DEFAULT {MONTHLY_BUDGET_CHF}")
        if "credit_chf" not in self._columns("invitations"):
            self._db.execute(f"ALTER TABLE invitations ADD COLUMN credit_chf REAL NOT NULL DEFAULT {MONTHLY_BUDGET_CHF}")

    def _run(self, sql: str, args: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._db.execute(sql, args)

    # people

    def add_person(self, name: str, now: datetime.datetime) -> None:
        name = name.strip()
        if not name:
            raise StoreError("Name der Person fehlt (am besten ein Kürzel wie T01, kein echter Name).")
        # a database from before G80 still has the monthly budget column; nothing reads it any more
        sql = ("INSERT INTO people (name, budget_usd, created) VALUES (?, 0, ?)" if self._legacy_budget
               else "INSERT INTO people (name, created) VALUES (?, ?)")
        try:
            self._run(sql, (name, _iso(now)))
        except sqlite3.IntegrityError as error:
            raise StoreError(f"Person {name} gibt es schon.") from error

    def has_person(self, name: str) -> bool:
        return self._run("SELECT 1 FROM people WHERE name = ?", (name,)).fetchone() is not None

    def people(self) -> list[dict]:
        return [dict(row) for row in self._run("SELECT name, created FROM people ORDER BY name")]

    # invitations and accesses

    def create_invitation(self, name: str, now: datetime.datetime, days: int = INVITATION_DAYS,
                          budget_chf: float = MONTHLY_BUDGET_CHF) -> str:
        if not 1 <= days <= MAX_INVITATION_DAYS:
            raise StoreError(f"Gültigkeit in Tagen: 1 bis {MAX_INVITATION_DAYS}.")
        check_budget(budget_chf)
        if not self.has_person(name):
            raise StoreError(f"Person {name} gibt es nicht.")
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        expires = now + datetime.timedelta(days=days)
        self._run("INSERT INTO invitations (code_hash, person, created, expires, used, credit_chf) "
                  "VALUES (?, ?, ?, ?, NULL, ?)", (_hash(code), name, _iso(now), _iso(expires), budget_chf))
        return "-".join(code[i:i + CODE_GROUP] for i in range(0, CODE_LENGTH, CODE_GROUP))

    def redeem(self, code: str, device: str, now: datetime.datetime, consent: str = "") -> str:
        """A new access for the person of the code, with the code's monthly budget; the code is used up.
        StoreError if invalid or expired. A person whose other access is used up may redeem too (G98)."""
        code_hash = _hash(normalize_code(code))
        token = "bwa_" + secrets.token_urlsafe(32)
        receipt = consent if CONSENT_RECEIPT.fullmatch(consent) else ""
        # the name comes from outside and is printed in the operator's terminal
        device = "".join(char for char in device if char.isprintable())
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                row = self._db.execute(
                    "UPDATE invitations SET used = ? WHERE code_hash = ? AND used IS NULL AND expires > ? "
                    "RETURNING person, credit_chf", (_iso(now), code_hash, _iso(now))).fetchone()
                if row is None:
                    raise StoreError("Der Code gilt nicht (falsch, schon benutzt oder abgelaufen).")
                self._db.execute("INSERT INTO accesses (token_hash, person, device, created, consent, credit_chf) "
                                 "VALUES (?, ?, ?, ?, ?, ?)",
                                 (_hash(token), row["person"], device.strip()[:60] or "Gerät", _iso(now), receipt,
                                  row["credit_chf"]))
                self._db.execute("COMMIT")
            except Exception:
                self._db.execute("ROLLBACK")
                raise
        return token

    def authenticate(self, token: str, now: datetime.datetime) -> Access | None:
        row = self._run(
            "SELECT id, person, credit_chf FROM accesses WHERE token_hash = ? AND revoked IS NULL",
            (_hash(token),)).fetchone()
        if row is None:
            return None
        self._run("UPDATE accesses SET last_used = ? WHERE id = ?", (_iso(now), row["id"]))
        return Access(row["id"], row["person"], row["credit_chf"])

    def revoke(self, name: str, now: datetime.datetime, access_id: int | None = None) -> int:
        """Revoke all accesses of a person, or one of them; returns how many were revoked."""
        sql = "UPDATE accesses SET revoked = ? WHERE person = ? AND revoked IS NULL"
        args: tuple = (_iso(now), name)
        if access_id is not None:
            sql, args = sql + " AND id = ?", args + (access_id,)
        return self._run(sql, args).rowcount

    def void_invitations(self, name: str, now: datetime.datetime) -> int:
        """Use up the open invitations of a person, so a revoked person cannot come back with one."""
        return self._run("UPDATE invitations SET used = ? WHERE person = ? AND used IS NULL", (_iso(now), name)).rowcount

    def set_budget(self, name: str, budget_chf: float, access_id: int | None = None) -> dict:
        """Set the monthly budget of the active accesses and open codes of a person, or of one access; it
        counts for the current month too. Returns how many accesses and codes changed."""
        check_budget(budget_chf)
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                if self._db.execute("SELECT 1 FROM people WHERE name = ?", (name,)).fetchone() is None:
                    raise StoreError(f"Person {name} gibt es nicht.")
                sql, args = "UPDATE accesses SET credit_chf = ? WHERE person = ? AND revoked IS NULL", (budget_chf, name)
                if access_id is not None:
                    sql, args = sql + " AND id = ?", args + (access_id,)
                accesses = self._db.execute(sql, args).rowcount
                invitations = 0 if access_id is not None else self._db.execute(
                    "UPDATE invitations SET credit_chf = ? WHERE person = ? AND used IS NULL", (budget_chf, name)).rowcount
                self._db.execute("COMMIT")
            except Exception:
                self._db.execute("ROLLBACK")
                raise
        return {"accesses": accesses, "invitations": invitations}

    def accesses(self, name: str, now: datetime.datetime | None = None) -> list[dict]:
        """The accesses of a person, each with its monthly budget and what it spent in the month of `now`, in CHF."""
        start, end = _month_range(months.month_of(now or datetime.datetime.now(datetime.timezone.utc)))
        rows = self._run(
            "SELECT a.id, a.device, a.created, a.last_used, a.revoked, a.consent, a.credit_chf AS budget_chf, "
            "COALESCE(SUM(u.cost_usd), 0) AS spent_usd FROM accesses a "
            "LEFT JOIN usage u ON u.access_id = a.id AND u.time >= ? AND u.time < ? "
            "WHERE a.person = ? GROUP BY a.id ORDER BY a.id", (start, end, name))
        return [{**{key: row[key] for key in row.keys() if key != "spent_usd"},
                 "spent_chf": round(cost_chf(row["spent_usd"]), 6)} for row in rows]

    # deletion

    def _holdings(self, name: str) -> dict:
        """What is stored about a person who may be deleted; call with the lock held."""
        if self._db.execute("SELECT 1 FROM people WHERE name = ?", (name,)).fetchone() is None:
            raise StoreError(f"Person {name} gibt es nicht.")
        if self._db.execute("SELECT 1 FROM accesses WHERE person = ? AND revoked IS NULL", (name,)).fetchone():
            raise StoreError(f"{name} hat noch einen aktiven Zugang. Zuerst sperren: revoke {name}")
        return {table: self._db.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE person = ?", (name,)).fetchone()["n"]
                for table in PERSON_TABLES}

    def holdings(self, name: str) -> dict:
        """Rows per table that `forget` would delete. StoreError if the person is unknown or still active."""
        with self._lock:
            return self._holdings(name)

    def forget(self, name: str) -> dict:
        """Delete a person with accesses, invitations and cost logs, all or nothing; returns the rows per table."""
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                removed = self._holdings(name)
                for table in PERSON_TABLES:
                    self._db.execute(f"DELETE FROM {table} WHERE person = ?", (name,))
                self._db.execute("DELETE FROM people WHERE name = ?", (name,))
                self._db.execute("COMMIT")
            except Exception:
                self._db.execute("ROLLBACK")
                raise
        return removed

    def due_for_deletion(self, now: datetime.datetime, days: int = RETENTION_DAYS) -> list[dict]:
        """People without an active access whose last revocation is at least `days` ago."""
        return [dict(row) for row in self._run(
            "SELECT person, MAX(revoked) AS revoked FROM accesses GROUP BY person "
            "HAVING SUM(revoked IS NULL) = 0 AND MAX(revoked) <= ? ORDER BY person",
            (_iso(now - datetime.timedelta(days=days)),))]

    # costs

    def record_usage(self, access: Access, model: str, usage: Usage, cost: float, status: int,
                     request_id: str | None, now: datetime.datetime) -> None:
        self._run("INSERT INTO usage (time, person, access_id, model, input_tokens, output_tokens, "
                  "cache_creation_input_tokens, cache_read_input_tokens, cost_usd, status, request_id) "
                  "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (_iso(now), access.person, access.id, model, *dataclasses.astuple(usage), cost, status, request_id))

    def spent(self, name: str, month: str) -> float:
        """What Anthropic billed for a person in a month (Swiss time), in USD; for the operator's accounts."""
        row = self._run("SELECT COALESCE(SUM(cost_usd), 0) AS total FROM usage WHERE person = ? AND time >= ? "
                        "AND time < ?", (name, *_month_range(month))).fetchone()
        return round(row["total"], 6)

    def spent_chf(self, access: Access, now: datetime.datetime) -> float:
        """What an access spent in the month of `now` (Swiss time), in CHF; earlier months do not count."""
        row = self._run("SELECT COALESCE(SUM(cost_usd), 0) AS total FROM usage WHERE access_id = ? AND time >= ? "
                        "AND time < ?", (access.id, *_month_range(months.month_of(now)))).fetchone()
        return round(cost_chf(row["total"]), 6)

    def costs(self, month: str) -> list[dict]:
        """Calls and costs per person in a month (Swiss time), in CHF."""
        rows = self._run(
            "SELECT p.name AS person, COUNT(u.id) AS calls, COALESCE(SUM(u.cost_usd), 0) AS cost_usd FROM people p "
            "LEFT JOIN usage u ON u.person = p.name AND u.time >= ? AND u.time < ? GROUP BY p.name ORDER BY p.name",
            _month_range(month))
        return [{"person": row["person"], "calls": row["calls"], "cost_chf": round(cost_chf(row["cost_usd"]), 6)}
                for row in rows]

"""Persons, invitations, accesses and costs in SQLite (MIN-344).

Invitation codes and accesses are stored only as SHA-256 hashes: both are long random values, so a
plain hash is enough. The usage table holds person, model, tokens and cost of each call, never content.
Times are UTC; a month is "YYYY-MM" in UTC.
"""
import dataclasses
import datetime
import hashlib
import re
import secrets
import sqlite3
import threading

from pricing import Usage

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # without 0/O and 1/I, easy to type
CODE_LENGTH = 16  # 80 bits
CODE_GROUP = 4
INVITATION_DAYS = 45  # long enough for a round of applications
MAX_INVITATION_DAYS = 365
CONSENT_RECEIPT = re.compile(r"\d{4}-\d{2} [a-z]{1,20}")  # version and kind of search, nothing about the person
RETENTION_DAYS = 30  # cost logs go at the latest this long after the last access was revoked
SCHEMA = """
CREATE TABLE IF NOT EXISTS people (name TEXT PRIMARY KEY, budget_usd REAL NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS invitations (code_hash TEXT PRIMARY KEY, person TEXT NOT NULL REFERENCES people(name),
    created TEXT NOT NULL, expires TEXT NOT NULL, used TEXT);
CREATE TABLE IF NOT EXISTS accesses (id INTEGER PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL,
    person TEXT NOT NULL REFERENCES people(name), device TEXT NOT NULL, created TEXT NOT NULL,
    last_used TEXT, revoked TEXT, consent TEXT NOT NULL DEFAULT '');
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
    budget_usd: float


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_code(code: str) -> str:
    return "".join(c for c in str(code).upper() if c.isalnum())


def _iso(moment: datetime.datetime) -> str:
    return moment.astimezone(datetime.timezone.utc).isoformat(timespec="seconds")


def month_of(moment: datetime.datetime) -> str:
    return moment.astimezone(datetime.timezone.utc).strftime("%Y-%m")


class Store:
    def __init__(self, path: str) -> None:
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._db.execute("PRAGMA foreign_keys = ON")
            self._db.executescript(SCHEMA)
            self._add_consent_column()

    def _add_consent_column(self) -> None:
        """`CREATE TABLE IF NOT EXISTS` leaves a database from before MIN-401 as it is."""
        columns = {row["name"] for row in self._db.execute("PRAGMA table_info(accesses)")}
        if "consent" not in columns:
            self._db.execute("ALTER TABLE accesses ADD COLUMN consent TEXT NOT NULL DEFAULT ''")

    def _run(self, sql: str, args: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._db.execute(sql, args)

    # people

    def add_person(self, name: str, budget_usd: float, now: datetime.datetime) -> None:
        name = name.strip()
        if not name:
            raise StoreError("Name der Person fehlt (am besten ein Kürzel wie T01, kein echter Name).")
        if budget_usd < 0:
            raise StoreError("Budget darf nicht negativ sein.")
        try:
            self._run("INSERT INTO people VALUES (?, ?, ?)", (name, budget_usd, _iso(now)))
        except sqlite3.IntegrityError as error:
            raise StoreError(f"Person {name} gibt es schon.") from error

    def has_person(self, name: str) -> bool:
        return self._run("SELECT 1 FROM people WHERE name = ?", (name,)).fetchone() is not None

    def set_budget(self, name: str, budget_usd: float) -> None:
        if budget_usd < 0:
            raise StoreError("Budget darf nicht negativ sein.")
        if self._run("UPDATE people SET budget_usd = ? WHERE name = ?", (budget_usd, name)).rowcount != 1:
            raise StoreError(f"Person {name} gibt es nicht.")

    def people(self) -> list[dict]:
        return [dict(row) for row in self._run("SELECT name, budget_usd, created FROM people ORDER BY name")]

    # invitations and accesses

    def create_invitation(self, name: str, now: datetime.datetime, days: int = INVITATION_DAYS) -> str:
        if not 1 <= days <= MAX_INVITATION_DAYS:
            raise StoreError(f"Gültigkeit in Tagen: 1 bis {MAX_INVITATION_DAYS}.")
        if not self.has_person(name):
            raise StoreError(f"Person {name} gibt es nicht.")
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        expires = now + datetime.timedelta(days=days)
        self._run("INSERT INTO invitations VALUES (?, ?, ?, ?, NULL)", (_hash(code), name, _iso(now), _iso(expires)))
        return "-".join(code[i:i + CODE_GROUP] for i in range(0, CODE_LENGTH, CODE_GROUP))

    def redeem(self, code: str, device: str, now: datetime.datetime, consent: str = "") -> str:
        """A new access for the person of the code; the code is used up. StoreError if invalid or expired."""
        code_hash = _hash(normalize_code(code))
        token = "bwa_" + secrets.token_urlsafe(32)
        receipt = consent if CONSENT_RECEIPT.fullmatch(consent) else ""
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                row = self._db.execute(
                    "UPDATE invitations SET used = ? WHERE code_hash = ? AND used IS NULL AND expires > ? "
                    "RETURNING person", (_iso(now), code_hash, _iso(now))).fetchone()
                if row is None:
                    raise StoreError("Der Code gilt nicht (falsch, schon benutzt oder abgelaufen).")
                self._db.execute("INSERT INTO accesses (token_hash, person, device, created, consent) VALUES (?, ?, ?, ?, ?)",
                                 (_hash(token), row["person"], device.strip()[:60] or "Gerät", _iso(now), receipt))
                self._db.execute("COMMIT")
            except Exception:
                self._db.execute("ROLLBACK")
                raise
        return token

    def authenticate(self, token: str, now: datetime.datetime) -> Access | None:
        row = self._run(
            "SELECT a.id, a.person, p.budget_usd FROM accesses a JOIN people p ON p.name = a.person "
            "WHERE a.token_hash = ? AND a.revoked IS NULL", (_hash(token),)).fetchone()
        if row is None:
            return None
        self._run("UPDATE accesses SET last_used = ? WHERE id = ?", (_iso(now), row["id"]))
        return Access(row["id"], row["person"], row["budget_usd"])

    def revoke(self, name: str, now: datetime.datetime, access_id: int | None = None) -> int:
        """Revoke all accesses of a person, or one of them; returns how many were revoked."""
        sql = "UPDATE accesses SET revoked = ? WHERE person = ? AND revoked IS NULL"
        args: tuple = (_iso(now), name)
        if access_id is not None:
            sql, args = sql + " AND id = ?", args + (access_id,)
        return self._run(sql, args).rowcount

    def accesses(self, name: str) -> list[dict]:
        return [dict(row) for row in self._run(
            "SELECT id, device, created, last_used, revoked, consent FROM accesses WHERE person = ? ORDER BY id", (name,))]

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
        row = self._run("SELECT COALESCE(SUM(cost_usd), 0) AS total FROM usage WHERE person = ? AND time LIKE ?",
                        (name, month + "%")).fetchone()
        return round(row["total"], 6)

    def costs(self, month: str) -> list[dict]:
        return [dict(row) for row in self._run(
            "SELECT p.name AS person, p.budget_usd, COUNT(u.id) AS calls, "
            "COALESCE(SUM(u.cost_usd), 0) AS cost_usd FROM people p "
            "LEFT JOIN usage u ON u.person = p.name AND u.time LIKE ? GROUP BY p.name ORDER BY p.name",
            (month + "%",))]

"""Administration of the mediation (MIN-344), on the server: `python admin.py <befehl>`.

  einladen T01 [--budget 20]     Person anlegen (falls neu) und Einladungscode ausgeben (7 Tage gültig)
  sperren T01 [--zugang 3]       alle Zugänge der Person sperren, oder nur einen (pro Gerät)
  budget T01 30                  Budget pro Monat in USD ändern
  zugaenge T01                   Zugänge mit Gerät, erstellt, zuletzt genutzt, gesperrt
  kosten [--monat 2026-11]       Kosten pro Person im Monat

Personen nur mit Kürzel anlegen (z.B. T01), nicht mit echtem Namen.
"""
import argparse
import datetime
import os
import sys

from store import Store, StoreError, month_of

DEFAULT_BUDGET_USD = 20.0
LINK = "bewerbungsassistent://einladung?code={code}"


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def invite(store: Store, args, now: datetime.datetime) -> str:
    if not store.has_person(args.person):
        store.add_person(args.person, args.budget, now)
    code = store.create_invitation(args.person, now)
    return f"Code für {args.person}: {code}\nLink: {LINK.format(code=code)}\nGültig 7 Tage, nur einmal."


def revoke(store: Store, args, now: datetime.datetime) -> str:
    count = store.revoke(args.person, now, args.zugang)
    return f"{count} Zugang/Zugänge von {args.person} gesperrt."


def budget(store: Store, args, now: datetime.datetime) -> str:
    store.set_budget(args.person, args.usd)
    return f"Budget von {args.person}: {args.usd:.2f} USD pro Monat."


def accesses(store: Store, args, now: datetime.datetime) -> str:
    rows = store.accesses(args.person)
    lines = [f"{r['id']:>4}  {r['device']:<20} erstellt {r['created']}  zuletzt {r['last_used'] or '–'}"
             f"{'  GESPERRT ' + r['revoked'] if r['revoked'] else ''}" for r in rows]
    return "\n".join(lines) or f"{args.person} hat keine Zugänge."


def costs(store: Store, args, now: datetime.datetime) -> str:
    month = args.monat or month_of(now)
    rows = store.costs(month)
    lines = [f"{r['person']:<8} {r['calls']:>5} Aufrufe  {r['cost_usd']:>8.2f} von {r['budget_usd']:.2f} USD"
             for r in rows]
    return f"Kosten {month}:\n" + ("\n".join(lines) or "keine Personen")


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Verwaltung der KI-Vermittlung")
    ap.add_argument("--db", default=os.environ.get("VERMITTLUNG_DB", "/data/vermittlung.sqlite"))
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("einladen")
    p.add_argument("person")
    p.add_argument("--budget", type=float, default=DEFAULT_BUDGET_USD)
    p.set_defaults(run=invite)
    p = sub.add_parser("sperren")
    p.add_argument("person")
    p.add_argument("--zugang", type=int)
    p.set_defaults(run=revoke)
    p = sub.add_parser("budget")
    p.add_argument("person")
    p.add_argument("usd", type=float)
    p.set_defaults(run=budget)
    p = sub.add_parser("zugaenge")
    p.add_argument("person")
    p.set_defaults(run=accesses)
    p = sub.add_parser("kosten")
    p.add_argument("--monat")
    p.set_defaults(run=costs)
    return ap


def main(argv: list[str] | None = None, now=_now) -> str:
    args = parser().parse_args(argv)
    try:
        return args.run(Store(args.db), args, now())
    except StoreError as error:
        sys.exit(str(error))


if __name__ == "__main__":
    print(main())

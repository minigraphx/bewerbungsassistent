"""Administration of the mediation (MIN-344), on the server: `python admin.py <command>`.

  invite T01 [--credit 5] [--days 45 | --weeks 6 | --months 2]
                                 Person anlegen (falls neu) und Einladungscode ausgeben: einmaliges Guthaben
                                 in CHF (Standard 5, G80), gültig 45 Tage; aufgebraucht braucht es einen neuen Code
  revoke T01 [--access 3]        alle Zugänge und offenen Einladungen der Person sperren, oder nur einen Zugang
  accesses T01                   Zugänge mit Gerät, Guthaben, erstellt, zuletzt genutzt, Einwilligung, gesperrt
  costs [--month 2026-11]        Kosten pro Person im Monat in CHF (1 USD von Anthropic zählt als 1 CHF)
  due                            Personen, deren Daten zu löschen sind (Sperrung vor 30 Tagen oder länger)
  forget T01 [--yes]             gesperrte Person samt Kostenprotokollen löschen; ohne --yes nur anzeigen

Personen nur mit Kürzel anlegen (z.B. T01), nicht mit echtem Namen.
"""
import argparse
import calendar
import datetime
import os
import sys

from store import (INVITATION_DAYS, MAX_INVITATION_DAYS, RETENTION_DAYS, TRIAL_CREDIT_CHF, Store, StoreError,
                   check_credit, month_of)

LINK = "bewerbungsbegleiter://einladung?code={code}"


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def add_months(moment: datetime.datetime, months: int) -> datetime.datetime:
    """Same day `months` calendar months later; the last day of the month when that day is missing."""
    index = moment.month - 1 + months
    year, month = moment.year + index // 12, index % 12 + 1
    return moment.replace(year=year, month=month, day=min(moment.day, calendar.monthrange(year, month)[1]))


def validity_days(args, now: datetime.datetime) -> int:
    if args.months is not None:
        return (add_months(now, args.months) - now).days if args.months > 0 else 0
    if args.weeks is not None:
        return args.weeks * 7
    return args.days if args.days is not None else INVITATION_DAYS


def invite(store: Store, args, now: datetime.datetime) -> str:
    days = validity_days(args, now)
    if not 1 <= days <= MAX_INVITATION_DAYS:
        raise StoreError(f"Gültigkeit: 1 bis {MAX_INVITATION_DAYS} Tage (höchstens 12 Monate).")
    check_credit(args.credit)
    if not store.has_person(args.person):
        store.add_person(args.person, now)
    code = store.create_invitation(args.person, now, days, args.credit)
    until = (now + datetime.timedelta(days=days)).astimezone(datetime.timezone.utc).strftime("%d.%m.%Y")
    return (f"Code für {args.person}: {code}\nLink: {LINK.format(code=code)}\nGültig bis {until} (UTC), nur einmal."
            f"\nGuthaben CHF {args.credit:.2f}, einmalig.")


def revoke(store: Store, args, now: datetime.datetime) -> str:
    count = store.revoke(args.person, now, args.access)
    voided = store.void_invitations(args.person, now) if args.access is None else 0
    return f"{count} Zugang/Zugänge von {args.person} gesperrt, {voided} offene Einladung(en) ungültig."


def accesses(store: Store, args, now: datetime.datetime) -> str:
    rows = store.accesses(args.person)
    lines = [f"{r['id']:>4}  {r['device']:<20} Guthaben CHF {r['spent_chf']:.2f} von {r['credit_chf']:.2f}"
             f"  erstellt {r['created']}  zuletzt {r['last_used'] or '–'}"
             f"  Einwilligung {r['consent'] or '–'}"
             f"{'  GESPERRT ' + r['revoked'] if r['revoked'] else ''}" for r in rows]
    return "\n".join(lines) or f"{args.person} hat keine Zugänge."


def costs(store: Store, args, now: datetime.datetime) -> str:
    month = args.month or month_of(now)
    rows = store.costs(month)
    lines = [f"{r['person']:<8} {r['calls']:>5} Aufrufe  {r['cost_chf']:>8.2f} CHF" for r in rows]
    return f"Kosten {month}:\n" + ("\n".join(lines) or "keine Personen")


def due(store: Store, args, now: datetime.datetime) -> str:
    rows = store.due_for_deletion(now)
    lines = [f"{r['person']:<8} gesperrt {r['revoked']}" for r in rows]
    return "\n".join(lines) or f"Niemand: keine Sperrung liegt {RETENTION_DAYS} Tage oder länger zurück."


def _summary(rows: dict) -> str:
    return f"{rows['usage']} Aufrufe, {rows['accesses']} Zugänge, {rows['invitations']} Einladungen"


def forget(store: Store, args, now: datetime.datetime) -> str:
    if not args.yes:
        return (f"Würde {args.person} löschen: {_summary(store.holdings(args.person))}. "
                "Vorher auswerten (costs), das lässt sich nicht rückgängig machen. Löschen mit --yes.")
    return f"{args.person} gelöscht: {_summary(store.forget(args.person))}."


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Verwaltung der KI-Vermittlung")
    ap.add_argument("--db", default=os.environ.get("VERMITTLUNG_DB", "/data/vermittlung.sqlite"))
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("invite", help="Person anlegen und Einladungscode ausgeben")
    p.add_argument("person")
    p.add_argument("--credit", type=float, default=TRIAL_CREDIT_CHF,
                   help=f"einmaliges Guthaben in CHF (Standard {TRIAL_CREDIT_CHF:.0f})")
    validity = p.add_mutually_exclusive_group()
    validity.add_argument("--days", type=int, help=f"Gültigkeit in Tagen (Standard {INVITATION_DAYS})")
    validity.add_argument("--weeks", type=int, help="Gültigkeit in Wochen")
    validity.add_argument("--months", type=int, help="Gültigkeit in Kalendermonaten")
    p.set_defaults(run=invite)
    p = sub.add_parser("revoke", help="Zugänge sperren")
    p.add_argument("person")
    p.add_argument("--access", type=int, help="nur diesen Zugang (ID aus accesses)")
    p.set_defaults(run=revoke)
    p = sub.add_parser("accesses", help="Zugänge einer Person")
    p.add_argument("person")
    p.set_defaults(run=accesses)
    p = sub.add_parser("costs", help="Kosten pro Person im Monat, in CHF")
    p.add_argument("--month", help="JJJJ-MM, Standard: laufender Monat (UTC)")
    p.set_defaults(run=costs)
    p = sub.add_parser("due", help="Personen, deren Daten zu löschen sind")
    p.set_defaults(run=due)
    p = sub.add_parser("forget", help="gesperrte Person samt Kostenprotokollen löschen")
    p.add_argument("person")
    p.add_argument("--yes", action="store_true", help="wirklich löschen, sonst nur anzeigen")
    p.set_defaults(run=forget)
    return ap


def main(argv: list[str] | None = None, now=_now) -> str:
    args = parser().parse_args(argv)
    try:
        return args.run(Store(args.db), args, now())
    except StoreError as error:
        sys.exit(str(error))


if __name__ == "__main__":
    print(main())

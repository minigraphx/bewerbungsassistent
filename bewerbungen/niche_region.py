"""Niche searches respect the region unless the ad names remote work (G111, #387), only for a job search.

Niches run without a place (jobs.ch without a town, job-room without cantons), so they search the whole country. A
hit that only niche searches found stays if its place lies in the profile's chosen cantons («Kantone (job-room)») or
at the places `hits.is_near` counts as home, or if its title or ad text names remote work. A remote mention keeps it
also when the profile says «Remote: nein» (Andy, 22.11.2026); the commuting limit itself stays prose for the AI. The
person can switch the remote mention off (G125, #390): «- Nischen mit Remote ausserhalb der Region: aussortieren»
under Region, set on Suche einstellen. Then such a hit counts with the reason «ausserhalb der Region».

The canton of a place comes from the fixed table in `place_cantons`; a place the app does not know for sure, or names
only «Homeoffice», «Remote» or «Schweiz», keeps the hit, and with several places one inside or unknown is enough.
Without chosen cantons the rule is off. Like the required words (G110), the ad text is asked at add time, when it
arrives: a hit outside is not stored, its link waits in `ausserhalb-region.yaml` with the region it lay outside of, and
the next screening counts it from its title without loading it again, until cantons or places change. A link kept out
while the switch was off carries that in its fingerprint, so turning the switch back on asks for its ad again; one kept
out while it was on stays out when it goes off, for it named no remote work either.
"""
import dataclasses
import pathlib
import re

import hits  # read only when called, so that hits may import this module
import place_cantons
import screened_links
import search_plan

REASON = "ausserhalb der Region, kein Remote"
REASON_OFF = "ausserhalb der Region"  # G125: with the switch off a remote mention does not count
REASONS = (REASON, REASON_OFF)
REMOTE_OFF = "remote:aus"  # in the fingerprint of a link kept out while the switch was off
LINKS_FILE = "ausserhalb-region.yaml"
COUNTED = "ausserhalb_region"  # how many, per query in the log and in the answer of hits.add
COUNTED_PLACES = "ausserhalb_orte"  # per query in the log: place name → how many lay there
MAX_PLACE_NAME = 80
_HOME_OFFICE = r"home[\s-]?office"
# Erring toward keeping: any case, any spaces, «100%» as well as «100 %», and «remote» at the start of a word.
REMOTE = re.compile(rf"\bremote|{_HOME_OFFICE}\W{{0,3}}100\s*%|\b100\s*%\W{{0,3}}{_HOME_OFFICE}|ortsunabh[aä]ngig|t[ée]l[ée]travail",
                    re.IGNORECASE)
# A place that only says where the work is not bound to, or the whole country
ANYWHERE = re.compile(rf"\b(?:{_HOME_OFFICE}|remote|ganze schweiz)\b", re.IGNORECASE)
COUNTRY = frozenset({"schweiz", "suisse", "svizzera", "switzerland", "ch"})
PARTS = re.compile(r"\s*(?:[,;/|&+]|\bund\b|\boder\b|\bet\b)\s*", re.IGNORECASE)

Key = frozenset[str]


def mentions_remote(*texts: str) -> bool:
    """Whether a title or an ad text names remote work: remote, Homeoffice 100 %, ortsunabhängig, télétravail."""
    return any(REMOTE.search(text) for text in texts if text)


def _parts(place: str) -> list[str]:
    """The places of a place string, without the country a portal may add («Lugano, Schweiz»)."""
    return [part for part in PARTS.split(place or "") if part.strip() and part.strip().casefold() not in COUNTRY]


def place_name(place: str) -> str:
    """The place as the yield names it: its first part, without postcode, «CH-» and brackets."""
    first = next(iter(_parts(place)), place or "")
    return " ".join(place_cantons.NOISE.sub(" ", first).split())[:MAX_PLACE_NAME]


@dataclasses.dataclass(frozen=True)
class Region:
    """What counts as inside for niche hits; empty cantons switch the rule off."""
    cantons: frozenset[str] = frozenset()
    homes: tuple[str, ...] = ()
    postal_codes: tuple[str, ...] = ()
    niches: frozenset[Key] = frozenset()  # the niche terms not also in the term list, by their words
    remote_keeps: bool = True  # G125: a remote mention keeps a hit outside

    @property
    def active(self) -> bool:
        return bool(self.cantons and self.niches)

    @property
    def reason(self) -> str:
        return REASON if self.remote_keeps else REASON_OFF

    def niche_only(self, queries) -> bool:
        """Every query that found the hit was a niche search without a place; a hit without queries (an older
        extension) is not one."""
        found = [query for query in queries or [] if isinstance(query, dict) and isinstance(query.get("stichwort"), str)]
        return bool(found) and all(not query.get("ort") and search_plan.profession_words(query["stichwort"]) in self.niches
                                   for query in found)

    def _part_inside(self, part: str) -> bool:
        if hits.is_near(part, self.homes, self.postal_codes):
            return True
        canton = place_cantons.canton_in(part)
        return canton is None or canton in self.cantons

    def inside(self, place: str) -> bool:
        """Whether a place keeps the hit: in the region, at home, unknown or ambiguous, or bound to no place."""
        if not (place or "").strip() or ANYWHERE.search(place) or hits.is_near(place, self.homes, self.postal_codes):
            return True
        parts = _parts(place)
        return not parts or any(self._part_inside(part) for part in parts)

    def _area(self) -> list[str]:
        areas = {f"plz:{code[:2]}" for code in self.postal_codes}
        return sorted({*(f"kanton:{c}" for c in self.cantons), *(f"ort:{h.casefold()}" for h in self.homes), *areas})

    def fingerprint(self) -> list[str]:
        """The region a link lay outside of: another canton, home or postal area asks for the ad again, and so does
        turning the remote switch back on (G125). With it on, the fingerprint is the one of 0.3.3."""
        return self._area() if self.remote_keeps else [*self._area(), REMOTE_OFF]

    def screened_by(self, fingerprint: list[str] | None) -> bool:
        """Whether a link remembered with this fingerprint stays out now: kept out for this region, with the switch
        as now or, now that it is off, while it was on."""
        return fingerprint is not None and fingerprint in (self.fingerprint(), self._area())

    def keeps(self, hit: dict, *texts: str) -> bool:
        """Whether this hit stays: the rule is off, it is no niche hit, it lies inside, or title or text name remote
        while the switch lets that count."""
        return (not self.active or not self.niche_only(hit.get(hits.QUERIES, [])) or self.inside(hit.get("ort", ""))
                or (self.remote_keeps and mentions_remote(hit.get("stelle", ""), *texts)))


OFF = Region()


def of_plan(plan: search_plan.SearchPlan) -> Region:
    """The region of a job search; none for apprenticeships, which search by radius and have no niches."""
    if plan.kind == search_plan.KIND_APPRENTICESHIP or not plan.cantons:
        return OFF
    listed = {search_plan.profession_words(term) for term in plan.keywords}
    niches = frozenset(key for key in map(search_plan.profession_words, plan.niche_keywords) if key and key not in listed)
    return Region(frozenset(plan.cantons), plan.places, plan.postal_codes, niches, plan.niche_remote_kept)


def of_folder(data_dir: pathlib.Path) -> Region:
    try:
        return of_plan(search_plan.for_folder(data_dir))
    except ValueError:  # a profile that searches nothing yet has no region to speak of
        return OFF


def remembered(folder: pathlib.Path, region: Region) -> dict[str, list[str]]:
    return screened_links.remembered(folder, LINKS_FILE) if region.active else {}


def screened_again(region: Region, hit: dict, link: str, known: dict[str, list[str]]) -> str:
    """The reason for a niche hit screened out before for this same region whose title still does not keep it (G125:
    with the switch off, not even a remote title does); it is not loaded again. '' for any other hit, which is left
    to its ad text."""
    if not known or region.keeps(hit) or not region.screened_by(known.get(link)):
        return ""
    return region.reason


def remember(folder: pathlib.Path, region: Region, links: list[str]) -> None:
    """Note the links outside; the caller holds the lock of the hits."""
    screened_links.remember(folder, LINKS_FILE, [(link, region.fingerprint()) for link in links])

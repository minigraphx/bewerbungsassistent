"""The hint on shared query limits names each place's real share (#195), with invented places."""
import search_plan

KEYWORDS = ", ".join(f"Begriff{number}" for number in range(1, 16))
PROFILE = f"""# Suchprofil

## Region
- Kantone (job-room): BE
- Orte (jobs.ch): Nordstadt, Südstadt, Oststadt, Weststadt
- PLZ (jobscout24): 1111, 2222, 3333, 4444
- Regionen (ictjobs): grossraum-bern

## Keywords
- Kernliste: {KEYWORDS}
- Nischen (ohne Ort suchen): Nische1, Nische2, Nische3, Nische4, Nische5, Nische6
"""


def hint(portal: str) -> str:
    [found] = [h for h in search_plan.parse(PROFILE).hints if h.startswith(f"{portal}:")]
    return found


def test_uneven_shares_name_each_places_number():
    assert hint("jobscout24") == ("jobscout24: 30 Suchen reichen nicht für alle 15 Begriffe in 4 Orten; in 1111 und 2222 laufen "
                                  "die ersten 8, in 3333 und 4444 die ersten 7. Wichtige Begriffe nach vorne stellen.")


def test_an_even_split_names_the_single_number():
    assert hint("jobs.ch") == ("jobs.ch: 30 Suchen reichen nicht für alle 15 Begriffe in 4 Orten; pro Ort laufen die ersten 6. "
                               "Wichtige Begriffe nach vorne stellen.")


def test_the_first_places_take_the_remainder():
    text = PROFILE.replace("Oststadt, Weststadt", "Oststadt, Weststadt, Mittelstadt")
    [found] = [h for h in search_plan.parse(text).hints if h.startswith("jobs.ch:")]
    assert "in Nordstadt, Südstadt, Oststadt und Weststadt laufen die ersten 5, in Mittelstadt die ersten 4." in found

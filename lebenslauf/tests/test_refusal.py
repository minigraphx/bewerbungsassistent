"""A refusal of the data: German text with its template and values for the app (#453, #455)."""
import pathlib

import pytest

import build
from refusal import Refusal


def test_a_refusal_fills_its_placeholders_and_keeps_its_template_and_values():
    refused = Refusal("Foto nicht gefunden: {pfad}", pfad=pathlib.Path("/daten/foto.png"))

    assert isinstance(refused, ValueError)
    assert str(refused) == "Foto nicht gefunden: /daten/foto.png"
    assert refused.template == "Foto nicht gefunden: {pfad}"
    assert refused.values == {"pfad": pathlib.Path("/daten/foto.png")}


def test_braces_that_are_no_placeholder_stay_as_written():
    refused = Refusal("basics.x-image muss eine Zuordnung sein, z.B. {mirror: true, zoom: 1.3}")

    assert str(refused) == "basics.x-image muss eine Zuordnung sein, z.B. {mirror: true, zoom: 1.3}"


def test_a_crop_refusal_is_german_and_carries_its_template_and_values():
    with pytest.raises(Refusal) as refused:
        build.pruefe_foto_optionen({"zoom": 5})

    assert str(refused.value) == "basics.x-image.zoom muss eine Zahl von 1 bis 4 sein, nicht 5"
    assert refused.value.template == "basics.x-image.{feld} muss eine Zahl von {unten} bis {oben} sein, nicht {wert}"
    assert refused.value.values == {"feld": "zoom", "unten": 1, "oben": 4, "wert": "5"}

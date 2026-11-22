"""The canton of a place for jobs.ch (G107, #380): jobs.ch searches a place together with its whole canton.

Only places whose canton is certain are listed: the larger towns of Switzerland, each checked on 22.11.2026 against
swisstopo's official list of municipalities (api3.geo.admin.ch SearchServer, origin gg25: exactly one municipality of
that name) and against jobs.ch's own place lookup (no place of the same name in another canton). Names left out because
they are not unique, such as Buchs, Wil, Gossau, Reinach, Biel, Muri or Wohlen, get no canton, and neither does any
place not listed: the app then says nothing rather than guess. The niche rule of G111 reads the same table, with the
cantons' own names and codes as the portals write them beside a place.
"""
import re

CANTON_NAMES = {
    "AG": "Aargau", "AI": "Appenzell Innerrhoden", "AR": "Appenzell Ausserrhoden", "BE": "Bern", "BL": "Basel-Landschaft",
    "BS": "Basel-Stadt", "FR": "Freiburg", "GE": "Genf", "GL": "Glarus", "GR": "Graubünden", "JU": "Jura", "LU": "Luzern",
    "NE": "Neuenburg", "NW": "Nidwalden", "OW": "Obwalden", "SG": "St. Gallen", "SH": "Schaffhausen", "SO": "Solothurn",
    "SZ": "Schwyz", "TG": "Thurgau", "TI": "Tessin", "UR": "Uri", "VD": "Waadt", "VS": "Wallis", "ZG": "Zug", "ZH": "Zürich",
}
_PLACES = {
    "AG": "Aarau, Baden, Wettingen, Brugg, Oftringen, Rheinfelden, Spreitenbach, Lenzburg, Zofingen, Obersiggenthal, "
          "Neuenhof, Suhr",
    "AI": "Appenzell",
    "AR": "Herisau",
    "BE": "Bern, Bienne, Thun, Köniz, Burgdorf, Ostermundigen, Steffisburg, Langenthal, Spiez, Muri bei Bern, Ittigen, "
          "Worb, Lyss, Münsingen, Zollikofen, Belp, Wohlen bei Bern",
    "BL": "Allschwil, Muttenz, Pratteln, Binningen, Liestal, Münchenstein, Birsfelden",
    "BS": "Basel, Riehen",
    "FR": "Fribourg, Bulle, Villars-sur-Glâne, Marly, Murten, Düdingen",
    "GE": "Genève, Genf, Vernier, Lancy, Meyrin, Carouge, Onex, Thônex, Versoix, Le Grand-Saconnex, Plan-les-Ouates",
    "GL": "Glarus, Glarus Nord",
    "GR": "Chur, Davos",
    "JU": "Moutier, Delémont, Porrentruy",
    "LU": "Luzern, Emmen, Kriens, Horw, Ebikon, Sursee",
    "NE": "Neuchâtel, La Chaux-de-Fonds, Le Locle",
    "NW": "Stans",
    "OW": "Sarnen",
    "SG": "St. Gallen, Rapperswil-Jona, Uzwil, Altstätten, Flawil, Wattwil, Rorschach",
    "SH": "Schaffhausen, Neuhausen am Rheinfall",
    "SO": "Solothurn, Olten",
    "SZ": "Schwyz, Einsiedeln, Küssnacht, Arth",
    "TG": "Frauenfeld, Kreuzlingen, Arbon, Amriswil, Weinfelden, Romanshorn",
    "TI": "Lugano, Bellinzona, Locarno, Mendrisio, Chiasso, Minusio",
    "VD": "Lausanne, Yverdon-les-Bains, Montreux, Renens, Nyon, Vevey, Pully, Morges, Gland, Prilly, La Tour-de-Peilz, Aigle",
    "VS": "Sion, Sierre, Martigny, Monthey, Brig-Glis, Visp, Naters, Collombey-Muraz",
    "ZG": "Zug, Cham, Risch, Steinhausen",
    "ZH": "Zürich, Winterthur, Uster, Dübendorf, Dietikon, Wädenswil, Kloten, Bülach, Horgen, Thalwil, Regensdorf, Opfikon, "
          "Adliswil, Illnau-Effretikon, Volketswil, Küsnacht, Wallisellen, Stäfa, Richterswil, Männedorf, Zollikon, Hinwil, "
          "Bassersdorf, Affoltern am Albis",
}


# G111, #387: the names the portals give a canton itself, in the languages of Switzerland
_CANTON_NAMES = {
    "AG": "Aargau, Argovie", "AI": "Appenzell Innerrhoden", "AR": "Appenzell Ausserrhoden", "BE": "Bern, Berne",
    "BL": "Basel-Landschaft, Baselland, Bâle-Campagne", "BS": "Basel-Stadt, Bâle-Ville", "FR": "Freiburg",
    "GE": "Genf, Genève, Geneva", "GL": "Glarus", "GR": "Graubünden, Grisons, Grigioni", "JU": "Jura",
    "LU": "Luzern, Lucerne", "NE": "Neuenburg, Neuchâtel", "NW": "Nidwalden", "OW": "Obwalden", "SG": "St. Gallen",
    "SH": "Schaffhausen", "SO": "Solothurn, Soleure", "SZ": "Schwyz", "TG": "Thurgau, Thurgovie", "TI": "Tessin, Ticino",
    "UR": "Uri", "VD": "Waadt, Vaud", "VS": "Wallis, Valais", "ZG": "Zug, Zoug", "ZH": "Zürich, Zurich",
}
_CANTON_WORD = re.compile(r"^(?:kanton|canton|cantone)\s+", re.IGNORECASE)
_CODE = re.compile(r"\b[A-Z]{2}\b")
NOISE = re.compile(r"\bCH-|\d+|\([^()]*\)")  # what a place string carries beside the name: «CH-», postcode, brackets


def _key(place: str) -> str:
    return " ".join(place.split()).lower().replace("st. ", "st.").replace("sankt ", "st.")


CANTON_OF = {_key(place): canton for canton, places in _PLACES.items() for place in places.split(", ")}
CANTON_BY_NAME = {_key(name): canton for canton, names in _CANTON_NAMES.items() for name in names.split(", ")}


def canton_of(place: str) -> str | None:
    """The canton of a place as the profile writes it, or None where the app cannot be sure."""
    return CANTON_OF.get(_key(place))


def canton_in(place: str) -> str | None:
    """The canton of one place as a portal writes it (G111): «6900 Lugano», «Lugano TI», «Lugano (TI)», «Kanton
    Tessin»; a canton code counts when it is the only one, else the name without postcode and brackets. None where
    the app cannot be sure, as for `canton_of`."""
    codes = {code for code in _CODE.findall(place) if code in CANTON_NAMES}
    if len(codes) == 1:
        return codes.pop()
    if codes:
        return None
    name = _CANTON_WORD.sub("", " ".join(NOISE.sub(" ", place).split()).strip(" -,"))
    return canton_of(name) or CANTON_BY_NAME.get(_key(name))

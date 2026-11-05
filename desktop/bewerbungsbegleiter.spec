# PyInstaller: the local app as one folder with Python, Typst, themes and fonts (MIN-342).
#   pyinstaller desktop/bewerbungsbegleiter.spec   (from the repo root)
# Modules of bewerbungen/, lebenslauf/, onboarding/ and desktop/ land side by side; their files keep the
# folder names the code expects next to the modules (seiten/, typst/, themes/, fonts/, data/, form.json).
import pathlib
import sys

from PyInstaller.utils.hooks import collect_submodules

REPO = pathlib.Path(SPECPATH).resolve().parent
MODULES = [REPO / name for name in ("desktop", "bewerbungen", "lebenslauf", "onboarding")]
NAME = "Bewerbungsbegleiter"

datas = [
    (str(REPO / "bewerbungen" / "seiten"), "seiten"),
    (str(REPO / "bewerbungen" / "typst"), "typst"),
    (str(REPO / "lebenslauf" / "themes"), "themes"),
    (str(REPO / "lebenslauf" / "fonts"), "fonts"),
    (str(REPO / "lebenslauf" / "data"), "data"),
    (str(REPO / "onboarding" / "form.json"), "."),
    (str(REPO / "vorlagen"), "vorlagen"),
    (str(REPO / "skills"), "skills"),
]
# The browser extension as developer add-on (MIN-339), without its tests
EXTENSION = REPO / "erweiterung"
datas += [(str(f), str(pathlib.Path("erweiterung") / f.parent.relative_to(EXTENSION)))
          for f in sorted(EXTENSION.rglob("*")) if f.is_file() and "tests" not in f.relative_to(EXTENSION).parts]
defaults = REPO / "desktop" / "build" / "voreinstellungen.json"  # written by the CI, see desktop/README.md
if defaults.is_file():
    datas.append((str(defaults), "."))

hidden = (collect_submodules("keyring.backends") + collect_submodules("ai")
          + ["routen_ablage", "routen_bewerbungen", "routen_foto", "routen_inhalte", "routes_ai", "routes_search", "routes_own_key", "routes_claude", "claude_setup", "mcp_server", "mcp_tools", "routes_sites", "own_sites", "search_plan", "hits", "app",
             "selftest"])

a = Analysis(
    [str(REPO / "desktop" / "start.py")],
    pathex=[str(p) for p in MODULES],
    datas=datas,
    hiddenimports=hidden,
    excludes=["tkinter", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    console=False,  # no black window; messages go to protokoll.txt in the app folder
    icon=None,
)
coll = COLLECT(exe, a.binaries, a.datas, name=NAME)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{NAME}.app",
        bundle_identifier="ch.bewerbungsbegleiter.app",
        info_plist={
            "CFBundleName": "Bewerbungsbegleiter",
            "CFBundleDisplayName": "Bewerbungsbegleiter",  # the file name stays: updates of installed versions rely on it
            "CFBundleURLTypes": [{"CFBundleURLName": "Einladung", "CFBundleURLSchemes": ["bewerbungsbegleiter"]}],
            "LSUIElement": True,  # no Dock icon: the interface is the browser
        },
    )

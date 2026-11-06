"""Start of the desktop app (MIN-342): double-click, the browser opens the local interface.

  Bewerbungsbegleiter.exe                         start, or open the running app
  Bewerbungsbegleiter.exe bewerbungsbegleiter://einladung?code=…   also redeem an invitation
  Bewerbungsbegleiter.exe --selbsttest            build a CV and a letter from example data, then exit
  Bewerbungsbegleiter.exe chrome-extension://…/    started by the browser for the extension (Native Messaging)
"""
import argparse
import logging
import os
import pathlib
import sys
import webbrowser

import extension
import instance
import mcp_server
import native_host
import native_messaging
import rename_migration
import settings
import setup
import updates_macos
import urlscheme

log = logging.getLogger("bewerbungsbegleiter")

FAILED_UPDATE_NOTE = "update-fehlgeschlagen.txt"


def bundle_dir() -> pathlib.Path:
    """Folder with the bundled files: next to the code, or PyInstaller's folder in the package."""
    return pathlib.Path(getattr(sys, "_MEIPASS", pathlib.Path(__file__).resolve().parent))


def _setup_logging(paths: settings.Paths) -> None:
    paths.app_dir.mkdir(parents=True, exist_ok=True)
    handlers = [logging.FileHandler(paths.log, encoding="utf-8")]
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", handlers=handlers, force=True)


def _apply_build_defaults(defaults: dict) -> None:
    """Addresses that come with the package; an environment variable still wins."""
    import os
    import updates
    from ai.connection import URL_VARIABLE
    from ai.consent import PAGE_VARIABLE
    for key, variable in (("ki_url", URL_VARIABLE), ("datenschutz_url", PAGE_VARIABLE), ("update_url", updates.URL_VARIABLE)):
        if defaults.get(key) and not os.environ.get(variable):
            os.environ[variable] = str(defaults[key])


def _redeem(kontext, code: str) -> None:
    """Through the route of the app: without the consent the code waits for it (MIN-401)."""
    import routes_ai
    try:
        routes_ai.redeem(kontext, {}, {"code": code})
        log.info("Einladung eingelöst")
    except ValueError as error:
        log.warning("Einladung nicht eingelöst: %s", error)


def _adopt_keychain() -> None:
    from ai.connection import adopt_old_keychain
    log.info("App-Ordner unter dem neuen Namen übernommen")
    adopt_old_keychain()


def parse(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Bewerbungsbegleiter")
    ap.add_argument("link", nargs="?", help="Einladungslink bewerbungsbegleiter://einladung?code=…")
    ap.add_argument("--selbsttest", action="store_true", help="Lebenslauf und Anschreiben probehalber bauen")
    ap.add_argument("--kein-browser", action="store_true", help="Browser nicht öffnen")
    ap.add_argument(updates_macos.CHECK_FLAG, action="store_true", help="Nach einem Update beim Beenden: Version prüfen, nichts öffnen")
    return ap.parse_args(argv)


def check_after_update() -> int:
    """The new version after an update on quitting (MIN-382): it loads, tells the swap and ends; no failure, no way back."""
    import selftest
    try:
        selftest.check_modules()
    except Exception as error:  # noqa: BLE001 (the swap brings the old version back)
        log.error("Neue Version unvollständig: %s", error)
        return 1
    updates_macos.confirm_started(updates_macos.running_app())
    return 0


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    if native_host.invoked(raw):
        paths = settings.Paths(settings.app_dir())
        _setup_logging(paths)
        return native_host.main(paths)
    if mcp_server.invoked(raw):
        paths = settings.Paths(settings.app_dir())
        _setup_logging(paths)
        return mcp_server.main(paths)
    args = parse(argv)
    if args.selbsttest:
        import selftest
        return selftest.run()
    if args.nach_update:
        return check_after_update()
    paths = settings.Paths(settings.app_dir())
    adopted = rename_migration.adopt_app_folder(paths.app_dir)  # before the log creates the new folder
    _setup_logging(paths)
    if adopted:
        _adopt_keychain()
    code = urlscheme.invitation_code(args.link)
    running = instance.find(paths)
    if running is not None:
        problem = instance.forward_code(running, code) if code else None
        if problem:
            log.warning("Einladung nicht eingelöst: %s", problem)
        if not args.kein_browser:
            webbrowser.open(running.url)
        return 0
    return serve(paths, code, open_browser=not args.kein_browser)


def _install_dir() -> pathlib.Path:
    """Folder of the installed app (replaced by updates); in development the folder of this module."""
    return pathlib.Path(sys.executable).parent if getattr(sys, "frozen", False) else bundle_dir()


def _host_executable(paths: settings.Paths) -> pathlib.Path:
    if getattr(sys, "frozen", False):
        return pathlib.Path(sys.executable)
    return native_messaging.launcher(paths, sys.platform, bundle_dir(), pathlib.Path(sys.executable))


def prepare_extension(paths: settings.Paths) -> pathlib.Path | None:
    """Register the Native Messaging host and provide the extension folder; the app runs without them too."""
    frozen = getattr(sys, "frozen", False)
    try:
        native_messaging.forget_old_host()
        where = native_messaging.register(paths, _host_executable(paths))
        log.info("Native Messaging eingetragen: %s", ", ".join(where) or "kein Browser gefunden")
        return extension.install(paths, extension.source(bundle_dir(), frozen), frozen)
    except OSError as error:
        log.warning("Erweiterung nicht vorbereitet: %s", error)
        return None


def start_folder(paths: settings.Paths) -> pathlib.Path:
    """The chosen data folder, or a placeholder until one is chosen (or when it is gone, e.g. a USB stick)."""
    chosen = settings.chosen_data_dir(paths)
    if chosen is not None and chosen.is_dir():
        return chosen
    if chosen is not None:
        log.warning("Datenordner nicht gefunden: %s", chosen)
    return setup.placeholder_dir(paths)


def adopt_claude_entry(config: pathlib.Path, command: list[str]) -> None:
    """An entry under the old name would start a program that no longer exists; the start goes on without it."""
    import claude_setup
    try:
        if claude_setup.adopt_old_entry(config, command):
            log.info("Eintrag in Claude Desktop unter dem neuen Namen übernommen")
    except (OSError, ValueError) as error:
        log.warning("Eintrag in Claude Desktop nicht übernommen: %s", error)


def claude_routes(paths: settings.Paths) -> "routes_claude.ClaudeRoutes":
    import claude_setup
    import routes_claude
    command = claude_setup.server_command(_host_executable(paths))
    config = claude_setup.desktop_config(sys.platform, dict(os.environ), pathlib.Path.home())
    adopt_claude_entry(config, command)
    return routes_claude.ClaudeRoutes(paths=paths, config=config, command=tuple(command), skills=claude_setup.skills_folder(bundle_dir()))


def serve(paths: settings.Paths, code: str | None, open_browser: bool = True) -> int:
    import app  # the existing interface (bewerbungen/app.py)
    if getattr(sys, "frozen", False):
        urlscheme.register_windows(sys.executable)
    _apply_build_defaults(settings.build_defaults(bundle_dir()))
    import routes_app
    import routes_angaben
    import routes_claude
    import routes_ai
    import routes_setup
    data = start_folder(paths)
    holder: dict = {}
    controls = routes_app.Controls(stop=lambda: holder["server"].shutdown(), failed_note=paths.app_dir / FAILED_UPDATE_NOTE)

    def switch(folder: pathlib.Path) -> None:
        new_context = app.erstelle_kontext(folder)
        routes_ai.hand_over_waiting_code(holder["server"].kontext, new_context)
        holder["server"].kontext = new_context
        log.info("Datenordner gewechselt: %s", folder)

    state = routes_setup.Setup(paths=paths, switch=switch, suggestion=settings.documents_dir() / settings.SUGGESTED_DATA_FOLDER,
                               forbidden=(paths.app_dir, _install_dir()), extension_dir=prepare_extension(paths))
    app_get, app_post = routes_app.make_routes(controls)
    setup_get, setup_post = routes_setup.make_routes(state)
    angaben_get, angaben_post, limits = routes_angaben.make_routes(state)
    claude_get, claude_post = routes_claude.make_routes(claude_routes(paths))
    try:
        server = app.erstelle_server(data, extra_routes=({**app_get, **setup_get, **angaben_get, **claude_get},
                                                         {**app_post, **setup_post, **angaben_post, **claude_post}), body_limits=limits,
                                     questions_page=settings.questions_page(paths))
        holder["server"] = server
    except (ValueError, OSError) as error:
        log.error("Start nicht möglich: %s", error)
        return 1
    instance.write(paths, server.server_address[1], server.token)
    updates_macos.confirm_started(controls.app)
    if code:
        _redeem(server.kontext, code)
    log.info("Bewerbungsbegleiter läuft auf %s, Daten in %s", server.url, data)
    if open_browser:
        webbrowser.open(server.url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        instance.remove(paths)
    return 0


if __name__ == "__main__":
    sys.exit(main())

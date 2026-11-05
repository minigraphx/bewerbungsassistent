"""Start of the desktop app (MIN-342): double-click, the browser opens the local interface.

  Bewerbungsassistent.exe                         start, or open the running app
  Bewerbungsassistent.exe bewerbungsassistent://einladung?code=…   also redeem an invitation
  Bewerbungsassistent.exe --selbsttest            build a CV and a letter from example data, then exit
  Bewerbungsassistent.exe chrome-extension://…/    started by the browser for the extension (Native Messaging)
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
import settings
import setup
import updates_macos
import urlscheme

log = logging.getLogger("bewerbungsassistent")

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


def _use_mediation(defaults: dict) -> None:
    """The address of the mediation comes with the package; an environment variable still wins."""
    import os
    from ai.connection import URL_VARIABLE
    if defaults.get("ki_url") and not os.environ.get(URL_VARIABLE):
        os.environ[URL_VARIABLE] = str(defaults["ki_url"])


def _redeem(code: str) -> None:
    from ai import invitation
    from ai.connection import mediation_url
    from ai.errors import AiError
    try:
        url = mediation_url()
        if url:
            invitation.redeem(url, code)
            log.info("Einladung eingelöst")
    except AiError as error:
        log.warning("Einladung nicht eingelöst: %s", error)


def parse(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Bewerbungsassistent")
    ap.add_argument("link", nargs="?", help="Einladungslink bewerbungsassistent://einladung?code=…")
    ap.add_argument("--selbsttest", action="store_true", help="Lebenslauf und Anschreiben probehalber bauen")
    ap.add_argument("--kein-browser", action="store_true", help="Browser nicht öffnen")
    return ap.parse_args(argv)


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
    paths = settings.Paths(settings.app_dir())
    _setup_logging(paths)
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


def claude_routes(paths: settings.Paths) -> "routes_claude.ClaudeRoutes":
    import claude_setup
    import routes_claude
    command = claude_setup.server_command(_host_executable(paths))
    config = claude_setup.desktop_config(sys.platform, dict(os.environ), pathlib.Path.home())
    return routes_claude.ClaudeRoutes(paths=paths, config=config, command=tuple(command), skills=claude_setup.skills_folder(bundle_dir()))


def serve(paths: settings.Paths, code: str | None, open_browser: bool = True) -> int:
    import app  # the existing interface (bewerbungen/app.py)
    if getattr(sys, "frozen", False):
        urlscheme.register_windows(sys.executable)
    _use_mediation(settings.build_defaults(bundle_dir()))
    import routes_app
    import routes_angaben
    import routes_claude
    import routes_setup
    data = start_folder(paths)
    holder: dict = {}
    controls = routes_app.Controls(stop=lambda: holder["server"].shutdown(), failed_note=paths.app_dir / FAILED_UPDATE_NOTE)

    def switch(folder: pathlib.Path) -> None:
        holder["server"].kontext = app.erstelle_kontext(folder)
        log.info("Datenordner gewechselt: %s", folder)

    state = routes_setup.Setup(paths=paths, switch=switch, suggestion=settings.documents_dir() / settings.APP_NAME,
                               forbidden=(paths.app_dir, _install_dir()), extension_dir=prepare_extension(paths))
    app_get, app_post = routes_app.make_routes(controls)
    setup_get, setup_post = routes_setup.make_routes(state)
    angaben_get, angaben_post, limits = routes_angaben.make_routes(state)
    claude_get, claude_post = routes_claude.make_routes(claude_routes(paths))
    try:
        server = app.erstelle_server(data, extra_routes=({**app_get, **setup_get, **angaben_get, **claude_get},
                                                         {**app_post, **setup_post, **angaben_post, **claude_post}), body_limits=limits)
        holder["server"] = server
    except (ValueError, OSError) as error:
        log.error("Start nicht möglich: %s", error)
        return 1
    instance.write(paths, server.server_address[1], server.token)
    updates_macos.confirm_started(controls.app)
    if code:
        _redeem(code)
    log.info("Bewerbungsassistent läuft auf %s, Daten in %s", server.url, data)
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

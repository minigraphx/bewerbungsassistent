"""Settings from environment variables; the Anthropic key only from the environment (a secret of the server)."""
import dataclasses
import os

DEFAULTS = {"VERMITTLUNG_DB": "/data/vermittlung.sqlite", "VERMITTLUNG_HOST": "0.0.0.0", "VERMITTLUNG_PORT": "8080",
            "VERMITTLUNG_ANFRAGEN_PRO_MINUTE": "20", "VERMITTLUNG_MAX_TOKENS": "16000",
            "VERMITTLUNG_HINTER_PROXY": "1"}


class ConfigError(ValueError):
    pass


@dataclasses.dataclass(frozen=True)
class Config:
    db_path: str
    host: str
    port: int
    calls_per_minute: int
    max_output_tokens: int
    behind_proxy: bool
    api_key: str = dataclasses.field(repr=False)


def _number(env: dict, name: str) -> int:
    value = env.get(name) or DEFAULTS[name]
    try:
        number = int(value)
    except ValueError as error:
        raise ConfigError(f"{name} muss eine Zahl sein") from error
    if number <= 0:
        raise ConfigError(f"{name} muss grösser als 0 sein")
    return number


def load(environ: dict | None = None, need_key: bool = True) -> Config:
    env = dict(os.environ if environ is None else environ)
    key = (env.get("ANTHROPIC_API_KEY") or "").strip()
    if need_key and not key:
        raise ConfigError("ANTHROPIC_API_KEY fehlt (als Geheimnis des Servers setzen, nie ins Repo)")
    return Config(db_path=env.get("VERMITTLUNG_DB") or DEFAULTS["VERMITTLUNG_DB"],
                  host=env.get("VERMITTLUNG_HOST") or DEFAULTS["VERMITTLUNG_HOST"],
                  port=_number(env, "VERMITTLUNG_PORT"),
                  calls_per_minute=_number(env, "VERMITTLUNG_ANFRAGEN_PRO_MINUTE"),
                  max_output_tokens=_number(env, "VERMITTLUNG_MAX_TOKENS"),
                  behind_proxy=(env.get("VERMITTLUNG_HINTER_PROXY") or DEFAULTS["VERMITTLUNG_HINTER_PROXY"]) == "1",
                  api_key=key)

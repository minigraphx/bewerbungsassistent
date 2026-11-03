"""Start the mediation: `python main.py` (settings in config.py, from the environment)."""
import logging
import sys

from config import ConfigError, load
from limits import RateLimiter
from policy import Policy
from service import Mediation, Server
from store import Store
from upstream import Upstream


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        config = load()
    except ConfigError as error:
        sys.exit(str(error))
    mediation = Mediation(store=Store(config.db_path), upstream=Upstream.from_key(config.api_key),
                          policy=Policy(max_output_tokens=config.max_output_tokens),
                          calls=RateLimiter(config.calls_per_minute), trust_proxy=config.behind_proxy)
    server = Server((config.host, config.port), mediation)
    logging.getLogger("vermittlung").info("Vermittlung läuft auf %s:%s", config.host, config.port)
    server.serve_forever()


if __name__ == "__main__":
    main()

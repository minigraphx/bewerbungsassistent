"""Reads a list of jobs from the text of a page without its own adapter (MIN-348).

The page is foreign data: only its text and the texts of its links go to the AI, under new labels in every request.
The addresses stay here and no CV goes along, so an answer can only point at a link that was on the page.
"""
import secrets

from ai import prompts, tasks
from ai.gateway import Gateway, Request

MAX_TEXT = 20_000
MAX_LINKS = 150
MAX_LINK_TEXT = 200
MAX_JOBS = 50
LABEL_BYTES = 3
FIELDS = {"stelle": "title", "firma": "company", "ort": "place", "pensum": "workload"}
MAX_FIELD = 200


def _labelled(links: list[dict]) -> dict[str, dict]:
    return {f"L{n}-{secrets.token_hex(LABEL_BYTES)}": link for n, link in enumerate(links[:MAX_LINKS], 1)}


def _job(item, labels: dict[str, dict]) -> dict | None:
    if not isinstance(item, dict) or item.get("link") not in labels:
        return None
    fields = {name: " ".join(str(item.get(source) or "").split())[:MAX_FIELD] for name, source in FIELDS.items()}
    if not fields["stelle"]:
        return None
    return {**{name: value for name, value in fields.items() if value}, "link": labels[item["link"]]["href"]}


def read_list(gateway: Gateway, title: str, text: str, links: list[dict], model: str | None = None) -> dict:
    """{"jobs": [{"stelle", "firma"?, "ort"?, "pensum"?, "link"}], "cost_usd"}; each link only once."""
    labels = _labelled(links)
    prompt = prompts.site_list_prompt(title, text[:MAX_TEXT], [(label, link["text"][:MAX_LINK_TEXT]) for label, link in labels.items()])
    answer = gateway.ask(Request(task="site_list", model=model or tasks.MODELS["site_list"], rules=prompts.SITE_LIST_RULES, context="",
                                 instructions=prompts.SITE_LIST, prompt=prompt, max_tokens=tasks.MAX_TOKENS["site_list"],
                                 schema=prompts.SITE_LIST_SCHEMA))
    items = answer.data.get("jobs") if isinstance(answer.data, dict) else None
    jobs: dict[str, dict] = {}
    for item in (items if isinstance(items, list) else [])[:MAX_JOBS]:
        job = _job(item, labels)
        if job and job["link"] not in jobs:
            jobs = {**jobs, job["link"]: job}
    return {"jobs": list(jobs.values()), "cost_usd": answer.cost_usd}

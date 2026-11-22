"""A stand-in for curl, so the store steps of erweiterung-einreichen.yml run without reaching a store (#365).

It understands the options those steps use, logs each call as one JSON line to $FAKE_CURL_LOG and answers from the
list in $FAKE_CURL_RESPONSES, in order: each entry names a part of the expected URL, the status code, the body and
the response headers. A request that does not match the next entry ends with exit code 99.
"""
import json
import os
import pathlib
import sys

VALUE_OPTIONS = {"-X", "-H", "-T", "-o", "-w", "-D", "--data", "-d"}


def parse(argv: list[str]) -> dict:
    call = {"method": None, "headers": [], "upload": None, "data": None, "out": None, "write_out": None,
            "dump_header": None, "url": None}
    rest = iter(argv)
    for arg in rest:
        if arg in VALUE_OPTIONS:
            value = next(rest)
            if arg == "-X":
                call["method"] = value
            elif arg == "-H":
                call["headers"] += read_headers(value)
            elif arg == "-T":
                call["upload"] = value
            elif arg in ("--data", "-d"):
                call["data"] = sys.stdin.read() if value == "@-" else value
            else:
                call[{"-o": "out", "-w": "write_out", "-D": "dump_header"}[arg]] = value
        elif arg.startswith("http"):
            call["url"] = arg
    return call


def read_headers(value: str) -> list[str]:
    if value.startswith("@"):
        return pathlib.Path(value[1:]).read_text(encoding="utf-8").splitlines()
    return [value]


def next_response(url: str) -> dict | None:
    counter = pathlib.Path(os.environ["FAKE_CURL_LOG"] + ".count")
    index = int(counter.read_text()) if counter.exists() else 0
    responses = json.loads(pathlib.Path(os.environ["FAKE_CURL_RESPONSES"]).read_text(encoding="utf-8"))
    counter.write_text(str(index + 1))
    if index >= len(responses) or responses[index]["match"] not in url:
        return None
    return responses[index]


def main(argv: list[str]) -> int:
    call = parse(argv)
    upload = pathlib.Path(call["upload"]) if call["upload"] else None
    entry = {**call, "argv": argv, "upload_bytes": upload.read_bytes().hex() if upload else None}
    with open(os.environ["FAKE_CURL_LOG"], "a", encoding="utf-8") as log:
        log.write(json.dumps(entry) + "\n")
    response = next_response(call["url"] or "")
    if response is None:
        print(f"fake curl: unexpected request {call['url']}", file=sys.stderr)
        return 99
    body = response.get("body", "")
    if call["out"]:
        pathlib.Path(call["out"]).write_text(body if isinstance(body, str) else json.dumps(body), encoding="utf-8")
    if call["dump_header"]:
        lines = [f"HTTP/2 {response['code']}", *(f"{k}: {v}" for k, v in response.get("headers", {}).items())]
        pathlib.Path(call["dump_header"]).write_text("\r\n".join(lines) + "\r\n\r\n", encoding="utf-8")
    if call["write_out"]:
        sys.stdout.write(call["write_out"].replace("%{http_code}", str(response["code"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

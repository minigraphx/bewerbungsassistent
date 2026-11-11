"""One signing identity for every macOS version (#213, G48), so the keychain stops asking after each update.

macOS ties the access to a keychain entry to the app's designated requirement. Signed ad hoc, each build has its own,
so after every update macOS asks again. Signed with the same self-signed certificate, the requirement names that
certificate and stays the same. The app checks an update against exactly this requirement (updates_macos.py).

`create <folder>` makes the identity once, on the person's machine and outside the repo: the private key never enters
the repo. It prints the steps to store it as the repository secrets MACOS_SIGNING_P12 and MACOS_SIGNING_PASSWORD
and the fingerprint that goes into CERTIFICATE_SHA1 below. CI (`.github/workflows/app.yml`) signs with it, checks
the secret against this fingerprint and refuses to build without it.
"""
import datetime
import os
import pathlib
import secrets
import sys

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import PrivateFormat, pkcs12
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

# SHA-1 of the certificate (DER), as codesign names it; set once the identity exists (Andy's step, see `create`).
CERTIFICATE_SHA1 = "05F941C78A51D142F9C374F21062FDE8515535B8"
BUNDLE_ID = "ch.bewerbungsbegleiter.app"  # as in bewerbungsbegleiter.spec
COMMON_NAME = "Bewerbungsbegleiter Signatur"
VALID_YEARS = 25  # without a timestamp, codesign checks the certificate's dates when it verifies
KEY_BITS = 3072
P12_NAME = "bewerbungsbegleiter-signatur.p12"
PASSWORD_NAME = "bewerbungsbegleiter-signatur-passwort.txt"
P12_SECRET_NAME = "MACOS_SIGNING_P12"
PASSWORD_SECRET_NAME = "MACOS_SIGNING_PASSWORD"
REPO = "minigraphx/bewerbungsassistent"
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE = 0o600
NOT_SET = "Die Signatur-Identität ist noch nicht eingetragen (desktop/signing_identity.py, CERTIFICATE_SHA1)."
USAGE = "usage: signing_identity.py create <folder outside the repo> | requirement | sha1 | check <p12 file>"


class IdentityError(Exception):
    """German message for the person or the CI log."""


def requirement(sha1: str | None = None) -> str:
    """The designated requirement every version must meet: our bundle, signed with exactly our certificate."""
    fingerprint = (CERTIFICATE_SHA1 if sha1 is None else sha1).strip().upper()
    if len(fingerprint) != 40 or any(c not in "0123456789ABCDEF" for c in fingerprint):
        raise IdentityError(NOT_SET)
    return f'identifier "{BUNDLE_ID}" and certificate leaf = H"{fingerprint}"'


def fingerprint(certificate: x509.Certificate) -> str:
    return certificate.fingerprint(hashes.SHA1()).hex().upper()  # noqa: S303 (codesign names certificates by SHA-1)


def _certificate(key: rsa.RSAPrivateKey, now: datetime.datetime) -> x509.Certificate:
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, COMMON_NAME)])
    return (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now.replace(year=now.year + VALID_YEARS))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=False,
                                         data_encipherment=False, key_agreement=False, key_cert_sign=False,
                                         crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CODE_SIGNING]), critical=True)
            .sign(key, hashes.SHA256()))


def _p12(key: rsa.RSAPrivateKey, certificate: x509.Certificate, password: bytes) -> bytes:
    """PKCS#12 with the classic algorithms, which `security import` on every macOS reads."""
    encryption = (PrivateFormat.PKCS12.encryption_builder()
                  .kdf_rounds(50_000)
                  .key_cert_algorithm(pkcs12.PBES.PBESv1SHA1And3KeyTripleDESCBC)
                  .hmac_hash(hashes.SHA1())
                  .build(password))
    return pkcs12.serialize_key_and_certificates(COMMON_NAME.encode(), key, certificate, None, encryption)


def _outside_repo(folder: pathlib.Path) -> pathlib.Path:
    resolved = folder.expanduser().resolve()
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
        raise IdentityError("Bitte einen Ordner ausserhalb des Repos wählen: Der private Schlüssel gehört nie ins Repo.")
    return resolved


def _write_private(path: pathlib.Path, data: bytes) -> None:
    if path.exists():
        raise IdentityError(f"{path} gibt es schon. Eine neue Identität liesse den Schlüsselbund wieder fragen; "
                            "die bestehende Datei bitte weiter verwenden.")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, PRIVATE)
    with os.fdopen(descriptor, "wb") as file:
        file.write(data)


def create(folder: pathlib.Path, now: datetime.datetime | None = None) -> tuple[pathlib.Path, pathlib.Path, str]:
    """Key and certificate as a PKCS#12 file plus its password, both readable only by the person; and the fingerprint."""
    target = _outside_repo(folder)
    target.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=KEY_BITS)
    certificate = _certificate(key, now or datetime.datetime.now(datetime.timezone.utc))
    password = secrets.token_urlsafe(32)
    p12, password_file = target / P12_NAME, target / PASSWORD_NAME
    _write_private(p12, _p12(key, certificate, password.encode()))
    _write_private(password_file, password.encode())
    return p12, password_file, fingerprint(certificate)


def steps(p12: pathlib.Path, password_file: pathlib.Path, sha1: str) -> str:
    """What the person does next; the password itself is never printed."""
    return "\n".join([
        f"Signatur-Identität erstellt: {p12}",
        "",
        "1. Beide Dateien sicher aufbewahren (zum Beispiel im Passwortmanager). Geht die Identität verloren,",
        "   fragt der Schlüsselbund nach dem nächsten Update einmal neu.",
        "2. Als Secrets des Repos speichern (GitHub CLI, angemeldet als Besitzer des Repos):",
        f'   base64 -i "{p12}" | gh secret set {P12_SECRET_NAME} --repo {REPO}',
        f'   gh secret set {PASSWORD_SECRET_NAME} --repo {REPO} < "{password_file}"',
        "3. Diesen Fingerabdruck im Repo eintragen lassen (desktop/signing_identity.py):",
        f'   CERTIFICATE_SHA1 = "{sha1}"',
        "Erst danach baut CI die App für macOS wieder.",
    ])


def check(p12_data: bytes, password: bytes, sha1: str | None = None) -> str:
    """The fingerprint of the certificate in the secret, if it is ours; IdentityError otherwise."""
    expected = requirement(sha1)  # also refuses when nothing is set yet
    try:
        _, certificate, _ = pkcs12.load_key_and_certificates(p12_data, password)
    except ValueError as error:
        raise IdentityError("Das Secret mit der Signatur-Identität lässt sich nicht lesen (Datei oder Passwort).") from error
    if certificate is None or f'H"{fingerprint(certificate)}"' not in expected:
        raise IdentityError("Die Signatur-Identität im Secret ist nicht die eingetragene (CERTIFICATE_SHA1).")
    return fingerprint(certificate)


def main(args: list[str]) -> int:
    try:
        match args:
            case ["create", folder]:
                print(steps(*create(pathlib.Path(folder))))
            case ["requirement"]:
                print(requirement())
            case ["sha1"]:
                requirement()
                print(CERTIFICATE_SHA1.strip().upper())
            case ["check", p12_file]:
                password = os.environ.get(PASSWORD_SECRET_NAME, "").encode()
                print(check(pathlib.Path(p12_file).read_bytes(), password))
            case _:
                print(USAGE, file=sys.stderr)
                return 2
    except (IdentityError, OSError) as error:
        print(f"::error::{error}" if os.environ.get("GITHUB_ACTIONS") else str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

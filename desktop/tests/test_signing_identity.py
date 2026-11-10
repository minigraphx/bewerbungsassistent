"""One self-signed identity for every macOS version (#213, G48). Identities here are made in a temporary folder."""
import datetime
import os
import pathlib
import shutil
import stat
import subprocess
import sys

import pytest
import yaml
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtendedKeyUsageOID

import signing_identity
import updates
import updates_macos
from test_updates_macos import PACKAGE_URL, ZIP_NAME, Tools, fake_app, release

WORKFLOW = pathlib.Path(__file__).resolve().parents[2] / ".github" / "workflows" / "app.yml"
NOW = datetime.datetime(2026, 11, 10, tzinfo=datetime.timezone.utc)


@pytest.fixture(scope="module")
def identity(tmp_path_factory):
    folder = tmp_path_factory.mktemp("identitaet")
    p12, password_file, sha1 = signing_identity.create(folder, NOW)
    return p12, password_file, sha1


def load(p12, password_file):
    return pkcs12.load_key_and_certificates(p12.read_bytes(), password_file.read_bytes())


# Creating the identity (the person's step)


def test_the_identity_is_a_self_signed_code_signing_certificate(identity):
    p12, password_file, sha1 = identity

    key, certificate, extra = load(p12, password_file)

    assert key is not None and not extra
    assert certificate.issuer == certificate.subject
    assert certificate.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value == x509.ExtendedKeyUsage(
        [ExtendedKeyUsageOID.CODE_SIGNING])
    assert certificate.not_valid_after_utc.year >= NOW.year + 20
    assert signing_identity.fingerprint(certificate) == sha1 and len(sha1) == 40


def test_only_the_person_can_read_key_and_password(identity):
    for path in identity[:2]:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_the_private_key_never_lands_in_the_repo():
    inside = signing_identity.REPO_ROOT / "desktop" / "build" / "identitaet"

    with pytest.raises(signing_identity.IdentityError, match="ausserhalb des Repos"):
        signing_identity.create(inside)
    assert not inside.exists()


def test_an_identity_is_never_replaced_by_accident(identity):
    with pytest.raises(signing_identity.IdentityError, match="gibt es schon"):
        signing_identity.create(identity[0].parent)
    assert load(*identity[:2])[1] is not None  # the first one is untouched


def test_the_steps_name_the_secrets_and_the_fingerprint_but_never_the_password(identity, tmp_path, capsys):
    assert signing_identity.main(["create", str(tmp_path / "neu")]) == 0
    printed = capsys.readouterr().out
    password = (tmp_path / "neu" / signing_identity.PASSWORD_NAME).read_text()
    sha1 = signing_identity.fingerprint(load(tmp_path / "neu" / signing_identity.P12_NAME,
                                             tmp_path / "neu" / signing_identity.PASSWORD_NAME)[1])

    assert "gh secret set MACOS_SIGNING_P12" in printed and "gh secret set MACOS_SIGNING_PASSWORD" in printed
    assert f'CERTIFICATE_SHA1 = "{sha1}"' in printed
    assert password not in printed


@pytest.mark.skipif(not shutil.which("openssl"), reason="needs openssl")
def test_the_p12_uses_algorithms_every_macos_imports(identity):
    p12, password_file, _ = identity
    info = subprocess.run(["openssl", "pkcs12", "-info", "-noout", "-in", p12, "-passin", f"file:{password_file}"],
                          capture_output=True, text=True)

    assert "3DES" in info.stderr + info.stdout or "pbeWithSHA1And3-KeyTripleDES-CBC" in info.stderr + info.stdout


# The requirement


def test_the_requirement_names_our_bundle_and_exactly_our_certificate(identity):
    assert signing_identity.requirement(identity[2]) == (
        f'identifier "ch.bewerbungsbegleiter.app" and certificate leaf = H"{identity[2]}"')


@pytest.mark.parametrize("sha1", ["", "kaputt", "0" * 39, "G" * 40])
def test_without_a_valid_fingerprint_there_is_no_requirement(sha1):
    with pytest.raises(signing_identity.IdentityError, match="nicht eingetragen"):
        signing_identity.requirement(sha1)


def test_the_secret_must_hold_the_registered_identity(identity, tmp_path):
    p12, password_file, sha1 = identity
    other_p12, other_password, _ = signing_identity.create(tmp_path / "fremd", NOW)

    assert signing_identity.check(p12.read_bytes(), password_file.read_bytes(), sha1) == sha1
    with pytest.raises(signing_identity.IdentityError, match="nicht die eingetragene"):
        signing_identity.check(other_p12.read_bytes(), other_password.read_bytes(), sha1)
    with pytest.raises(signing_identity.IdentityError, match="nicht lesen"):
        signing_identity.check(p12.read_bytes(), b"falsch", sha1)


# The updater accepts exactly that identity


def test_the_updater_asks_codesign_for_exactly_our_identity(tmp_path, monkeypatch, identity):
    monkeypatch.setattr(signing_identity, "CERTIFICATE_SHA1", identity[2])
    app, tools = fake_app(tmp_path), Tools()

    staging = updates_macos.prepare(updates.latest(release(), "darwin"), app, release(), tools)

    assert tools.calls[1] == [updates_macos.CODESIGN, "--verify", "--deep", "--strict",
                              "-R", f"={signing_identity.requirement(identity[2])}", str(staging / updates_macos.NEW_APP)]


def test_an_app_signed_by_anyone_else_is_refused(tmp_path, monkeypatch, identity):
    monkeypatch.setattr(signing_identity, "CERTIFICATE_SHA1", identity[2])
    app, tools = fake_app(tmp_path), Tools()
    tools.signed = False  # codesign: the requirement is not met

    with pytest.raises(updates.UpdateError, match="Signatur"):
        updates_macos.prepare(updates.latest(release(), "darwin"), app, release(), tools)
    assert not (tmp_path / updates_macos.STAGING).exists()


def test_a_version_without_the_identity_does_not_update_itself(tmp_path, monkeypatch):
    monkeypatch.setattr(signing_identity, "CERTIFICATE_SHA1", "")
    app, tools = fake_app(tmp_path), Tools()

    with pytest.raises(updates.UpdateError, match="von Hand"):
        updates_macos.prepare(updates.latest(release(), "darwin"), app, release(), tools)
    assert updates_macos.CODESIGN not in [call[0] for call in tools.calls]


@pytest.mark.skipif(sys.platform != "darwin", reason="codesign exists on macOS only")
def test_real_codesign_refuses_an_ad_hoc_signed_package(tmp_path, monkeypatch, identity):
    """The real tools, on a package signed ad hoc as before #213: it does not meet our requirement."""
    import hashlib
    monkeypatch.setattr(signing_identity, "CERTIFICATE_SHA1", identity[2])
    package = fake_app(tmp_path / "build")
    shutil.copy("/bin/ls", package / "Contents" / "MacOS" / "Bewerbungsbegleiter")
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(package)], check=True, capture_output=True)
    subprocess.run(["ditto", "-c", "-k", "--keepParent", str(package), str(tmp_path / ZIP_NAME)], check=True)
    archive = (tmp_path / ZIP_NAME).read_bytes()
    update = updates.Update("9.2.0", "https://x", PACKAGE_URL + ZIP_NAME, hashlib.sha256(archive).hexdigest())
    installed = tmp_path / "Programme"
    installed.mkdir()

    with pytest.raises(updates.UpdateError, match="Signatur"):
        updates_macos.prepare(update, fake_app(installed), lambda url, limit: archive)


# CI signs with it and refuses to build without it


@pytest.fixture(scope="module")
def macos_job():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["macos"]


def signing_step(job):
    return next(step for step in job["steps"] if step.get("name") == "Signieren")


def test_ci_signs_with_the_identity_from_the_secrets_and_checks_it(macos_job):
    step = signing_step(macos_job)
    names = [s.get("name") for s in macos_job["steps"]]

    assert names.index("Paket bauen") < names.index("Signieren") < names.index("Paket testen")
    assert step["env"]["P12"] == "${{ secrets.MACOS_SIGNING_P12 }}"
    assert step["env"]["MACOS_SIGNING_PASSWORD"] == "${{ secrets.MACOS_SIGNING_PASSWORD }}"
    assert "signing_identity.py check" in step["run"] and '-R "=$requirement"' in step["run"]
    assert "--sign -" not in WORKFLOW.read_text(encoding="utf-8")  # never ad hoc


def test_the_released_package_is_verified_against_the_requirement(macos_job):
    test_step = next(step for step in macos_job["steps"] if step.get("name") == "Paket testen")

    assert '-R "=$(python desktop/signing_identity.py requirement)" entpackt/Bewerbungsbegleiter.app' in test_step["run"]


def test_without_the_secrets_ci_fails_with_a_clear_message(macos_job, tmp_path):
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("needs bash")
    env = {"PATH": os.environ["PATH"], "RUNNER_TEMP": str(tmp_path), "P12": "", "MACOS_SIGNING_PASSWORD": ""}

    done = subprocess.run([bash, "-e", "-c", signing_step(macos_job)["run"]], env=env, capture_output=True, text=True,
                          cwd=tmp_path)

    assert done.returncode == 1
    assert "::error::Die Secrets MACOS_SIGNING_P12 und MACOS_SIGNING_PASSWORD fehlen" in done.stdout

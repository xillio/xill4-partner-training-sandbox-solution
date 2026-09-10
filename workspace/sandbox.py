"""Naming, ports and credentials for one trainee's sandbox.

A trainee's sandbox has two halves: a workspace directory on the host, and a database
inside the shared MongoDB where their Xill4 keeps its projects and flows. Both are named
from the trainee id, and both have to be reset together -- reseeding the directory while
leaving yesterday's flows in the database is not a reset.

Every name, port and credential is derived here rather than in the provisioner's shell and
again in the preflight's Python. The two disagreeing about which database belongs to whom
is the failure that hands one trainee another's work.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import secrets
import sys
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import quote

# A stable per-trainee port keeps a persistent workspace reachable at the same URL for the
# length of a course. 100 slots is far beyond the cohort sizes we design for.
XILL4_PORT_BASE = 8100
MINIO_PORT_BASE = 9100
PORT_SLOTS = 100

# Mongo database names may not contain /\. "$*<>:|?, and a name that is also a legal URL
# component and a legal shell word saves escaping it in three more places later.
_UNSAFE = re.compile(r"[^a-z0-9]+")

_ENV_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


class TraineeIdError(ValueError):
    """A trainee id that cannot be turned into a database name."""


def slug(trainee: str) -> str:
    """Reduce a trainee id to the characters a database name and a URL both allow."""
    cleaned = _UNSAFE.sub("_", trainee.strip().lower()).strip("_")
    if not cleaned:
        raise TraineeIdError(f"trainee id {trainee!r} has no usable characters")
    return cleaned


def database_name(trainee: str) -> str:
    return f"xill4_{slug(trainee)}"


def database_user(trainee: str) -> str:
    """The trainee's Mongo user, scoped to their database and nothing else."""
    return slug(trainee)


def preferred_slot(trainee: str) -> int:
    """The port slot a trainee gets when it is free.

    sha256 rather than the shell's `cksum`, because the provisioner is bash and the
    preflight is Python: a hash that differs between them puts a trainee's instance on a
    port the tooling then looks for somewhere else.
    """
    digest = hashlib.sha256(slug(trainee).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % PORT_SLOTS


def assign_slot(trainee: str, taken: Mapping[str, int]) -> int:
    """Pick a free port slot, keeping any slot this trainee already holds.

    Reuse comes first: a trainee's URL must survive a reset and a re-provision, so an
    allocation already recorded in their env file wins over what the hash now prefers.
    """
    key = slug(trainee)
    normalised = {slug(name): slot for name, slot in taken.items()}
    if key in normalised:
        return normalised[key]

    used = {slot for name, slot in normalised.items() if name != key}
    if len(used) >= PORT_SLOTS:
        raise RuntimeError(
            f"all {PORT_SLOTS} port slots are allocated; retire a trainee before adding one"
        )
    slot = preferred_slot(trainee)
    while slot in used:
        slot = (slot + 1) % PORT_SLOTS
    return slot


def connection_string(user: str, password: str, database: str,
                      host: str = "mongo", port: int = 27017) -> str:
    """The trainee's own Mongo URI, scoped to their own database.

    Percent-encoded, because a generated password containing `@` or `/` otherwise produces
    a URI that parses as a different host entirely.
    """
    credentials = f"{quote(user, safe='')}:{quote(password, safe='')}"
    return f"mongodb://{credentials}@{host}:{port}/{database}?authSource={database}"


def generate_password(length: int = 24) -> str:
    """A URL-safe password. Kept out of the repository: env files are gitignored."""
    return secrets.token_urlsafe(length)


def parse_env(text: str) -> dict[str, str]:
    """Read a KEY=VALUE env file. Comments and blank lines are ignored, quotes are not."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _ENV_LINE.match(stripped)
        if match:
            values[match.group(1)] = match.group(2)
    return values


def read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return parse_env(path.read_text(encoding="utf-8"))


def env_file_for(env_dir: Path, trainee: str) -> Path:
    """One env file per trainee, not one shared file.

    The single `workspace/.env` of Phase 0 could only describe one trainee at a time, so
    bringing up the second sandbox rewrote the first one's port and credentials.
    """
    return Path(env_dir) / f".env.{slug(trainee)}"


def allocated_slots(env_dir: Path) -> dict[str, int]:
    """Port slots already handed out, read back from the per-trainee env files."""
    slots: dict[str, int] = {}
    for path in sorted(Path(env_dir).glob(".env.*")):
        values = read_env_file(path)
        trainee, port = values.get("TRAINEE"), values.get("XILL4_PORT")
        if trainee and port and port.isdigit():
            slots[slug(trainee)] = int(port) - XILL4_PORT_BASE
    return slots


def render_env(trainee: str, scenario: str, workspace_dir: str, slot: int,
               secrets_in: Mapping[str, str]) -> str:
    """The per-trainee half of the compose environment.

    The deployment-wide half -- licence key, environment secret, image version -- stays in
    .env.platform and is passed as a second --env-file, so a secret shared by the whole
    cohort is not copied into one file per trainee.
    """
    database = database_name(trainee)
    user = database_user(trainee)
    password = secrets_in["MONGO_PASSWORD"]
    lines = [
        f"# {trainee}'s sandbox. Generated by provision.sh -- edit provision.sh, not this.",
        f"TRAINEE={trainee}",
        f"WORKSPACE_DIR={workspace_dir}",
        f"SCENARIO={scenario}",
        "",
        f"XILL4_PORT={XILL4_PORT_BASE + slot}",
        f"XILL4_DATABASE_CONNECTION_STRING={connection_string(user, password, database)}",
        "",
        f"MONGO_DATABASE={database}",
        f"MONGO_USER={user}",
        f"MONGO_PASSWORD={password}",
        "",
        f"MINIO_PORT={MINIO_PORT_BASE + slot}",
        f"S3_ACCESS_KEY={secrets_in.get('S3_ACCESS_KEY', 'trainee')}",
        f"S3_SECRET_KEY={secrets_in['S3_SECRET_KEY']}",
        "",
    ]
    return "\n".join(lines)


def prepare_workspace_permissions(workspace: Path, uid: int | None = None) -> dict[str, str]:
    """Make the mounted target writable by the container, and lock down the answer key.

    A container that runs as a non-root uid cannot write a bind-mounted directory the host
    created as root, and the failure is quiet in the worst way: the instance starts, the
    trainee builds a migration, and nothing lands. The uid belongs to the image, so it is
    read from the image rather than assumed -- workspace/preflight.py reports it.

    The answer key goes the other way. It is not mounted anywhere, but on a trainer's host
    it sat world-readable, which is one `cat` away from being the answer sheet.
    """
    workspace = Path(workspace)
    actions: dict[str, str] = {}
    target, expected = workspace / "target", workspace / ".expected"

    if os.name != "posix":
        return {"skipped": "not a POSIX host; Docker Desktop maps ownership itself"}

    if uid is not None and os.geteuid() == 0:
        for path in (target, *target.rglob("*")):
            os.chown(path, uid, -1)
        # Narrow it again: an earlier run without a known uid may have left it 0777.
        target.chmod(0o755)
        actions["target"] = f"owned by uid {uid}"
    else:
        # No privilege to hand the directory over, so widen it instead. This is per-trainee
        # scratch data that is regenerated on every reset; the answer key below is not.
        target.chmod(0o777)
        actions["target"] = ("mode 0777 (could not chown: "
                             + ("no uid known" if uid is None else "not running as root") + ")")

    if expected.exists():
        expected.chmod(0o700)
        actions["expected"] = "mode 0700"
    return actions


def _prepare_workspace_command(args: argparse.Namespace) -> int:
    actions = prepare_workspace_permissions(Path(args.workspace),
                                            int(args.uid) if args.uid else None)
    for name, action in actions.items():
        print(f"{name}: {action}")
    return 0


def _render_env_command(args: argparse.Namespace) -> int:
    """Print a trainee's env file, reusing whatever they already hold."""
    env_dir = Path(args.env_dir)
    existing = read_env_file(env_file_for(env_dir, args.trainee))
    slot = assign_slot(args.trainee, allocated_slots(env_dir))
    carried = {
        "MONGO_PASSWORD": existing.get("MONGO_PASSWORD") or generate_password(),
        "S3_ACCESS_KEY": existing.get("S3_ACCESS_KEY", "trainee"),
        "S3_SECRET_KEY": existing.get("S3_SECRET_KEY") or generate_password(),
    }
    sys.stdout.write(
        render_env(args.trainee, args.scenario, args.workspace_dir, slot, carried)
    )
    return 0


def init_platform_env(env_dir: Path) -> tuple[Path, bool]:
    """Create .env.platform from its example on first use, generating the secrets.

    Only the licence key is left for a human to paste in. The passwords are generated so
    that nobody has to invent one, and the per-deployment environment secret is generated
    once here rather than per trainee -- it is deployment-wide, and every instance in the
    cohort must present the same value.
    """
    destination = Path(env_dir) / ".env.platform"
    if destination.exists():
        return destination, False

    template = parse_env((Path(env_dir) / ".env.platform.example").read_text(encoding="utf-8"))
    template["MONGO_ROOT_PASSWORD"] = generate_password()
    template["XILL4_ENVIRONMENT_SECRET"] = generate_password(32)
    body = "\n".join(f"{key}={value}" for key, value in template.items())
    destination.write_text(
        "# Generated on first provision. Secrets live here and nowhere else in the repo;\n"
        "# workspace/.env* is gitignored. Paste the licence key below.\n" + body + "\n",
        encoding="utf-8",
    )
    destination.chmod(0o600)
    return destination, True


def _init_platform_command(args: argparse.Namespace) -> int:
    destination, created = init_platform_env(Path(args.env_dir))
    print(f"{'created' if created else 'exists'} {destination}")
    return 0


def _env_path_command(args: argparse.Namespace) -> int:
    """Print where a trainee's env file lives, so the shell need not re-derive the slug."""
    print(env_file_for(Path(args.env_dir), args.trainee))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sandbox", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    render = sub.add_parser("render-env", help="print one trainee's compose env file")
    render.add_argument("--trainee", required=True)
    render.add_argument("--scenario", required=True)
    render.add_argument("--workspace-dir", required=True)
    render.add_argument("--env-dir", default=str(Path(__file__).parent))
    render.set_defaults(handler=_render_env_command)

    where = sub.add_parser("env-path", help="print the path of one trainee's env file")
    where.add_argument("--trainee", required=True)
    where.add_argument("--env-dir", default=str(Path(__file__).parent))
    where.set_defaults(handler=_env_path_command)

    init = sub.add_parser("init-platform-env", help="create .env.platform if it is missing")
    init.add_argument("--env-dir", default=str(Path(__file__).parent))
    init.set_defaults(handler=_init_platform_command)

    prepare = sub.add_parser("prepare-workspace",
                             help="make target/ writable by the container, .expected/ private")
    prepare.add_argument("--workspace", required=True)
    prepare.add_argument("--uid", default="", help="uid the image runs as, if known")
    prepare.set_defaults(handler=_prepare_workspace_command)

    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (TraineeIdError, RuntimeError) as exc:
        print(f"sandbox: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Prove one real Xill4 container works, and report what it costs.

Run this on a host that can reach docker.cloudsmith.io and holds the licence key. It is the
one step that cannot be developed against a stand-in, so it is written to be run once, by
someone else, and to come back with everything the rest of Phase 1 needs to know:

  * does the image pull, and how big is it
  * which user does it run as -- the answer to whether it can write the mounted target/
  * which URL answers, so the compose healthcheck stops being a guess
  * does the trainee's scoped Mongo user actually hold the instance's state, and what
    shape is that state in -- the question that decides whether a check can grade an
    extraction or a job run from the database rather than only from produced files
  * can one trainee's credentials reach another's database (this must fail)
  * what one container costs at idle

Nothing here modifies a trainee's sandbox: it provisions its own throwaway trainee, and
removes it again unless --keep is given.

  python workspace/preflight.py                     # the real image, from .env.platform
  python workspace/preflight.py --json report.json  # ... and a report to send on
  python workspace/preflight.py --image mongo:7.0   # prove the harness without the image

After a trainee has actually done an exercise, the same script reports what their instance
wrote to its database -- the interesting moment for grading, which a freshly booted
instance cannot show:

  python workspace/preflight.py --schema-only --trainee alice --json alice-schema.json

Every check runs even when an earlier one fails, so one run reports every problem rather
than the first. Exit status is non-zero if any check failed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sandbox

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"

# The image's health endpoint is not documented anywhere we have; these are the candidates
# worth trying before hard-coding one into the compose healthcheck.
HEALTH_PATHS = ["/", "/health", "/healthz", "/status", "/actuator/health", "/api/health"]

WORKSPACE_DIR = Path(__file__).resolve().parent
REPO_ROOT = WORKSPACE_DIR.parent


@dataclass
class Result:
    name: str
    status: str
    summary: str
    detail: dict = field(default_factory=dict)


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command, capturing both streams. Never raises on a non-zero exit."""
    return subprocess.run(command, capture_output=True, text=True, check=False, **kwargs)


class Preflight:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.results: list[Result] = []
        self.platform_env = WORKSPACE_DIR / ".env.platform"
        self.trainee_env = sandbox.env_file_for(WORKSPACE_DIR, args.trainee)
        self.settings: dict[str, str] = {}
        self.run_as_uid: int | None = None
        self.container = f"xill4-sbx-{sandbox.slug(args.trainee)}-engine"
        self.image = ""

    # ------------------------------------------------------------------ bookkeeping
    def record(self, name: str, status: str, summary: str, **detail) -> Result:
        result = Result(name, status, summary, detail)
        self.results.append(result)
        marker = {PASS: "PASS", FAIL: "FAIL", SKIP: "SKIP"}[status]
        print(f"  {marker}  {name}: {summary}", flush=True)
        return result

    def status_of(self, name: str) -> str:
        for result in self.results:
            if result.name == name:
                return result.status
        return SKIP

    def compose_environment(self) -> dict[str, str]:
        """Process environment for compose, carrying any substitute-image overrides.

        Compose lets the shell environment win over an --env-file, which is how --image
        redirects the stack at a stand-in without editing anyone's .env.platform.
        """
        environment = dict(os.environ)
        if not self.args.image:
            return environment
        repository, _, tag = self.args.image.rpartition(":")
        if not repository or "/" in tag:  # no tag, just a repository
            repository, tag = self.args.image, "latest"
        environment["XILL4_IMAGE_REPO"] = repository
        environment["XILL4_VERSION"] = tag
        # The stand-in has no licence to check; a real run must still fail without one.
        environment.setdefault("XILL4_LICENSE_KEY", "")
        if not self.settings.get("XILL4_LICENSE_KEY"):
            environment["XILL4_LICENSE_KEY"] = "substitute-image-run"
        return environment

    def compose(self, *arguments: str) -> subprocess.CompletedProcess:
        command = ["docker", "compose", "--env-file", str(self.platform_env),
                   "--env-file", str(self.trainee_env),
                   "-f", str(WORKSPACE_DIR / "docker-compose.yml"), *arguments]
        return run(command, cwd=WORKSPACE_DIR, env=self.compose_environment())

    def platform_compose(self, *arguments: str) -> subprocess.CompletedProcess:
        command = ["docker", "compose", "--env-file", str(self.platform_env),
                   "-f", str(WORKSPACE_DIR / "docker-compose.platform.yml"), *arguments]
        return run(command, cwd=WORKSPACE_DIR)

    def mongosh(self, script: str, environment: dict[str, str]) -> subprocess.CompletedProcess:
        """Run a snippet in the platform's mongo container, credentials passed as env."""
        command = ["docker", "exec"]
        for key, value in environment.items():
            command += ["-e", f"{key}={value}"]
        command += [self.args.mongo_container, "mongosh", "--quiet", "--eval", script]
        return run(command)

    # ------------------------------------------------------------------ the checks
    def check_docker(self) -> None:
        info = run(["docker", "info", "--format", "{{.ServerVersion}}"])
        if info.returncode != 0:
            self.record("docker", FAIL, "no Docker daemon reachable",
                        stderr=info.stderr.strip()[:400])
            return
        compose = run(["docker", "compose", "version", "--short"])
        self.record("docker", PASS, f"engine {info.stdout.strip()}, "
                                    f"compose {compose.stdout.strip() or 'unknown'}")

    def load_settings(self) -> None:
        sandbox.init_platform_env(WORKSPACE_DIR)
        self.settings = sandbox.read_env_file(self.platform_env)
        repository = self.settings.get("XILL4_IMAGE_REPO", "")
        version = self.settings.get("XILL4_VERSION", "")
        self.image = self.args.image or f"{repository}:{version}"
        # A schema report starts no instance, so it needs the database credentials and
        # nothing else. Demanding a licence key for it would fail a run that is fine.
        required = (("MONGO_ROOT_PASSWORD",) if self.args.schema_only
                    else ("XILL4_LICENSE_KEY", "XILL4_ENVIRONMENT_SECRET",
                          "MONGO_ROOT_PASSWORD"))
        missing = [key for key in required if not self.settings.get(key)]
        if missing and not self.args.image:
            self.record("config", FAIL,
                        f"{', '.join(missing)} not set in {self.platform_env.name}",
                        env_file=str(self.platform_env))
            return
        self.record("config", PASS,
                    "database credentials present" if self.args.schema_only
                    else f"image {self.image}", substitute_image=bool(self.args.image))

    def check_registry(self) -> None:
        """Log in to the private registry, if a token was supplied."""
        token = self.args.token
        if self.args.image:
            self.record("registry-login", SKIP, "running against a substitute image")
            return
        if not token:
            self.record("registry-login", SKIP,
                        "no entitlement token given; relying on an existing docker login")
            return
        registry = self.image.split("/")[0]
        login = run(["docker", "login", registry, "--username", self.args.registry_user,
                     "--password-stdin"], input=token)
        if login.returncode != 0:
            self.record("registry-login", FAIL, f"login to {registry} refused",
                        stderr=login.stderr.strip()[:400])
            return
        self.record("registry-login", PASS, f"logged in to {registry}")

    def check_image(self) -> None:
        if self.status_of("config") == FAIL:
            self.record("image-pull", SKIP, "configuration incomplete")
            return
        started = time.monotonic()
        pull = run(["docker", "pull", self.image])
        elapsed = round(time.monotonic() - started, 1)
        size = run(["docker", "image", "inspect", self.image, "--format", "{{.Size}}"])
        present = size.returncode == 0
        if pull.returncode != 0 and not present:
            self.record("image-pull", FAIL, f"cannot pull {self.image}",
                        stderr=pull.stderr.strip()[:600] or pull.stdout.strip()[-600:])
            return
        megabytes = round(int(size.stdout.strip() or 0) / 1_048_576, 1)
        # A pull that fails over an image already on the host is not a failure: it is what a
        # second run, or a locally built stand-in, looks like.
        summary = (f"{megabytes} MB, pulled in {elapsed}s" if pull.returncode == 0
                   else f"{megabytes} MB, already on this host (pull did not succeed)")
        self.record("image-pull", PASS, summary, image=self.image, size_mb=megabytes,
                    pull_seconds=elapsed, pulled=pull.returncode == 0)

    def inspect_image(self) -> None:
        """Read the uid, ports and declared variables out of the image.

        The uid is the one that decides whether the trainee's Xill4 can write the mounted
        target/ at all -- a container running as a non-root uid with no write bit on the
        host directory produces a migration that silently lands nothing.
        """
        if self.status_of("image-pull") != PASS:
            self.record("image-metadata", SKIP, "image not available")
            return
        template = ("{{.Config.User}}|{{json .Config.ExposedPorts}}|"
                    "{{json .Config.Entrypoint}}|{{json .Config.Cmd}}|{{json .Config.Env}}")
        inspect = run(["docker", "image", "inspect", self.image, "--format", template])
        user, ports, entrypoint, command, environment = inspect.stdout.strip().split("|")
        declared = [value.split("=", 1)[0] for value in json.loads(environment or "[]")
                    if value.startswith("XILL4_")]
        self.run_as_uid = _numeric_uid(user, self.image)
        self.record("image-metadata", PASS,
                    f"runs as uid {self.run_as_uid if self.run_as_uid is not None else '?'} "
                    f"({user or 'root implicitly'}), exposes {ports}",
                    user=user or "root (implicit)", uid=self.run_as_uid,
                    exposed_ports=json.loads(ports or "{}"),
                    entrypoint=json.loads(entrypoint or "null"),
                    command=json.loads(command or "null"), declared_xill4_env=declared)

    def start_platform(self) -> None:
        up = self.platform_compose("up", "-d")
        if up.returncode != 0:
            self.record("mongo", FAIL, "shared MongoDB would not start",
                        stderr=up.stderr.strip()[-600:])
            return
        for _ in range(30):
            ping = self.mongosh("db.runCommand({ping:1}).ok", {})
            if ping.returncode == 0:
                self.record("mongo", PASS, "shared MongoDB is up")
                return
            time.sleep(2)
        self.record("mongo", FAIL, "MongoDB did not become reachable within 60s")

    def provision(self) -> None:
        """Seed a throwaway workspace and create its scoped database user."""
        if self.status_of("mongo") != PASS:
            self.record("provision", SKIP, "no MongoDB")
            return
        workspace_dir = f".workspaces/{sandbox.slug(self.args.trainee)}/{self.args.scenario}"
        workspace = REPO_ROOT / workspace_dir
        workspace.mkdir(parents=True, exist_ok=True)
        seed = run([sys.executable,
                    str(REPO_ROOT / "scenarios" / self.args.scenario / "seedgen.py"),
                    "--workspace", str(workspace), "--seed",
                    f"{self.args.trainee}:{self.args.scenario}", "--force"])
        if seed.returncode != 0:
            self.record("provision", FAIL, "seeding failed", stderr=seed.stderr.strip()[-400:])
            return

        # The uid comes from the image, so this can only happen after it is inspected.
        permissions = sandbox.prepare_workspace_permissions(workspace, self.run_as_uid)

        existing = sandbox.read_env_file(self.trainee_env)
        carried = {"MONGO_PASSWORD": existing.get("MONGO_PASSWORD") or sandbox.generate_password(),
                   "S3_ACCESS_KEY": "trainee",
                   "S3_SECRET_KEY": existing.get("S3_SECRET_KEY") or sandbox.generate_password()}
        slot = sandbox.assign_slot(self.args.trainee, sandbox.allocated_slots(WORKSPACE_DIR))
        self.trainee_env.write_text(
            sandbox.render_env(self.args.trainee, self.args.scenario, workspace_dir,
                               slot, carried), encoding="utf-8")
        self.trainee_env.chmod(0o600)

        created = self.mongosh(_CREATE_USER_JS, {
            "ROOT_USER": self.settings.get("MONGO_ROOT_USER", ""),
            "ROOT_PASSWORD": self.settings.get("MONGO_ROOT_PASSWORD", ""),
            "DB_NAME": sandbox.database_name(self.args.trainee),
            "DB_USER": sandbox.database_user(self.args.trainee),
            "DB_PASSWORD": carried["MONGO_PASSWORD"],
        })
        if created.returncode != 0:
            self.record("provision", FAIL, "could not create the scoped database user",
                        stderr=created.stderr.strip()[-400:])
            return
        self.record("provision", PASS,
                    f"workspace {workspace_dir}, database "
                    f"{sandbox.database_name(self.args.trainee)}, port "
                    f"{sandbox.XILL4_PORT_BASE + slot}",
                    port=sandbox.XILL4_PORT_BASE + slot, permissions=permissions)

    def check_isolation(self) -> None:
        """One trainee's credentials must not read another trainee's database.

        This is the check that must never regress: with authentication disabled, MongoDB
        accepts a scoped user's credentials and then ignores the scope entirely, and every
        trainee's connection string reads the whole cohort's work.
        """
        if self.status_of("provision") != PASS:
            self.record("mongo-isolation", SKIP, "no provisioned database")
            return
        neighbour = f"{sandbox.database_name(self.args.trainee)}_neighbour"
        environment = {
            "ROOT_USER": self.settings.get("MONGO_ROOT_USER", ""),
            "ROOT_PASSWORD": self.settings.get("MONGO_ROOT_PASSWORD", ""),
            "NEIGHBOUR": neighbour,
            "DB_NAME": sandbox.database_name(self.args.trainee),
            "DB_USER": sandbox.database_user(self.args.trainee),
            "DB_PASSWORD": sandbox.read_env_file(self.trainee_env).get("MONGO_PASSWORD", ""),
        }
        probe = self.mongosh(_ISOLATION_JS, environment)
        verdict = probe.stdout.strip().splitlines()[-1] if probe.stdout.strip() else ""
        if verdict == "DENIED":
            self.record("mongo-isolation", PASS,
                        "a trainee's credentials cannot read another trainee's database")
        else:
            self.record("mongo-isolation", FAIL,
                        "a trainee's credentials READ another trainee's database -- "
                        "is mongod running with --auth?", verdict=verdict or probe.stderr[-300:])

    def start_instance(self) -> None:
        if self.status_of("provision") != PASS or self.status_of("image-pull") != PASS:
            self.record("instance-start", SKIP, "nothing to start")
            return
        started = time.monotonic()
        up = self.compose("up", "-d", "xill4")
        if up.returncode != 0:
            self.record("instance-start", FAIL, "the trainee stack would not start",
                        stderr=up.stderr.strip()[-800:])
            return
        self.record("instance-start", PASS,
                    f"container {self.container} started in "
                    f"{round(time.monotonic() - started, 1)}s")

    def check_http(self) -> None:
        """Wait for the instance to answer, then find out which path a healthcheck can use.

        Readiness is an HTTP response, not an open socket: Docker's published-port proxy
        accepts connections the moment the container is created, so a TCP check reports a
        service ready before it has started and every health path then looks dead.
        """
        if self.status_of("instance-start") != PASS:
            self.record("http", SKIP, "instance not running")
            return
        port = int(sandbox.read_env_file(self.trainee_env)["XILL4_PORT"])
        started = time.monotonic()
        responses: dict[str, int | str] = {}
        while time.monotonic() - started < self.args.timeout:
            responses = {path: _probe_path(port, path) for path in HEALTH_PATHS}
            # Any HTTP status at all -- 401 and 404 included -- means a server answered.
            if any(isinstance(code, int) for code in responses.values()):
                break
            time.sleep(2)
        else:
            logs = self.compose("logs", "--tail", "40", "xill4")
            self.record("http", FAIL,
                        f"port {port} never answered HTTP within {self.args.timeout}s",
                        port=port, responses=responses, logs=logs.stdout[-1500:])
            return

        elapsed = round(time.monotonic() - started, 1)
        usable = [path for path, code in responses.items()
                  if isinstance(code, int) and code < 400]
        self.record("http", PASS,
                    f"answered on port {port} after {elapsed}s; healthcheck path: "
                    f"{usable[0] if usable else 'none of the candidates'}",
                    port=port, ready_seconds=elapsed, responses=responses,
                    suggested_health_path=usable[0] if usable else None)

    def check_volumes(self) -> None:
        """The three mount facts grading depends on."""
        if self.status_of("instance-start") != PASS:
            self.record("volumes", SKIP, "instance not running")
            return
        mounts = run(["docker", "inspect", self.container, "--format",
                      "{{json .Mounts}}"]).stdout.strip()
        parsed = json.loads(mounts or "[]")
        leaked = [m["Source"] for m in parsed if ".expected" in str(m.get("Source", ""))]

        write = run(["docker", "exec", self.container, "sh", "-c",
                     "id -u; touch /data/target/.preflight && echo WRITABLE"])
        read_only = run(["docker", "exec", self.container, "sh", "-c",
                         "touch /data/source/.preflight 2>&1 || echo READONLY"])
        probe_file = REPO_ROOT / (f".workspaces/{sandbox.slug(self.args.trainee)}/"
                                  f"{self.args.scenario}/target/.preflight")
        owner = None
        if probe_file.exists():
            stat = probe_file.stat()
            owner = f"{stat.st_uid}:{stat.st_gid}"
            probe_file.unlink()

        problems = []
        if leaked:
            problems.append("the answer key is mounted into the trainee's container")
        if "WRITABLE" not in write.stdout:
            problems.append("the container cannot write /data/target -- set XILL4_RUN_AS_UID="
                            f"{self.run_as_uid if self.run_as_uid is not None else '<uid>'} "
                            "in .env.platform and re-provision")
        if "READONLY" not in read_only.stdout:
            problems.append("/data/source is not read-only")
        detail = {"container_uid": write.stdout.strip().splitlines()[0] if write.stdout else None,
                  "host_owner_of_written_file": owner,
                  "expected_key_mounted": leaked,
                  "shell_available": write.returncode == 0}
        if problems:
            self.record("volumes", FAIL, "; ".join(problems), **detail)
        else:
            self.record("volumes", PASS,
                        f"target writable as uid {detail['container_uid']}, source read-only, "
                        f"answer key not mounted", **detail)

    def check_mongo_state(self) -> None:
        """Did the instance actually put its state in the trainee's database?

        If it did not, the connection string was not accepted and the isolation model is
        describing something the product is not doing.
        """
        if self.status_of("instance-start") != PASS:
            self.record("mongo-state", SKIP, "instance not running")
            return
        probe = self.mongosh(
            'const admin = db.getSiblingDB("admin");'
            'admin.auth(process.env.ROOT_USER, process.env.ROOT_PASSWORD);'
            'print(JSON.stringify(db.getSiblingDB(process.env.DB_NAME)'
            '  .getCollectionNames()));',
            {"ROOT_USER": self.settings.get("MONGO_ROOT_USER", ""),
             "ROOT_PASSWORD": self.settings.get("MONGO_ROOT_PASSWORD", ""),
             "DB_NAME": sandbox.database_name(self.args.trainee)})
        collections = json.loads(probe.stdout.strip().splitlines()[-1] or "[]") \
            if probe.returncode == 0 else []
        if collections:
            self.record("mongo-state", PASS,
                        f"{len(collections)} collection(s) in "
                        f"{sandbox.database_name(self.args.trainee)}", collections=collections)
        else:
            self.record("mongo-state", FAIL,
                        "the instance wrote nothing to its database -- was the connection "
                        "string accepted?", stderr=probe.stderr.strip()[-300:])

    def inspect_mongo_schema(self) -> None:
        """Report the shape of what the instance keeps in its database.

        Field names and types only -- never values. The instance is handed a licence key
        and an environment secret, and if it persists either of them, a dump of values
        would put them in a report that gets passed around.

        This is reconnaissance rather than a pass/fail: it answers whether a check can
        assert on an extraction or a job run from the database, which matters for the
        phases of a migration that produce no file to compare.
        """
        if self.status_of("mongo") != PASS:
            self.record("mongo-schema", SKIP, "no MongoDB")
            return
        probe = self.mongosh(_SCHEMA_JS, {
            "ROOT_USER": self.settings.get("MONGO_ROOT_USER", ""),
            "ROOT_PASSWORD": self.settings.get("MONGO_ROOT_PASSWORD", ""),
            "DB_NAME": sandbox.database_name(self.args.trainee),
            "SAMPLE": str(self.args.schema_sample),
        })
        if probe.returncode != 0:
            self.record("mongo-schema", FAIL, "could not read the database's shape",
                        stderr=probe.stderr.strip()[-400:])
            return
        shape = json.loads(probe.stdout.strip().splitlines()[-1] or "[]")
        if not shape:
            self.record("mongo-schema", SKIP,
                        "the database is empty -- re-run with --schema-only once a "
                        "trainee has actually done an exercise")
            return
        paths = sum(len(entry["fields"]) for entry in shape)
        self.record("mongo-schema", PASS,
                    f"{len(shape)} collection(s), {paths} field path(s) "
                    f"({sum(entry['documents'] for entry in shape)} document(s))",
                    values_included=False, collections=shape)

    def measure_footprint(self) -> None:
        """What one trainee's container costs at idle -- the Phase 1 sizing question."""
        if self.status_of("instance-start") != PASS:
            self.record("footprint", SKIP, "instance not running")
            return
        time.sleep(self.args.settle)
        stats = run(["docker", "stats", "--no-stream", "--format",
                     "{{.CPUPerc}}|{{.MemUsage}}", self.container])
        cpu, _, memory = stats.stdout.strip().partition("|")
        self.record("footprint", PASS, f"idle CPU {cpu}, memory {memory}",
                    idle_cpu=cpu, idle_memory=memory, settled_after_seconds=self.args.settle)

    def teardown(self) -> None:
        if self.args.keep:
            print("\n--keep: the preflight sandbox is still running.")
            return
        self.compose("down", "-v")
        self.mongosh('db.getSiblingDB("admin").auth(process.env.ROOT_USER, '
                     'process.env.ROOT_PASSWORD);'
                     'db.getSiblingDB(process.env.DB_NAME).dropDatabase();'
                     'db.getSiblingDB(process.env.DB_NAME + "_neighbour").dropDatabase();',
                     {"ROOT_USER": self.settings.get("MONGO_ROOT_USER", ""),
                      "ROOT_PASSWORD": self.settings.get("MONGO_ROOT_PASSWORD", ""),
                      "DB_NAME": sandbox.database_name(self.args.trainee)})
        self.trainee_env.unlink(missing_ok=True)

    # ------------------------------------------------------------------ orchestration
    def run_schema_only(self) -> int:
        """Report one existing trainee's database shape, and change nothing else.

        Meant for after the pilot: boot-time state says little, state written by a real
        job is the thing worth looking at.
        """
        print(f"Xill4 sandbox schema report -- {self.args.trainee}\n")
        self.check_docker()
        self.load_settings()
        self.start_platform()
        self.inspect_mongo_schema()
        return self.finish()

    def run_all(self) -> int:
        print(f"Xill4 sandbox preflight -- {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.check_docker()
        self.load_settings()
        self.check_registry()
        self.check_image()
        self.inspect_image()
        self.start_platform()
        self.provision()
        self.check_isolation()
        self.start_instance()
        self.check_http()
        self.check_volumes()
        self.check_mongo_state()
        self.inspect_mongo_schema()
        self.measure_footprint()
        self.teardown()
        return self.finish()

    def finish(self) -> int:
        failures = [result for result in self.results if result.status == FAIL]
        passed = [result for result in self.results if result.status == PASS]
        skipped = [result for result in self.results if result.status == SKIP]
        print(f"\n{len(passed)} passed, {len(failures)} failed, {len(skipped)} skipped"
              f"{'' if not failures else ' -- failed: ' + ', '.join(f.name for f in failures)}")
        for line in self.next_steps():
            print(f"  {line}")
        if self.args.json:
            report = {"image": self.image, "substitute_image": bool(self.args.image),
                      "when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "results": [asdict(result) for result in self.results]}
            self.args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(f"report written to {self.args.json}")
        return 1 if failures else 0


    def next_steps(self) -> list[str]:
        """The handful of values a run of this produces that other files need."""
        steps = []
        metadata = next((r for r in self.results if r.name == "image-metadata"), None)
        if metadata and metadata.detail.get("uid") is not None:
            steps.append(f"add XILL4_RUN_AS_UID={metadata.detail['uid']} to .env.platform")
        http = next((r for r in self.results if r.name == "http"), None)
        if http and http.detail.get("suggested_health_path"):
            steps.append("set XILL4_HEALTH_PATH="
                         f"{http.detail['suggested_health_path']} in .env.platform "
                         "(the compose healthcheck currently guesses)")
        return ["", "next:", *steps] if steps else []


_CREATE_USER_JS = """
const env = process.env;
if (!db.getSiblingDB("admin").auth(env.ROOT_USER, env.ROOT_PASSWORD)) {
  throw new Error("root authentication failed");
}
const target = db.getSiblingDB(env.DB_NAME);
const roles = [{role: "dbOwner", db: env.DB_NAME}];
if (target.getUser(env.DB_USER)) {
  target.updateUser(env.DB_USER, {pwd: env.DB_PASSWORD, roles: roles});
} else {
  target.createUser({user: env.DB_USER, pwd: env.DB_PASSWORD, roles: roles});
}
print("ok");
"""

# Writes a document into a neighbouring database as root, then tries to read it back with
# only the trainee's own credentials. "DENIED" is the passing answer.
_ISOLATION_JS = """
const env = process.env;
if (!db.getSiblingDB("admin").auth(env.ROOT_USER, env.ROOT_PASSWORD)) {
  throw new Error("root authentication failed");
}
db.getSiblingDB(env.NEIGHBOUR).flows.insertOne({name: "another trainee's flow"});
const trainee = new Mongo().getDB(env.DB_NAME);
if (!trainee.auth(env.DB_USER, env.DB_PASSWORD)) {
  throw new Error("the trainee's own credentials were refused");
}
try {
  const stolen = trainee.getSiblingDB(env.NEIGHBOUR).flows.findOne();
  print(stolen ? "READ" : "EMPTY");
} catch (e) {
  print("DENIED");
}
"""


# Walks a sample of each collection and reports field PATHS and TYPES only. Values are
# never read out: the instance holds a licence key and an environment secret, and a shape
# report is meant to be pasted into a ticket.
_SCHEMA_JS = """
const env = process.env;
if (!db.getSiblingDB("admin").auth(env.ROOT_USER, env.ROOT_PASSWORD)) {
  throw new Error("root authentication failed");
}
const target = db.getSiblingDB(env.DB_NAME);
const sample = parseInt(env.SAMPLE || "5", 10);
const MAX_PATHS = 200;

function kindOf(value) {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  if (value instanceof Date) return "date";
  if (value && value._bsontype) return value._bsontype;
  return typeof value;
}

function walk(document, prefix, fields, depth) {
  for (const key of Object.keys(document)) {
    if (Object.keys(fields).length >= MAX_PATHS) return;
    const path = prefix ? prefix + "." + key : key;
    const value = document[key];
    fields[path] = kindOf(value);
    const nested = value && typeof value === "object" && !Array.isArray(value)
                   && !(value instanceof Date) && !value._bsontype;
    if (depth > 0 && nested) walk(value, path, fields, depth - 1);
  }
}

const shape = [];
for (const name of target.getCollectionNames()) {
  const collection = target.getCollection(name);
  const fields = {};
  collection.find().limit(sample).forEach(d => walk(d, "", fields, 2));
  shape.push({collection: name, documents: collection.countDocuments(), fields: fields});
}
print(JSON.stringify(shape));
"""


def _numeric_uid(user: str, image: str) -> int | None:
    """The uid the image runs as, resolving a user *name* by asking the image itself."""
    if user.isdigit():
        return int(user)
    probe = run(["docker", "run", "--rm", "--entrypoint", "id", image, "-u"])
    answer = probe.stdout.strip()
    return int(answer) if answer.isdigit() else None


def _probe_path(port: int, path: str) -> int | str:
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return f"no answer ({exc.__class__.__name__})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="preflight", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trainee", default="preflight",
                        help="throwaway trainee id to provision (default: preflight)")
    parser.add_argument("--scenario", default="01-legacy-fileshare")
    parser.add_argument("--image", help="substitute image, to exercise this script without "
                                        "access to the real one")
    parser.add_argument("--token", help="Cloudsmith entitlement token; prefer having run "
                                        "`docker login` beforehand to keep it out of shell history")
    parser.add_argument("--registry-user", default="xillio/xill4")
    parser.add_argument("--mongo-container", default="xill4-sbx-mongo")
    parser.add_argument("--timeout", type=int, default=180,
                        help="seconds to wait for the instance to answer (default: 180)")
    parser.add_argument("--settle", type=int, default=30,
                        help="seconds to idle before measuring the footprint (default: 30)")
    parser.add_argument("--schema-sample", type=int, default=5,
                        help="documents sampled per collection for the shape report")
    parser.add_argument("--schema-only", action="store_true",
                        help="report an existing trainee's database shape and do nothing "
                             "else -- run it after a trainee has done an exercise")
    parser.add_argument("--keep", action="store_true", help="leave the sandbox running")
    parser.add_argument("--json", type=Path, help="write the full report here")
    args = parser.parse_args(argv)
    preflight = Preflight(args)
    return preflight.run_schema_only() if args.schema_only else preflight.run_all()


if __name__ == "__main__":
    raise SystemExit(main())

"""Opt-in hosted coding/checkpoint acceptance. This creates billable compute.

Run only after preparing a provider template and configuring a dedicated test
Postgres database. No model calls are made; native harness acceptance is separate.
"""

import argparse
import os
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from agno.db.postgres import PostgresDb
from agno.sandbox import SandboxSpec
from agno.sandbox.allocation import PostgresAllocationJournal
from agno.sandbox.checkpoint import FileCheckpointStore
from agno.sandbox.hosted_transfer import HostedCheckpointTransfer
from agno.sandbox.postgres import PostgresSandboxStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider", choices=("e2b", "daytona", "modal", "vercel"), required=True
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Prepared provider template/snapshot/image identifier",
    )
    parser.add_argument("--cpus", type=float, default=2)
    parser.add_argument("--memory-mb", type=int)
    parser.add_argument("--lifetime", type=int, default=600)
    args = parser.parse_args()

    namespace = "acceptance-" + uuid4().hex[:12]
    db = PostgresDb(
        db_url=os.environ["AGNO_TEST_SANDBOX_DB_URL"],
        session_table=namespace.replace("-", "_") + "_sessions",
        runs_table=namespace.replace("-", "_") + "_runs",
    )
    store = PostgresSandboxStore(
        db, table_name=namespace.replace("-", "_") + "_bindings"
    )
    store.setup()
    journal = PostgresAllocationJournal(
        store, table_name=namespace.replace("-", "_") + "_allocations"
    )
    journal.setup()
    if args.provider == "e2b":
        from agno.sandbox.e2b import E2BSandboxProvider

        provider = E2BSandboxProvider(
            namespace, journal, max_allocations=2, lifetime=args.lifetime
        )
    elif args.provider == "daytona":
        from agno.sandbox.daytona import DaytonaSandboxProvider

        provider = DaytonaSandboxProvider(
            namespace, journal, max_allocations=2, lifetime=args.lifetime
        )
    elif args.provider == "modal":
        from agno.sandbox.modal import ModalSandboxProvider

        provider = ModalSandboxProvider(
            namespace,
            journal,
            app_name=os.environ["AGNO_MODAL_APP"],
            max_allocations=2,
            lifetime=args.lifetime,
        )
    else:
        from agno.sandbox.vercel import VercelSandboxProvider

        provider = VercelSandboxProvider(
            namespace, journal, max_allocations=2, lifetime=args.lifetime
        )
    spec = SandboxSpec(
        "coder",
        "acceptance",
        1,
        args.image,
        pids_limit=None,
        workspace_mb=None,
        cpus=args.cpus,
        memory_mb=args.memory_mb
        if args.memory_mb is not None
        else (4096 if args.provider == "vercel" else 2048),
    )
    script = Path(__file__).with_name("workload_fixture.py").read_text()
    handles = []
    try:
        with TemporaryDirectory() as directory:
            transfer = HostedCheckpointTransfer(
                provider, FileCheckpointStore(Path(directory) / "objects")
            )
            first = provider.create(spec)
            handles.append(first)
            result = provider.exec(
                first, ["python", "-c", script, "prepare"], timeout=90
            )
            assert result.exit_code == 0, result.stderr
            print(result.stdout.strip())
            checkpoint = transfer.capture(
                first, state={"fixture": "hosted-workload-v1"}
            )
            provider.destroy(first)
            second = provider.create(replace(spec, generation=2))
            handles.append(second)
            assert transfer.restore(second, checkpoint) == {
                "fixture": "hosted-workload-v1"
            }
            result = provider.exec(
                second, ["python", "-c", script, "verify"], timeout=30
            )
            assert result.exit_code == 0, result.stderr
            print(result.stdout.strip())
            print("Verified checkpoint:", checkpoint.sha256)
    finally:
        for handle in handles:
            provider.destroy(handle)
        # Keep allocation records for ambiguous-create reconciliation. This
        # cookbook never deletes an uncertain intent merely to tidy test data.
        print("Inspect test allocation table before removal:", journal.table.name)
        db.db_engine.dispose()


if __name__ == "__main__":
    main()

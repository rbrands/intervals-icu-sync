"""Deploy the Foundry prompt agent and (re)build its coach-logic vector store.

This script is the CI/CD entry point for publishing a new version of the
``training-architect-agent`` Foundry prompt agent. It performs three steps:

1. Build (or refresh) a vector store from the ``coach-logic/`` knowledge files.
2. Assemble the final agent definition from ``agent.yaml`` — embedding all
   discipline profiles and the freshly created vector store id. The discipline
   is selected at runtime via the ``{{discipline}}`` structured input.
3. Upsert a new agent version via the Foundry agents data-plane REST API.

Authentication uses ``DefaultAzureCredential`` so it works both locally
(``az login``) and in GitHub Actions (OIDC federated credential).

Flags
-----
- ``--dry-run`` — render the assembled definition to ``foundry-agent/.rendered/``
  without contacting Foundry or building a vector store.
- ``--vector-store-only`` — only build/refresh the ``coach-logic`` vector store
  and print its id; do not create a new agent version.

Required environment variables
------------------------------
- ``FOUNDRY_PROJECT_ENDPOINT`` — e.g. ``https://<resource>.services.ai.azure.com/api/projects/<project>``

Optional environment variables
-------------------------------
- ``AGENT_NAME`` — defaults to the ``name`` field in ``agent.yaml``
- ``MODEL`` — overrides ``definition.model`` from ``agent.yaml``
- ``VECTOR_STORE_NAME`` — defaults to ``coach-logic``
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_AGENT_FILE = _REPO_ROOT / "foundry-agent" / "agent.yaml"
_COACH_LOGIC_DIR = _REPO_ROOT / "coach-logic"
_PROMPTS_DIR = _REPO_ROOT / "prompts"

_PROFILES_PLACEHOLDER = "<<INSERT DISCIPLINE PROFILES HERE>>"
_VECTOR_STORE_PLACEHOLDER = "<VECTOR_STORE_ID>"

# Discipline blocks embedded into the instructions; selected at runtime via the
# {{discipline}} structured input.
_DISCIPLINES = ["climber", "criterium", "marathon", "roadrace"]

_KNOWLEDGE_FILES = [
    "coaching-principles.md",
    "interpretation-rules.md",
    "decision-process.md",
    "training-zones.md",
    "input-schema.md",
    "workout-library.md",
]


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"ERROR: required environment variable {name} is not set.")
        sys.exit(1)
    return value


def _load_agent_definition() -> dict:
    return yaml.safe_load(_AGENT_FILE.read_text(encoding="utf-8"))


def _embed_discipline_profiles(instructions: str) -> str:
    """Replace the profiles placeholder with all discipline blocks.

    The runtime ``{{discipline}}`` structured input selects which block applies;
    all blocks are embedded so a single agent version serves every discipline.
    """
    if _PROFILES_PLACEHOLDER not in instructions:
        print(f"WARNING: placeholder '{_PROFILES_PLACEHOLDER}' not found; instructions left unchanged.")
        return instructions

    sections: list[str] = []
    for discipline in _DISCIPLINES:
        block_file = _PROMPTS_DIR / f"discipline_{discipline}.md"
        if not block_file.exists():
            print(f"ERROR: discipline prompt missing: {block_file}")
            sys.exit(1)
        block = block_file.read_text(encoding="utf-8").strip()
        sections.append(f"### {discipline}\n\n{block}")

    return instructions.replace(_PROFILES_PLACEHOLDER, "\n\n".join(sections))


def _openai_client(endpoint: str, credential):
    """Return a project-scoped OpenAI-compatible client for vector stores/files."""
    from azure.ai.projects import AIProjectClient

    project_client = AIProjectClient(
        endpoint=endpoint,
        credential=credential,
        allow_preview=True,
    )
    return project_client.get_openai_client()


def _find_vector_store(client, name: str):
    """Return an existing vector store with the given name, or None."""
    for store in client.vector_stores.list():
        if store.name == name:
            return store
    return None


def _clear_vector_store_files(client, store_id: str) -> None:
    """Detach and delete all files currently attached to the vector store."""
    from openai import APIError

    for entry in client.vector_stores.files.list(vector_store_id=store_id):
        client.vector_stores.files.delete(vector_store_id=store_id, file_id=entry.id)
        # Also remove the underlying uploaded file so old revisions don't pile up.
        file_id = getattr(entry, "file_id", None)
        if file_id:
            try:
                client.files.delete(file_id)
            except APIError as exc:
                print(f"  WARNING: could not delete file {file_id}: {exc}")


def _build_vector_store(client) -> str:
    name = os.environ.get("VECTOR_STORE_NAME", "coach-logic")

    store = _find_vector_store(client, name)
    if store is None:
        print(f"Creating vector store '{name}' ...")
        store = client.vector_stores.create(name=name)
    else:
        print(f"Reusing vector store '{name}' ({store.id}); refreshing files ...")
        _clear_vector_store_files(client, store.id)

    for filename in _KNOWLEDGE_FILES:
        path = _COACH_LOGIC_DIR / filename
        if not path.exists():
            print(f"ERROR: knowledge file missing: {path}")
            sys.exit(1)
        print(f"  uploading {filename} ...")
        with path.open("rb") as handle:
            uploaded = client.files.create(file=handle, purpose="assistants")
        client.vector_stores.files.create_and_poll(
            vector_store_id=store.id, file_id=uploaded.id
        )

    print(f"Vector store ready: {store.id}")
    return store.id


def _upsert_agent(project_client, definition: dict) -> None:
    from azure.core.exceptions import HttpResponseError

    agent_name = os.environ.get("AGENT_NAME") or definition.get("name")
    if not agent_name:
        print("ERROR: agent name not provided (AGENT_NAME or agent.yaml 'name').")
        sys.exit(1)

    print(f"Upserting agent '{agent_name}' via Azure AI Projects SDK ...")
    try:
        result = project_client.agents.create_version(
            agent_name=agent_name,
            definition=definition["definition"],
            description=definition.get("description", ""),
        )
    except HttpResponseError as exc:
        print(f"ERROR: agent upsert failed: {exc}")
        sys.exit(1)

    deployed_name = getattr(result, "name", agent_name)
    deployed_version = getattr(result, "version", "?")
    print(f"Agent deployed: {deployed_name} version {deployed_version}")


def _dry_run(definition: dict) -> None:
    """Render the assembled definition to disk without contacting Foundry."""
    inner = definition["definition"]
    if "MODEL" in os.environ:
        inner["model"] = os.environ["MODEL"]
    inner["instructions"] = _embed_discipline_profiles(inner.get("instructions", ""))

    out_dir = _REPO_ROOT / "foundry-agent" / ".rendered"
    out_dir.mkdir(parents=True, exist_ok=True)

    instructions_path = out_dir / "instructions.txt"
    definition_path = out_dir / "agent.definition.json"
    instructions_path.write_text(inner["instructions"], encoding="utf-8")
    definition_path.write_text(json.dumps(definition, indent=2, ensure_ascii=False), encoding="utf-8")

    if _PROFILES_PLACEHOLDER in inner["instructions"]:
        print(f"WARNING: '{_PROFILES_PLACEHOLDER}' still present in rendered instructions.")

    print("Dry run — no Foundry calls made. Vector store NOT built.")
    print(f"  instructions: {instructions_path}")
    print(f"  definition:   {definition_path}")
    print("Note: the file_search tool still shows the <VECTOR_STORE_ID> placeholder;")
    print("      it is replaced with a real id only during an actual deploy.")


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    vector_store_only = "--vector-store-only" in sys.argv

    definition = _load_agent_definition()

    if dry_run:
        _dry_run(definition)
        return

    endpoint = _require_env("FOUNDRY_PROJECT_ENDPOINT")
    from azure.identity import DefaultAzureCredential

    credential = DefaultAzureCredential()

    if vector_store_only:
        client = _openai_client(endpoint, credential)
        vector_store_id = _build_vector_store(client)
        print(f"Vector store only — agent NOT updated. Vector store id: {vector_store_id}")
        return

    inner = definition["definition"]

    if "MODEL" in os.environ:
        inner["model"] = os.environ["MODEL"]

    inner["instructions"] = _embed_discipline_profiles(inner.get("instructions", ""))

    client = _openai_client(endpoint, credential)
    vector_store_id = _build_vector_store(client)

    for tool in inner.get("tools", []):
        if tool.get("type") == "file_search":
            tool["vector_store_ids"] = [vector_store_id]

    if _VECTOR_STORE_PLACEHOLDER in yaml.safe_dump(inner):
        print(f"WARNING: '{_VECTOR_STORE_PLACEHOLDER}' still present; no file_search tool updated.")

    from azure.ai.projects import AIProjectClient

    project_client = AIProjectClient(endpoint=endpoint, credential=credential, allow_preview=True)
    _upsert_agent(project_client, definition)


if __name__ == "__main__":
    main()

"""Deploy the Foundry prompt agent and (re)build its coach-logic vector store.

This script is the CI/CD entry point for publishing a new version of the
``training-architect-agent`` Foundry prompt agent. It performs five steps:

1. Build (or refresh) a vector store from the ``coach-logic/`` knowledge files.
2. Build a new version of the ``training-plan-generation`` skill from
    ``coach-logic/skill/SKILL.md`` and selected reference files.
3. Build/update ``training-plan-toolbox`` with a skill reference to the
    deployed skill version.
4. Assemble the final agent definition from ``agent.yaml`` — embedding all
   discipline profiles and the freshly created vector store id. The discipline
   is selected at runtime via the ``{{discipline}}`` structured input.
5. Upsert a new agent version via the Foundry agents data-plane REST API.

Authentication uses ``DefaultAzureCredential`` so it works both locally
(``az login``) and in GitHub Actions (OIDC federated credential).

Flags
-----
- ``--dry-run`` — render the assembled definition to ``foundry-agent/.rendered/``
  without contacting Foundry or building a vector store.
- ``--vector-store-only`` — only build/refresh the ``coach-logic`` vector store
  and print its id; do not create a new agent version.
- ``--skill-only`` — only build/refresh the ``training-plan-generation`` skill
    and print the deployed version; do not update the agent.

Required environment variables
------------------------------
- ``FOUNDRY_PROJECT_ENDPOINT`` — e.g. ``https://<resource>.services.ai.azure.com/api/projects/<project>``

Optional environment variables
-------------------------------
- ``AGENT_NAME`` — defaults to the ``name`` field in ``agent.yaml``
- ``MODEL`` — overrides ``definition.model`` from ``agent.yaml``
- ``VECTOR_STORE_NAME`` — defaults to ``coach-logic``
- ``SKILL_NAME`` — defaults to ``training-plan-generation``
- ``TOOLBOX_NAME`` — defaults to ``training-plan-toolbox``
"""

from __future__ import annotations

import io
import json
import hashlib
import os
import sys
import zipfile
from pathlib import Path

import yaml
from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[1]
_AGENT_FILE = _REPO_ROOT / "foundry-agent" / "agent.yaml"
_COACH_LOGIC_DIR = _REPO_ROOT / "coach-logic"
_PROMPTS_DIR = _REPO_ROOT / "prompts"
_SKILL_DIR = _COACH_LOGIC_DIR / "skill"

_PROFILES_PLACEHOLDER = "<<INSERT DISCIPLINE PROFILES HERE>>"
_VECTOR_STORE_PLACEHOLDER = "<VECTOR_STORE_ID>"
_DEFAULT_SKILL_NAME = "training-plan-generation"
_DEFAULT_TOOLBOX_NAME = "training-plan-toolbox"

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

_SKILL_REFERENCE_FILES = [
    "decision-process.md",
    "workout-library.md",
]


def _read_skill_source_files() -> dict[str, bytes]:
    """Return skill source files keyed by archive path."""
    skill_manifest = _SKILL_DIR / "SKILL.md"
    if not skill_manifest.exists():
        print(f"ERROR: skill manifest missing: {skill_manifest}")
        sys.exit(1)

    files: dict[str, bytes] = {
        "SKILL.md": skill_manifest.read_bytes(),
    }
    for filename in _SKILL_REFERENCE_FILES:
        path = _COACH_LOGIC_DIR / filename
        if not path.exists():
            print(f"ERROR: skill reference file missing: {path}")
            sys.exit(1)
        files[f"references/{filename}"] = path.read_bytes()
    return files


def _hash_skill_file_map(files: dict[str, bytes]) -> str:
    """Hash skill payload deterministically by path and content."""
    digest = hashlib.sha256()
    for rel_path in sorted(files):
        digest.update(rel_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(files[rel_path])
        digest.update(b"\0")
    return digest.hexdigest()


def _hash_skill_zip_content(zip_bytes: bytes) -> str:
    """Hash a downloaded skill ZIP by logical file content, ignoring ZIP metadata."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        files: dict[str, bytes] = {}
        for name in zf.namelist():
            normalized = name.replace("\\", "/").strip("/")
            if normalized.endswith("/"):
                continue
            files[normalized] = zf.read(name)
    return _hash_skill_file_map(files)


def _download_skill_version_zip(project_client, skill_name: str, skill_version: str) -> bytes:
    """Download a skill version archive as raw bytes."""
    chunks = project_client.beta.skills.download_version(name=skill_name, version=skill_version)
    return b"".join(chunks)


def _load_env() -> None:
    """Load environment variables from .env if present."""
    env_file = _REPO_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=False)


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
            metadata=definition.get("metadata"),
        )
    except HttpResponseError as exc:
        print(f"ERROR: agent upsert failed: {exc}")
        sys.exit(1)

    deployed_name = getattr(result, "name", agent_name)
    deployed_version = getattr(result, "version", "?")
    print(f"Agent deployed: {deployed_name} version {deployed_version}")


def _zip_skill() -> bytes:
    """Pack SKILL.md and selected reference files into an in-memory ZIP."""
    files = _read_skill_source_files()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path, content in files.items():
            zf.writestr(rel_path, content)

    return buf.getvalue()


def _build_skill(project_client) -> tuple[str, str, bool]:
    """Create/update skill only when content changed. Returns (name, version, changed)."""
    from azure.core.exceptions import HttpResponseError

    if not hasattr(project_client, "beta") or not hasattr(project_client.beta, "skills"):
        print("ERROR: this azure-ai-projects version does not expose beta.skills operations.")
        print("       Upgrade foundry-agent dependencies and try again.")
        sys.exit(1)

    skill_name = os.environ.get("SKILL_NAME", _DEFAULT_SKILL_NAME)
    desired_files = _read_skill_source_files()
    desired_hash = _hash_skill_file_map(desired_files)

    try:
        details = project_client.beta.skills.get(name=skill_name)
        current_default = getattr(details, "default_version", None)
    except HttpResponseError:
        current_default = None

    if current_default:
        current_zip = _download_skill_version_zip(project_client, skill_name, current_default)
        current_hash = _hash_skill_zip_content(current_zip)
        if current_hash == desired_hash:
            print(f"Skill '{skill_name}' unchanged; reusing default version {current_default}.")
            return skill_name, current_default, False

    skill_zip = _zip_skill()
    zip_stream = io.BytesIO(skill_zip)
    zip_stream.name = f"{skill_name}.zip"

    print(f"Building skill '{skill_name}' ...")
    version = project_client.beta.skills.create_from_files(
        name=skill_name,
        content={
            "files": [(zip_stream.name, zip_stream, "application/zip")],
            "default": True,
        },
    )
    skill_version = getattr(version, "version", None)
    if not skill_version:
        print("ERROR: skill version creation returned no version.")
        sys.exit(1)

    # Keep this explicit promotion step for deterministic behavior across SDK versions.
    project_client.beta.skills.update(name=skill_name, default_version=skill_version)
    print(f"Skill deployed: {skill_name} version {skill_version} (default)")
    return skill_name, skill_version, True


def _toolbox_version_uses_skill(project_client, toolbox_name: str, toolbox_version: str, skill_name: str, skill_version: str) -> bool:
    """Check whether a toolbox version already references the target skill version."""
    version_obj = project_client.beta.toolboxes.get_version(name=toolbox_name, version=toolbox_version)
    for skill in getattr(version_obj, "skills", []) or []:
        if getattr(skill, "name", None) == skill_name and getattr(skill, "version", None) == skill_version:
            return True
        if isinstance(skill, dict) and skill.get("name") == skill_name and skill.get("version") == skill_version:
            return True
    return False


def _build_toolbox(project_client, skill_name: str, skill_version: str) -> tuple[str, str, bool]:
    """Create/update toolbox only when skill reference differs. Returns (name, version, changed)."""
    from azure.core.exceptions import HttpResponseError

    if not hasattr(project_client, "beta") or not hasattr(project_client.beta, "toolboxes"):
        print("ERROR: this azure-ai-projects version does not expose beta.toolboxes operations.")
        print("       Upgrade foundry-agent dependencies and try again.")
        sys.exit(1)

    toolbox_name = os.environ.get("TOOLBOX_NAME", _DEFAULT_TOOLBOX_NAME)

    try:
        toolbox_details = project_client.beta.toolboxes.get(name=toolbox_name)
        current_default = getattr(toolbox_details, "default_version", None)
    except HttpResponseError:
        current_default = None

    if current_default:
        if _toolbox_version_uses_skill(project_client, toolbox_name, current_default, skill_name, skill_version):
            print(f"Toolbox '{toolbox_name}' unchanged; reusing default version {current_default}.")
            return toolbox_name, current_default, False

    print(f"Building toolbox '{toolbox_name}' with skill '{skill_name}:{skill_version}' ...")

    toolbox_version = project_client.beta.toolboxes.create_version(
        name=toolbox_name,
        tools=[],
        skills=[
            {
                "type": "skill_reference",
                "name": skill_name,
                "version": skill_version,
            }
        ],
        description="Toolbox for training plan generation skill",
    )

    version = getattr(toolbox_version, "version", None)
    if not version:
        print("ERROR: toolbox version creation returned no version.")
        sys.exit(1)

    project_client.beta.toolboxes.update(name=toolbox_name, default_version=version)
    print(f"Toolbox deployed: {toolbox_name} version {version} (default)")
    return toolbox_name, version, True


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
    _load_env()

    dry_run = "--dry-run" in sys.argv
    vector_store_only = "--vector-store-only" in sys.argv
    skill_only = "--skill-only" in sys.argv

    definition = _load_agent_definition()

    if dry_run:
        _dry_run(definition)
        return

    endpoint = _require_env("FOUNDRY_PROJECT_ENDPOINT")
    from azure.identity import DefaultAzureCredential

    credential = DefaultAzureCredential()
    from azure.ai.projects import AIProjectClient

    project_client = AIProjectClient(endpoint=endpoint, credential=credential, allow_preview=True)

    if skill_only:
        skill_name, skill_version, skill_changed = _build_skill(project_client)
        status = "updated" if skill_changed else "unchanged"
        print(f"Skill only — agent NOT updated. Skill: {skill_name} version {skill_version} ({status})")
        return

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
    skill_name, skill_version, skill_changed = _build_skill(project_client)
    toolbox_name, toolbox_version, toolbox_changed = _build_toolbox(project_client, skill_name, skill_version)

    for tool in inner.get("tools", []):
        if tool.get("type") == "file_search":
            tool["vector_store_ids"] = [vector_store_id]

    if _VECTOR_STORE_PLACEHOLDER in yaml.safe_dump(inner):
        print(f"WARNING: '{_VECTOR_STORE_PLACEHOLDER}' still present; no file_search tool updated.")

    metadata = definition.get("metadata") or {}
    metadata["skill_name"] = skill_name
    metadata["skill_version"] = skill_version
    metadata["skill_changed"] = str(skill_changed).lower()
    metadata["toolbox_name"] = toolbox_name
    metadata["toolbox_version"] = toolbox_version
    metadata["toolbox_changed"] = str(toolbox_changed).lower()
    definition["metadata"] = metadata

    _upsert_agent(project_client, definition)


if __name__ == "__main__":
    main()

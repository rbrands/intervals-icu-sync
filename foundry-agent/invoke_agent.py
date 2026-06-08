"""Invoke the deployed Foundry prompt agent for local testing.

This calls the agent through the Responses API and supplies the runtime
structured inputs (discipline + intervals.icu credentials) that the agent
forwards to the MCP server as ``X-Intervals-*`` headers. It mirrors what the
end-user application does, so you can test the production path without the
Playground (which does not send structured inputs).

Authentication to Foundry uses ``DefaultAzureCredential`` (``az login`` locally).

Required environment variables (can be set in a .env file)
----------------------------------------------------------
- ``FOUNDRY_PROJECT_ENDPOINT`` — e.g. ``https://<resource>.services.ai.azure.com/api/projects/<project>``
- ``ATHLETE_ID`` — intervals.icu athlete id (sent as X-Intervals-Athlete-Id)
- ``INTERVALS_API_KEY`` — intervals.icu API key (sent as X-Intervals-Api-Key; never logged)

Optional environment variables
-------------------------------
- ``AGENT_NAME`` — defaults to ``training-architect-agent``
- ``DISCIPLINE`` — climber | criterium | marathon | roadrace (default ``climber``)
- ``MESSAGE`` — the user message to send (default: a short weekly assessment ask)

Usage
-----
    # values are read from .env (or the environment)
    python foundry-agent/invoke_agent.py            # single turn (one Q/A)
    python foundry-agent/invoke_agent.py --chat     # interactive multi-turn chat

In ``--chat`` mode each turn chains from the previous response id, so the
agent keeps dialog context even when the Conversations endpoint is unavailable.
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()

_DEFAULT_MESSAGE = (
    "Please assess my current training week. Use the MCP tools to fetch data first."
)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"ERROR: required environment variable {name} is not set.")
        sys.exit(1)
    return value


def _openai_client(endpoint: str, agent_name: str):
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    project_client = AIProjectClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
        allow_preview=True,
    )
    return project_client.get_openai_client(agent_name=agent_name)


def _send(client, message, structured_inputs, previous_response_id=None):
    kwargs = {
        "input": message,
        "extra_body": {
            "structured_inputs": structured_inputs,
        },
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id

    response = client.responses.create(**kwargs)
    return response.output_text, response.id


def main() -> None:
    interactive = "--chat" in sys.argv

    endpoint = _require_env("FOUNDRY_PROJECT_ENDPOINT")
    athlete_id = _require_env("ATHLETE_ID")
    api_key = _require_env("INTERVALS_API_KEY")

    agent_name = os.environ.get("AGENT_NAME", "training-architect-agent")
    discipline = os.environ.get("DISCIPLINE", "climber")
    message = os.environ.get("MESSAGE", _DEFAULT_MESSAGE)

    # The same structured inputs are sent on every turn — they are per-request.
    structured_inputs = {
        "discipline": discipline,
        "intervals_athlete_id": athlete_id,
        "intervals_api_key": api_key,
    }

    client = _openai_client(endpoint, agent_name)
    print(f"Agent: {agent_name} (discipline={discipline})")

    if not interactive:
        # Single-turn mode: one question, one answer.
        print("\n--- Agent response ---\n")
        answer, _ = _send(client, message, structured_inputs)
        print(answer)
        return

    # Multi-turn mode: chain responses so context is preserved across turns.
    previous_response_id = None
    print("Multi-turn chat — type your message, or 'exit' / 'quit' to stop.\n")
    while True:
        try:
            user_message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_message:
            continue
        if user_message.lower() in {"exit", "quit"}:
            break
        answer, previous_response_id = _send(
            client,
            user_message,
            structured_inputs,
            previous_response_id=previous_response_id,
        )
        print(f"\nCoach: {answer}\n")


if __name__ == "__main__":
    main()

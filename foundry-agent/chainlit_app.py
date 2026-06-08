"""Chainlit web frontend for local testing of the Foundry prompt agent.

This app mirrors ``invoke_agent.py`` but provides a browser-based chat UI.
It keeps a multi-turn context using ``previous_response_id`` and forwards
runtime structured inputs on every request.

Required environment variables:
- FOUNDRY_PROJECT_ENDPOINT
- ATHLETE_ID
- INTERVALS_API_KEY

Optional environment variables:
- AGENT_NAME (default: training-architect-agent)
- DISCIPLINE (default: climber)
- RESPONSE_LANGUAGE (default: de)
"""

from __future__ import annotations

import asyncio
import os

import chainlit as cl
from dotenv import load_dotenv

load_dotenv()


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Required environment variable {name} is not set.")
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


def _send(client, message: str, structured_inputs: dict[str, str], previous_response_id: str | None):
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


def _settings_text(structured_inputs: dict[str, str]) -> str:
    return (
        "Current settings\n"
        f"- discipline: {structured_inputs['discipline']}\n"
        f"- response_language: {structured_inputs['response_language']}\n"
        "\nCommands\n"
        "- /discipline <climber|criterium|marathon|roadrace>\n"
        "- /language <de|en|...>\n"
        "- /settings"
    )


@cl.on_chat_start
async def on_chat_start() -> None:
    try:
        endpoint = _require_env("FOUNDRY_PROJECT_ENDPOINT")
        athlete_id = _require_env("ATHLETE_ID")
        api_key = _require_env("INTERVALS_API_KEY")
    except ValueError as exc:
        await cl.Message(content=f"Configuration error: {exc}").send()
        return

    agent_name = os.environ.get("AGENT_NAME", "training-architect-agent")
    discipline = os.environ.get("DISCIPLINE", "climber")
    response_language = os.environ.get("RESPONSE_LANGUAGE", "de")

    client = _openai_client(endpoint, agent_name)
    structured_inputs = {
        "discipline": discipline,
        "response_language": response_language,
        "intervals_athlete_id": athlete_id,
        "intervals_api_key": api_key,
    }

    cl.user_session.set("client", client)
    cl.user_session.set("structured_inputs", structured_inputs)
    cl.user_session.set("previous_response_id", None)

    await cl.Message(
        content=(
            f"Connected to agent **{agent_name}**.\n\n"
            f"{_settings_text(structured_inputs)}"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    content = message.content.strip()
    if not content:
        return

    structured_inputs = cl.user_session.get("structured_inputs")
    client = cl.user_session.get("client")
    previous_response_id = cl.user_session.get("previous_response_id")

    if client is None or structured_inputs is None:
        await cl.Message(content="Session is not initialized. Please refresh the page.").send()
        return

    if content.startswith("/discipline "):
        new_value = content.split(" ", 1)[1].strip()
        if not new_value:
            await cl.Message(content="Usage: /discipline <value>").send()
            return
        structured_inputs["discipline"] = new_value
        cl.user_session.set("structured_inputs", structured_inputs)
        await cl.Message(content=_settings_text(structured_inputs)).send()
        return

    if content.startswith("/language "):
        new_value = content.split(" ", 1)[1].strip()
        if not new_value:
            await cl.Message(content="Usage: /language <value>").send()
            return
        structured_inputs["response_language"] = new_value
        cl.user_session.set("structured_inputs", structured_inputs)
        await cl.Message(content=_settings_text(structured_inputs)).send()
        return

    if content == "/settings":
        await cl.Message(content=_settings_text(structured_inputs)).send()
        return

    from azure.core.exceptions import HttpResponseError
    from openai import (
        APIConnectionError,
        APIStatusError,
        AuthenticationError,
        BadRequestError,
        NotFoundError,
        PermissionDeniedError,
        RateLimitError,
    )

    try:
        answer, response_id = await asyncio.to_thread(
            _send,
            client,
            content,
            structured_inputs,
            previous_response_id,
        )
    except (
        APIConnectionError,
        APIStatusError,
        AuthenticationError,
        BadRequestError,
        NotFoundError,
        PermissionDeniedError,
        RateLimitError,
        HttpResponseError,
    ) as exc:
        await cl.Message(content=f"Agent request failed: {exc}").send()
        return

    cl.user_session.set("previous_response_id", response_id)
    await cl.Message(content=answer).send()

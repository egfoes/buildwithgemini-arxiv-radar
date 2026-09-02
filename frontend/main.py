"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.

Why A2A: agents-cli 1.1.0 (GA) deploys ADK agents to Agent Runtime as A2A agents
and no longer registers the reasoning-engine operation schema the old
`agent_engines.get(...).stream_query()` path relied on (operation_schemas() comes
back empty). The container serves the A2A protocol over the Agent Engine HTTP
passthrough, so this proxy fetches the agent's card and sends messages with the
a2a-sdk client (the same path `agents-cli run --mode a2a` uses). This works for
both A2A and plain ADK 1.1.0 deployments (the container serves A2A either way).

Run:
  pip install -r requirements.txt
  export AGENT_ENGINE_RESOURCE_NAME="projects/.../locations/.../reasoningEngines/..."
  export AGENT_DIRECTORY="app"   # your agent's app directory (agents-cli-manifest.yaml)
  python main.py                 # -> http://localhost:8080
"""

import json
import os
import re
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    Message,
    Part,
    Role,
    SendMessageConfiguration,
    SendMessageRequest,
    TaskArtifactUpdateEvent,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from google.protobuf.json_format import MessageToDict, ParseDict

RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/390086943548/locations/us-east1/reasoningEngines/3431373480149385216",
)
# The agent's app directory (matches agent_directory in agents-cli-manifest.yaml).
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
# Location is embedded in the resource name: projects/<p>/locations/<loc>/reasoningEngines/<id>.
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

# A2A endpoint for an Agent Runtime deployment, via the Agent Engine HTTP
# passthrough. The card lives at the well-known path under this base.
A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

# The agent tags its A2UI data parts with this mime type.
_A2UI_MIME = "application/json+a2ui"

# Role value for user role in A2A protobuf enum
_USER_ROLE = getattr(Role, "ROLE_USER", getattr(Role, "user", 1))

# One set of ADC credentials, refreshed per request (access tokens expire ~1h).
_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    # Always return JSON so the browser never receives a plain-text 500 page
    # (which shows up in the chat as "Unexpected token 'I', "Internal S"... is
    # not valid JSON"). Any server-side failure now surfaces as a readable
    # message in the chat bubble instead.
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


# Reuse ONE A2A context per user so the agent remembers the conversation.
_contexts: dict[str, str] = {}
# Cache the agent card after the first fetch.
_card: AgentCard | None = None


def _parse_card(card_json: dict) -> AgentCard:
    try:
        return ParseDict(card_json, AgentCard(), ignore_unknown_fields=True)
    except Exception:
        if hasattr(AgentCard, "model_validate"):
            return AgentCard.model_validate(card_json)
        return AgentCard(**card_json)


async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        card_json = resp.json()
        card = _parse_card(card_json)
        if getattr(card, "supported_interfaces", None):
            for iface in card.supported_interfaces:
                iface.url = A2A_BASE
        _card = card
    return _card


def _extract_parts(parts: list) -> list[dict]:
    """Turn A2A response parts into structured parts for the chat UI.

    Text parts pass through as {"kind": "text"}. Embedded <a2ui-json> or ```json ``` blocks containing
    A2UI payloads are extracted into {"kind": "a2ui", "data": ...} and stripped from
    the text string to prevent raw JSON from cluttering the text bubble.
    """
    out: list[dict] = []
    for p in parts:
        root = getattr(p, "root", p)
        text = getattr(root, "text", None)
        if isinstance(text, str) and text:
            # Find embedded <a2ui-json> and ```json ``` blocks
            blocks = re.findall(r"<a2ui-json>\s*([\s\S]*?)\s*</a2ui-json>", text)
            blocks.extend(re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text))

            clean_text = re.sub(r"<a2ui-json>\s*[\s\S]*?\s*</a2ui-json>", "", text)
            clean_text = re.sub(r"```(?:json)?\s*[\s\S]*?\s*```", "", clean_text).strip()

            for block in blocks:
                if "beginRendering" in block or "surfaceUpdate" in block:
                    try:
                        parsed = json.loads(block)
                        if isinstance(parsed, list):
                            for item in parsed:
                                if isinstance(item, dict) and ("beginRendering" in item or "surfaceUpdate" in item):
                                    out.append({"kind": "a2ui", "data": item})
                        elif isinstance(parsed, dict) and ("beginRendering" in parsed or "surfaceUpdate" in parsed):
                            out.append({"kind": "a2ui", "data": parsed})
                    except Exception:
                        pass

            if clean_text:
                out.append({"kind": "text", "text": clean_text})

        if hasattr(root, "HasField") and root.HasField("data"):
            d = MessageToDict(root.data)
            a2ui_payload = d.get("data") if isinstance(d, dict) and "data" in d else d
            mime = d.get("metadata", {}).get("mimeType") if isinstance(d, dict) else None

            if isinstance(a2ui_payload, dict) and ("beginRendering" in a2ui_payload or "surfaceUpdate" in a2ui_payload or mime == _A2UI_MIME):
                out.append({"kind": "a2ui", "data": a2ui_payload})
            elif isinstance(d, dict) and "text" in d and isinstance(d["text"], str):
                t = d["text"]
                clean_t = re.sub(r"<a2ui-json>\s*[\s\S]*?\s*</a2ui-json>", "", t)
                clean_t = re.sub(r"```(?:json)?\s*[\s\S]*?\s*```", "", clean_t).strip()
                if clean_t:
                    out.append({"kind": "text", "text": clean_t})
        elif getattr(root, "url", None):
            out.append({"kind": "text", "text": root.url})
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
        card = await _get_card(client)
        factory = ClientFactory(
            ClientConfig(
                httpx_client=client,
            )
        )
        a2a_client = factory.create(card)

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=_USER_ROLE,
            parts=[Part(text=message)],
            context_id=_contexts.get(user_id),
        )

        send_req = SendMessageRequest(
            message=msg,
            configuration=SendMessageConfiguration(),
        )

        last_task = None
        got_artifact_update = False
        async for event in a2a_client.send_message(send_req):
            if isinstance(event, tuple):
                task, update = event
                if task is not None:
                    last_task = task
                    if getattr(task, "context_id", None):
                        _contexts[user_id] = task.context_id
                if isinstance(update, TaskArtifactUpdateEvent):
                    got_artifact_update = True
                    parts.extend(_extract_parts(update.artifact.parts))
            elif hasattr(event, "HasField"):
                if event.HasField("task") and getattr(event.task, "context_id", None):
                    _contexts[user_id] = event.task.context_id
                if event.HasField("artifact_update") and getattr(event.artifact_update, "artifact", None):
                    got_artifact_update = True
                    parts.extend(_extract_parts(event.artifact_update.artifact.parts))
                elif event.HasField("message") and getattr(event.message, "parts", None):
                    got_artifact_update = True
                    parts.extend(_extract_parts(event.message.parts))

        # Fallback if no streaming artifact updates were extracted: check event.task.artifacts
        if not got_artifact_update and last_task is not None:
            for artifact in getattr(last_task, "artifacts", None) or []:
                parts.extend(_extract_parts(artifact.parts))

    if not parts:
        # The turn produced no text or UI (e.g. the agent only ran tools, or a
        # tool stalled). Be honest rather than silent.
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


# Serve the chat UI (keep this mount last so /chat wins).
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

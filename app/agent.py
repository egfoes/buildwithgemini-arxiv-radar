# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.agent_engine_sandbox_code_executor import (
    AgentEngineSandboxCodeExecutor,
)
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from .a2ui_utils import a2ui_callback
from .tools import (
    check_peer_review,
    get_papers_from_firestore,
    get_theme_history,
    get_trend_history_from_firestore,
    manage_active_projects,
    manage_watchlist,
    record_feedback,
    save_paper_to_firestore,
    save_trend_summary_to_firestore,
    search_arxiv,
    update_theme_history,
    upload_media_to_gcs,
)

MODEL = "gemini-3.6-flash"
PROJECT_ID = "qwiklabs-gcp-04-b94b6676e7e5"
LOCATION = "us-east1"
AGENT_ENGINE_ID = "3431373480149385216"

# Resource name for Agent Engine sandbox code execution
AGENT_ENGINE_RESOURCE_NAME = f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{AGENT_ENGINE_ID}"

# Initialize A2UI Schema Manager with Basic Catalog v0.8
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

DOMAIN_DIRECTIVES = """
DUAL FORMATTING INSTRUCTION FOR OPTIMAL USER EXPERIENCE:
1. ALWAYS present a complete, clean, human-readable Markdown summary first with clear headings, bold badges, bullet points, arXiv links, and project relevance callouts.
2. At the end of your response, append the corresponding A2UI JSON array block so A2UI-capable renderers can draw cards while plain-text and streaming clients display clean Markdown.

SANDBOX PYTHON CODE EXECUTION & PUBLIC MEDIA STORAGE:
- You have Agent Platform Python code execution enabled via `AgentEngineSandboxCodeExecutor`.
- You can safely run Python code blocks in a secure Agent Engine sandbox to execute mathematical calculations, paper frequency statistics, data processing, or generate charts and plot images.
- When sandbox code generates visual assets (e.g. plot images, figures, charts), call `upload_media_to_gcs` to publish the asset to your public Cloud Storage bucket (`arxiv-radar-media-qwiklabs-gcp-04-b94b6676e7e5`) and set the A2UI Image url to that exact https link.

FIRESTORE DATABASE BACKEND:
- You have full Firestore database tools enabled for paper records (`arxiv_papers` collection) AND research trend summaries (`research_trends` collection).
- `save_paper_to_firestore`: Call when saving/starring curated paper records.
- `get_papers_from_firestore`: Call to read saved paper records from Firestore.
- `get_trend_history_from_firestore`: Call when drafting Section 3 (Comparative Macro-Theme Analysis) to retrieve past weekly theme summaries and historical trend baselines stored in Firestore.
- `save_trend_summary_to_firestore`: Call after drafting Section 3 to persist this week's theme summary and comparative macro analysis into Firestore.

MEMORY BANK & LONG-TERM RESEARCH TRENDS:
- You also have cross-session long-term memory enabled via Vertex AI Memory Bank (`PreloadMemoryTool`).
- Combine preloaded memories and `get_trend_history_from_firestore` when analyzing long-term research trajectories.

TOKEN EFFICIENCY DIRECTIVE:
- NEVER attempt to fetch or read full paper PDFs.
- Work STRICTLY with paper metadata (title, authors, arXiv ID, date, venue) and abstracts.

ACTIVE PROJECT MATCHING:
- Call `manage_active_projects(action='list')` during report generation to check the user's active projects.
- Whenever a paper abstract matches an active project's focus area, include a 🎯 **Project Relevance Callout** under that paper's summary explaining how the paper's findings/methodology apply to the project.

WEEKLY DIGEST STRUCTURE:
When asked to generate a weekly report or research digest, structure your response into EXACTLY 3 SECTIONS:
1. Highlighted Papers (with peer-review badges 🟢/⚪, arXiv links, abstract summaries, and 🎯 Project Relevance Callouts).
2. Weekly Theme Summary (synthesis of 2-3 overarching themes/patterns).
3. Comparative Macro-Theme Analysis (comparing against Firestore history via `get_trend_history_from_firestore` and persisting via `save_trend_summary_to_firestore`).
"""

SYSTEM_INSTRUCTION = schema_manager.generate_system_prompt(
    role_description="You are ArXiv Radar, an expert research assistant specializing in Responsible AI, AI Evaluations, and Interpretability.",
    workflow_description="Analyze research queries, arXiv paper search results, watchlists, active projects, and Cloud Firestore records. Provide clean Markdown reports along with structured A2UI JSON cards.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket, such as https://storage.googleapis.com/arxiv-radar-media-qwiklabs-gcp-04-b94b6676e7e5/...). "
        "Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis."
    ),
    include_schema=True,
    include_examples=True,
) + "\n\n" + DOMAIN_DIRECTIVES


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE callback: sends session events to Vertex AI Memory Bank after each turn."""
    await callback_context.add_session_to_memory()
    return None


code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=AGENT_ENGINE_RESOURCE_NAME
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=SYSTEM_INSTRUCTION,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        search_arxiv,
        check_peer_review,
        save_paper_to_firestore,
        get_papers_from_firestore,
        save_trend_summary_to_firestore,
        get_trend_history_from_firestore,
        upload_media_to_gcs,
        manage_watchlist,
        manage_active_projects,
        record_feedback,
        get_theme_history,
        update_theme_history,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)

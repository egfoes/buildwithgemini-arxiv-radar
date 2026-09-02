# Project Brief: ArXiv Radar

## Executive Summary
**ArXiv Radar** is an AI agent designed to discover, analyze, and synthesize AI safety, model sycophancy, and interpretability research papers from arXiv. It equips researchers with paper summaries, cross-paper topic analysis, and rich visual A2UI cards for paper metadata.

---

## Core Capabilities & Tools

1. **arXiv Paper Discovery & Retrieval**:
   - Searches arXiv papers by ID (e.g. `2609.00067`) or topic keywords.
   - Summarizes paper hypotheses, methodologies, findings, and project relevance.

2. **A2UI Rich Interface Generation**:
   - Uses `A2uiSchemaManager` (v0.8 Basic Catalog) to emit visual card layouts (title, badges, key findings, and project relevance) alongside text responses.

3. **Code Execution & Artifact Media Storage**:
   - Includes `AgentEngineSandboxCodeExecutor` for running analytical scripts in a sandboxed runtime.
   - Integrates Google Cloud Storage (`gs://arxiv-radar-media-qwiklabs-gcp-04-b94b6676e7e5`) for hosting generated media assets.

---

## Deployment & Infrastructure

- **GCP Project**: `qwiklabs-gcp-04-b94b6676e7e5`
- **Region**: `us-east1`
- **Deployed Agent Resource**: `projects/390086943548/locations/us-east1/reasoningEngines/3431373480149385216`
- **Service Account**: `service-390086943548@gcp-sa-aiplatform-re.iam.gserviceaccount.com` (Granted `roles/datastore.user` and `roles/storage.objectAdmin`)
- **Frontend App**: FastAPI A2A proxy + HTML/JS chat frontend running on `http://localhost:8080`

---

## Future UI Enhancements

The following UI improvements have been identified for future iterations of the **ArXiv Radar** frontend:

### 1. 🌓 Dark / Light Mode Theme Toggle
- Add a dark mode toggle button in the header bar.
- Switch between Light (`#f8fafc`) and Dark (`#0f172a` / `#1e293b`) color themes for low-light research environments.

### 2. ⚡ Animated "Scanning arXiv..." Thinking Indicator
- Replace the simple loading placeholder with a radar pulse / dot-wave animation (*"Radar scanning arXiv papers..."*).
- Provides immediate visual feedback while multi-step tool calls execute in the background.

### 3. 🏷️ Research Topic Category Filter Bar
- Add quick filter chips above the prompt bar (e.g., `All Topics`, `Model Sycophancy`, `Interpretability`, `Safety Benchmarks`).
- Enables one-click filtering of research queries by category.

### 4. 📋 Copy-to-Clipboard & BibTeX Export Actions
- Add a subtle action bar to agent response bubbles and A2UI paper cards:
  - **Copy Summary**: Copies formatted Markdown summary to the clipboard.
  - **Export BibTeX**: Generates a standard BibTeX citation snippet for the paper.

### 5. 🗂️ Collapsible Session History Sidebar
- Add a left sidebar tracking the user's paper search history during a session.
- Allows researchers to jump back to previously generated paper cards and summaries without re-running queries.

### 6. 🔗 Direct Paper Action Links in A2UI Cards
- Add direct action buttons inside paper cards:
  - `[ 📄 Open PDF ]`: Opens the paper's PDF on `arxiv.org`.
  - `[ 🔬 View Code Repo ]`: Direct link to GitHub repositories mentioned in the paper.

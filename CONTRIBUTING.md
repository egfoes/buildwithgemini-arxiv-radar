# Contributing to ArXiv Radar 📡

Thank you for your interest in contributing to **ArXiv Radar**!

## Development Workflow

1. **Fork & Clone**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/buildwithgemini-arxiv-radar.git
   cd buildwithgemini-arxiv-radar
   ```

2. **Setup Dependencies**:
   ```bash
   uv sync
   ```

3. **Run Tests**:
   ```bash
   uv run pytest
   ```

4. **Lint & Code Style**:
   ```bash
   uv run ruff check .
   ```

## Adding Tools or Custom Watchlists

- **Custom Watchlists**: Modify [`app/watchlist.json`](app/watchlist.json) to add research keywords or arXiv topic categories.
- **Active Projects**: Update [`app/active_projects.json`](app/active_projects.json) to add active project focus areas for paper relevance matching.
- **Agent Tools**: Add python tool definitions in [`app/tools.py`](app/tools.py) and bind them to `root_agent` in [`app/agent.py`](app/agent.py).

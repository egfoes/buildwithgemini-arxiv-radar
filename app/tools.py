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

import datetime
import json
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from google.cloud import firestore, storage

# CRITICAL: Hardcode GCP Project ID string and GCS bucket string to ensure Agent Platform safety
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-04-b94b6676e7e5"
FIRESTORE_COLLECTION = "arxiv_papers"
TRENDS_COLLECTION = "research_trends"
GCS_BUCKET_NAME = "arxiv-radar-media-qwiklabs-gcp-04-b94b6676e7e5"

WATCHLIST_FILE = os.path.join(os.path.dirname(__file__), "watchlist.json")
FEEDBACK_FILE = os.path.join(os.path.dirname(__file__), "feedback_history.json")
THEME_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "theme_history.json")
PROJECTS_FILE = os.path.join(os.path.dirname(__file__), "active_projects.json")


def _get_firestore_db():
    """Initializes Firestore client with hardcoded project ID."""
    return firestore.Client(project=FIRESTORE_PROJECT_ID)


def _init_storage():
    """Ensures storage files exist with default values."""
    if not os.path.exists(WATCHLIST_FILE):
        default_watchlist = {
            "keywords": [
                "responsible ai",
                "ai evaluation",
                "interpretability",
                "mechanistic interpretability",
                "AI red teaming",
                "RLHF safety",
                "AI sycophancy",
                "LLM sycophancy",
                "AI alignment",
                "LLM alignment",
                "agentic alignment",
                "agentic evaluations",
            ],
            "authors": [],
            "topics": ["cs.AI", "cs.LG", "cs.CL"],
        }
        with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(default_watchlist, f, indent=2)

    if not os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

    if not os.path.exists(THEME_HISTORY_FILE):
        default_theme = {
            "last_updated": None,
            "comparative_summary": "No historical theme baseline established yet. This is the initial run.",
        }
        with open(THEME_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(default_theme, f, indent=2)

    if not os.path.exists(PROJECTS_FILE):
        default_projects = [
            {
                "name": "EvalBench-Sycophancy",
                "description": "Building an evaluation framework for testing user-pressure answer flipping and sycophancy in LLMs.",
                "key_topics": ["sycophancy", "evaluations", "RLHF", "user pressure"],
            }
        ]
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_projects, f, indent=2)


_init_storage()


def upload_media_to_gcs(file_path: str, destination_name: str = "") -> Dict[str, Any]:
    """Uploads a local image, plot chart, or media asset file to the project's public Cloud Storage bucket.

    Use this tool when code executed in the Python sandbox generates chart images or diagrams to obtain a public HTTPS URL that can be embedded directly in markdown reports or web pages.

    Args:
        file_path: Local path to the file (e.g. 'sycophancy_growth_chart.png').
        destination_name: Optional custom filename in bucket (defaults to basename of file_path).

    Returns:
        Dictionary with public_url and GCS URI.
    """
    try:
        if not os.path.exists(file_path):
            return {"error": f"File '{file_path}' does not exist locally."}

        client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = client.bucket(GCS_BUCKET_NAME)
        dest = destination_name or os.path.basename(file_path)
        blob = bucket.blob(dest)
        blob.upload_from_filename(file_path)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{dest}"
        return {
            "status": "success",
            "filename": dest,
            "public_url": public_url,
            "gcs_uri": f"gs://{GCS_BUCKET_NAME}/{dest}",
        }
    except Exception as e:
        return {"error": f"Failed to upload media to GCS: {str(e)}"}


def save_paper_to_firestore(
    arxiv_id: str,
    title: str,
    authors: List[str],
    topic: str = "General AI",
    peer_review_status: str = "⚪ Unreviewed Preprint",
    summary: str = "",
    relevance_score: float = 0.9,
    pdf_url: str = "",
) -> Dict[str, Any]:
    """Saves or updates a paper document in the Firestore 'arxiv_papers' database collection.

    Args:
        arxiv_id: The unique arXiv ID (e.g., '2608.31079v1').
        title: Paper title.
        authors: List of author names.
        topic: Primary topic category (e.g., 'LLM Sycophancy', 'Mechanistic Interpretability').
        peer_review_status: Status badge ('🟢 Peer-Reviewed' or '⚪ Unreviewed Preprint').
        summary: Concise summary of the paper's key findings.
        relevance_score: Calculated relevance score (0.0 to 1.0).
        pdf_url: Direct URL to paper PDF.

    Returns:
        Status message and saved document metadata.
    """
    try:
        db = _get_firestore_db()
        doc_data = {
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": authors,
            "topic": topic,
            "peer_review_status": peer_review_status,
            "summary": summary,
            "relevance_score": relevance_score,
            "pdf_url": pdf_url or f"https://arxiv.org/pdf/{arxiv_id}.pdf",
            "date_added": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        db.collection(FIRESTORE_COLLECTION).document(arxiv_id).set(doc_data)
        return {"status": "success", "message": f"Paper '{arxiv_id}' saved to Firestore collection '{FIRESTORE_COLLECTION}'.", "data": doc_data}
    except Exception as e:
        return {"error": f"Failed to save paper to Firestore: {str(e)}"}


def get_papers_from_firestore(topic: str = "", limit: int = 5) -> List[Dict[str, Any]]:
    """Reads saved arXiv paper records from the Firestore 'arxiv_papers' database collection.

    Args:
        topic: Optional topic filter (e.g. 'LLM Sycophancy' or 'Mechanistic Interpretability').
        limit: Maximum number of papers to retrieve (default: 5).

    Returns:
        List of paper document dictionaries stored in Firestore.
    """
    try:
        db = _get_firestore_db()
        query_ref = db.collection(FIRESTORE_COLLECTION)

        if topic:
            docs = query_ref.where("topic", "==", topic).limit(limit).stream()
        else:
            docs = query_ref.limit(limit).stream()

        results = []
        for doc in docs:
            data = doc.to_dict()
            results.append(data)

        if not results and topic:
            docs = query_ref.limit(limit).stream()
            results = [doc.to_dict() for doc in docs]

        return results
    except Exception as e:
        return [{"error": f"Failed to read papers from Firestore: {str(e)}"}]


def save_trend_summary_to_firestore(
    weekly_theme_summary: str,
    comparative_macro_summary: str,
    key_topics: List[str] = [],
) -> Dict[str, Any]:
    """Saves weekly theme summaries and long-term research trend analyses to the Firestore 'research_trends' collection.

    Args:
        weekly_theme_summary: The Section 2 summary of this week's paper themes and technical patterns.
        comparative_macro_summary: The Section 3 comparative analysis comparing this week's themes against historical baselines.
        key_topics: List of primary topics/keywords covered in this report.

    Returns:
        Status message and saved trend record details.
    """
    try:
        db = _get_firestore_db()
        now = datetime.datetime.now(datetime.timezone.utc)
        digest_id = f"digest_{now.strftime('%Y_w%U_%H%M')}"
        doc_data = {
            "digest_id": digest_id,
            "timestamp": now.isoformat(),
            "weekly_theme_summary": weekly_theme_summary,
            "comparative_macro_summary": comparative_macro_summary,
            "key_topics": key_topics,
        }
        db.collection(TRENDS_COLLECTION).document(digest_id).set(doc_data)

        # Also update local fallback JSON for compatibility
        update_theme_history(comparative_macro_summary)

        return {"status": "success", "message": f"Trend summary saved to Firestore collection '{TRENDS_COLLECTION}' as '{digest_id}'.", "data": doc_data}
    except Exception as e:
        return {"error": f"Failed to save trend summary to Firestore: {str(e)}"}


def get_trend_history_from_firestore(limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieves past weekly theme summaries and long-term research trends from the Firestore 'research_trends' collection.

    Use this tool when drafting Section 3 (Comparative Macro-Theme Analysis) to compare current weekly findings against historical trend baselines stored in Firestore.

    Args:
        limit: Maximum number of past trend records to retrieve (default: 5).

    Returns:
        List of historical research trend records ordered by timestamp descending.
    """
    try:
        db = _get_firestore_db()
        docs = db.collection(TRENDS_COLLECTION).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream()

        results = []
        for doc in docs:
            results.append(doc.to_dict())

        if not results:
            # Fallback to local file if empty
            local_hist = get_theme_history()
            return [{
                "digest_id": "digest_local_fallback",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "weekly_theme_summary": "Local baseline theme history.",
                "comparative_macro_summary": local_hist.get("comparative_summary", ""),
                "key_topics": [],
            }]

        return results
    except Exception as e:
        local_hist = get_theme_history()
        return [{
            "error": f"Firestore read failed ({str(e)}), using local fallback.",
            "comparative_macro_summary": local_hist.get("comparative_summary", "")
        }]


def search_arxiv(query: str, max_results: int = 5, start: int = 0) -> List[Dict[str, Any]]:
    """Queries the public arXiv API by keyword, author, or category and returns paper metadata and abstracts.

    Token Efficiency Notice: Returns ONLY metadata (title, authors, published date, arXiv ID, doi, journal_ref)
    and the paper abstract. Full PDF content is NOT fetched or read.

    Args:
        query: Search string (e.g. 'all:interpretability' or 'au:Anthropic' or 'cat:cs.AI AND all:"responsible ai"').
        max_results: Number of results to return (default: 5, max: 20).
        start: Pagination start index (default: 0).

    Returns:
        List of dictionaries containing paper metadata and abstracts.
    """
    base_url = "http://export.arxiv.org/api/query?"
    params = {
        "search_query": query,
        "start": start,
        "max_results": min(max_results, 20),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = base_url + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers={"User-Agent": "ArXivRadar/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        papers = []
        for entry in root.findall("atom:entry", ns):
            arxiv_id_elem = entry.find("atom:id", ns)
            raw_id = arxiv_id_elem.text.strip() if arxiv_id_elem is not None else ""
            arxiv_id = raw_id.split("/abs/")[-1]

            title_elem = entry.find("atom:title", ns)
            title = title_elem.text.strip().replace("\n", " ") if title_elem is not None else "Untitled"

            summary_elem = entry.find("atom:summary", ns)
            abstract = summary_elem.text.strip().replace("\n", " ") if summary_elem is not None else ""

            published_elem = entry.find("atom:published", ns)
            published = published_elem.text.strip()[:10] if published_elem is not None else ""

            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.find("atom:name", ns)
                if name is not None and name.text:
                    authors.append(name.text.strip())

            journal_ref_elem = entry.find("arxiv:journal_ref", ns)
            journal_ref = journal_ref_elem.text.strip() if journal_ref_elem is not None else ""

            doi_elem = entry.find("arxiv:doi", ns)
            doi = doi_elem.text.strip() if doi_elem is not None else ""

            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

            papers.append({
                "arxiv_id": arxiv_id,
                "title": title,
                "authors": authors,
                "published": published,
                "journal_ref": journal_ref,
                "doi": doi,
                "pdf_url": pdf_url,
                "abstract": abstract[:1500],  # Truncate abstract for token safety
            })
        return papers
    except Exception as e:
        return [{"error": f"Failed to fetch arXiv papers: {str(e)}"}]


def check_peer_review(arxiv_id: str, journal_ref: str = "", doi: str = "") -> Dict[str, Any]:
    """Verifies whether an arXiv paper has been peer-reviewed and published in a reputable conference or journal.

    Args:
        arxiv_id: The arXiv ID (e.g. '2401.12345').
        journal_ref: Optional journal reference string from arXiv metadata.
        doi: Optional DOI string from arXiv metadata.

    Returns:
        Dictionary with peer-review status badge, venue name, and review confidence level.
    """
    if journal_ref or doi:
        return {
            "arxiv_id": arxiv_id,
            "badge": "🟢 Peer-Reviewed",
            "venue": journal_ref or f"DOI: {doi}",
            "verified": True,
            "source": "arXiv Metadata",
        }

    clean_id = arxiv_id.split("v")[0]
    ss_url = f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{clean_id}?fields=venue,publicationVenue,externalIds,publicationTypes"
    req = urllib.request.Request(ss_url, headers={"User-Agent": "ArXivRadar/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            venue = data.get("venue") or ""
            pub_venue = data.get("publicationVenue") or {}
            venue_name = pub_venue.get("name") if isinstance(pub_venue, dict) else venue

            if venue_name and venue_name.lower() != "arxiv":
                return {
                    "arxiv_id": arxiv_id,
                    "badge": "🟢 Peer-Reviewed",
                    "venue": venue_name,
                    "verified": True,
                    "source": "Semantic Scholar API",
                }
    except Exception:
        pass

    return {
        "arxiv_id": arxiv_id,
        "badge": "⚪ Unreviewed Preprint",
        "venue": "ArXiv Preprint (Not yet published in a peer-reviewed venue)",
        "verified": False,
        "source": "ArXiv",
    }


def manage_watchlist(action: str, category: str = "keywords", item: str = "") -> Dict[str, Any]:
    """Manages the user's research watchlist (keywords, authors, or topics).

    Args:
        action: 'list', 'add', or 'remove'.
        category: 'keywords', 'authors', or 'topics'.
        item: The keyword or author name to add or remove.

    Returns:
        Current state of the watchlist or action summary.
    """
    _init_storage()
    with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
        watchlist = json.load(f)

    if action == "list":
        return watchlist

    if category not in watchlist:
        return {"error": f"Invalid category '{category}'. Choose from: keywords, authors, topics."}

    if action == "add" and item:
        if item not in watchlist[category]:
            watchlist[category].append(item)
            with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(watchlist, f, indent=2)
        return {"status": "success", "message": f"Added '{item}' to {category}.", "watchlist": watchlist}

    if action == "remove" and item:
        if item in watchlist[category]:
            watchlist[category].remove(item)
            with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(watchlist, f, indent=2)
        return {"status": "success", "message": f"Removed '{item}' from {category}.", "watchlist": watchlist}

    return {"error": "Invalid action. Use 'list', 'add', or 'remove'."}


def manage_active_projects(action: str, name: str = "", description: str = "", key_topics: str = "") -> Dict[str, Any]:
    """Manages user's active projects portfolio for paper relevance matching.

    Args:
        action: 'list', 'add', or 'remove'.
        name: Name of the project (e.g. 'EvalBench-Sycophancy').
        description: Brief summary of what the project does or aims to solve.
        key_topics: Comma-separated topics or tags relevant to the project.

    Returns:
        List of active projects or action status.
    """
    _init_storage()
    with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
        projects = json.load(f)

    if action == "list":
        return {"active_projects": projects}

    if action == "add" and name:
        topics_list = [t.strip() for t in key_topics.split(",")] if key_topics else []
        new_proj = {
            "name": name,
            "description": description,
            "key_topics": topics_list,
        }
        projects.append(new_proj)
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump(projects, f, indent=2)
        return {"status": "success", "message": f"Added project '{name}'.", "projects": projects}

    if action == "remove" and name:
        projects = [p for p in projects if p.get("name").lower() != name.lower()]
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump(projects, f, indent=2)
        return {"status": "success", "message": f"Removed project '{name}'.", "projects": projects}

    return {"error": "Invalid action. Use 'list', 'add', or 'remove'."}


def record_feedback(arxiv_id: str, rating: str, comment: str = "") -> Dict[str, Any]:
    """Records user feedback (relevant, irrelevant, starred) on a recommended paper.

    Args:
        arxiv_id: The arXiv ID of the paper.
        rating: Rating value ('relevant', 'irrelevant', 'starred').
        comment: Optional user comment explaining why it was or was not useful.

    Returns:
        Status message confirming feedback recorded.
    """
    _init_storage()
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        history = json.load(f)

    record = {
        "arxiv_id": arxiv_id,
        "rating": rating,
        "comment": comment,
    }
    history.append(record)

    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    return {"status": "success", "message": f"Recorded '{rating}' feedback for paper {arxiv_id}."}


def get_theme_history() -> Dict[str, Any]:
    """Retrieves the latest rolling comparative theme summary from previous runs.

    Returns:
        Dictionary containing the previous comparative theme summary.
    """
    _init_storage()
    with open(THEME_HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def update_theme_history(new_comparative_summary: str) -> Dict[str, Any]:
    """Updates the rolling comparative theme summary for future weekly runs.

    Args:
        new_comparative_summary: The new comparative theme analysis text to persist.

    Returns:
        Status message confirming the update.
    """
    _init_storage()
    data = {
        "last_updated": "2026-09-02",
        "comparative_summary": new_comparative_summary,
    }
    with open(THEME_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return {"status": "success", "message": "Updated rolling comparative theme history."}

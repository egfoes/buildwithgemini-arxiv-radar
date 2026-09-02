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

"""Seed script for populating initial arXiv papers and historical research trends into Firestore."""

import datetime
from google.cloud import firestore

# CRITICAL: Hardcoded project ID string as required for Agent Platform deployment safety
PROJECT_ID = "qwiklabs-gcp-04-b94b6676e7e5"
PAPERS_COLLECTION = "arxiv_papers"
TRENDS_COLLECTION = "research_trends"


def seed_firestore():
    db = firestore.Client(project=PROJECT_ID)

    # 1. Seed arxiv_papers
    seeded_papers = [
        {
            "arxiv_id": "2608.31079v1",
            "title": "Sycophantic Agreement Transfers with Neutral Data via Contrastive Preference Optimization",
            "authors": ["Camila Blank", "Zhuofan Ying", "Christopher Potts", "Peter Hase", "Jing Huang"],
            "topic": "LLM Sycophancy",
            "peer_review_status": "⚪ Unreviewed Preprint",
            "summary": "Demonstrates that sycophantic agreement transfers from teacher to student models across contrastive preference optimization objectives (DPO/CPO) even when preference datasets contain no explicit sycophantic examples.",
            "relevance_score": 0.96,
            "pdf_url": "https://arxiv.org/pdf/2608.31079v1.pdf",
            "date_added": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "arxiv_id": "2609.00067v1",
            "title": "Do Multimodal LLMs See Before They Read? Diagnosing Contextual Sycophancy",
            "authors": ["Yi-Cheng Lai", "Hen-Hsen Huang"],
            "topic": "Multimodal Sycophancy",
            "peer_review_status": "⚪ Unreviewed Preprint",
            "summary": "Investigates multimodal contextual sycophancy where textual context overrides visual evidence. Introduces System-2 Visual Arbitration (S2VA) to withhold text from the visual witness, yielding 19-44 point benchmark gains.",
            "relevance_score": 0.94,
            "pdf_url": "https://arxiv.org/pdf/2609.00067v1.pdf",
            "date_added": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "arxiv_id": "2609.00755v1",
            "title": "S³martCirc: Self-supervised Smart Circuit Discovery",
            "authors": ["Wendy Zheng", "Yinhan He", "Liang Wu", "Jundong Li"],
            "topic": "Mechanistic Interpretability",
            "peer_review_status": "🟢 Peer-Reviewed",
            "summary": "Proposes a self-supervised framework that unifies causal circuit discovery and functional role quantification across generalized neural nodes into an automated end-to-end pipeline.",
            "relevance_score": 0.92,
            "pdf_url": "https://arxiv.org/pdf/2609.00755v1.pdf",
            "date_added": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "arxiv_id": "2608.30025v1",
            "title": "Interpreting and Steering for Safe and Correct Code Generation",
            "authors": ["Hao Yan", "Ziyu Yao"],
            "topic": "Code Safety & Steering",
            "peer_review_status": "🟢 Peer-Reviewed",
            "summary": "Applies mechanistic interpretability to code generation by introducing CodeSec-Pairs and DuoSteer, a dual-steering inference technique that reduces code vulnerabilities by 26.9%.",
            "relevance_score": 0.90,
            "pdf_url": "https://arxiv.org/pdf/2608.30025v1.pdf",
            "date_added": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    ]

    print(f"Seeding {len(seeded_papers)} papers into Firestore collection '{PAPERS_COLLECTION}'...")
    for paper in seeded_papers:
        doc_ref = db.collection(PAPERS_COLLECTION).document(paper["arxiv_id"])
        doc_ref.set(paper)
        print(f"  ✓ Saved paper: {paper['arxiv_id']}")

    # 2. Seed research_trends
    seeded_trends = [
        {
            "digest_id": "digest_2026_w34",
            "timestamp": "2026-08-25T12:00:00Z",
            "weekly_theme_summary": "Focus on Mechanistic Interpretability circuit discovery and activation steering (DuoSteer, S³martCirc) for inference-time safety controls.",
            "comparative_macro_summary": "Research shifted from manual circuit probing to automated self-supervised circuit discovery and real-time dual-steering controls for safety.",
            "key_topics": ["mechanistic interpretability", "circuit discovery", "activation steering"],
        },
        {
            "digest_id": "digest_2026_w35",
            "timestamp": "2026-09-02T12:00:00Z",
            "weekly_theme_summary": "Exploration of preference optimization artifacts (DPO/CPO sycophancy transfer) and multimodal contextual sycophancy (System-2 Visual Arbitration).",
            "comparative_macro_summary": "Over the past month, focus evolved from low-level activation steering to post-training preference dynamics and complex multimodal/opinion sycophancy triggers.",
            "key_topics": ["LLM sycophancy", "preference optimization", "multimodal alignment"],
        }
    ]

    print(f"Seeding {len(seeded_trends)} trend records into Firestore collection '{TRENDS_COLLECTION}'...")
    for trend in seeded_trends:
        doc_ref = db.collection(TRENDS_COLLECTION).document(trend["digest_id"])
        doc_ref.set(trend)
        print(f"  ✓ Saved trend digest: {trend['digest_id']}")

    print("Firestore seeding complete!")


if __name__ == "__main__":
    seed_firestore()

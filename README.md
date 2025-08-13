# Agentic Video QA — Preschool Day (Transcript-First Demo)

## Product Objective
- Purpose: Help parents understand their child’s day in preschool — what happened, how the child engaged, mood/affect, participation, and notable events — through concise, trustworthy answers to natural questions.

## High-Level Architecture
- Multi-agent system: LangGraph-based orchestration that routes questions, selects relevant footage/transcripts, and composes grounded answers.
- Modalities: Classroom CCTV video (multimodal) and text transcripts. Videos live outside the repo (GCS or equivalent).
- Adapters: LLM for reasoning and composition; catalog for video metadata; optional evidence snipping for clips.
- Data inputs: Day-level transcripts and optional per-child transcripts generated from videos.
- Outputs: Concise answer with optional follow-up guidance and evidence clip pointers.
- Full graph details: See ARCHITECTURE.md for routing and follow-ups.

## This Branch (Demo Scope)
- MVP behavior: Transcript-first demo operating solely on event transcripts pre-generated from classroom videos.
- Supported questions: High-level “what happened today?”, engagement/attention, mood/affect, participation/behaviors, distress incidents.
- How it works: Identify child → pick relevant videos → refine question → build transcript context → answer from transcripts → compose final answer → offer follow-ups.
- Important: If transcripts cannot answer, this branch returns a polite fallback and does not invoke video analyzers.

## Not In This Branch (Broader Tool)
- Multimodal analysis: When enabled, the system routes to video analyzers if transcripts are insufficient, using Gemini to reason directly over CCTV (via GCS URIs).
- Broader question set: Visual details, fine-grained activity recognition, body language and interaction cues, richer evidence generation.
- Path when enabled: child_identifier → video_picker → question_refiner → transcript_router → transcript_answerer → if insufficient, route to video_analyzers → composer → followup_advisor.

## How To Run
- Prerequisites:
  - Python 3.10+.
  - Google Cloud Vertex AI access (the demo still uses the LLM for reasoning). Set `GOOGLE_CLOUD_PROJECT` and authenticate.
- Setup:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  export GOOGLE_CLOUD_PROJECT="<your-project-id>"
  gcloud auth application-default login
  ```
- Run the demo (interactive; Ayaan preselected; transcripts-only):
  ```bash
  python main.py --demo
  ```
- Run non-interactively (still transcript-first):
  ```bash
  python main.py --question "What activities did Ayaan do today?" --transcripts-only
  ```

## Repo Walkthrough
- config/: Video catalog and metadata (e.g., `videos.yaml` for prep and analyzers).
- data/
  - transcripts/: Day transcripts (committed).
  - child_transcripts/: Per-child transcripts (committed).
  - snippedvideos/: Local evidence clips (ignored by git).
- prompts/: Prompt templates used by the demo.
- prompts_archive/: Prompts for full multimodal paths and variants (not used by this demo).
- src/
  - graph.py: LangGraph wiring and flow.
  - nodes/: Modular nodes (child_identifier, video_picker, question_refiner, transcript_builder, transcript_answerer, composer, followup_advisor, evidence_snipper).
  - adapters/: LLM (Vertex AI Gemini) and catalog integrations.
  - state.py: Shared state and message schema.
  - cli_runner.py: Interactive CLI and follow-ups.
- scripts/: Optional prep, e.g., `generate_child_from_image` (internal use).
- tests/: Targeted tests for flow and adapters.
- main.py: Simple CLI entry forwarding to `src/cli_runner.py`.

## How The Demo Answers
- Inputs: User question + transcripts (day-level JSON/text; optional per-child JSON).
- Routing: The graph refines the question, selects relevant videos, and prepares transcript evidence.
- Answering: The LLM composes a concise answer from transcripts; if insufficient, returns a polite fallback (no video analysis in this branch).
- Follow-ups: Ask new questions, re-route via transcript path, or generate local evidence clip stubs.

## Notes & Hygiene
- No videos in git. Transcripts under `data/transcripts/**` and `data/child_transcripts/**` are committed; videos/clips are ignored.
- Catalog access: If using broader tooling, ensure `config/videos.yaml` GCS URIs are reachable by your ADC identity.
- Region: Default Vertex AI region is `us-central1` (config in `LLMAdapter`).

## Troubleshooting
- Auth/Project: Verify `GOOGLE_CLOUD_PROJECT` and run `gcloud auth application-default login`.
- Permissions: Ensure ADC has viewer permissions on any referenced GCS URIs (for prep/broader toolpaths).
- Generic answers: Tune prompts in `prompts/` or adjust temperatures in adapters.

## Roadmap (Beyond Demo)
- Enable transcript router + video analyzers for multimodal fallback.
- Expand question taxonomy and routing rules.
- Deterministic evidence clip selection and caching.
- Enhance parent advisor and coach integrations.

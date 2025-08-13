# Architecture — Agentic Video QA (Full Graph)

This document outlines the end-to-end architecture and execution paths of the full system, including the transcript router, video analyzers, and follow-up flows. It complements the transcript-first demo described in the README.

## Overview
- Objective: Answer parent questions about a child’s preschool day with concise, grounded responses.
- Orchestration: LangGraph-based pipeline with modular nodes that transform state and route between text and multimodal analysis.
- Modalities: Transcript (text/JSON) and video (CCTV via GCS URIs). Video analysis is used when transcripts are insufficient (not enabled in the demo branch by default).

## Core Components
- Graph and State
  - `src/graph.py`: Constructs and runs the graph.
  - `src/state.py`: `QAState` holds fields like `user_question`, `child_info`, `target_videos`, `target_question`, `transcript_path`, `child_transcript_data`, `per_video_answers`, `final_answer`, `conversation_history`, `transcripts_only`, and flags like `transcript_can_answer`.

- Nodes (selected)
  - `child_identifier`: Ensures the graph knows which child the question targets.
  - `video_picker`: Narrows to relevant videos for the day.
  - `question_refiner`: Clarifies/normalizes the question for downstream nodes.
  - `transcript_router`: Chooses between transcript path and video analyzers based on question type and availability/quality of transcripts.
  - `transcript_builder`: Resolves transcript resources (day-level JSON/text, optional per-child JSON).
  - `transcript_answerer`: Answers from transcripts; computes `transcript_can_answer` and assembles evidence.
  - `video_analyzers`: Runs multimodal reasoning on selected videos when transcripts are insufficient.
  - `composer`: Produces the final, parent-facing answer using gathered evidence.
  - `followup_advisor`: Interprets follow-up questions and suggests the best route (transcripts, evidence, or advisor response).
  - `evidence_snipper`: Produces local clip pointers for evidence when requested.

- Adapters
  - `src/adapters/llm_adapter.py`: Vertex AI Gemini (text and video) calls (`call_text`, `call_json`, `call_video`, `call_video_with_image`).
  - `src/adapters/catalog_adapter.py`: Resolves video metadata and URIs.

- Prompts
  - `prompts/transcript_answerer.txt`, `prompts/child_transcript_answerer.txt`.
  - `prompts/video_analyzer.txt` (for multimodal path).
  - Additional templates in `prompts/` and references in `prompts_archive/`.

## Full Graph Flow

ASCII path (simplified):

```
User Q
  |
  v
child_identifier --(needs child info)--> END (ask user, then resume)
      | (has child info)
      v
video_picker -> question_refiner -> transcript_router
                                  /                \
                                 v                  v
                      transcript_builder       video_analyzers
                                 |                  |
                        transcript_answerer         |
                             |                      |
      (can answer) --------- v                      |
                     composer <---------------------/
                         |
                followup_advisor
                         |
                        END
```

Notes
- `transcript_router` decides whether to prioritize transcripts or escalate to video analyzers. In demo mode, routing is forced to transcripts-only and analyzers are skipped.
- `transcript_answerer` sets `transcript_can_answer` (with confidence). If false and not in transcripts-only mode, the flow proceeds to `video_analyzers`.
- `composer` synthesizes the final answer using `per_video_answers` and context.

## Decision Points
- Child identification
  - If the child is unknown, the system asks for clarification before proceeding.
- Transcript router
  - Factors: question intent (e.g., participation vs. subtle visual cues), transcript presence/quality, explicit demo flag `transcripts_only`.
- Transcript answerer
  - Computes can/cannot answer; if cannot and not transcripts-only, escalate to video analyzers.
- Video analyzers
  - For each `video_id`, build a prompt from `prompts/video_analyzer.txt` + `target_question` (+ optional `child_info`).
  - Use `CatalogAdapter` to resolve GCS URIs and `LLMAdapter.call_video` to obtain grounded responses.

## Follow-Up Flow
After the first answer, the CLI supports follow-up questions and routes them with `followup_advisor`.

ASCII loop:

```
composer -> (show answer) -> followup_advisor
                                  |
               +------------------+-------------------+
               |                  |                   |
               v                  v                   v
        transcript_child     transcript_day        evidence
               |                  |                   |
       run_main_flow         run_main_flow     evidence_snipper
           (new Q)               (new Q)             (clips)
               \____________________|__________________/
                                     |
                                     v
                               show result
                                     |
                                    END or new follow-up
```

Routes
- `transcript_child` / `transcript_day`: Re-enters the main flow with the follow-up question, optionally preserving `child_info` when known.
- `evidence`: Runs `evidence_snipper` and returns clip pointers (saved locally under `data/snippedvideos/`, pathing may be implementation-specific).
- Otherwise: Returns an advisor response (e.g., parent coaching) without re-running analysis.

## Data and Storage
- Transcripts (committed): `data/transcripts/**` (day-level), `data/child_transcripts/**` (per-child).
- Videos (not committed): Reside in GCS or external storage; URIs referenced via `config/videos.yaml` and `CatalogAdapter`.
- Evidence clips (local): Saved under `data/snippedvideos/` and ignored by git.

## Execution Context
- Entry points
  - `main.py`: CLI entry; demo mode (`--demo`) forces transcripts-only and preselects the child (Ayaan in the demo).
  - `src/cli_runner.py`: Runs the main flow and manages interactive follow-ups.
- Key flags
  - `--demo`: Preselects child, prints greeting, sets transcripts-only.
  - `--transcripts-only`: Uses only transcripts; if insufficient, returns a polite fallback instead of video analysis.

## Extensibility
- Add nodes: Implement `src/nodes/<name>.py`, register edges in `src/graph.py`.
- Tune behavior: Update prompts in `prompts/` to adjust routing/answer style without code changes.
- Model/region: Configure in `LLMAdapter` (default `gemini-2.5-flash`, region `us-central1`).
- MIME types: For non-MP4, add `mime_type` to catalog entries and update adapter calls as needed.

## References
- Graph wiring: `src/graph.py`
- Nodes: `src/nodes/`
- Adapters: `src/adapters/`
- Prompts: `prompts/` and `prompts_archive/`


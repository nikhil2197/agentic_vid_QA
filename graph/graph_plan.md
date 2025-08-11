# Graph Execution Plan – Agentic Path Only

## Purpose
This plan defines the sequential and parallel execution flow for the agentic system, which answers user questions about stored videos in GCS.

## Execution Order
1. **video_picker** – Selects up to 5 most relevant video IDs from catalog based on user_question.
2. **question_refiner** – Rewrites the user_question into a specific, verifiable query for a single video.
3. **video_analyzers** – Runs in parallel for each target_video. Uses video multimodal input to answer the refined question.
4. **composer** – Synthesizes all per-video answers into a single, clear, parent-friendly final_answer.
5. **followup_advisor** – Handles follow-up questions or requests for actionables based on final_answer and ongoing conversation.

## Parallelism
- `video_analyzers` node fans out to one sub-call per target_video.
- Results are fanned in and aggregated before composer.

## Termination
- Graph ends after `followup_advisor` produces `followup_response` or, if no follow-up, after `composer` outputs final_answer.

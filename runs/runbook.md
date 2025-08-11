# Manual Runbook – Agentic Path QA

## Purpose
To manually verify the agentic system can answer a question from a parent about stored videos.

## Steps
1. Confirm `config/videos.yaml` exists and lists the 4 GCS videos with valid URIs.
2. Pick a test question from a parent and set as `user_question`.
3. Run **video_picker**:
   - Expect ≤5 video IDs in `target_videos`.
4. Run **question_refiner**:
   - Expect `target_question` to be one sentence, specific and verifiable.
5. For each video in `target_videos`:
   - Run **video_analyzers** with the video’s URI and `target_question`.
   - Expect a short paragraph answer or “Not enough evidence in this video.”
6. Run **composer**:
   - Expect `final_answer` as a single, coherent paragraph.
7. (Optional) Provide a follow-up message from the parent and run **followup_advisor**:
   - Expect a conversational, actionable response in `followup_response`.

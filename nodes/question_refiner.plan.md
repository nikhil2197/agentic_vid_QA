# Node Plan – question_refiner

## Inputs
- `user_question` (string) – Original question from parent.

## Process
- Load prompt: `prompts/question_refiner.txt`.
- Insert the `user_question` into the prompt.
- Send to Gemini 2.5 Flash.
- Expect exactly one sentence, focused on a single video’s content, containing actors, activity, and time range if implied.
- Strip extra whitespace.

## Output
- `target_question` (string) – Refined question for per-video analysis.

## Failure Behavior
- If no clear refinement is produced, fall back to the original `user_question`.

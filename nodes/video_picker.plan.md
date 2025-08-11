# Node Plan – video_picker

## Inputs
- `user_question` (string) – Original question from parent.
- Video catalog (`config/videos.yaml`) – List of available videos with IDs, URIs, labels, durations, and day.

## Process
- Load prompt: `prompts/video_picker.txt`.
- Insert the `user_question` and the catalog (IDs + labels + day + duration) into the prompt.
- Send to Gemini 2.5 Flash with strict instruction to return only valid JSON: `{"videos": ["vid_1", "vid_3", ...]}`.
- Parse and validate the JSON output.
- Select at most 5 IDs.

## Output
- `target_videos` (list of strings) – IDs of selected videos.

## Failure Behavior
- If no valid IDs returned, run on all 5 videos.

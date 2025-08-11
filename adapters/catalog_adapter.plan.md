# Adapter Plan – Catalog Adapter

## Source
- config/videos.yaml

## Fields
- video_id
- gcs_uri
- session-type
- start-time
- end-time
- act-description

## Process
- Load the YAML into memory at startup.
- Provide lookup methods:
  - get_uri(video_id) → gcs_uri
  - get_session_type(video_id) → session_type

## Validation
- Ensure no duplicate video_ids.
- Ensure all gcs_uris are valid gs:// paths.

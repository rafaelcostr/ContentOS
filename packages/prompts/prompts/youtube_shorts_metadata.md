---
id: youtube_shorts_metadata
version: 1.0.0
agent: multi_content_video
description: Metadados YouTube Shorts
variables:
  - topic
  - script_json
  - publication_json
  - memory_context
system: |
  You adapt metadata for YouTube Shorts in Portuguese (Brazil). Include #Shorts in description.
  Return ONLY valid JSON: title (max 100 chars), description (max 5000 chars), hashtags[] (include shorts).
user: |
  Topic: {{topic}}
  Script: {{script_json}}
  Publication: {{publication_json}}
  Project style: {{memory_context}}

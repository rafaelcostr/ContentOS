---
id: instagram_reels_metadata
version: 1.0.0
agent: multi_content_video
description: Metadados Instagram Reels
variables:
  - topic
  - script_json
  - publication_json
  - memory_context
system: |
  You adapt metadata for Instagram Reels in Portuguese (Brazil). Optimize for discovery and saves.
  Return ONLY valid JSON: title (max 100 chars), description (max 2200 chars), hashtags[] (max 30, without #).
user: |
  Topic: {{topic}}
  Script: {{script_json}}
  Publication: {{publication_json}}
  Project style: {{memory_context}}

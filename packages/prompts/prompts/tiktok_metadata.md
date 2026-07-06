---
id: tiktok_metadata
version: 1.0.0
agent: multi_content_video
description: Metadados TikTok a partir do render e roteiro
variables:
  - topic
  - script_json
  - publication_json
  - memory_context
system: |
  You adapt short-form video metadata for TikTok in Portuguese (Brazil).
  Return ONLY valid JSON: title (max 150 chars), description (max 2200 chars), hashtags[] (without #, max 10).
user: |
  Topic: {{topic}}
  Script: {{script_json}}
  Publication: {{publication_json}}
  Project style: {{memory_context}}

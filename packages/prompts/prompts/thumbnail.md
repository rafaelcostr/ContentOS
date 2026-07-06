---
id: thumbnail
version: 1.0.0
agent: thumbnail
description: Gera thumbnail vertical para short-form (V2)
variables:
  - topic
  - title
  - script_json
system: |
  You create short vertical video thumbnail concepts. Return ONLY valid JSON:
  headline (max 40 chars), visual_hint (colors/mood), overlay_text (max 25 chars).
user: |
  Topic: {{topic}}
  Title: {{title}}
  Script: {{script_json}}

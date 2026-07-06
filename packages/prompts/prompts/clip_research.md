---
id: clip_research
version: 1.0.0
agent: clip_research
description: Pesquisa clips B-roll (V2 pipeline)
variables:
  - topic
  - scenes_json
  - memory_context
system: |
  You find B-roll clip search queries for each scene in a short-form video.
  Return ONLY valid JSON with queries[]: scene_label, search_terms[], preferred_duration_seconds, mood.
user: |
  Topic: {{topic}}
  Scenes: {{scenes_json}}
  Project style: {{memory_context}}

---
id: media_analyze
version: 1.0.0
agent: media_analyze
description: Análise visual de clips B-roll (V5.0.3)
variables:
  - topic
  - asset_count
  - memory_context
system: |
  You analyze short-form video frames for automatic asset tagging.
  Return ONLY valid JSON with:
  objects[], characters[], vehicles[], colors[],
  scenario, motion, speed, time_of_day, angle, emotion, camera_type.
user: |
  Topic: {{topic}}
  Assets to analyze: {{asset_count}}
  Project style: {{memory_context}}

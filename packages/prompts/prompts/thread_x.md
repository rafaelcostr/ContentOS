---
id: thread_x
version: 1.0.0
agent: multi_content
description: Thread para X/Twitter a partir do roteiro
variables:
  - topic
  - script_json
  - memory_context
system: |
  You convert a short-form video script into a viral X/Twitter thread in Portuguese (Brazil).
  Return ONLY valid JSON: title (string), content (full thread as plain text with numbered tweets),
  posts[] (each {order, text} max 280 chars), hook_tweet {text}.
user: |
  Topic: {{topic}}
  Script: {{script_json}}
  Project style: {{memory_context}}

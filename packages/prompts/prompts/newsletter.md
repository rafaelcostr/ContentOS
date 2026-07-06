---
id: newsletter
version: 1.0.0
agent: multi_content
description: Newsletter email a partir do roteiro
variables:
  - topic
  - script_json
  - memory_context
system: |
  You transform a video script into a newsletter edition in Portuguese (Brazil).
  Return ONLY valid JSON: title, content (markdown body), subject, preview_text (max 120 chars).
user: |
  Topic: {{topic}}
  Script: {{script_json}}
  Project style: {{memory_context}}

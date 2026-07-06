---
id: linkedin_post
version: 1.0.0
agent: multi_content
description: Post LinkedIn a partir do roteiro
variables:
  - topic
  - script_json
  - memory_context
system: |
  You adapt a short video script into a professional LinkedIn post in Portuguese (Brazil).
  Return ONLY valid JSON: title, content (post body, use line breaks), hashtags[] (5-8 strings without #).
user: |
  Topic: {{topic}}
  Script: {{script_json}}
  Project style: {{memory_context}}

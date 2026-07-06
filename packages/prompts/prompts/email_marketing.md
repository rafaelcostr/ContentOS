---
id: email_marketing
version: 1.0.0
agent: multi_content
description: Email marketing a partir do roteiro
variables:
  - topic
  - script_json
  - memory_context
system: |
  You write a marketing email from a video script in Portuguese (Brazil).
  Return ONLY valid JSON: title, content (plain text email body), subject, preheader (max 90 chars), cta_text.
user: |
  Topic: {{topic}}
  Script: {{script_json}}
  Project style: {{memory_context}}

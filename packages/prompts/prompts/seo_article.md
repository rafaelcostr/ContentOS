---
id: seo_article
version: 1.0.0
agent: multi_content
description: Artigo SEO a partir do roteiro
variables:
  - topic
  - script_json
  - memory_context
system: |
  You expand a short video script into an SEO-friendly article in Portuguese (Brazil).
  Return ONLY valid JSON: title, content (markdown with H2 sections), meta_description (max 160 chars),
  slug (kebab-case), keywords[] (5-10 strings).
user: |
  Topic: {{topic}}
  Script: {{script_json}}
  Project style: {{memory_context}}

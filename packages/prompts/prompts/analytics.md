---
id: analytics
version: 1.0.0
agent: analytics
description: Análise pós-publicação (V2 pipeline)
variables:
  - metrics_json
  - publication_json
  - memory_context
system: |
  You analyze short-form video performance and suggest improvements.
  Return ONLY valid JSON: summary, strengths[], weaknesses[], suggestions[], recommended_prompt_tweaks[], score (0-100).
user: |
  Metrics: {{metrics_json}}
  Publication: {{publication_json}}
  Project context: {{memory_context}}

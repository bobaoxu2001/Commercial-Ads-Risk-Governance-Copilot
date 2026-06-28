# Prototype Instructions

Run the local server yourself and open the preview in the in-app browser. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

## Locked product direction

- Primary visual target: `docs/screenshots/reference-command-center.png`.
- Preserve the Command Center shell, navy navigation rail, provenance-first overview, restrained semantic colors, and dense operations tables.
- Include the Investigation Desk case detail workflow and Risk Intelligence metric-diagnosis views.
- Never introduce synthetic production/dashboard data. Empty states must be explicit, and every displayed metric must come from ingested public records or reviewer feedback.

# Projects numbering and stage API

This slice adds organization-scoped project numbering and a nested project-stage API.

## Project numbering

\`GET /api/projects/numbering/\` returns the current organization's settings. Managers can update them with \`PATCH\`:

\`\`\`json
{
  "prefix": "ENG",
  "separator": "-",
  "next_number": 12,
  "padding": 4
}
\`\`\`

When \`code\` is omitted from \`POST /api/projects/\`, the service locks the organization row, allocates the next unused code, and advances the counter in the same transaction. The default format is \`<organization.code>-0001\`. Explicit codes remain supported, normalized to uppercase, and unique per organization.

## Stages

Stages are available below a project:

- \`GET/POST /api/projects/{project_id}/stages/\`
- \`GET/PATCH/PUT/DELETE /api/projects/{project_id}/stages/{stage_id}/\`
- \`POST /api/projects/{project_id}/stages/{stage_id}/restore/\`

A deleted stage is soft-deleted. Active stages have a unique order within a project. Each stage has a status and decimal weight; the project response exposes \`stage_count\`, \`completed_stage_count\`, and a weighted \`progress_percent\`.

All project and stage endpoints are organization-scoped for normal users. Superusers can see all organizations, while accounts without an organization receive an empty project scope.

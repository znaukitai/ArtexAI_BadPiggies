# MCP Servers Specification

Tools across `academic_schedule` and `campus_services` return a JSON envelope:

```json
{
  "ok": true,
  "data": {},
  "error": null,
  "source": "live | demo",
  "elapsed_ms": 12
}
```

## 1. `academic_schedule` (`mcp_servers/academic_schedule.py`)

| Tool Name | Arguments | Description |
| --- | --- | --- |
| `get_today` | `{}` | Current date and weekday in `Asia/Almaty` (`+05:00`). |
| `add_deadline` | `course`, `title`, `due_date`, `priority` | Validates ISO 8601 date and adds a deadline. |
| `list_deadlines` | `days_ahead`, `course` | Returns sorted deadlines with `days_left` and `urgency`. |
| `plan_week` | `start_date` | Generates a 7-day study schedule. |
| `parse_syllabus_text` | `text` | Extracts candidate deadlines from raw syllabus text. |

## 2. `campus_services` (`mcp_servers/campus_services.py`)

| Tool Name | Arguments | Description |
| --- | --- | --- |
| `github_repo_status` | `repo_url` | GitHub REST API lookup (`/repos/{owner}/{repo}` & `/commits`). |
| `github_assignment_check` | `repo_url`, `expected_files` | Verifies existence of required files via GitHub Contents API. |
| `find_campus_place` | `query` | Searches AITU campus blocks (`C1.1`, `C1.2`, `C1.3`) and facilities. |

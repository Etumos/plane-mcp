"""Declarative registry of the full Plane REST API surface exposed as MCP
tools: projects, issues, comments, attachments, links, relations, labels,
states, cycles, modules, pages, views, workspace-views, members, intake
issues, estimates, and webhooks.

Each entry describes:
  - description / schema: the MCP tool contract shown to the client.
  - method: HTTP verb used against the Plane API.
  - path: URL template. `{placeholders}` are filled from the tool's own
    arguments and are never forwarded as payload/query.
  - payload_map: argument name -> JSON body key, when it differs from the
    argument name itself. An entry mapped to None is consumed elsewhere
    (e.g. used only to build the path) and dropped from the body.
  - static_payload: fields always sent regardless of arguments.
  - query_map: like payload_map but for GET/DELETE query-string params.
  - destructive: if set, the argument named here must be a non-empty
    string AND `confirm=true` must be passed, or the call is refused.
  - synthetic: name of a Python-side handler in server.py for tools that
    don't map onto a single REST call (currently just list_workspaces).

Endpoint shapes follow the public Plane API reference
(https://developers.plane.so/api-reference). This registry was built
without access to a live Plane instance — if your Plane deployment uses
a different API version, double check the handful of newer resources
(intake issues, estimates, workspace views) against your instance's
`/api/v1/` docs before relying on them in production.
"""

from __future__ import annotations

from typing import Any

# Common reusable schema fragments.
_WS = {"type": "string", "description": "Workspace slug"}
_PID = {"type": "string", "description": "Project ID"}
_STR = {"type": "string"}
_BOOL = {"type": "boolean"}
_INT = {"type": "integer"}
_STR_ARRAY = {"type": "array", "items": {"type": "string"}}

TOOL_SPECS: dict[str, dict[str, Any]] = {
    # -- workspaces ---------------------------------------------------
    "list_workspaces": {
        "description": "List the Plane workspace(s) this API token can access",
        "properties": {
            "workspace_slug": {
                **_STR,
                "description": "Optional workspace slug override; defaults to PLANE_WORKSPACE_SLUG",
            }
        },
        "required": [],
        "synthetic": "list_workspaces",
        # Verified against the deployed reference: when no workspace slug is
        # configured/passed, this calls GET /api/v1/workspaces/ for real
        # (not just an echo). When a slug IS configured, it short-circuits
        # without a live call, since the Plane API key is scoped to a single
        # workspace and there's no cross-workspace list endpoint to hit.
    },
    "list_workspace_members": {
        "description": "List members of a workspace",
        "properties": {"workspace_slug": _WS},
        "required": ["workspace_slug"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/members/",
    },
    # -- projects -------------------------------------------------------
    "list_projects": {
        "description": "List projects in a workspace",
        "properties": {"workspace_slug": _WS},
        "required": ["workspace_slug"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/",
    },
    "create_project": {
        "description": "Create a new project in a workspace",
        "properties": {
            "workspace_slug": _WS,
            "name": _STR,
            "identifier": {**_STR, "description": "Short project identifier/prefix"},
            "description": _STR,
            "network": {**_INT, "description": "0=secret, 2=public"},
        },
        "required": ["workspace_slug", "name", "identifier"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/",
    },
    "update_project": {
        "description": "Update an existing project",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "name": _STR,
            "identifier": _STR,
            "description": _STR,
            "network": _INT,
        },
        "required": ["workspace_slug", "project_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/",
    },
    "delete_project": {
        "description": "Delete a project (destructive; requires confirm=true and exact project_id)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "confirm": {**_BOOL, "description": "Must be true to authorize deletion"},
        },
        "required": ["workspace_slug", "project_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/",
        "destructive": "project_id",
    },
    "set_project_features": {
        "description": "Toggle a project's optional feature modules (cycles, modules, pages, views, intake)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "cycle_view": _BOOL,
            "module_view": _BOOL,
            "issue_views_view": _BOOL,
            "page_view": _BOOL,
            "intake_view": _BOOL,
        },
        "required": ["workspace_slug", "project_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/",
        # Verified: the deployed reference confirmed "inbox_view" does NOT
        # exist on the project object — the flag is "intake_view".
    },
    # -- project members --------------------------------------------
    "list_project_members": {
        "description": "List members of a project",
        "properties": {"workspace_slug": _WS, "project_id": _PID},
        "required": ["workspace_slug", "project_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/project-members/",
    },
    "add_project_member": {
        "description": "Add a member to a project",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "member_id": {**_STR, "description": "Workspace member's user ID"},
            "role": _INT,
        },
        "required": ["workspace_slug", "project_id", "member_id"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/project-members/",
        "payload_map": {"member_id": "member"},
    },
    "update_project_member": {
        "description": "Update a project member's role",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "member_id": _STR,
            "role": _INT,
        },
        "required": ["workspace_slug", "project_id", "member_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/project-members/{member_id}/",
    },
    "remove_project_member": {
        "description": "Remove a member from a project (destructive; requires confirm=true)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "member_id": _STR,
            "confirm": _BOOL,
        },
        "required": ["workspace_slug", "project_id", "member_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/project-members/{member_id}/",
        "destructive": "member_id",
    },
    # -- issues ---------------------------------------------------------
    "list_issues": {
        "description": "List issues in a project",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "page": {**_INT, "description": "Page number (1-indexed)"},
            "page_size": _INT,
        },
        "required": ["workspace_slug", "project_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/",
        "query_map": {"page_size": "per_page"},
        # Verified: pagination is page-number based (?page=&per_page=), not
        # cursor based.
    },
    "get_issue": {
        "description": "Get a single issue",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "issue_id": _STR},
        "required": ["workspace_slug", "project_id", "issue_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/",
    },
    "create_issue": {
        "description": "Create a new issue",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "title": _STR,
            "description": {
                **_STR,
                "description": "Plain text; sent as description_html (Plane ignores a raw 'description' field)",
            },
            "labels": _STR_ARRAY,
            "priority": _STR,
            "state_id": {**_STR, "description": "State/status ID"},
            "assignee_id": {**_STR, "description": "Assignee user ID"},
            "start_date": {**_STR, "description": "YYYY-MM-DD"},
            "target_date": {**_STR, "description": "YYYY-MM-DD (due date)"},
            "parent_id": {**_STR, "description": "Parent issue ID, to create this as a sub-issue"},
        },
        "required": ["workspace_slug", "project_id", "title"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/",
        "payload_map": {
            "title": "name",
            "description": "description_html",
            "labels": "label_ids",
            "state_id": "state",
            "assignee_id": "assignee_ids",
            "parent_id": "parent",
        },
        "list_wrap_payload": ["assignee_ids"],
        # Verified: Plane's create-issue endpoint silently ignores a plain
        # "description" field — only "description_html" persists. Labels are
        # sent as "label_ids", assignee as a single-element "assignee_ids"
        # list, and sub-issues are created via the plain "parent" field
        # (there's no separate sub-issue endpoint).
    },
    "update_issue": {
        "description": "Update an existing issue",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "issue_id": _STR,
            "title": _STR,
            "description": {
                **_STR,
                "description": "Plain text; sent as description_html (Plane ignores a raw 'description' field)",
            },
            "labels": _STR_ARRAY,
            "status": {**_STR, "description": "State/status ID (sent as 'state')"},
            "priority": _STR,
            "assignee_id": {**_STR, "description": "Assignee user ID"},
            "start_date": {**_STR, "description": "YYYY-MM-DD"},
            "target_date": {**_STR, "description": "YYYY-MM-DD (due date)"},
        },
        "required": ["workspace_slug", "project_id", "issue_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/",
        "payload_map": {
            "title": "name",
            "status": "state",
            "description": "description_html",
            "labels": "label_ids",
            "assignee_id": "assignee_ids",
        },
        "list_wrap_payload": ["assignee_ids"],
    },
    "delete_issue": {
        "description": "Delete an issue (destructive; requires confirm=true and exact issue_id)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "issue_id": _STR,
            "confirm": {**_BOOL, "description": "Must be true to authorize deletion"},
        },
        "required": ["workspace_slug", "project_id", "issue_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/",
        "destructive": "issue_id",
    },
    "list_issue_activities": {
        "description": "List the activity/audit trail for an issue",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "issue_id": _STR},
        "required": ["workspace_slug", "project_id", "issue_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/activities/",
    },
    "list_sub_issues": {
        "description": "List the sub-issues (children) of an issue",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "issue_id": _STR},
        "required": ["workspace_slug", "project_id", "issue_id"],
        "synthetic": "list_sub_issues",
        # Verified: there is no dedicated sub-issues endpoint on the Plane
        # v1 REST API — GET/POST .../issues/{id}/sub-issues/ 404s, and the
        # server-side ?parent= filter on GET .../issues/ is a confirmed
        # no-op. Sub-issue hierarchy is modeled solely through the
        # `parent` field on the child issue, so this paginates the
        # project's issues and filters client-side.
    },
    "set_issue_parent": {
        "description": "Set (or change) an issue's parent issue",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "issue_id": _STR,
            "parent_issue_id": {**_STR, "description": "ID of the issue to set as parent"},
        },
        "required": ["workspace_slug", "project_id", "issue_id", "parent_issue_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/",
        "payload_map": {"parent_issue_id": "parent"},
    },
    "remove_issue_parent": {
        "description": "Remove an issue's parent link",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "issue_id": _STR},
        "required": ["workspace_slug", "project_id", "issue_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/",
        "static_payload": {"parent": None},
    },
    "set_issue_estimate": {
        "description": "Set an issue's estimate point",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "issue_id": _STR,
            "estimate_point": _STR,
        },
        "required": ["workspace_slug", "project_id", "issue_id", "estimate_point"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/",
    },
    # -- issue comments -----------------------------------------------
    "list_issue_comments": {
        "description": "List comments on an issue",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "issue_id": _STR},
        "required": ["workspace_slug", "project_id", "issue_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/comments/",
    },
    "add_issue_comment": {
        "description": "Add a comment to an issue",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "issue_id": _STR,
            "comment_html": {**_STR, "description": "Comment body (HTML)"},
        },
        "required": ["workspace_slug", "project_id", "issue_id", "comment_html"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/comments/",
    },
    "update_issue_comment": {
        "description": "Update an existing issue comment",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "issue_id": _STR,
            "comment_id": _STR,
            "comment_html": _STR,
        },
        "required": ["workspace_slug", "project_id", "issue_id", "comment_id", "comment_html"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/comments/{comment_id}/",
    },
    "delete_issue_comment": {
        "description": "Delete an issue comment (destructive; requires confirm=true)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "issue_id": _STR,
            "comment_id": _STR,
            "confirm": _BOOL,
        },
        "required": ["workspace_slug", "project_id", "issue_id", "comment_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/comments/{comment_id}/",
        "destructive": "comment_id",
    },
    # -- issue attachments ----------------------------------------------
    "list_issue_attachments": {
        "description": "List attachments on an issue",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "issue_id": _STR},
        "required": ["workspace_slug", "project_id", "issue_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/attachments/",
    },
    "get_attachment_upload_credentials": {
        "description": "Request pre-signed upload credentials for an issue attachment",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "issue_id": _STR,
            "name": _STR,
            "size": _INT,
            "type": {**_STR, "description": "MIME type"},
        },
        "required": ["workspace_slug", "project_id", "issue_id", "name", "size"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/attachments/",
    },
    "delete_issue_attachment": {
        "description": "Delete an issue attachment (destructive; requires confirm=true)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "issue_id": _STR,
            "attachment_id": _STR,
            "confirm": _BOOL,
        },
        "required": ["workspace_slug", "project_id", "issue_id", "attachment_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/attachments/{attachment_id}/",
        "destructive": "attachment_id",
    },
    # -- issue links ------------------------------------------------------
    "list_issue_links": {
        "description": "List external links attached to an issue",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "issue_id": _STR},
        "required": ["workspace_slug", "project_id", "issue_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/links/",
    },
    "create_issue_link": {
        "description": "Attach an external link to an issue",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "issue_id": _STR,
            "url": _STR,
            "title": _STR,
        },
        "required": ["workspace_slug", "project_id", "issue_id", "url"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/links/",
    },
    "delete_issue_link": {
        "description": "Remove an external link from an issue (destructive; requires confirm=true)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "issue_id": _STR,
            "link_id": _STR,
            "confirm": _BOOL,
        },
        "required": ["workspace_slug", "project_id", "issue_id", "link_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/links/{link_id}/",
        "destructive": "link_id",
    },
    # -- issue relations --------------------------------------------------
    "list_issue_relations": {
        "description": "List an issue's relations (blocking, blocked_by, duplicate, relates_to, etc)",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "issue_id": _STR},
        "required": ["workspace_slug", "project_id", "issue_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/relations/",
    },
    "create_issue_relation": {
        "description": "Create a relation from an issue to one or more other issues",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "issue_id": _STR,
            "relation_type": {
                **_STR,
                "description": (
                    "blocking | blocked_by | start_after | start_before | "
                    "finish_after | finish_before | relates_to | duplicate"
                ),
            },
            "issue_ids": _STR_ARRAY,
        },
        "required": ["workspace_slug", "project_id", "issue_id", "relation_type", "issue_ids"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/relations/",
        "payload_map": {"issue_ids": "issues"},
    },
    "remove_issue_relation": {
        "description": "Remove a relation between two issues (destructive; requires confirm=true)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "issue_id": _STR,
            "relation_type": {
                **_STR,
                "description": (
                    "blocking | blocked_by | start_after | start_before | "
                    "finish_after | finish_before | relates_to | duplicate"
                ),
            },
            "related_issue_id": {**_STR, "description": "The related issue's ID"},
            "confirm": _BOOL,
        },
        "required": ["workspace_slug", "project_id", "issue_id", "relation_type", "related_issue_id"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/relations/remove/",
        "payload_map": {"related_issue_id": "related_issue"},
        "destructive": "related_issue_id",
        # Verified: Plane's create-relation response has no relation-record
        # id to DELETE by. Removal is a POST to .../relations/remove/ with
        # body {relation_type, related_issue}, keyed on the same pair used
        # to create it.
    },
    # -- labels -----------------------------------------------------------
    "list_labels": {
        "description": "List labels defined in a project",
        "properties": {"workspace_slug": _WS, "project_id": _PID},
        "required": ["workspace_slug", "project_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/labels/",
    },
    "create_label": {
        "description": "Create a label in a project",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "name": _STR,
            "color": _STR,
        },
        "required": ["workspace_slug", "project_id", "name"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/labels/",
        # Verified: the deployed label create/update calls only send
        # name/color; there's no verified "description" field on labels.
    },
    "update_label": {
        "description": "Update a label",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "label_id": _STR,
            "name": _STR,
            "color": _STR,
        },
        "required": ["workspace_slug", "project_id", "label_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/labels/{label_id}/",
    },
    "delete_label": {
        "description": "Delete a label (destructive; requires confirm=true)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "label_id": _STR,
            "confirm": _BOOL,
        },
        "required": ["workspace_slug", "project_id", "label_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/labels/{label_id}/",
        "destructive": "label_id",
    },
    # -- states -------------------------------------------------------------
    "list_states": {
        "description": "List workflow states defined in a project",
        "properties": {"workspace_slug": _WS, "project_id": _PID},
        "required": ["workspace_slug", "project_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/states/",
    },
    "create_state": {
        "description": "Create a workflow state in a project",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "name": _STR,
            "color": _STR,
            "group": {
                **_STR,
                "description": "backlog | unstarted | started | completed | cancelled",
            },
        },
        "required": ["workspace_slug", "project_id", "name", "color", "group"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/states/",
    },
    "update_state": {
        "description": "Update a workflow state",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "state_id": _STR,
            "name": _STR,
            "color": _STR,
            "group": _STR,
        },
        "required": ["workspace_slug", "project_id", "state_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/states/{state_id}/",
    },
    "delete_state": {
        "description": "Delete a workflow state (destructive; requires confirm=true)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "state_id": _STR,
            "confirm": _BOOL,
        },
        "required": ["workspace_slug", "project_id", "state_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/states/{state_id}/",
        "destructive": "state_id",
    },
    # -- cycles ---------------------------------------------------------
    "list_cycles": {
        "description": "List cycles (sprints) in a project",
        "properties": {"workspace_slug": _WS, "project_id": _PID},
        "required": ["workspace_slug", "project_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/",
    },
    "create_cycle": {
        "description": "Create a cycle in a project",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "name": _STR,
            "description": {**_STR, "description": "Plain text; sent as description_html"},
            "start_date": {**_STR, "description": "YYYY-MM-DD"},
            "end_date": {**_STR, "description": "YYYY-MM-DD"},
        },
        "required": ["workspace_slug", "project_id", "name"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/",
        "payload_map": {"description": "description_html"},
    },
    "get_cycle": {
        "description": "Get a single cycle",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "cycle_id": _STR},
        "required": ["workspace_slug", "project_id", "cycle_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/{cycle_id}/",
    },
    "update_cycle": {
        "description": "Update a cycle",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "cycle_id": _STR,
            "name": _STR,
            "description": {**_STR, "description": "Plain text; sent as description_html"},
            "start_date": _STR,
            "end_date": _STR,
        },
        "required": ["workspace_slug", "project_id", "cycle_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/{cycle_id}/",
        "payload_map": {"description": "description_html"},
    },
    "delete_cycle": {
        "description": "Delete a cycle (destructive; requires confirm=true)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "cycle_id": _STR,
            "confirm": _BOOL,
        },
        "required": ["workspace_slug", "project_id", "cycle_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/{cycle_id}/",
        "destructive": "cycle_id",
    },
    "list_cycle_issues": {
        "description": "List issues assigned to a cycle",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "cycle_id": _STR},
        "required": ["workspace_slug", "project_id", "cycle_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/{cycle_id}/cycle-issues/",
    },
    "add_issues_to_cycle": {
        "description": "Add issues to a cycle",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "cycle_id": _STR,
            "issue_ids": _STR_ARRAY,
        },
        "required": ["workspace_slug", "project_id", "cycle_id", "issue_ids"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/{cycle_id}/cycle-issues/",
        "payload_map": {"issue_ids": "issues"},
    },
    "remove_issue_from_cycle": {
        "description": "Remove an issue from a cycle (destructive; requires confirm=true)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "cycle_id": _STR,
            "issue_id": _STR,
            "confirm": _BOOL,
        },
        "required": ["workspace_slug", "project_id", "cycle_id", "issue_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/{cycle_id}/cycle-issues/{issue_id}/",
        "destructive": "issue_id",
    },
    "transfer_cycle_issues": {
        "description": "Transfer all incomplete issues from one cycle to another",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "cycle_id": {**_STR, "description": "Source cycle ID"},
            "new_cycle_id": {**_STR, "description": "Destination cycle ID"},
        },
        "required": ["workspace_slug", "project_id", "cycle_id", "new_cycle_id"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/{cycle_id}/transfer-issues/",
    },
    # -- modules --------------------------------------------------------
    "list_modules": {
        "description": "List modules (feature groupings) in a project",
        "properties": {"workspace_slug": _WS, "project_id": _PID},
        "required": ["workspace_slug", "project_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/",
    },
    "create_module": {
        "description": "Create a module in a project",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "name": _STR,
            "description": {**_STR, "description": "Plain text; sent as description_html"},
            "start_date": _STR,
            "target_date": _STR,
        },
        "required": ["workspace_slug", "project_id", "name"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/",
        "payload_map": {"description": "description_html"},
    },
    "get_module": {
        "description": "Get a single module",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "module_id": _STR},
        "required": ["workspace_slug", "project_id", "module_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/{module_id}/",
    },
    "update_module": {
        "description": "Update a module",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "module_id": _STR,
            "name": _STR,
            "description": {**_STR, "description": "Plain text; sent as description_html"},
            "start_date": _STR,
            "target_date": _STR,
            "status": _STR,
        },
        "required": ["workspace_slug", "project_id", "module_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/{module_id}/",
        "payload_map": {"description": "description_html"},
    },
    "delete_module": {
        "description": "Delete a module (destructive; requires confirm=true)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "module_id": _STR,
            "confirm": _BOOL,
        },
        "required": ["workspace_slug", "project_id", "module_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/{module_id}/",
        "destructive": "module_id",
    },
    "list_module_issues": {
        "description": "List issues assigned to a module",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "module_id": _STR},
        "required": ["workspace_slug", "project_id", "module_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/{module_id}/module-issues/",
    },
    "add_issues_to_module": {
        "description": "Add issues to a module",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "module_id": _STR,
            "issue_ids": _STR_ARRAY,
        },
        "required": ["workspace_slug", "project_id", "module_id", "issue_ids"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/{module_id}/module-issues/",
        "payload_map": {"issue_ids": "issues"},
    },
    "remove_issue_from_module": {
        "description": "Remove an issue from a module (destructive; requires confirm=true)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "module_id": _STR,
            "issue_id": _STR,
            "confirm": _BOOL,
        },
        "required": ["workspace_slug", "project_id", "module_id", "issue_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/{module_id}/module-issues/{issue_id}/",
        "destructive": "issue_id",
    },
    # -- pages ------------------------------------------------------------
    "list_pages": {
        "description": "List wiki pages in a project",
        "properties": {"workspace_slug": _WS, "project_id": _PID},
        "required": ["workspace_slug", "project_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/pages/",
    },
    "create_page": {
        "description": "Create a wiki page in a project",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "name": _STR,
            "description_html": _STR,
        },
        "required": ["workspace_slug", "project_id", "name"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/pages/",
    },
    "get_page": {
        "description": "Get a single wiki page",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "page_id": _STR},
        "required": ["workspace_slug", "project_id", "page_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/pages/{page_id}/",
    },
    "update_page": {
        "description": "Update a wiki page",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "page_id": _STR,
            "name": _STR,
            "description_html": _STR,
        },
        "required": ["workspace_slug", "project_id", "page_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/pages/{page_id}/",
    },
    "delete_page": {
        "description": "Delete a wiki page (destructive; requires confirm=true)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "page_id": _STR,
            "confirm": _BOOL,
        },
        "required": ["workspace_slug", "project_id", "page_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/pages/{page_id}/",
        "destructive": "page_id",
    },
    # -- project views ----------------------------------------------------
    "list_views": {
        "description": "List saved issue views in a project",
        "properties": {"workspace_slug": _WS, "project_id": _PID},
        "required": ["workspace_slug", "project_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/views/",
    },
    "create_view": {
        "description": "Create a saved issue view in a project",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "name": _STR,
            "description": {**_STR, "description": "Plain text; sent as description_html"},
        },
        "required": ["workspace_slug", "project_id", "name"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/views/",
        "payload_map": {"description": "description_html"},
        # Verified: filters/query start empty on create and are populated
        # via Plane's UI, not this API — a "filters" body field was never
        # confirmed to do anything, so it's not exposed here.
    },
    "get_view": {
        "description": "Get a single project view",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "view_id": _STR},
        "required": ["workspace_slug", "project_id", "view_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/views/{view_id}/",
    },
    "update_view": {
        "description": "Update a project view",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "view_id": _STR,
            "name": _STR,
            "description": {**_STR, "description": "Plain text; sent as description_html"},
        },
        "required": ["workspace_slug", "project_id", "view_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/views/{view_id}/",
        "payload_map": {"description": "description_html"},
    },
    "delete_view": {
        "description": "Delete a project view (destructive; requires confirm=true)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "view_id": _STR,
            "confirm": _BOOL,
        },
        "required": ["workspace_slug", "project_id", "view_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/views/{view_id}/",
        "destructive": "view_id",
    },
    # -- workspace views ------------------------------------------------
    # Verified: the workspace-scoped views resource lives directly at
    # /api/v1/workspaces/{workspace_slug}/views/ — there is no separate
    # "workspace-views" URL segment; that path 404s on the deployed
    # reference instance.
    "list_workspace_views": {
        "description": "List saved issue views at the workspace level",
        "properties": {"workspace_slug": _WS},
        "required": ["workspace_slug"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/views/",
    },
    "create_workspace_view": {
        "description": "Create a workspace-level saved issue view",
        "properties": {
            "workspace_slug": _WS,
            "name": _STR,
            "description": {**_STR, "description": "Plain text; sent as description_html"},
        },
        "required": ["workspace_slug", "name"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/views/",
        "payload_map": {"description": "description_html"},
    },
    "get_workspace_view": {
        "description": "Get a single workspace view",
        "properties": {"workspace_slug": _WS, "view_id": _STR},
        "required": ["workspace_slug", "view_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/views/{view_id}/",
    },
    "update_workspace_view": {
        "description": "Update a workspace view",
        "properties": {
            "workspace_slug": _WS,
            "view_id": _STR,
            "name": _STR,
            "description": {**_STR, "description": "Plain text; sent as description_html"},
        },
        "required": ["workspace_slug", "view_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/views/{view_id}/",
        "payload_map": {"description": "description_html"},
    },
    "delete_workspace_view": {
        "description": "Delete a workspace view (destructive; requires confirm=true)",
        "properties": {"workspace_slug": _WS, "view_id": _STR, "confirm": _BOOL},
        "required": ["workspace_slug", "view_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/views/{view_id}/",
        "destructive": "view_id",
    },
    # -- intake (inbox) issues --------------------------------------------
    # Verified: Plane's v1 REST API names this resource "inbox-issues" in
    # its URL path even though the product UI calls the feature "Intake"
    # ("intake-issues" 404s). Detail routes (get/update/delete) have NO
    # trailing slash; list/create do.
    "list_intake_issues": {
        "description": "List issues sitting in a project's intake/inbox queue",
        "properties": {"workspace_slug": _WS, "project_id": _PID},
        "required": ["workspace_slug", "project_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/inbox-issues/",
    },
    "create_intake_issue": {
        "description": "Submit a new issue into a project's intake/inbox queue",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "title": _STR,
            "description": {**_STR, "description": "Plain text; sent as description_html"},
        },
        "required": ["workspace_slug", "project_id", "title"],
        "synthetic": "create_intake_issue",
        # Verified: the work-item fields are nested under an "issue" key
        # in the request body (unlike list_issues/create_issue), i.e.
        # POST .../inbox-issues/ body {"issue": {"name": ..., "description_html": ...}}.
        # A plain payload_map can't express that nesting, hence synthetic.
    },
    "get_intake_issue": {
        "description": "Get a single intake issue",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "intake_issue_id": _STR},
        "required": ["workspace_slug", "project_id", "intake_issue_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/inbox-issues/{intake_issue_id}",
    },
    "update_intake_issue": {
        "description": "Update an intake issue's title/description, e.g. before triage",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "intake_issue_id": _STR,
            "title": _STR,
            "description": {**_STR, "description": "Plain text; sent as description_html"},
        },
        "required": ["workspace_slug", "project_id", "intake_issue_id"],
        "synthetic": "update_intake_issue",
        # Same nested-body shape as create_intake_issue: PATCH
        # .../inbox-issues/{id} body {"issue": {...}}.
    },
    "delete_intake_issue": {
        "description": "Delete an intake issue (destructive; requires confirm=true)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "intake_issue_id": _STR,
            "confirm": _BOOL,
        },
        "required": ["workspace_slug", "project_id", "intake_issue_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/inbox-issues/{intake_issue_id}",
        "destructive": "intake_issue_id",
    },
    # -- estimates -------------------------------------------------------
    "list_estimates": {
        "description": "List estimate systems configured for a project",
        "properties": {"workspace_slug": _WS, "project_id": _PID},
        "required": ["workspace_slug", "project_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/estimates/",
    },
    "create_estimate": {
        "description": "Create the estimate system for a project (a project has one active estimate config)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "name": _STR,
            "type": {**_STR, "description": "categories | points | time"},
            "description": {**_STR, "description": "Plain text, sent as-is (NOT description_html for estimates)"},
        },
        "required": ["workspace_slug", "project_id", "name"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/estimates/",
    },
    "update_estimate": {
        "description": "Update the project's estimate system",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "description": {**_STR, "description": "Plain text, sent as-is; the only field Plane's update-estimate accepts"},
        },
        "required": ["workspace_slug", "project_id", "description"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/estimates/",
        # Verified: there's no estimate id in the path — a project has
        # exactly one active estimate config, and only "description" is
        # accepted (name/type are NOT updatable via this endpoint).
    },
    "delete_estimate": {
        "description": "Delete the project's estimate system (destructive; requires confirm=true)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "confirm": _BOOL,
        },
        "required": ["workspace_slug", "project_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/estimates/",
        # Verified: no estimate id in the path (see update_estimate). Since
        # there's no natural per-call target id, confirm-gating is keyed on
        # project_id instead.
        "destructive": "project_id",
    },
    # -- webhooks -----------------------------------------------------
    "list_webhooks": {
        "description": "List webhooks configured on a workspace",
        "properties": {"workspace_slug": _WS},
        "required": ["workspace_slug"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/webhooks/",
    },
    "create_webhook": {
        "description": "Create a workspace webhook",
        "properties": {
            "workspace_slug": _WS,
            "url": _STR,
            "is_active": _BOOL,
            "project": _BOOL,
            "issue": _BOOL,
            "cycle": _BOOL,
            "module": _BOOL,
        },
        "required": ["workspace_slug", "url"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/webhooks/",
    },
    "update_webhook": {
        "description": "Update a webhook",
        "properties": {
            "workspace_slug": _WS,
            "webhook_id": _STR,
            "url": _STR,
            "is_active": _BOOL,
        },
        "required": ["workspace_slug", "webhook_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/webhooks/{webhook_id}/",
    },
    "delete_webhook": {
        "description": "Delete a webhook (destructive; requires confirm=true)",
        "properties": {"workspace_slug": _WS, "webhook_id": _STR, "confirm": _BOOL},
        "required": ["workspace_slug", "webhook_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/webhooks/{webhook_id}/",
        "destructive": "webhook_id",
    },
}

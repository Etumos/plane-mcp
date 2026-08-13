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
            "inbox_view": _BOOL,
        },
        "required": ["workspace_slug", "project_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/",
    },
    # -- project members --------------------------------------------
    "list_project_members": {
        "description": "List members of a project",
        "properties": {"workspace_slug": _WS, "project_id": _PID},
        "required": ["workspace_slug", "project_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/members/",
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
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/members/",
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
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/members/{member_id}/",
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
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/members/{member_id}/",
        "destructive": "member_id",
    },
    # -- issues ---------------------------------------------------------
    "list_issues": {
        "description": "List issues in a project",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "cursor": _STR,
            "page_size": _INT,
        },
        "required": ["workspace_slug", "project_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/",
        "query_map": {"page_size": "per_page"},
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
            "description": _STR,
            "labels": _STR_ARRAY,
            "priority": _STR,
        },
        "required": ["workspace_slug", "project_id", "title"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/",
        "payload_map": {"title": "name"},
    },
    "update_issue": {
        "description": "Update an existing issue",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "issue_id": _STR,
            "title": _STR,
            "description": _STR,
            "labels": _STR_ARRAY,
            "status": _STR,
            "priority": _STR,
        },
        "required": ["workspace_slug", "project_id", "issue_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/",
        "payload_map": {"title": "name", "status": "state"},
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
        "description": "List the sub-issues of an issue",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "issue_id": _STR},
        "required": ["workspace_slug", "project_id", "issue_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/sub-issues/",
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
        "description": "List an issue's relations (blocks, blocked_by, duplicate, relates_to)",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "issue_id": _STR},
        "required": ["workspace_slug", "project_id", "issue_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/issue-relation/",
    },
    "create_issue_relation": {
        "description": "Create a relation from an issue to one or more other issues",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "issue_id": _STR,
            "relation_type": {
                **_STR,
                "description": "blocking | blocked_by | duplicate | relates_to",
            },
            "issue_ids": _STR_ARRAY,
        },
        "required": ["workspace_slug", "project_id", "issue_id", "relation_type", "issue_ids"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/issue-relation/",
        "payload_map": {"issue_ids": "issues"},
    },
    "remove_issue_relation": {
        "description": "Remove a relation between two issues (destructive; requires confirm=true)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "issue_id": _STR,
            "relation_id": _STR,
            "confirm": _BOOL,
        },
        "required": ["workspace_slug", "project_id", "issue_id", "relation_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/issue-relation/{relation_id}/",
        "destructive": "relation_id",
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
            "description": _STR,
        },
        "required": ["workspace_slug", "project_id", "name"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/labels/",
    },
    "update_label": {
        "description": "Update a label",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "label_id": _STR,
            "name": _STR,
            "color": _STR,
            "description": _STR,
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
            "description": _STR,
            "start_date": {**_STR, "description": "YYYY-MM-DD"},
            "end_date": {**_STR, "description": "YYYY-MM-DD"},
        },
        "required": ["workspace_slug", "project_id", "name"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/",
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
            "description": _STR,
            "start_date": _STR,
            "end_date": _STR,
        },
        "required": ["workspace_slug", "project_id", "cycle_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/{cycle_id}/",
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
            "description": _STR,
            "start_date": _STR,
            "target_date": _STR,
        },
        "required": ["workspace_slug", "project_id", "name"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/",
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
            "description": _STR,
            "start_date": _STR,
            "target_date": _STR,
            "status": _STR,
        },
        "required": ["workspace_slug", "project_id", "module_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/{module_id}/",
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
            "description": _STR,
            "filters": {"type": "object"},
        },
        "required": ["workspace_slug", "project_id", "name"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/views/",
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
            "description": _STR,
            "filters": {"type": "object"},
        },
        "required": ["workspace_slug", "project_id", "view_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/views/{view_id}/",
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
    "list_workspace_views": {
        "description": "List saved issue views at the workspace level",
        "properties": {"workspace_slug": _WS},
        "required": ["workspace_slug"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/workspace-views/",
    },
    "create_workspace_view": {
        "description": "Create a workspace-level saved issue view",
        "properties": {
            "workspace_slug": _WS,
            "name": _STR,
            "description": _STR,
            "filters": {"type": "object"},
        },
        "required": ["workspace_slug", "name"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/workspace-views/",
    },
    "get_workspace_view": {
        "description": "Get a single workspace view",
        "properties": {"workspace_slug": _WS, "view_id": _STR},
        "required": ["workspace_slug", "view_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/workspace-views/{view_id}/",
    },
    "update_workspace_view": {
        "description": "Update a workspace view",
        "properties": {
            "workspace_slug": _WS,
            "view_id": _STR,
            "name": _STR,
            "description": _STR,
            "filters": {"type": "object"},
        },
        "required": ["workspace_slug", "view_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/workspace-views/{view_id}/",
    },
    "delete_workspace_view": {
        "description": "Delete a workspace view (destructive; requires confirm=true)",
        "properties": {"workspace_slug": _WS, "view_id": _STR, "confirm": _BOOL},
        "required": ["workspace_slug", "view_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/workspace-views/{view_id}/",
        "destructive": "view_id",
    },
    # -- intake (inbox) issues --------------------------------------------
    "list_intake_issues": {
        "description": "List issues sitting in a project's intake/inbox queue",
        "properties": {"workspace_slug": _WS, "project_id": _PID},
        "required": ["workspace_slug", "project_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/intake-issues/",
    },
    "create_intake_issue": {
        "description": "Submit a new issue into a project's intake/inbox queue",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "title": _STR,
            "description": _STR,
        },
        "required": ["workspace_slug", "project_id", "title"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/intake-issues/",
        "payload_map": {"title": "name"},
    },
    "get_intake_issue": {
        "description": "Get a single intake issue",
        "properties": {"workspace_slug": _WS, "project_id": _PID, "intake_issue_id": _STR},
        "required": ["workspace_slug", "project_id", "intake_issue_id"],
        "method": "GET",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/intake-issues/{intake_issue_id}/",
    },
    "update_intake_issue": {
        "description": "Update an intake issue, e.g. to accept/reject/snooze it",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "intake_issue_id": _STR,
            "status": {
                **_INT,
                "description": "-2=pending, -1=rejected, 0=snoozed, 1=accepted, 2=duplicate",
            },
        },
        "required": ["workspace_slug", "project_id", "intake_issue_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/intake-issues/{intake_issue_id}/",
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
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/intake-issues/{intake_issue_id}/",
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
        "description": "Create an estimate system in a project",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "name": _STR,
            "type": {**_STR, "description": "categories | points | time"},
        },
        "required": ["workspace_slug", "project_id", "name"],
        "method": "POST",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/estimates/",
    },
    "update_estimate": {
        "description": "Update an estimate system",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "estimate_id": _STR,
            "name": _STR,
        },
        "required": ["workspace_slug", "project_id", "estimate_id"],
        "method": "PATCH",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/estimates/{estimate_id}/",
    },
    "delete_estimate": {
        "description": "Delete an estimate system (destructive; requires confirm=true)",
        "properties": {
            "workspace_slug": _WS,
            "project_id": _PID,
            "estimate_id": _STR,
            "confirm": _BOOL,
        },
        "required": ["workspace_slug", "project_id", "estimate_id"],
        "method": "DELETE",
        "path": "/api/v1/workspaces/{workspace_slug}/projects/{project_id}/estimates/{estimate_id}/",
        "destructive": "estimate_id",
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

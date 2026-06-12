def format_workflow_submission(workflow_session_full_id: str, status: str = "Pending") -> dict:
    return {
        "message": "request submitted",
        "status": status,
        "workflow_session_full_id": workflow_session_full_id,
    }

import os
import re
from devworkwire.core.domain import Epic, Priority, Label

def parse_epic_markdown(file_path: str) -> Epic:
    """
    Parses a markdown file into an Epic.
    Expected format:
    # Epic: [Title]
    **Description**: [desc]
    **Priority**: [priority]
    **Labels**: [label1, label2]
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Markdown file not found: {file_path}")
        
    with open(file_path, "r") as f:
        content = f.read()
        
    title_match = re.search(r"^# Epic:\s*(.+)$", content, re.MULTILINE)
    desc_match = re.search(r"\*\*Description\*\*:\s*(.*?)(?=\*\*|$)", content, re.DOTALL)
    priority_match = re.search(r"\*\*Priority\*\*:\s*(.+)$", content, re.MULTILINE)
    labels_match = re.search(r"\*\*Labels\*\*:\s*(.+)$", content, re.MULTILINE)
    
    title = title_match.group(1).strip() if title_match else "Untitled Epic"
    description = desc_match.group(1).strip() if desc_match else ""
    priority = Priority.from_jira_name(priority_match.group(1).strip()) if priority_match else None
    
    labels = []
    if labels_match:
        labels_raw = labels_match.group(1).strip()
        labels = [Label(name=lbl.strip()) for lbl in labels_raw.split(",") if lbl.strip()]
        
    return Epic.create(
        title=title,
        description=description,
        priority=priority,
        labels=labels
    )

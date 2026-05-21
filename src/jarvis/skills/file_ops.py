"""
File operations skill — allows Jarvis to create, read, edit, and delete files.
Security: Restricted to user's home directory and common project folders.
"""
import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jarvis.skills.file_ops")

# ── Allowed directories (security) ────────────────────────────────────
ALLOWED_BASE_PATHS = [
    Path.home(),  # User's home directory
    Path.home() / "Documents",
    Path.home() / "Downloads",
    Path.home() / "Desktop",
    Path.home() / "Projects",
    Path.cwd(),  # Current working directory
]
FULL_ACCESS = os.getenv("JARVIS_FILE_FULL_ACCESS", "false").lower() in {"1", "true", "yes", "on"}


def _is_safe_path(path: Path) -> bool:
    """Verify path is within allowed directories."""
    if FULL_ACCESS:
        return True
    try:
        path = path.resolve()
        for allowed in ALLOWED_BASE_PATHS:
            try:
                path.relative_to(allowed)
                return True
            except ValueError:
                continue
    except Exception as e:
        logger.warning(f"Path safety check failed: {e}")
    return False


def _extract_file_path(query: str) -> Optional[str]:
    """Extract file path from natural language query."""
    # Match patterns like "save to ~/file.txt" or "edit documents/readme.md"
    patterns = [
        r"(?:save|write|create|edit|open)(?:\s+to)?\s+(?:file\s+)?['\"]?([^\s'\"]+)['\"]?",
        r"file\s+(?:at\s+|path\s+)['\"]?([^\s'\"]+)['\"]?",
        r"(?:in|to)\s+(?:file\s+)?['\"]?([^\s'\"]+)['\"]?",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            path_str = match.group(1).strip()
            if path_str and len(path_str) > 2:
                return path_str
    return None


def _resolve_path(path_str: str) -> Optional[Path]:
    """Resolve user-friendly path strings to actual paths."""
    # Expand ~, environment variables
    expanded = os.path.expanduser(os.path.expandvars(path_str))
    path = Path(expanded)
    
    # If relative, make it relative to current working directory
    if not path.is_absolute():
        path = Path.cwd() / path
    
    if _is_safe_path(path):
        return path
    
    logger.warning(f"Path outside allowed directories: {path}")
    return None


def handle(query: str) -> Optional[str]:
    """
    Route file operation requests.
    Examples:
      - "Create a file called test.py with hello world"
      - "Write to ~/notes.txt: Remember to call mom"
      - "Read the file Documents/todo.txt"
      - "Edit src/main.py"
      - "Delete ~/temp_file.txt"
    """
    query_lower = query.lower()
    
    # ── CREATE / WRITE ────────────────────────────────────────────────
    if any(x in query_lower for x in ["create", "write", "save", "make a file"]):
        return _handle_write(query)
    
    # ── READ ──────────────────────────────────────────────────────────
    if any(x in query_lower for x in ["read", "show", "display", "cat", "open file"]):
        return _handle_read(query)
    
    # ── EDIT ──────────────────────────────────────────────────────────
    if any(x in query_lower for x in ["edit", "modify", "replace", "change", "append"]):
        return _handle_edit(query)
    
    # ── DELETE ────────────────────────────────────────────────────────
    if any(x in query_lower for x in ["delete", "remove", "erase"]):
        return _handle_delete(query)
    
    # ── LIST ──────────────────────────────────────────────────────────
    if any(x in query_lower for x in ["list files", "show files", "what's in", "contents of directory"]):
        return _handle_list(query)
    
    return None


def _handle_write(query: str) -> Optional[str]:
    """Create or write to a file."""
    try:
        # Extract file path
        file_path_str = _extract_file_path(query)
        if not file_path_str:
            return None
        
        file_path = _resolve_path(file_path_str)
        if not file_path:
            return f"I cannot access that file path, sir. Please use a location within your home directory or current projects."
        
        # Extract content — look for "with ...", "containing ...", "content is ..."
        content_patterns = [
            r"(?:with|containing|content)\s+['\"]?(.+?)(?:['\"]|$)",
            r":\s*(.+)$",  # After colon
        ]
        
        content = ""
        for pattern in content_patterns:
            match = re.search(pattern, query, re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip()
                break
        
        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        file_path.write_text(content, encoding="utf-8")
        
        logger.info(f"Created/wrote file: {file_path}")
        return f"File created at {file_path.name}, sir. {len(content)} characters written."
    
    except Exception as e:
        logger.error(f"Write error: {e}")
        return f"I encountered an error writing the file, sir: {e}"


def _handle_read(query: str) -> Optional[str]:
    """Read and display file contents."""
    try:
        file_path_str = _extract_file_path(query)
        if not file_path_str:
            return None
        
        file_path = _resolve_path(file_path_str)
        if not file_path:
            return f"I cannot access that file path, sir."
        
        if not file_path.exists():
            return f"The file does not exist, sir: {file_path.name}"
        
        if not file_path.is_file():
            return f"That is a directory, not a file, sir."
        
        # Don't read files larger than 10KB (for voice efficiency)
        if file_path.stat().st_size > 10240:
            return f"The file is quite large, sir — {file_path.stat().st_size / 1024:.1f} kilobytes. I'll read the first few lines: {open(file_path).readlines()[:5]}"
        
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        logger.info(f"Read file: {file_path}")
        
        # Summarize for voice output
        lines = content.split("\n")
        if len(lines) > 20:
            preview = "\n".join(lines[:20])
            return f"File {file_path.name} contains {len(lines)} lines. Here is the beginning: {preview}"
        
        return content
    
    except Exception as e:
        logger.error(f"Read error: {e}")
        return f"I had trouble reading that file, sir: {e}"


def _handle_edit(query: str) -> Optional[str]:
    """Edit/append to an existing file."""
    try:
        file_path_str = _extract_file_path(query)
        if not file_path_str:
            return None
        
        file_path = _resolve_path(file_path_str)
        if not file_path:
            return f"I cannot access that file path, sir."
        
        if not file_path.exists():
            return f"The file does not exist, sir. Would you like me to create it?"
        
        # Extract new content
        content_patterns = [
            r"(?:with|to)\s+['\"]?(.+?)(?:['\"]|$)",
            r":\s*(.+)$",
        ]
        
        new_content = ""
        for pattern in content_patterns:
            match = re.search(pattern, query, re.IGNORECASE | re.DOTALL)
            if match:
                new_content = match.group(1).strip()
                break
        
        if not new_content:
            return "I did not understand what you want to write to the file, sir."
        
        # Check if appending or replacing
        if "append" in query.lower():
            current = file_path.read_text(encoding="utf-8", errors="ignore")
            file_path.write_text(current + "\n" + new_content, encoding="utf-8")
            return f"Content appended to {file_path.name}, sir."
        else:
            file_path.write_text(new_content, encoding="utf-8")
            return f"File {file_path.name} has been updated, sir."
    
    except Exception as e:
        logger.error(f"Edit error: {e}")
        return f"I encountered an error editing the file, sir: {e}"


def _handle_delete(query: str) -> Optional[str]:
    """Delete a file (with confirmation)."""
    try:
        file_path_str = _extract_file_path(query)
        if not file_path_str:
            return None
        
        file_path = _resolve_path(file_path_str)
        if not file_path:
            return f"I cannot access that file path, sir."
        
        if not file_path.exists():
            return f"The file does not exist, sir."
        
        # Safety: ask for confirmation
        if "confirm" not in query.lower() and "yes" not in query.lower():
            return f"I am about to delete {file_path.name}. Please confirm by saying 'confirm delete' or 'yes, delete'."
        
        file_path.unlink()
        logger.info(f"Deleted file: {file_path}")
        return f"File {file_path.name} has been deleted, sir."
    
    except Exception as e:
        logger.error(f"Delete error: {e}")
        return f"I encountered an error deleting the file, sir: {e}"


def _handle_list(query: str) -> Optional[str]:
    """List files in a directory."""
    try:
        file_path_str = _extract_file_path(query)
        
        # Default to home if no path specified
        if not file_path_str or "directory" in query.lower():
            dir_path = Path.home()
        else:
            dir_path = _resolve_path(file_path_str)
        
        if not dir_path:
            dir_path = Path.home()
        
        if not dir_path.is_dir():
            return f"That is not a directory, sir."
        
        files = list(dir_path.iterdir())[:20]  # Limit to 20 for voice
        
        if not files:
            return f"The directory is empty, sir."
        
        file_names = [f.name for f in sorted(files)]
        return f"In {dir_path.name}, I found: {', '.join(file_names)}"
    
    except Exception as e:
        logger.error(f"List error: {e}")
        return f"I had trouble listing the directory, sir: {e}"

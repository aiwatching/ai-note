"""Markdown file storage management."""
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import frontmatter
from loguru import logger

from ..config import get_settings


class MarkdownStorage:
    """Manage Markdown file storage for notes."""

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize Markdown storage.

        Args:
            base_path: Base path for notes directory
        """
        settings = get_settings()
        self.base_path = Path(base_path or settings.notes_base_path)
        self.raw_path = self.base_path / "raw"
        self.organized_path = self.base_path / "organized"
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.raw_path.mkdir(parents=True, exist_ok=True)
        self.organized_path.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, note_id: int, suffix: str = "") -> str:
        """
        Generate filename for a note.

        Args:
            note_id: Note ID
            suffix: Optional suffix (e.g., "_org" for organized)

        Returns:
            Filename string
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}_{note_id:06d}{suffix}.md"

    def save_raw(self, note_id: int, content: str, metadata: Dict) -> str:
        """
        Save raw note content to file.

        Args:
            note_id: Note ID
            content: Raw note content
            metadata: Note metadata

        Returns:
            File path
        """
        filename = self._generate_filename(note_id)
        filepath = self.raw_path / filename

        # Create frontmatter post
        post = frontmatter.Post(content, **metadata)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(frontmatter.dumps(post))
            logger.debug(f"Saved raw note to {filepath}")
            return str(filepath)
        except IOError as e:
            logger.error(f"Failed to save raw note: {e}")
            raise

    def save_organized(self, note_id: int, content: str, metadata: Dict) -> str:
        """
        Save organized note content to file.

        Args:
            note_id: Note ID
            content: Organized note content
            metadata: Note metadata with AI analysis

        Returns:
            File path
        """
        filename = self._generate_filename(note_id, suffix="_org")
        filepath = self.organized_path / filename

        # Add organized timestamp
        metadata["organized_at"] = datetime.now().isoformat()

        post = frontmatter.Post(content, **metadata)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(frontmatter.dumps(post))
            logger.debug(f"Saved organized note to {filepath}")
            return str(filepath)
        except IOError as e:
            logger.error(f"Failed to save organized note: {e}")
            raise

    def read(self, filepath: str) -> Tuple[str, Dict]:
        """
        Read note file.

        Args:
            filepath: Path to note file

        Returns:
            Tuple of (content, metadata)
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
            return post.content, dict(post.metadata)
        except IOError as e:
            logger.error(f"Failed to read note file {filepath}: {e}")
            raise

    def delete(self, filepath: str) -> bool:
        """
        Delete note file.

        Args:
            filepath: Path to note file

        Returns:
            True if deleted successfully
        """
        try:
            path = Path(filepath)
            if path.exists():
                path.unlink()
                logger.debug(f"Deleted note file {filepath}")
                return True
            return False
        except IOError as e:
            logger.error(f"Failed to delete note file {filepath}: {e}")
            return False

    def update(self, filepath: str, content: str, metadata: Dict) -> bool:
        """
        Update existing note file.

        Args:
            filepath: Path to note file
            content: Updated content
            metadata: Updated metadata

        Returns:
            True if updated successfully
        """
        try:
            metadata["updated_at"] = datetime.now().isoformat()
            post = frontmatter.Post(content, **metadata)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(frontmatter.dumps(post))
            logger.debug(f"Updated note file {filepath}")
            return True
        except IOError as e:
            logger.error(f"Failed to update note file {filepath}: {e}")
            return False

    def generate_organized_content(self, raw_content: str, analysis: Dict) -> str:
        """
        Generate organized Markdown content from raw content and AI analysis.

        Args:
            raw_content: Raw note content
            analysis: AI analysis result

        Returns:
            Organized Markdown content
        """
        lines = []

        # Title
        title = analysis.get("title") or "Untitled Note"
        lines.append(f"# {title}")
        lines.append("")

        # Summary
        if analysis.get("summary"):
            lines.append(f"> {analysis['summary']}")
            lines.append("")

        # Original content section
        lines.append("## Content")
        lines.append("")
        lines.append(raw_content)
        lines.append("")

        # Suggested actions
        suggested_actions = analysis.get("suggested_actions", [])
        if suggested_actions:
            lines.append("## Suggested Actions")
            lines.append("")
            for action in suggested_actions:
                action_type = action.get("type", "")
                action_title = action.get("title", "")
                if action_type == "create_todo":
                    due = action.get("due_date", "")
                    priority = action.get("priority", "medium")
                    lines.append(f"- [ ] {action_title} (Due: {due}, Priority: {priority})")
                elif action_type == "create_schedule":
                    time = action.get("start_time", "")
                    participants = ", ".join(action.get("participants", []))
                    lines.append(f"- [ ] {action_title} (Time: {time}, With: {participants})")
            lines.append("")

        # Metadata section
        lines.append("---")
        lines.append("")
        lines.append("## Metadata")
        lines.append("")
        lines.append(f"- **Category**: {analysis.get('category', 'Unknown')}")
        if analysis.get("subcategory"):
            lines.append(f"- **Subcategory**: {analysis['subcategory']}")
        if analysis.get("tags"):
            lines.append(f"- **Tags**: {', '.join(analysis['tags'])}")
        if analysis.get("priority"):
            lines.append(f"- **Priority**: {analysis['priority']}")

        # Entities
        entities = analysis.get("entities", {})
        if entities.get("persons"):
            lines.append(f"- **People**: {', '.join(entities['persons'])}")
        if entities.get("dates"):
            lines.append(f"- **Dates**: {', '.join(entities['dates'])}")
        if entities.get("locations"):
            lines.append(f"- **Locations**: {', '.join(entities['locations'])}")
        if entities.get("companies"):
            lines.append(f"- **Companies**: {', '.join(entities['companies'])}")

        return "\n".join(lines)

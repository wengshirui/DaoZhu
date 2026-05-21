"""Skill loader — scan, index, and load skills from disk.

Scans both user skills (~/.accobot/skills/) and bundled skills (accobot/skills/)
to build a compact index for the system prompt and load full content on demand.

Inspired by Hermes Agent's agent/skill_commands.py and tools/skills_tool.py.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from accobot.config import get_accobot_home

logger = logging.getLogger(__name__)

# Limits
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 80
MAX_SKILL_CONTENT_CHARS = 5000

# Directories
BUNDLED_SKILLS_DIR = Path(__file__).parent  # accobot/skills/


def get_user_skills_dir() -> Path:
    """Return the user skills directory (~/.accobot/skills/)."""
    return get_accobot_home() / "skills"


def get_all_skills_dirs() -> List[Path]:
    """Return all skill directories to scan (user first, then bundled)."""
    dirs = []
    user_dir = get_user_skills_dir()
    if user_dir.exists():
        dirs.append(user_dir)
    if BUNDLED_SKILLS_DIR.exists():
        dirs.append(BUNDLED_SKILLS_DIR)
    return dirs


# =========================================================================
# Frontmatter Parsing
# =========================================================================

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from a SKILL.md file.

    Returns (frontmatter_dict, body_text).
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        frontmatter = {}

    body = content[match.end():]
    return frontmatter, body


# =========================================================================
# Skill Scanning & Indexing
# =========================================================================

def scan_skills() -> List[Dict[str, Any]]:
    """Scan all skill directories and return a list of skill metadata.

    Each entry contains: name, description, category, path, is_builtin.
    User skills take precedence over bundled skills with the same name.
    """
    skills = []
    seen_names = set()

    for skills_dir in get_all_skills_dirs():
        is_builtin = (skills_dir == BUNDLED_SKILLS_DIR)

        for skill_md in sorted(skills_dir.rglob("SKILL.md")):
            # Skip hidden directories
            if any(part.startswith(".") for part in skill_md.parts):
                continue

            try:
                content = skill_md.read_text(encoding="utf-8")
                frontmatter, body = parse_frontmatter(content)

                name = frontmatter.get("name", skill_md.parent.name)
                if name in seen_names:
                    continue  # User skill takes precedence

                description = frontmatter.get("description", "")
                if not description:
                    # Extract first non-heading line as description
                    for line in body.strip().split("\n"):
                        line = line.strip()
                        if line and not line.startswith("#"):
                            description = line[:MAX_DESCRIPTION_LENGTH]
                            break

                category = frontmatter.get("category", "")
                tags = frontmatter.get("tags", [])
                if isinstance(tags, str):
                    tags = [tags]

                seen_names.add(name)
                skills.append({
                    "name": name,
                    "description": description[:MAX_DESCRIPTION_LENGTH],
                    "category": category,
                    "tags": tags,
                    "path": str(skill_md.parent),
                    "is_builtin": is_builtin,
                })

            except Exception as e:
                logger.warning("Failed to parse skill %s: %s", skill_md, e)
                continue

    return skills


def build_skills_index(skills: Optional[List[Dict[str, Any]]] = None) -> str:
    """Build a compact skill index string for system prompt injection.

    Format:
    <available_skills>
    - skill-name: description
    - another-skill: description
    </available_skills>

    Returns empty string if no skills found.
    """
    if skills is None:
        skills = scan_skills()

    if not skills:
        return ""

    lines = ["<available_skills>"]

    # Group by category
    by_category: Dict[str, List[Dict]] = {}
    for skill in skills:
        cat = skill.get("category") or "general"
        by_category.setdefault(cat, []).append(skill)

    for category in sorted(by_category.keys()):
        if len(by_category) > 1:
            lines.append(f"[{category}]")
        for skill in by_category[category]:
            lines.append(f"- {skill['name']}: {skill['description']}")

    lines.append("</available_skills>")
    return "\n".join(lines)


# =========================================================================
# Skill Loading (Full Content)
# =========================================================================

def load_skill(name: str, file_path: Optional[str] = None) -> Dict[str, Any]:
    """Load a skill's full content by name.

    Args:
        name: Skill name (matches directory name or frontmatter name)
        file_path: Optional sub-file to load (e.g., "references/api.md")

    Returns:
        Dict with keys: success, name, content, path, is_builtin, frontmatter
    """
    # Search all skill directories
    for skills_dir in get_all_skills_dirs():
        is_builtin = (skills_dir == BUNDLED_SKILLS_DIR)

        for skill_md in skills_dir.rglob("SKILL.md"):
            if any(part.startswith(".") for part in skill_md.parts):
                continue

            # Match by directory name or frontmatter name
            if skill_md.parent.name == name:
                return _load_skill_from_path(skill_md, name, file_path, is_builtin)

            # Also check frontmatter name
            try:
                content = skill_md.read_text(encoding="utf-8")
                fm, _ = parse_frontmatter(content)
                if fm.get("name") == name:
                    return _load_skill_from_path(skill_md, name, file_path, is_builtin)
            except Exception:
                continue

    return {"success": False, "error": f"Skill '{name}' not found"}


def _load_skill_from_path(
    skill_md: Path, name: str, file_path: Optional[str], is_builtin: bool
) -> Dict[str, Any]:
    """Load skill content from a resolved SKILL.md path."""
    skill_dir = skill_md.parent

    if file_path:
        # Load a sub-file
        target = skill_dir / file_path
        if not target.exists():
            return {"success": False, "error": f"File '{file_path}' not found in skill '{name}'"}
        if not target.is_file():
            return {"success": False, "error": f"'{file_path}' is not a file"}
        try:
            content = target.read_text(encoding="utf-8")
            return {
                "success": True,
                "name": name,
                "content": content,
                "path": str(target),
                "is_builtin": is_builtin,
                "file_path": file_path,
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to read: {e}"}

    # Load main SKILL.md
    try:
        content = skill_md.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)

        return {
            "success": True,
            "name": frontmatter.get("name", name),
            "content": body.strip(),
            "raw_content": content,
            "path": str(skill_md),
            "skill_dir": str(skill_dir),
            "is_builtin": is_builtin,
            "frontmatter": frontmatter,
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to read skill: {e}"}


# =========================================================================
# Skill Management (Create / Edit / Delete)
# =========================================================================

def create_skill(name: str, content: str, category: Optional[str] = None) -> Dict[str, Any]:
    """Create a new user skill.

    Args:
        name: Skill name (used as directory name)
        content: Full SKILL.md content (including frontmatter)
        category: Optional category subdirectory

    Returns:
        Dict with success status and path.
    """
    # Validate name
    if not name or len(name) > MAX_NAME_LENGTH:
        return {"success": False, "error": f"Skill name must be 1-{MAX_NAME_LENGTH} characters"}

    # Validate content has frontmatter
    frontmatter, body = parse_frontmatter(content)
    if "name" not in frontmatter:
        return {"success": False, "error": "SKILL.md must have 'name' in frontmatter"}
    if "description" not in frontmatter:
        return {"success": False, "error": "SKILL.md must have 'description' in frontmatter"}
    if len(frontmatter.get("description", "")) > MAX_DESCRIPTION_LENGTH:
        return {"success": False, "error": f"Description must be ≤ {MAX_DESCRIPTION_LENGTH} characters"}

    # Validate content size
    if len(content) > MAX_SKILL_CONTENT_CHARS:
        return {
            "success": False,
            "error": f"Content too large ({len(content)} chars, max {MAX_SKILL_CONTENT_CHARS}). "
                     "Put detailed content in references/ sub-files.",
        }

    # Determine target directory
    user_dir = get_user_skills_dir()
    if category:
        skill_dir = user_dir / category / name
    else:
        skill_dir = user_dir / name

    if skill_dir.exists():
        return {"success": False, "error": f"Skill '{name}' already exists at {skill_dir}"}

    # Create directory and write file
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(content, encoding="utf-8")

    return {
        "success": True,
        "name": name,
        "path": str(skill_md),
        "message": f"Skill '{name}' created at {skill_dir}",
    }


def edit_skill(name: str, content: str) -> Dict[str, Any]:
    """Edit an existing user skill's SKILL.md content.

    Cannot edit bundled (read-only) skills.
    """
    result = load_skill(name)
    if not result.get("success"):
        return result

    if result.get("is_builtin"):
        return {"success": False, "error": f"Cannot edit bundled skill '{name}' (read-only)"}

    # Validate new content
    frontmatter, body = parse_frontmatter(content)
    if "name" not in frontmatter or "description" not in frontmatter:
        return {"success": False, "error": "Content must have 'name' and 'description' in frontmatter"}

    skill_md = Path(result["path"])
    if not skill_md.name == "SKILL.md":
        skill_md = Path(result.get("skill_dir", "")) / "SKILL.md"

    skill_md.write_text(content, encoding="utf-8")
    return {
        "success": True,
        "name": name,
        "path": str(skill_md),
        "message": f"Skill '{name}' updated",
    }


def delete_skill(name: str) -> Dict[str, Any]:
    """Delete a user skill.

    Cannot delete bundled (read-only) skills.
    """
    import shutil

    result = load_skill(name)
    if not result.get("success"):
        return {"success": False, "error": f"Skill '{name}' not found"}

    if result.get("is_builtin"):
        return {"success": False, "error": f"Cannot delete bundled skill '{name}' (read-only)"}

    skill_dir = Path(result.get("skill_dir", ""))
    if not skill_dir.exists():
        return {"success": False, "error": f"Skill directory not found"}

    shutil.rmtree(skill_dir)
    return {
        "success": True,
        "name": name,
        "message": f"Skill '{name}' deleted",
    }

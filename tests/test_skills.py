"""Tests for the Skill system (REQ-016)."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from accobot.skills.loader import (
    parse_frontmatter,
    scan_skills,
    build_skills_index,
    load_skill,
    create_skill,
    edit_skill,
    delete_skill,
    get_user_skills_dir,
    BUNDLED_SKILLS_DIR,
)


# =========================================================================
# Frontmatter Parsing
# =========================================================================

class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        content = "---\nname: test\ndescription: A test skill\n---\n\n# Body"
        fm, body = parse_frontmatter(content)
        assert fm["name"] == "test"
        assert fm["description"] == "A test skill"
        assert "# Body" in body

    def test_no_frontmatter(self):
        content = "# Just a markdown file\nNo frontmatter here."
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert "# Just a markdown file" in body

    def test_empty_frontmatter(self):
        content = "---\n---\n\nBody text"
        fm, body = parse_frontmatter(content)
        assert fm == {} or fm is None  # yaml.safe_load returns None for empty
        # Body should still be extracted
        assert "Body text" in body


# =========================================================================
# Skill Scanning
# =========================================================================

class TestScanSkills:
    def test_finds_bundled_skills(self):
        skills = scan_skills()
        names = [s["name"] for s in skills]
        assert "create-skill" in names

    def test_bundled_skills_marked_correctly(self):
        skills = scan_skills()
        for s in skills:
            if s["name"] == "create-skill":
                assert s["is_builtin"] is True

    def test_skills_have_required_fields(self):
        skills = scan_skills()
        for s in skills:
            assert "name" in s
            assert "description" in s
            assert "path" in s
            assert "is_builtin" in s
            assert len(s["description"]) <= 80


# =========================================================================
# Skills Index
# =========================================================================

class TestBuildSkillsIndex:
    def test_index_contains_skill_names(self):
        index = build_skills_index()
        assert "create-skill" in index

    def test_index_has_tags(self):
        index = build_skills_index()
        assert "<available_skills>" in index
        assert "</available_skills>" in index

    def test_empty_index_returns_empty_string(self):
        index = build_skills_index(skills=[])
        assert index == ""


# =========================================================================
# Skill Loading
# =========================================================================

class TestLoadSkill:
    def test_load_bundled_skill(self):
        result = load_skill("create-skill")
        assert result["success"] is True
        assert "创建新 Skill" in result["content"]
        assert result["is_builtin"] is True

    def test_load_nonexistent_skill(self):
        result = load_skill("不存在的skill")
        assert result["success"] is False
        assert "not found" in result["error"]


# =========================================================================
# Skill Management (Create / Edit / Delete)
# =========================================================================

class TestSkillManagement:
    @pytest.fixture
    def temp_skills_dir(self, tmp_path):
        """Redirect user skills to a temp directory."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        with patch("accobot.skills.loader.get_user_skills_dir", return_value=skills_dir):
            yield skills_dir

    def test_create_skill(self, temp_skills_dir):
        content = "---\nname: test-skill\ndescription: A test\n---\n\n# Test\nHello"
        with patch("accobot.skills.loader.get_user_skills_dir", return_value=temp_skills_dir):
            result = create_skill("test-skill", content)
        assert result["success"] is True
        assert (temp_skills_dir / "test-skill" / "SKILL.md").exists()

    def test_create_skill_missing_frontmatter(self, temp_skills_dir):
        content = "# No frontmatter\nJust body"
        with patch("accobot.skills.loader.get_user_skills_dir", return_value=temp_skills_dir):
            result = create_skill("bad-skill", content)
        assert result["success"] is False
        assert "name" in result["error"]

    def test_create_skill_description_too_long(self, temp_skills_dir):
        desc = "x" * 100
        content = f"---\nname: long-desc\ndescription: {desc}\n---\n\n# Body"
        with patch("accobot.skills.loader.get_user_skills_dir", return_value=temp_skills_dir):
            result = create_skill("long-desc", content)
        assert result["success"] is False
        assert "80" in result["error"]

    def test_edit_skill(self, temp_skills_dir):
        # Create first
        content = "---\nname: editable\ndescription: Original\n---\n\n# V1"
        with patch("accobot.skills.loader.get_user_skills_dir", return_value=temp_skills_dir):
            create_skill("editable", content)
            # Edit
            new_content = "---\nname: editable\ndescription: Updated\n---\n\n# V2"
            result = edit_skill("editable", new_content)
        assert result["success"] is True
        saved = (temp_skills_dir / "editable" / "SKILL.md").read_text(encoding="utf-8")
        assert "V2" in saved

    def test_cannot_edit_bundled_skill(self):
        result = edit_skill("create-skill", "---\nname: x\ndescription: y\n---\nHack")
        assert result["success"] is False
        assert "read-only" in result["error"]

    def test_delete_skill(self, temp_skills_dir):
        content = "---\nname: deleteme\ndescription: To delete\n---\n\n# Bye"
        with patch("accobot.skills.loader.get_user_skills_dir", return_value=temp_skills_dir):
            create_skill("deleteme", content)
            assert (temp_skills_dir / "deleteme").exists()
            result = delete_skill("deleteme")
        assert result["success"] is True
        assert not (temp_skills_dir / "deleteme").exists()

    def test_cannot_delete_bundled_skill(self):
        result = delete_skill("create-skill")
        assert result["success"] is False
        assert "read-only" in result["error"]


# =========================================================================
# Skill Tool Integration
# =========================================================================

class TestSkillTools:
    def test_skill_list_tool(self):
        from accobot.tools.skill_tool import skill_list
        result = json.loads(skill_list({}))
        assert result["count"] >= 1
        names = [s["name"] for s in result["skills"]]
        assert "create-skill" in names

    def test_skill_view_tool(self):
        from accobot.tools.skill_tool import skill_view
        result = json.loads(skill_view({"name": "create-skill"}))
        assert result["success"] is True
        assert "skill_manage" in result["content"]

    def test_skill_view_not_found(self):
        from accobot.tools.skill_tool import skill_view
        result = json.loads(skill_view({"name": "不存在"}))
        assert "error" in result

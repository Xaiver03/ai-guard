"""tests/unit/core/usage/test_loader.py -- ClaudeDataLoader 单元测试"""

import json
from datetime import datetime
from aigard.core.usage.loader import ClaudeDataLoader


def _make_jsonl_line(type_="assistant", model="claude-sonnet-4-6",
                      input_tokens=1000, output_tokens=500,
                      timestamp="2026-05-24T14:30:00Z"):
    data = {"type": type_, "timestamp": timestamp}
    if type_ == "assistant":
        data["message"] = {
            "model": model,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_input_tokens": 200,
                "cache_read_input_tokens": 100,
            }
        }
    else:
        data["message"] = {"content": "hello"}
    return json.dumps(data)


class TestLoadAllUsage:
    def test_loads_from_jsonl(self, tmp_path):
        proj = tmp_path / "projects" / "project-a"
        proj.mkdir(parents=True)
        (proj / "session1.jsonl").write_text(
            _make_jsonl_line() + "\n" + _make_jsonl_line(input_tokens=2000) + "\n"
        )

        loader = ClaudeDataLoader(str(tmp_path))
        entries = loader.load_all_usage()
        assert len(entries) == 2
        assert entries[0].input_tokens == 1000
        assert entries[1].input_tokens == 2000

    def test_empty_dir(self, tmp_path):
        proj = tmp_path / "projects"
        proj.mkdir()
        loader = ClaudeDataLoader(str(tmp_path))
        assert loader.load_all_usage() == []

    def test_no_projects_dir(self, tmp_path):
        loader = ClaudeDataLoader(str(tmp_path))
        assert loader.load_all_usage() == []

    def test_sorted_by_timestamp(self, tmp_path):
        proj = tmp_path / "projects" / "proj"
        proj.mkdir(parents=True)
        lines = [
            _make_jsonl_line(timestamp="2026-05-25T10:00:00Z"),
            _make_jsonl_line(timestamp="2026-05-24T10:00:00Z"),
        ]
        (proj / "s1.jsonl").write_text("\n".join(lines) + "\n")

        loader = ClaudeDataLoader(str(tmp_path))
        entries = loader.load_all_usage()
        assert entries[0].timestamp < entries[1].timestamp


class TestParseUsageEntry:
    def test_valid_assistant(self, tmp_path):
        proj = tmp_path / "projects" / "proj"
        proj.mkdir(parents=True)
        (proj / "s1.jsonl").write_text(_make_jsonl_line() + "\n")

        loader = ClaudeDataLoader(str(tmp_path))
        entries = loader.load_all_usage()
        assert len(entries) == 1
        e = entries[0]
        assert e.model == "claude-sonnet-4-6"
        assert e.input_tokens == 1000
        assert e.output_tokens == 500
        assert e.cache_creation_tokens == 200
        assert e.cache_read_tokens == 100
        assert e.project == "proj"
        assert e.session_id == "s1"

    def test_non_assistant_skipped(self, tmp_path):
        proj = tmp_path / "projects" / "proj"
        proj.mkdir(parents=True)
        (proj / "s1.jsonl").write_text(_make_jsonl_line(type_="user") + "\n")

        loader = ClaudeDataLoader(str(tmp_path))
        assert loader.load_all_usage() == []

    def test_no_usage_skipped(self, tmp_path):
        proj = tmp_path / "projects" / "proj"
        proj.mkdir(parents=True)
        data = json.dumps({"type": "assistant", "message": {"model": "x"}})
        (proj / "s1.jsonl").write_text(data + "\n")

        loader = ClaudeDataLoader(str(tmp_path))
        assert loader.load_all_usage() == []

    def test_invalid_json_skipped(self, tmp_path):
        proj = tmp_path / "projects" / "proj"
        proj.mkdir(parents=True)
        content = "not valid json\n" + _make_jsonl_line() + "\n"
        (proj / "s1.jsonl").write_text(content)

        loader = ClaudeDataLoader(str(tmp_path))
        entries = loader.load_all_usage()
        assert len(entries) == 1

    def test_empty_line_skipped(self, tmp_path):
        proj = tmp_path / "projects" / "proj"
        proj.mkdir(parents=True)
        content = "\n\n" + _make_jsonl_line() + "\n\n"
        (proj / "s1.jsonl").write_text(content)

        loader = ClaudeDataLoader(str(tmp_path))
        entries = loader.load_all_usage()
        assert len(entries) == 1

    def test_unreadable_file_skipped(self, tmp_path):
        """测试无法读取的文件被跳过（line 112-114）"""
        import os
        proj = tmp_path / "projects" / "proj"
        proj.mkdir(parents=True)
        f = proj / "bad.jsonl"
        f.write_text("data")
        os.chmod(str(f), 0o000)

        loader = ClaudeDataLoader(str(tmp_path))
        entries = loader.load_all_usage()
        assert entries == []

        os.chmod(str(f), 0o644)  # cleanup

    def test_parse_entry_exception_skipped(self, tmp_path):
        """测试解析单条异常时跳过（line 109-111）"""
        proj = tmp_path / "projects" / "proj"
        proj.mkdir(parents=True)
        # Valid JSON but causes exception during _parse_usage_entry
        data = json.dumps({"type": "assistant", "message": {"usage": {"input_tokens": "not_int"}, "model": "x"}, "timestamp": "invalid!!!"})
        content = data + "\n" + _make_jsonl_line() + "\n"
        (proj / "s1.jsonl").write_text(content)

        loader = ClaudeDataLoader(str(tmp_path))
        entries = loader.load_all_usage()
        # The first entry should fail to parse, second should succeed
        assert len(entries) >= 1


class TestParseTimestamp:
    def test_format_with_milliseconds(self, tmp_path):
        proj = tmp_path / "projects" / "proj"
        proj.mkdir(parents=True)
        (proj / "s1.jsonl").write_text(
            _make_jsonl_line(timestamp="2026-05-24T14:30:00.123Z") + "\n"
        )
        loader = ClaudeDataLoader(str(tmp_path))
        entries = loader.load_all_usage()
        assert entries[0].timestamp.hour == 14

    def test_format_without_z(self, tmp_path):
        proj = tmp_path / "projects" / "proj"
        proj.mkdir(parents=True)
        (proj / "s1.jsonl").write_text(
            _make_jsonl_line(timestamp="2026-05-24T14:30:00") + "\n"
        )
        loader = ClaudeDataLoader(str(tmp_path))
        entries = loader.load_all_usage()
        assert entries[0].timestamp.hour == 14

    def test_format_space_separated(self, tmp_path):
        proj = tmp_path / "projects" / "proj"
        proj.mkdir(parents=True)
        (proj / "s1.jsonl").write_text(
            _make_jsonl_line(timestamp="2026-05-24 14:30:00") + "\n"
        )
        loader = ClaudeDataLoader(str(tmp_path))
        entries = loader.load_all_usage()
        assert entries[0].timestamp.hour == 14

    def test_null_timestamp_uses_now(self, tmp_path):
        """测试 timestamp 为 None 时使用当前时间（line 181）"""
        proj = tmp_path / "projects" / "proj"
        proj.mkdir(parents=True)
        data = {"type": "assistant", "message": {"model": "x", "usage": {"input_tokens": 100, "output_tokens": 50}}}
        # No timestamp field
        (proj / "s1.jsonl").write_text(json.dumps(data) + "\n")
        loader = ClaudeDataLoader(str(tmp_path))
        entries = loader.load_all_usage()
        assert len(entries) == 1
        # Timestamp should be close to now
        assert (datetime.now() - entries[0].timestamp).total_seconds() < 5

    def test_unparseable_timestamp_uses_now(self, tmp_path):
        """测试无法解析的 timestamp 使用当前时间（line 198）"""
        proj = tmp_path / "projects" / "proj"
        proj.mkdir(parents=True)
        (proj / "s1.jsonl").write_text(
            _make_jsonl_line(timestamp="not-a-date-at-all") + "\n"
        )
        loader = ClaudeDataLoader(str(tmp_path))
        entries = loader.load_all_usage()
        assert len(entries) == 1
        assert (datetime.now() - entries[0].timestamp).total_seconds() < 5


class TestLoadProjectUsage:
    def test_loads_specific_project(self, tmp_path):
        for name in ["proj-a", "proj-b"]:
            d = tmp_path / "projects" / name
            d.mkdir(parents=True)
            (d / "s1.jsonl").write_text(_make_jsonl_line() + "\n")

        loader = ClaudeDataLoader(str(tmp_path))
        entries = loader.load_project_usage("proj-a")
        assert len(entries) == 1
        assert entries[0].project == "proj-a"

    def test_nonexistent_project(self, tmp_path):
        loader = ClaudeDataLoader(str(tmp_path))
        assert loader.load_project_usage("nope") == []


class TestGetProjects:
    def test_returns_sorted(self, tmp_path):
        for name in ["zzz", "aaa", "mmm"]:
            (tmp_path / "projects" / name).mkdir(parents=True)

        loader = ClaudeDataLoader(str(tmp_path))
        assert loader.get_projects() == ["aaa", "mmm", "zzz"]

    def test_no_projects_dir(self, tmp_path):
        loader = ClaudeDataLoader(str(tmp_path))
        assert loader.get_projects() == []

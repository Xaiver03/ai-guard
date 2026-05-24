"""tests/unit/core/test_whitelist.py -- WhitelistManager 单元测试"""

import threading
from aigard.core.whitelist import WhitelistManager


class TestWhitelistInit:
    def test_init_from_config(self):
        cfg = {
            "process_names": ["Chrome", "Firefox"],
            "command_keywords": ["python", "node"],
            "pids": [100, 200],
        }
        wm = WhitelistManager(cfg)
        result = wm.get_all()
        assert "chrome" in result["process_names"]
        assert "firefox" in result["process_names"]
        assert "python" in result["command_keywords"]
        assert 100 in result["pids"]

    def test_init_empty_config(self):
        wm = WhitelistManager({})
        result = wm.get_all()
        assert result["process_names"] == []
        assert result["command_keywords"] == []
        assert result["pids"] == []


class TestIsWhitelisted:
    def test_by_pid(self):
        wm = WhitelistManager({"pids": [123]})
        assert wm.is_whitelisted({"pid": 123, "name": "test", "cmdline": ""}) is True

    def test_by_process_name_case_insensitive(self):
        wm = WhitelistManager({"process_names": ["Chrome"]})
        assert wm.is_whitelisted({"pid": 1, "name": "chrome", "cmdline": ""}) is True
        assert wm.is_whitelisted({"pid": 1, "name": "CHROME", "cmdline": ""}) is True

    def test_by_command_keyword(self):
        wm = WhitelistManager({"command_keywords": ["python"]})
        proc = {"pid": 1, "name": "test", "cmdline": "/usr/bin/python test.py"}
        assert wm.is_whitelisted(proc) is True

    def test_not_whitelisted(self):
        wm = WhitelistManager({"process_names": ["chrome"]})
        proc = {"pid": 999, "name": "firefox", "cmdline": "/usr/bin/firefox"}
        assert wm.is_whitelisted(proc) is False

    def test_cmdline_keyword_case_insensitive(self):
        wm = WhitelistManager({"command_keywords": ["python"]})
        proc = {"pid": 1, "name": "x", "cmdline": "/usr/bin/PYTHON3 test.py"}
        assert wm.is_whitelisted(proc) is True


class TestCRUD:
    def test_add_process_name(self):
        wm = WhitelistManager({})
        assert wm.add_process_name("chrome") is True
        assert wm.is_whitelisted({"pid": 1, "name": "chrome", "cmdline": ""}) is True

    def test_add_process_name_duplicate(self):
        wm = WhitelistManager({"process_names": ["chrome"]})
        assert wm.add_process_name("chrome") is False

    def test_remove_process_name(self):
        wm = WhitelistManager({"process_names": ["chrome"]})
        assert wm.remove_process_name("chrome") is True
        assert wm.is_whitelisted({"pid": 1, "name": "chrome", "cmdline": ""}) is False

    def test_remove_process_name_not_found(self):
        wm = WhitelistManager({})
        assert wm.remove_process_name("chrome") is False

    def test_add_command_keyword(self):
        wm = WhitelistManager({})
        assert wm.add_command_keyword("python") is True
        assert wm.is_whitelisted({"pid": 1, "name": "x", "cmdline": "python"}) is True

    def test_add_command_keyword_duplicate(self):
        wm = WhitelistManager({"command_keywords": ["python"]})
        assert wm.add_command_keyword("python") is False

    def test_remove_command_keyword(self):
        wm = WhitelistManager({"command_keywords": ["python"]})
        assert wm.remove_command_keyword("python") is True

    def test_remove_command_keyword_not_found(self):
        wm = WhitelistManager({})
        assert wm.remove_command_keyword("python") is False

    def test_add_pid(self):
        wm = WhitelistManager({})
        assert wm.add_pid(123) is True
        assert wm.is_whitelisted({"pid": 123, "name": "", "cmdline": ""}) is True

    def test_add_pid_duplicate(self):
        wm = WhitelistManager({"pids": [123]})
        assert wm.add_pid(123) is False

    def test_remove_pid(self):
        wm = WhitelistManager({"pids": [123]})
        assert wm.remove_pid(123) is True

    def test_remove_pid_not_found(self):
        wm = WhitelistManager({})
        assert wm.remove_pid(123) is False


class TestGetAllAndClear:
    def test_get_all_sorted(self):
        wm = WhitelistManager({
            "process_names": ["zsh", "chrome", "apple"],
            "command_keywords": ["node", "go"],
            "pids": [300, 100, 200],
        })
        result = wm.get_all()
        assert result["process_names"] == ["apple", "chrome", "zsh"]
        assert result["command_keywords"] == ["go", "node"]
        assert result["pids"] == [100, 200, 300]

    def test_clear_pids(self):
        wm = WhitelistManager({"pids": [1, 2, 3]})
        wm.clear_pids()
        assert wm.get_all()["pids"] == []
        assert wm.is_whitelisted({"pid": 1, "name": "", "cmdline": ""}) is False


class TestThreadSafety:
    def test_concurrent_access(self):
        wm = WhitelistManager({})
        errors = []

        def add_and_check(n):
            try:
                for i in range(50):
                    wm.add_process_name(f"proc_{n}_{i}")
                    wm.is_whitelisted({"pid": 1, "name": f"proc_{n}_{i}", "cmdline": ""})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_and_check, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert len(wm.get_all()["process_names"]) == 200

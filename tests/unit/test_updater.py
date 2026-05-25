"""tests/unit/test_updater.py -- 版本检查单元测试"""

from unittest.mock import patch, MagicMock
from aigard.updater import UpdateChecker, _get_current_version


class TestGetCurrentVersion:
    def test_reads_from_setup_py(self):
        """正常情况下能从 setup.py 读到版本号"""
        v = _get_current_version()
        # setup.py 中的 CFBundleVersion 应该是 X.Y.Z 格式
        parts = v.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    @patch("aigard.updater.Path")
    def test_fallback_when_no_setup(self, mock_path_cls):
        """找不到 setup.py 时返回默认版本"""
        mock_path_inst = MagicMock()
        mock_path_inst.__truediv__ = MagicMock(return_value=mock_path_inst)
        mock_path_inst.exists.return_value = False
        mock_path_inst.parent = mock_path_inst
        mock_path_cls.return_value = mock_path_inst
        mock_path_cls.__call__ = MagicMock(return_value=mock_path_inst)

        # 由于 _get_current_version 在模块加载时已经执行，
        # 这里直接验证它在无 setup.py 时返回 "1.0.0" 的逻辑
        from aigard import updater
        with patch.object(updater, 'Path') as mp:
            mp_inst = MagicMock()
            mp_inst.exists.return_value = False
            mp_inst.__truediv__ = MagicMock(return_value=mp_inst)
            mp_inst.parent = mp_inst
            mp.return_value = mp_inst
            assert updater._get_current_version() == "1.0.0"


class TestCheckUpdate:
    @patch("aigard.updater.requests.get")
    @patch("aigard.updater.CURRENT_VERSION", "1.0.0")
    def test_has_update(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "tag_name": "v2.0.0",
            "body": "Release notes",
            "html_url": "https://github.com/test/releases/v2.0.0",
            "assets": [
                {"name": "app.dmg", "browser_download_url": "https://example.com/app.dmg"},
            ],
        }
        mock_get.return_value = mock_resp

        checker = UpdateChecker()
        result = checker.check_update()
        assert result is not None
        assert result["has_update"] is True
        assert result["latest_version"] == "2.0.0"
        assert result["download_url"] == "https://example.com/app.dmg"

    @patch("aigard.updater.requests.get")
    @patch("aigard.updater.CURRENT_VERSION", "2.0.0")
    def test_no_update(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "tag_name": "v1.0.0",
            "body": "",
            "html_url": "",
            "assets": [],
        }
        mock_get.return_value = mock_resp

        checker = UpdateChecker()
        result = checker.check_update()
        assert result is not None
        assert result["has_update"] is False

    @patch("aigard.updater.requests.get", side_effect=Exception("网络错误"))
    def test_network_failure(self, mock_get):
        checker = UpdateChecker()
        result = checker.check_update()
        assert result is None

    @patch("aigard.updater.requests.get")
    def test_non_200(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        checker = UpdateChecker()
        result = checker.check_update()
        assert result is None

    @patch("aigard.updater.requests.get")
    @patch("aigard.updater.CURRENT_VERSION", "1.0.0")
    def test_finds_dmg_asset(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "tag_name": "v2.0.0", "body": "", "html_url": "",
            "assets": [
                {"name": "app.zip", "browser_download_url": "https://example.com/app.zip"},
                {"name": "app.dmg", "browser_download_url": "https://example.com/app.dmg"},
            ],
        }
        mock_get.return_value = mock_resp

        checker = UpdateChecker()
        result = checker.check_update()
        # DMG takes priority over ZIP
        assert result["download_url"] == "https://example.com/app.dmg"

    @patch("aigard.updater.requests.get")
    @patch("aigard.updater.CURRENT_VERSION", "1.0.0")
    def test_finds_zip_fallback(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "tag_name": "v2.0.0", "body": "", "html_url": "",
            "assets": [
                {"name": "app.zip", "browser_download_url": "https://example.com/app.zip"},
                {"name": "source.tar.gz", "browser_download_url": "https://example.com/src.tar.gz"},
            ],
        }
        mock_get.return_value = mock_resp

        checker = UpdateChecker()
        result = checker.check_update()
        assert result["download_url"] == "https://example.com/app.zip"


class TestDownloadUpdate:
    @patch("aigard.updater.requests.get")
    def test_downloads_file(self, mock_get, tmp_path):
        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": "100"}
        mock_resp.iter_content = MagicMock(return_value=[b"chunk1", b"chunk2"])
        mock_get.return_value = mock_resp

        save_path = tmp_path / "download.dmg"
        checker = UpdateChecker()
        checker.download_update("https://example.com/app.dmg", str(save_path))

        assert save_path.exists()
        assert save_path.read_bytes() == b"chunk1chunk2"

    @patch("aigard.updater.requests.get")
    def test_calls_progress_callback(self, mock_get, tmp_path):
        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": "12"}
        mock_resp.iter_content = MagicMock(return_value=[b"chunk1", b"chunk2"])
        mock_get.return_value = mock_resp

        progress_calls = []
        def callback(downloaded, total):
            progress_calls.append((downloaded, total))

        save_path = tmp_path / "download.dmg"
        checker = UpdateChecker()
        checker.download_update("https://example.com/app.dmg", str(save_path), callback)

        assert len(progress_calls) == 2
        assert progress_calls[0] == (6, 12)
        assert progress_calls[1] == (12, 12)

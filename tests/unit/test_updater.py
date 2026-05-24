"""tests/unit/test_updater.py -- 版本检查单元测试"""

from unittest.mock import patch, MagicMock
from aigard.updater import UpdateChecker


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

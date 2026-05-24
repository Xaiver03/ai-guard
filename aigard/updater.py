"""aigard/updater.py - 自动更新检查模块

使用 GitHub Releases API 检查更新
"""
import requests
from packaging import version
from typing import Optional, Dict
import sys
from pathlib import Path

# 从 setup.py 读取当前版本
def _get_current_version() -> str:
    """从 setup.py 读取当前版本号"""
    try:
        setup_path = Path(__file__).parent.parent / "setup.py"
        if not setup_path.exists():
            # py2app 打包后，从 Resources 读取
            exe = Path(sys.executable)
            if "Contents/MacOS" in str(exe):
                resources = exe.parent.parent / "Resources"
                setup_path = resources / "setup.py"

        if setup_path.exists():
            content = setup_path.read_text()
            import re
            match = re.search(r'"CFBundleVersion":\s*"([0-9.]+)"', content)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"读取版本号失败: {e}")

    return "1.0.0"  # 默认版本

GITHUB_REPO = "Xaiver03/AI-Guard"  # 替换为实际的 GitHub 仓库
CURRENT_VERSION = _get_current_version()

class UpdateChecker:
    def __init__(self):
        self.api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    def check_update(self) -> Optional[Dict]:
        """检查是否有新版本

        Returns:
            Dict: {
                'has_update': bool,
                'latest_version': str,
                'download_url': str,
                'release_notes': str,
                'current_version': str
            }
        """
        try:
            resp = requests.get(self.api_url, timeout=5)
            if resp.status_code != 200:
                return None

            data = resp.json()
            latest = data['tag_name'].lstrip('v')

            # 比较版本
            has_update = version.parse(latest) > version.parse(CURRENT_VERSION)

            # 找到 .dmg 或 .zip 下载链接
            download_url = None
            for asset in data['assets']:
                if asset['name'].endswith('.dmg'):
                    download_url = asset['browser_download_url']
                    break
                elif asset['name'].endswith('.zip'):
                    download_url = asset['browser_download_url']

            return {
                'has_update': has_update,
                'latest_version': latest,
                'current_version': CURRENT_VERSION,
                'download_url': download_url,
                'release_notes': data.get('body', ''),
                'html_url': data.get('html_url', '')
            }

        except Exception as e:
            print(f"检查更新失败: {e}")
            return None

    def download_update(self, url: str, save_path: str, progress_callback=None):
        """下载更新文件

        Args:
            url: 下载链接
            save_path: 保存路径
            progress_callback: 进度回调函数 callback(downloaded, total)
        """
        resp = requests.get(url, stream=True, timeout=30)
        total = int(resp.headers.get('content-length', 0))
        downloaded = 0

        with open(save_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total)


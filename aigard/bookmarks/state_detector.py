"""
# [CN] 浏览器状态检测器
# [CN] 检测浏览器是否正在运行,提供修改建议
"""

import psutil
from typing import Dict, List, Optional, Any


class BrowserStateDetector:
    """浏览器状态检测器"""

    # 浏览器进程名称映射
    PROCESS_NAMES = {
        'chrome': ['Google Chrome', 'chrome', 'Google Chrome Helper'],
        'edge': ['Microsoft Edge', 'msedge', 'Microsoft Edge Helper'],
        'dia': ['Dia', 'dia', 'Dia Helper'],
        'safari': ['Safari', 'com.apple.Safari'],
        'quark': ['Quark', 'quark']
    }

    def is_browser_running(self, browser: str) -> bool:
        """
        检测浏览器是否正在运行

        Args:
            browser: 浏览器名称

        Returns:
            True 如果浏览器正在运行
        """
        process_names = self.PROCESS_NAMES.get(browser, [])

        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name']
                if any(pn in proc_name for pn in process_names):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return False

    def get_browser_processes(self, browser: str) -> List[Dict[str, Any]]:
        """
        获取浏览器相关的所有进程

        Returns:
            进程列表
        """
        process_names = self.PROCESS_NAMES.get(browser, [])
        processes = []

        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                proc_name = proc.info['name']
                if any(pn in proc_name for pn in process_names):
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'memory_mb': proc.info['memory_info'].rss / 1024 / 1024
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return processes

    def get_modification_strategy(self, browser: str) -> Dict[str, Any]:
        """
        获取修改策略

        Returns:
            策略字典,包含:
            - safe: 是否安全修改
            - action: 建议的操作
            - message: 提示信息
            - processes: 运行的进程列表
        """
        is_running = self.is_browser_running(browser)
        processes = self.get_browser_processes(browser) if is_running else []

        if is_running:
            browser_display_names = {
                'chrome': 'Chrome',
                'edge': 'Edge',
                'dia': 'Dia',
                'safari': 'Safari',
                'quark': 'Quark'
            }
            display_name = browser_display_names.get(browser, browser.title())

            return {
                'safe': False,
                'action': 'warn_user',
                'message': f'检测到 {display_name} 正在运行({len(processes)} 个进程)',
                'recommendation': f'建议关闭 {display_name} 后再修改书签',
                'processes': processes,
                'can_force': True,
                'force_warning': '强制修改可能导致:\n1. 修改被浏览器覆盖\n2. 需要重启浏览器才能生效\n3. 可能出现数据不一致'
            }
        else:
            return {
                'safe': True,
                'action': 'proceed',
                'message': '浏览器已关闭,可以安全修改',
                'recommendation': '修改完成后重新打开浏览器即可生效',
                'processes': [],
                'can_force': False,
                'force_warning': ''
            }

    def wait_for_browser_close(self, browser: str, timeout: int = 300) -> bool:
        """
        等待浏览器关闭

        Args:
            browser: 浏览器名称
            timeout: 超时时间(秒)

        Returns:
            True 如果浏览器已关闭
        """
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            if not self.is_browser_running(browser):
                return True
            time.sleep(2)

        return False

    def get_all_browsers_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有浏览器的状态

        Returns:
            浏览器状态字典
        """
        status = {}
        for browser in self.PROCESS_NAMES.keys():
            status[browser] = {
                'running': self.is_browser_running(browser),
                'processes': self.get_browser_processes(browser)
            }
        return status

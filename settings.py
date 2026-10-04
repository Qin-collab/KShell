"""
设置管理模块
使用 JSON 文件存储用户配置
"""

import json
import pathlib
from typing import Any, Optional

class SettingsManager:
    """设置管理器"""

    def __init__(self, config_path: str = "kshell_config.json"):
        self.config_path = pathlib.Path(config_path)
        self.settings = self._load_settings()

    def _load_settings(self) -> dict:
        """加载设置文件"""
        default_settings = self._get_default_settings()

        if not self.config_path.exists():
            # 如果配置文件不存在，创建默认配置文件
            self._save_settings(default_settings)
            return default_settings.copy()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # 合并默认设置，防止缺少某些键
                return {**default_settings, **loaded}
        except (json.JSONDecodeError, IOError):
            # 读取失败，返回默认设置
            return default_settings.copy()

    def _save_settings(self, settings: dict):
        """保存设置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Could not save settings: {e}")

    def _get_default_settings(self) -> dict:
        """获取默认设置"""
        return {
            "banner_enabled": True,
            "history_size": 1000,
            "prompt_style": "default",  # default, simple, poweruser
            "use_colors": True,
            "welcome_message": "Welcome to KShell!",
            "aliases": {},
            "environment": {},  # 自定义环境变量
            "theme": "default",  # 颜色主题
            # v2.0：内置命令优先于系统同名命令
            # True  = 内置优先（默认），用 command <cmd> 可强制执行系统版本
            # False = 系统命令优先，系统不存在时回退到内置
            "builtin_priority": True,
            # v2.1：插件系统
            #   enabled —— { "插件名": true/false }
            #   config  —— { "插件名": { "键": 值 } }
            #   dirs    —— 额外插件搜索目录（数组）
            "plugins": {
                "enabled": {},
                "config": {},
                "dirs": [],
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取设置值。

        支持点号路径（如 "plugins.enabled"）读取嵌套配置；
        若嵌套路径不存在，会回退查找同名的扁平键（兼容早期写法）。
        """
        if '.' in key:
            current = self.settings
            for part in key.split('.'):
                if not isinstance(current, dict) or part not in current:
                    # 回退：查找扁平的 "a.b" 键
                    return self.settings.get(key, default)
                current = current[part]
            return current
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        """设置值。key 含点号时写入嵌套结构（如 plugins.enabled）"""
        if '.' in key:
            parts = key.split('.')
            current = self.settings
            for part in parts[:-1]:
                nxt = current.get(part)
                if not isinstance(nxt, dict):
                    nxt = {}
                    current[part] = nxt
                current = nxt
            current[parts[-1]] = value
            # 清理可能存在的同名扁平键，避免两处数据不一致
            self.settings.pop(key, None)
        else:
            self.settings[key] = value
        self._save_settings(self.settings)

    def reset(self):
        """重置为默认设置"""
        self.settings = self._get_default_settings()
        self._save_settings(self.settings)

    def get_all(self) -> dict:
        """获取所有设置（不加载文件，直接返回内存）"""
        return self.settings.copy()

    def add_alias(self, name: str, command: str):
        """添加别名到配置文件"""
        if "aliases" not in self.settings:
            self.settings["aliases"] = {}
        self.settings["aliases"][name] = command
        self._save_settings(self.settings)

    def remove_alias(self, name: str):
        """从配置文件移除别名"""
        if "aliases" in self.settings and name in self.settings["aliases"]:
            del self.settings["aliases"][name]
            self._save_settings(self.settings)

    def get_aliases(self) -> dict:
        """获取持久化别名"""
        return self.settings.get("aliases", {})
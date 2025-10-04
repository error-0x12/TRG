import json
import os
from typing import Dict, Any, Callable, List

class ConfigManager:
    """配置管理器，用于保存和加载游戏设置"""
    
    def __init__(self, config_file: str = "game_config.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.default_config = {
            'music_volume': 0.7,
            'sfx_volume': 0.8,
            'music_delay': 150,
            'fps': 60,
            'key_bindings': {
                'track_0': 'd',
                'track_1': 'f',
                'track_2': 'j',
                'track_3': 'k',
                'pause': ' '
            },
            'autoplay': False,
            'debug_timer': False
        }
        
        # 回调系统
        self._callbacks: Dict[str, List[Callable]] = {}
    
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            配置字典
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 确保所有必需的键都存在
                    for key, value in self.default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except (json.JSONDecodeError, IOError):
                # 如果加载失败，返回默认配置
                return self.default_config
        else:
            # 如果配置文件不存在，返回默认配置
            return self.default_config
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        保存配置到文件
        
        Args:
            config: 配置字典
            
        Returns:
            保存是否成功
        """
        try:
            # 创建一个不包含autoplay和debug_timer设置的配置副本
            # 这样这些设置只会在同一游戏进程中保留，不同游戏进程不会保留
            config_to_save = config.copy()
            if 'autoplay' in config_to_save:
                del config_to_save['autoplay']
            if 'debug_timer' in config_to_save:
                del config_to_save['debug_timer']
                
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=4, ensure_ascii=False)
            
            # 触发设置更改回调
            self._trigger_callbacks('on_settings_changed', config)
            
            return True
        except IOError:
            return False
    
    def add_callback(self, event_name: str, callback: Callable) -> None:
        """
        添加事件回调
        
        Args:
            event_name (str): 事件名称
            callback (Callable): 回调函数
        """
        if event_name not in self._callbacks:
            self._callbacks[event_name] = []
        self._callbacks[event_name].append(callback)
    
    def _trigger_callbacks(self, event_name: str, *args, **kwargs) -> None:
        """
        触发指定事件的所有回调
        
        Args:
            event_name (str): 事件名称
            *args: 传递给回调的位置参数
            **kwargs: 传递给回调的关键字参数
        """
        if event_name in self._callbacks:
            for callback in self._callbacks[event_name]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    print(f"Error in callback for event {event_name}: {e}")
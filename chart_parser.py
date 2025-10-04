#!/usr/bin/env python3
"""
TRG (Terminal Rhythm Game) - 谱面解析器模块

这个模块负责解析.chart格式的谱面文件，将其转换为游戏引擎可以理解的数据结构。
"""

import os
import re
from typing import Dict, List, Any, Tuple
import logging
from enum import Enum

# 配置日志
# 创建logger实例
logger = logging.getLogger('TRG.ChartParser')
logger.setLevel(logging.INFO)

# 清除现有的处理器
if logger.handlers:
    logger.handlers.clear()

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 创建文件处理器
log_file = os.path.join(os.path.dirname(__file__), 'chart_log.log')
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)

# 设置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# 添加处理器到logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)


class NoteType(Enum):
    """音符类型枚举"""
    NORMAL = "normal"  # 普通音符
    HOLD = "hold"      # 长按音符
    DRAG = "drag"      # 拖动音符


class ChartParser:
    """谱面解析器类 - 用于解析.chart格式的谱面文件"""
    
    def __init__(self):
        """初始化谱面解析器"""
        self.reset()
    
    def reset(self):
        """
        重置解析器状态
        """
        self.metadata = {
            'id': '',  # 文件名作为唯一ID
            'title': '未知曲目',
            'maker': '未知作者',
            'song_maker': '未知',
            'difficulty_level': 0,
            'difficulty_name': 'EZ',
            'audio_file': '',
            'speed': 5.0,  # 默认速度：每秒5行
        }
        self.notes = []
        self.text_events = []
        self.current_time_ms = 0
        self.end_time_ms = None  # 谱面结束符的时间戳
    
    def parse_time_str(self, time_str: str) -> int:
        """
        解析时间字符串为毫秒
        
        Args:
            time_str (str): 时间字符串，格式为 "分:秒" 或 "分:秒:毫秒"
            
        Returns:
            int: 对应的毫秒数
        """
        parts = time_str.split(':')
        if len(parts) == 2:
            minutes, seconds = map(int, parts)
            milliseconds = 0
        elif len(parts) == 3:
            minutes, seconds, milliseconds = map(int, parts)
        else:
            logger.warning(f"Invalid time format: {time_str}")
            return 0
        
        return minutes * 60 * 1000 + seconds * 1000 + milliseconds
    
    def parse_chart_file(self, file_path: str) -> Dict[str, Any]:
        """
        解析.chart格式的谱面文件
        
        Args:
            file_path (str): 谱面文件路径
            
        Returns:
            Dict[str, Any]: 解析后的谱面数据，包含metadata和notes
        """
        try:
            # 重置解析器状态
            self.reset()
            
            # 提取文件名作为唯一ID
            self.metadata['id'] = os.path.splitext(os.path.basename(file_path))[0]
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 重置音符列表
            self.notes = []
            
            # 解析每一行
            for line_num, line in enumerate(lines, 1):
                # 去除注释和空白
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # 检查结束标记
                if line == '&':
                    logger.info(f"Reached end of chart at line {line_num}, current time: {self.current_time_ms}ms")
                    # 记录结束符的时间戳
                    self.end_time_ms = self.current_time_ms
                    break
                
                # 解析时间控制
                time_match = re.match(r'^(\d+:\d+(?::\d+)?)', line)
                if time_match:
                    time_str = time_match.group(1)
                    self.current_time_ms = self.parse_time_str(time_str)
                    # 分解时间字符串以便更详细的日志
                    parts = time_str.split(':')
                    if len(parts) == 2:
                        minutes, seconds = parts
                        milliseconds = '000'
                    else:
                        minutes, seconds, milliseconds = parts if len(parts) == 3 else (parts[0], parts[1], '000')
                    logger.debug(f"Set time to: {minutes}:{seconds}:{milliseconds} ({self.current_time_ms}ms) at line {line_num}")
                    continue
                
                # 解析初始化信息
                if self.parse_initialization_info(line):
                    continue
                
                # 解析音符和其他元素
                self.parse_chart_element(line)
            
            # 打印前几个音符的详细信息进行调试
            for i, note in enumerate(self.notes[:3]):
                logger.debug(f"Note {i+1}: type={note.get('type', 'unknown')}, track={note.get('track_index', -1)}, time={note.get('perfect_time', 0)}ms")
            
            # 构建返回的谱面数据
            chart_data = {
                'metadata': self.metadata,
                'notes': self.notes,
                'text_events': self.text_events,
                'end_time_ms': self.end_time_ms  # 添加结束符时间戳
            }
            
            logger.info(f"Successfully parsed chart file: {file_path}")
            logger.info(f"Found {len(self.notes)} notes and {len(self.text_events)} text events")
            return chart_data
            
        except Exception as e:
            logger.error(f"Failed to parse chart file {file_path}: {e}")
            return {'metadata': {'id': 'error', 'title': '解析错误'}, 'notes': [], 'text_events': []}
    
    def parse_initialization_info(self, line: str) -> bool:
        """
        解析初始化信息行
        
        Args:
            line (str): 一行文本
            
        Returns:
            bool: 是否成功解析为初始化信息
        """
        # 解析曲名
        if line.startswith('name-'):
            self.metadata['title'] = line[5:].strip()
            logger.info(f"Found title: {self.metadata['title']}")
            return True
        
        # 解析作者
        elif line.startswith('maker-'):
            parts = line[6:].split('-', 1)
            self.metadata['maker'] = parts[0].strip()
            if len(parts) > 1:
                self.metadata['song_maker'] = parts[1].strip()
            logger.info(f"Found maker: {self.metadata['maker']}, song maker: {self.metadata['song_maker']}")
            return True
        
        # 解析难度
        elif line.startswith('level-'):
            parts = line[6:].split('-', 1)
            try:
                # 检查难度名称是否有效
                valid_difficulty_names = ['EZ', 'HD', 'IN', 'AT', 'SP']
                
                if len(parts) > 1:
                    difficulty_name = parts[1].strip().upper()
                    # 检查难度名称是否在允许的列表中
                    if difficulty_name in valid_difficulty_names:
                        self.metadata['difficulty_name'] = difficulty_name
                        
                        # 对于SP难度，不对等级进行数字限制
                        if difficulty_name == 'SP':
                            # SP难度可以使用非数字等级
                            self.metadata['difficulty_level'] = parts[0].strip()
                        else:
                            # 其他难度必须是数字等级
                            self.metadata['difficulty_level'] = int(parts[0])
                    else:
                        logger.warning(f"Invalid difficulty name: {difficulty_name}. Must be one of: {', '.join(valid_difficulty_names)}")
                        # 使用默认值
                        self.metadata['difficulty_level'] = 1
                        self.metadata['difficulty_name'] = 'EZ'
                else:
                    # 如果没有提供难度名称，使用默认值
                    self.metadata['difficulty_level'] = int(parts[0])
                    self.metadata['difficulty_name'] = 'EZ'
            except ValueError:
                logger.warning(f"Invalid difficulty format: {line}. Level must be a number for non-SP difficulties")
                # 使用默认值
                self.metadata['difficulty_level'] = 1
                self.metadata['difficulty_name'] = 'EZ'
            
            logger.info(f"Found difficulty: {self.metadata['difficulty_level']} ({self.metadata['difficulty_name']})")
            return True
        
        # 解析音乐资源
        elif line.startswith('audio-'):
            # 确保移除'audio-'前缀
            audio_file = line[6:].strip()
            # 二次检查，确保不包含多个'audio-'前缀
            if audio_file.startswith('audio-'):
                audio_file = audio_file[6:].strip()
                logger.info(f"注意: 从音频文件名中移除重复的'audio-'前缀: {audio_file}")
            self.metadata['audio_file'] = audio_file
            logger.info(f"Found audio file: {self.metadata['audio_file']}")
            return True
        
        # 解析流速
        elif line.startswith('speed-') or line.startswith('line-'):
            try:
                # 支持两种格式：speed-和line-
                if line.startswith('speed-'):
                    speed_value = float(line[6:])
                else:
                    speed_value = float(line[5:])
                self.metadata['speed'] = speed_value
            except ValueError:
                logger.warning(f"Invalid speed format: {line}")
            logger.info(f"Found speed: {self.metadata['speed']} lines per second")
            return True
        
        return False
    
    def _calculate_judgment_time(self) -> int:
        """
        计算音符到达判定线的预计判定时间
        
        Returns:
            int: 预计的判定时间（毫秒）
        """
        # 获取游戏速度，默认为5.0行/秒
        speed = self.metadata.get('speed', 5.0)
        
        # 音符判定时间为放置时间
        judgment_time = self.current_time_ms
        
        # 记录计算过程，包含速度信息以便调试
        logger.debug(f"Calculated judgment time: placement={self.current_time_ms}ms, speed={speed} lines/s, total={judgment_time}ms")
        return judgment_time
    
    def parse_chart_element(self, line: str) -> None:
        """
        解析谱面元素（音符、文字等）
        
        Args:
            line (str): 一行文本
        """
        # 解析普通音符
        if line.startswith('tab-'):
            parts = line[4:].split('-')
            try:
                # 轨道编号从1开始，转换为0-based索引
                if len(parts) > 0:
                    track_index = int(parts[0]) - 1
                    if 0 <= track_index < 4:
                        # 计算音符的预计判定时间
                        perfect_time = self._calculate_judgment_time()
                        
                        note = {
                            'type': NoteType.NORMAL.value,
                            'track_index': track_index,
                            'perfect_time': perfect_time,
                            'placement_time': self.current_time_ms  # 保留原始放置时间用于参考
                        }
                        self.notes.append(note)
                        # 记录成功解析的音符信息
                        logger.debug(f"Parsed tab note: track={track_index}, placement_time={self.current_time_ms}ms, perfect_time={perfect_time}ms")
                    else:
                        logger.warning(f"Invalid track index {track_index + 1} in tab note: {line}")
                else:
                    logger.warning(f"Insufficient parameters in tab note: {line}")
            except ValueError as e:
                logger.warning(f"Invalid tab note format: {line}, error: {e}")
            return
        
        # 解析长按音符
        elif line.startswith('hold-'):
            parts = line[5:].split('-')
            try:
                if len(parts) > 0:
                    track_index = int(parts[0]) - 1
                    if 0 <= track_index < 4:
                        # 长按长度（行）转换为时间（毫秒）
                        # 假设每行占用的时间为 1000/speed 毫秒
                        duration_lines = 1.0  # 默认1行
                        if len(parts) > 1:
                            try:
                                duration_lines = float(parts[1])
                            except ValueError:
                                logger.warning(f"Invalid duration format in hold note: {line}")
                        
                        # 确保speed存在，否则使用默认值
                        speed = self.metadata.get('speed', 12.0)
                        duration_ms = int(duration_lines * 1000 / speed)
                        
                        # 计算音符的预计判定时间
                        perfect_time = self._calculate_judgment_time()
                        
                        note = {
                            'type': NoteType.HOLD.value,
                            'track_index': track_index,
                            'perfect_time': perfect_time,
                            'placement_time': self.current_time_ms,
                            'duration': duration_ms
                        }
                        self.notes.append(note)
                        logger.debug(f"Parsed hold note: track={track_index}, placement_time={self.current_time_ms}ms, perfect_time={perfect_time}ms, duration={duration_ms}ms")
                    else:
                        logger.warning(f"Invalid track index {track_index + 1} in hold note: {line}")
                else:
                    logger.warning(f"Insufficient parameters in hold note: {line}")
            except ValueError as e:
                logger.warning(f"Invalid hold note format: {line}, error: {e}")
            return
        
        # 解析拖动音符
        elif line.startswith('drag-'):
            parts = line[5:].split('-')
            try:
                if len(parts) > 0:
                    track_index = int(parts[0]) - 1
                    if 0 <= track_index < 4:
                        # 忽略目标轨道参数，drag音符不需要目标轨道
                        
                        # 计算音符的预计判定时间
                        perfect_time = self._calculate_judgment_time()
                        
                        note = {
                            'type': NoteType.DRAG.value,
                            'track_index': track_index,
                            'perfect_time': perfect_time,
                            'placement_time': self.current_time_ms  # 保留原始放置时间用于参考
                            # 移除drag_target参数
                        }
                        self.notes.append(note)
                        logger.debug(f"Parsed drag note: track={track_index}, placement_time={self.current_time_ms}ms, perfect_time={perfect_time}ms")
                    else:
                        logger.warning(f"Invalid track index {track_index + 1} in drag note: {line}")
                else:
                    logger.warning(f"Insufficient parameters in drag note: {line}")
            except ValueError as e:
                logger.warning(f"Invalid drag note format: {line}, error: {e}")
            return
        
        # 解析文字显示
        elif line.startswith('write-'):
            parts = line[6:].split('-')
            if len(parts) >= 2:
                try:
                    # 合并前n-1部分作为文字内容，最后一部分作为显示时间
                    text_content = '-'.join(parts[:-1])
                    display_time_ms = int(parts[-1]) * 1000  # 转换为毫秒
                    # 添加文字事件
                    self.text_events.append({
                        'content': text_content,
                        'start_time': self.current_time_ms,
                        'duration': display_time_ms
                    })
                    logger.debug(f"Parsed text event: '{text_content}', time={self.current_time_ms}ms, duration={display_time_ms}ms")
                except ValueError:
                    logger.warning(f"Invalid write format: {line}")
            return
        
        # 未知元素类型
        if line:
            logger.debug(f"Unknown chart element: {line}")


# 工具函数：获取charts目录下的所有谱面

def get_available_charts(charts_dir: str = None) -> List[Dict[str, Any]]:
    """
    获取charts目录下的所有可用谱面
    
    Args:
        charts_dir (str): charts目录路径，如果为None则使用主程序相同目录下的'charts'目录
        
    Returns:
        List[Dict[str, Any]]: 谱面信息列表
    """
    charts = []
    parser = ChartParser()
    
    # 如果没有提供charts_dir，则使用主程序相同目录下的charts文件夹
    if charts_dir is None:
        # 获取当前脚本的绝对路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建charts目录的绝对路径
        charts_dir = os.path.join(script_dir, 'charts')
    
    try:
        # 检查目录是否存在
        if not os.path.exists(charts_dir):
            logger.warning(f"Charts directory not found: {charts_dir}")
            return charts
        
        # 获取所有.chart文件
        for file_name in os.listdir(charts_dir):
            if file_name.endswith('.chart'):
                file_path = os.path.join(charts_dir, file_name)
                try:
                    # 解析谱面元数据
                    chart_data = parser.parse_chart_file(file_path)
                    metadata = chart_data['metadata']
                    
                    # 添加文件路径信息
                    chart_info = {
                        'id': metadata['id'],
                        'file_path': file_path,
                        'name': metadata['title'],  # UI管理器需要name字段
                        'title': metadata['title'],
                        'maker': metadata['maker'],
                        'song_maker': metadata['song_maker'],
                        'level': metadata['difficulty_level'],  # UI管理器需要level字段，对于SP难度可以是非数字
                        'bpm': 120,  # 默认为120BPM（可以从谱面中解析实际值）
                        'difficulty': f"{metadata['difficulty_level']} ({metadata['difficulty_name']})",
                        'audio_file': metadata['audio_file'],
                        'speed': metadata['speed'],
                        'note_count': len(chart_data['notes'])
                    }
                    
                    charts.append(chart_info)
                    logger.info(f"Found chart: {metadata['title']} ({file_name})")
                    
                except Exception as e:
                    logger.error(f"Failed to parse chart {file_name}: {e}")
        
        # 按标题排序
        charts.sort(key=lambda x: x['title'])
        
    except Exception as e:
        logger.error(f"Error getting available charts: {e}")
    
    return charts


# 工具函数：加载指定ID的谱面

def load_chart_by_id(chart_id: str, charts_dir: str = None) -> Dict[str, Any]:
    """
    通过ID加载指定的谱面
    
    Args:
        chart_id (str): 谱面ID（文件名不包含扩展名）
        charts_dir (str): charts目录路径，如果为None则使用主程序相同目录下的'charts'目录
        
    Returns:
        Dict[str, Any]: 解析后的谱面数据
    """
    parser = ChartParser()
    
    # 如果没有提供charts_dir，则使用主程序相同目录下的charts文件夹
    if charts_dir is None:
        # 获取当前脚本的绝对路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建charts目录的绝对路径
        charts_dir = os.path.join(script_dir, 'charts')
    
    file_path = os.path.join(charts_dir, f"{chart_id}.chart")
    
    if not os.path.exists(file_path):
        logger.error(f"Chart file not found: {file_path}")
        return {'metadata': {'id': 'not_found', 'title': '谱面不存在'}, 'notes': [], 'text_events': []}
    
    chart_data = parser.parse_chart_file(file_path)
    
    # 调整数据格式，确保与game_engine.py兼容
    # 提取metadata中的信息到顶层
    if 'metadata' in chart_data:
        metadata = chart_data['metadata']
        # 添加name字段（游戏引擎可能需要）
        chart_data['name'] = metadata.get('title', '未知曲目')
        # 添加audio字段（用于音频加载）
        audio_file = metadata.get('audio_file', '')
        # 确保音频文件名不包含'audio-'前缀
        if audio_file.startswith('audio-'):
            audio_file = audio_file[6:].strip()
            logger.info(f"注意: 从音频文件名中移除'audio-'前缀: {audio_file}")
        chart_data['audio'] = audio_file
        # 添加speed字段（用于流速控制）
        chart_data['speed'] = metadata.get('speed', 5.0)
        # 添加maker和song_maker字段
        chart_data['maker'] = metadata.get('maker', '未知作者')
        chart_data['song_maker'] = metadata.get('song_maker', '未知')
        # 添加难度信息
        chart_data['difficulty_level'] = metadata.get('difficulty_level', 0)
        chart_data['difficulty_name'] = metadata.get('difficulty_name', 'EZ')
    
    return chart_data
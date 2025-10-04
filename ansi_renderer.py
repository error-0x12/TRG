#!/usr/bin/env python3
"""
TRG (Terminal Rhythm Game) - ANSI渲染器模块

这个模块负责使用ANSI转义序列在终端中绘制游戏画面，包括背景、音符、判定线和用户界面元素。
"""

import os
import sys
from typing import Optional, Dict, List, Tuple
from game_engine import GameState, JudgementResult, NoteType


class ANSIRenderer:
    """ANSI渲染器类 - 使用ANSI转义序列在终端中绘制游戏画面"""
    
    # 颜色定义和配置 (使用ANSI颜色代码)
    COLOR_CODES = {
        'background': '',           # 默认背景色
        'foreground': '\033[37m',   # 白色
        'note_normal': '\033[32m',  # 绿色
        'note_hold': '\033[34m',    # 蓝色
        'judgement_perfect': '\033[32m',  # 绿色
        'judgement_great': '\033[36m',    # 青色
        'judgement_good': '\033[33m',     # 黄色
        'judgement_miss': '\033[31m',     # 红色
        'track': '\033[37m',        # 白色
        'combo': '\033[35m',        # 紫色
        'score': '\033[33m',        # 黄色
        'track_active': '\033[32m', # 绿色
        'judgement_line': '\033[31m', # 红色
        'debug': '\033[35m',        # 紫色
        'reset': '\033[0m',         # 重置颜色
    }
    
    # 字符配置
    CHAR_CONFIG = {
        'note_normal': '######',  # 普通音符字符
        'note_hold': '██████',    # 长按音符字符
        'note_drag': '$$$$$$',    # 拖动音符字符
        'note_hold_fill': '██████', # 长按音符填充字符
        'track_border': '|', # 轨道边界字符
        'judgement_line': '=', # 判定线字符
        'debug': '┼',       # 调试辅助线字符
    }
    
    def __init__(self, game_state: GameState):
        """
        初始化ANSI渲染器
        
        Args:
            game_state (GameState): 游戏状态对象的引用
        """
        self.game_state = game_state
        
        # 获取终端尺寸
        self.screen_height, self.screen_width = self._get_terminal_size()
        
        # 游戏区域配置
        self.num_tracks = 4  # 轨道数量
        self.judgement_line_y = self.screen_height - 5  # 判定线的y坐标
        
        # 动态计算轨道宽度和间距，使总宽度与屏幕宽度相等
        self._calculate_track_dimensions()
        
        # 音符配置
        self.note_visible_time = 2000  # 音符在屏幕上显示的总时间（毫秒）
        self.time_offset = 0  # 时间偏移量，用于微调音符显示位置（毫秒）
        
        # 判定窗口可视化配置
        self.show_judgement_windows = False  # 是否显示判定窗口范围
        
        # 缓存轨道位置信息
        self._cache_track_positions()
        
        # 屏幕缓冲区
        self.screen_buffer = [[' ' for _ in range(self.screen_width)] for _ in range(self.screen_height)]
        self.color_buffer = [[self.COLOR_CODES['reset'] for _ in range(self.screen_width)] for _ in range(self.screen_height)]
    
    def _get_terminal_size(self) -> Tuple[int, int]:
        """获取终端尺寸"""
        rows, columns = os.popen('stty size', 'r').read().split() if os.name != 'nt' else (24, 80)
        return int(rows), int(columns)
    
    def _calculate_track_dimensions(self) -> None:
        """动态计算轨道宽度和间距，使总宽度与屏幕宽度相等或相近"""
        # 确保屏幕宽度有效
        if self.screen_width <= 0:
            self.track_width = 6
            self.track_spacing = 5
            return
        
        # 计算可用总宽度（减去边界占用的字符）
        total_width_needed = self.screen_width - 5  # 留出一点余量
        
        # 计算轨道宽度：总宽度减去所有轨道间距后的平均宽度
        # 轨道间距数量 = 轨道数量 - 1
        spacing_count = self.num_tracks - 1
        
        # 每个轨道间距至少为1个字符
        min_spacing = 2
        available_track_width = total_width_needed - (spacing_count * min_spacing)
        
        # 计算每个轨道的宽度
        self.track_width = max(3, available_track_width // self.num_tracks)  # 确保每个轨道至少有3个字符宽
        
        # 重新计算轨道间距，使总宽度与屏幕宽度尽量接近
        actual_total_width = self.num_tracks * self.track_width
        remaining_space = total_width_needed - actual_total_width
        
        if spacing_count > 0:
            self.track_spacing = min_spacing + (remaining_space // spacing_count)
        else:
            self.track_spacing = 0
    
    def _cache_track_positions(self) -> None:
        """缓存轨道位置信息，提高渲染性能"""
        # 首先重新计算轨道尺寸
        self._calculate_track_dimensions()
        
        self.track_positions = []
        for i in range(self.num_tracks):
            track_left = i * (self.track_width + self.track_spacing)
            track_right = track_left + self.track_width - 1
            track_center = (track_left + track_right) // 2
            
            self.track_positions.append({
                'left': track_left,
                'right': track_right,
                'center': track_center,
                'inner_left': track_left + 1,
                'inner_right': track_right - 1
            })
    
    def _time_to_y_position(self, note_time: int) -> Optional[int]:
        """
        将音符时间戳映射到屏幕Y坐标
        
        实现原理：
        - 计算音符与当前时间的时间差
        - 根据时间差和谱面速度计算Y坐标
        - 谱面速度影响音符下落速度
        - 当时间差为负（已错过）时，不显示
        - 当时间差为0时，音符在判定线上
        - 当时间差为正（即将到达）时，音符在判定线上方
        
        Args:
            note_time (int): 音符的时间戳（毫秒）
            
        Returns:
            Optional[int]: 音符在屏幕上的Y坐标，如果不在可视范围内则返回None
        """
        # 计算时间差，应用时间偏移
        adjusted_note_time = note_time + self.time_offset
        time_diff = adjusted_note_time - self.game_state.current_time_ms
        
        # 如果音符已经错过判定窗口，则不显示
        if time_diff < -200:  # 200ms是MISS判定窗口
            return None
        
        # 计算可见范围（从顶部到底部判定线）
        visible_range = self.judgement_line_y - 1
        
        # 如果可见范围无效，返回None
        if visible_range <= 0:
            return None
        
        # 获取谱面速度设置，如果没有则使用默认值5.0
        chart_speed = getattr(self.game_state, 'speed', 5.0) if hasattr(self.game_state, 'speed') else 5.0
        
        # 设置一个基础预显示时间，但让流速影响音符的下落速度
        # 基础预显示时间为3秒，流速越高，音符下落越快
        base_pre_display_ms = 3000
        
        # 根据谱面速度调整预显示时间
        # 速度越高，预显示时间越短，音符下落越快
        pre_display_time_ms = int(base_pre_display_ms * (5.0 / chart_speed))
        
        # 计算音符应该出现的最早时间
        earliest_display_time = note_time - pre_display_time_ms
        
        # 如果当前时间还没到音符应该出现的时间，则不显示
        if self.game_state.current_time_ms < earliest_display_time:
            return None
        
        # 将时间差映射到屏幕Y坐标
        # 当时间差为pre_display_time_ms时，音符在屏幕顶部
        # 当时间差为0时，音符在判定线上
        progress = min(1.0, max(0.0, time_diff / pre_display_time_ms))
        y_pos = int(self.judgement_line_y - (progress * visible_range))
        
        # 确保Y坐标在有效范围内
        if y_pos < 0 or y_pos >= self.screen_height:
            return None
        
        return y_pos
    
    def _clear_screen_buffer(self) -> None:
        """清空屏幕缓冲区"""
        for y in range(self.screen_height):
            for x in range(self.screen_width):
                self.screen_buffer[y][x] = ' '
                self.color_buffer[y][x] = self.COLOR_CODES['reset']
    
    def _set_char(self, y: int, x: int, char: str, color: str = '') -> None:
        """
        在屏幕缓冲区中设置字符和颜色
        
        Args:
            y (int): Y坐标
            x (int): X坐标
            char (str): 要设置的字符
            color (str): ANSI颜色代码
        """
        if 0 <= y < self.screen_height and 0 <= x < self.screen_width:
            self.screen_buffer[y][x] = char
            self.color_buffer[y][x] = color
    
    def draw_background(self) -> None:
        """绘制游戏背景，包括4条固定轨道的边界"""
        # 绘制轨道背景和边界
        for i, track_pos in enumerate(self.track_positions):
            # 获取轨道颜色（如果轨道被激活则使用激活颜色）
            track_color = self.COLOR_CODES['track_active'] if (i < len(self.game_state.tracks) and self.game_state.tracks[i].activated) else self.COLOR_CODES['track']
            
            # 绘制轨道边界
            for y in range(self.screen_height):
                # 左边界
                self._set_char(y, track_pos['left'], self.CHAR_CONFIG['track_border'], track_color)
                # 右边界
                self._set_char(y, track_pos['right'], self.CHAR_CONFIG['track_border'], track_color)
    
    def draw_notes(self) -> None:
        """绘制当前活跃的音符"""
        for note in self.game_state.notes:
            # 计算音符的Y坐标
            y_pos = self._time_to_y_position(note.perfect_time)
            
            # 如果音符不在可视范围内，跳过
            if y_pos is None:
                continue
            
            # 获取轨道位置信息
            if note.track_index < 0 or note.track_index >= len(self.track_positions):
                continue  # 无效的轨道索引
            
            track_pos = self.track_positions[note.track_index]
            
            # 选择音符颜色和字符
            if note.type == NoteType.HOLD:
                color_code = self.COLOR_CODES['note_hold']
                note_char = self.CHAR_CONFIG['note_hold']
                fill_char = self.CHAR_CONFIG['note_hold_fill']
            elif note.type == NoteType.DRAG:
                color_code = self.COLOR_CODES['note_normal']
                note_char = self.CHAR_CONFIG['note_drag']
                fill_char = note_char
            else:
                color_code = self.COLOR_CODES['note_normal']
                note_char = self.CHAR_CONFIG['note_normal']
                fill_char = note_char
            
            # 计算音符在轨道中的显示
            if note.type == NoteType.HOLD:
                # 直接使用谱面定义的speed参数来计算hold音符长度
                # 获取游戏状态中的speed设置，如果没有则使用默认值6.0
                speed = getattr(self.game_state, 'speed', 6.0) if hasattr(self.game_state, 'speed') else 6.0
                
                # 直接根据音符时长和谱面speed计算应该渲染的行数
                # 音符时长转换为秒，乘以谱面speed（每秒行数）得到行数
                # 添加一个比例因子来调整长度，使其更符合预期
                scale_factor = 0.8  # 缩放因子，可根据需要调整
                if note.duration > 0:
                    # 音符时长（秒） × 谱面speed（行/秒） × 缩放因子 = 应该渲染的行数
                    note_height = max(1, int((note.duration / 1000.0) * speed * scale_factor))
                    # 设置最大行数限制，避免过长
                    max_height = min(10, self.judgement_line_y - 5)  # 最多10行或屏幕可见区域的一部分
                    note_height = min(note_height, max_height)
                else:
                    note_height = 1
                
                # 绘制HOLD音符的完整长度，实现颜色渐变效果
                for h in range(note_height):
                    current_y = y_pos - h
                    if current_y < 0:  # 确保不超出屏幕顶部
                        break
                    
                    # 计算颜色透明度（离初始音符越远，颜色越浅）
                    # 距离比例：h / note_height，0表示初始位置，1表示最远位置
                    distance_ratio = h / note_height if note_height > 1 else 0
                    # 根据距离调整颜色深浅
                    # 使用ANSI颜色的亮度控制（22m是默认亮度，2m是暗亮度）
                    # 越远越暗，使用不同的ANSI亮度代码
                    brightness_code = f'\033[2m' if distance_ratio > 0.3 else ''
                    
                    # 组合颜色代码
                    gradient_color = brightness_code + color_code
                    
                    for x in range(track_pos['inner_left'], track_pos['inner_right'] + 1):
                        self._set_char(current_y, x, note_char, gradient_color)
                
                # 如果是长按音符且已被击中，绘制已按住的部分（使用填充字符）
                if note.hit:
                    # 计算长按音符已按住部分的长度
                    hold_progress = min(note.held_time / note.duration, 1.0) if note.duration > 0 else 0.0
                    hold_height = int(hold_progress * note_height)
                    
                    # 绘制已按住的部分，同样应用颜色渐变
                    for h in range(hold_height):
                        hold_y = y_pos - h
                        if hold_y < 0:
                            break
                        
                        # 计算已按住部分的颜色透明度
                        distance_ratio = h / note_height if note_height > 1 else 0
                        brightness_code = f'\033[2m' if distance_ratio > 0.3 else ''
                        gradient_color = brightness_code + color_code
                        
                        for x in range(track_pos['inner_left'], track_pos['inner_right'] + 1):
                            self._set_char(hold_y, x, fill_char, gradient_color)
            else:
                # 普通音符和拖动音符显示完整的多字符样式
                # 计算起始位置，使音符居中显示在轨道内
                start_x = track_pos['center'] - (len(note_char) // 2)
                
                # 绘制每个字符，确保不超出轨道边界
                for i, char in enumerate(note_char):
                    x_pos = start_x + i
                    # 确保字符在轨道范围内
                    if track_pos['inner_left'] <= x_pos <= track_pos['inner_right']:
                        self._set_char(y_pos, x_pos, char, color_code)
    
    def draw_hud(self) -> None:
        """绘制游戏顶部的HUD（平视显示器），显示分数、连击数和上一次判定结果"""
        # 获取要显示的信息
        score = self.game_state.score
        combo = self.game_state.combo
        max_combo = self.game_state.max_combo
        judgement = self.game_state.judgement
        
        # 定义HUD元素
        hud_elements = [
            # 分数 - 左侧显示
            {'text': f"SCORE: {score:,}", 'x': 0, 'color': 'score'},
            # 连击数或AutoPlay - 居中显示
            {'text': f"AutoPlay: {combo} (MAX: {max_combo})" if hasattr(self.game_state, 'autoplay') and self.game_state.autoplay else f"COMBO: {combo} (MAX: {max_combo})", 'x': 'center', 'color': 'combo'},
        ]
        
        # 如果有判定结果，添加到HUD元素中（右侧显示）
        if judgement:
            hud_elements.append({
                'text': judgement.value,
                'x': 'right',
                'color': f'judgement_{judgement.value.lower()}'
            })
            
        # 如果启用了调试计时器，添加到HUD元素中
        if hasattr(self.game_state, 'debug_timer') and self.game_state.debug_timer:
            current_time = self.game_state.current_time_ms
            # 格式化时间为 分:秒.毫秒
            minutes = current_time // 60000
            seconds = (current_time % 60000) // 1000
            milliseconds = current_time % 1000
            timer_str = f"TIME: {minutes:02d}:{seconds:02d}.{milliseconds:03d}"
            hud_elements.append({
                'text': timer_str,
                'x': self.screen_width - len(timer_str) - 1,  # 右侧显示
                'color': 'debug'  # 使用调试颜色
            })
        
        # 绘制所有HUD元素
        for element in hud_elements:
            text = element['text']
            color = self.COLOR_CODES[element['color']]
            
            # 计算X坐标
            if element['x'] == 'center':
                x = max(0, (self.screen_width - len(text)) // 2)
            elif element['x'] == 'right':
                x = max(0, self.screen_width - len(text) - 1)
            else:
                x = max(0, min(element['x'], self.screen_width - len(text)))
            
            # 绘制文本
            for i, char in enumerate(text):
                if x + i < self.screen_width:
                    self._set_char(0, x + i, char, color)
    
    def draw_judgement_line(self) -> None:
        """绘制底部的判定线"""
        # 生成判定线字符串
        line_length = min(self.screen_width, self.num_tracks * (self.track_width + self.track_spacing) - self.track_spacing)
        judgement_line = self.CHAR_CONFIG['judgement_line'] * line_length
        
        # 绘制判定线
        color = self.COLOR_CODES['judgement_line']
        for i, char in enumerate(judgement_line):
            self._set_char(self.judgement_line_y, i, char, color)
    
    def draw_text_events(self) -> None:
        """绘制当前应该显示的文字事件"""
        if not hasattr(self.game_state, 'text_events'):
            return
        
        # 文字显示位置：判定线下方两行
        text_y = self.judgement_line_y + 2
        
        # 检查是否在有效范围内
        if text_y >= self.screen_height:
            return
        
        # 获取当前需要显示的文字事件
        current_texts = []
        for event in self.game_state.text_events:
            if event['start_time'] <= self.game_state.current_time_ms <= event['start_time'] + event['duration']:
                current_texts.append(event['content'])
        
        # 如果有多个文字事件，将它们合并显示
        if current_texts:
            display_text = ' '.join(current_texts)
            # 从终端最左侧开始显示文字
            text_x = 0
            
            # 首先清除该行的所有轨道分割线（用空格覆盖）
            for x in range(self.screen_width):
                self._set_char(text_y, x, ' ', self.COLOR_CODES['background'])
            
            # 绘制文字
            for i, char in enumerate(display_text):
                if text_x + i < self.screen_width:
                    self._set_char(text_y, text_x + i, char, self.COLOR_CODES['foreground'])
    
    def refresh(self) -> None:
        """刷新整个游戏画面"""
        try:
            # 重新获取屏幕尺寸（以防用户调整了终端窗口大小）
            new_height, new_width = self._get_terminal_size()
            
            # 如果屏幕尺寸发生变化，更新配置
            if new_height != self.screen_height or new_width != self.screen_width:
                self.screen_height, self.screen_width = new_height, new_width
                self.judgement_line_y = self.screen_height - 5  # 更新判定线位置
                self._cache_track_positions()  # 重新缓存轨道位置
                
                # 重新创建缓冲区
                self.screen_buffer = [[' ' for _ in range(self.screen_width)] for _ in range(self.screen_height)]
                self.color_buffer = [[self.COLOR_CODES['reset'] for _ in range(self.screen_width)] for _ in range(self.screen_height)]
            
            # 清空屏幕缓冲区
            self._clear_screen_buffer()
            
            # 绘制所有游戏元素
            self.draw_background()
            self.draw_notes()
            self.draw_judgement_line()
            self.draw_text_events()
            self.draw_hud()
            
            # 输出到终端
            self._render_to_terminal()
            
        except Exception as e:
            # 错误处理，确保程序不会崩溃
            pass
    
    def _render_to_terminal(self) -> None:
        """将屏幕缓冲区渲染到终端"""
        # 清屏
        sys.stdout.write('\033[2J\033[H')  # ANSI清屏和光标回到左上角
        
        # 渲染每一行
        for y in range(self.screen_height):
            line = ''
            current_color = ''
            for x in range(self.screen_width):
                char_color = self.color_buffer[y][x]
                if char_color != current_color:
                    line += char_color
                    current_color = char_color
                line += self.screen_buffer[y][x]
            
            # 输出行并重置颜色
            sys.stdout.write(line + self.COLOR_CODES['reset'] + '\n')
        
        # 刷新输出
        sys.stdout.flush()
    
    def draw_game_result(self, perfect: int, good: int, miss: int, accuracy: float, score: int, max_combo: int, autoplay: bool = False) -> None:
        """
        绘制结算界面
        
        Args:
            perfect (int): Perfect判定数量
            good (int): Good判定数量
            miss (int): Miss判定数量
            accuracy (float): 准确率
            score (int): 分数
            max_combo (int): 最大连击数
            autoplay (bool): 是否启用了自动判定模式
        """
        # 清空屏幕缓冲区
        self._clear_screen_buffer()
        
        # 绘制标题 - 根据autoplay状态显示不同的标题
        title = "AutoPlay" if autoplay else "游戏结算"
        title_color = self.COLOR_CODES['combo']
        title_x = max(0, (self.screen_width - len(title)) // 2)
        title_y = 2
        
        for i, char in enumerate(title):
            self._set_char(title_y, title_x + i, char, title_color)
        
        # 绘制分隔线
        separator = "=" * min(self.screen_width, 40)
        separator_x = max(0, (self.screen_width - len(separator)) // 2)
        separator_y = title_y + 2
        
        for i, char in enumerate(separator):
            self._set_char(separator_y, separator_x + i, char, title_color)
        
        # 绘制各项数据
        result_items = [
            f"Score: {score:,}",
            f"Max Combo: {max_combo}",
            f"Perfect: {perfect}",
            f"Good: {good}",
            f"Miss: {miss}",
            f"Accuracy: {accuracy:.2f}%"
        ]
        
        # 计算数据起始位置
        data_start_y = separator_y + 2
        data_color = self.COLOR_CODES['score']
        
        # 绘制每一项数据
        for i, item in enumerate(result_items):
            item_x = max(0, (self.screen_width - len(item)) // 2)
            item_y = data_start_y + i
            
            for j, char in enumerate(item):
                self._set_char(item_y, item_x + j, char, data_color)
        
        # 绘制提示信息
        hint = "Press ENTER to return to main menu"
        hint_color = self.COLOR_CODES['foreground']
        hint_x = max(0, (self.screen_width - len(hint)) // 2)
        hint_y = min(self.screen_height - 2, data_start_y + len(result_items) + 2)
        
        for i, char in enumerate(hint):
            self._set_char(hint_y, hint_x + i, char, hint_color)
        
        # 输出到终端
        self._render_to_terminal()
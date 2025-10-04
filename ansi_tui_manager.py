#!/usr/bin/env python3
"""
TRG (Terminal Rhythm Game) - ANSI TUI管理器模块

这个模块负责管理游戏的终端用户界面，使用ANSI转义序列绘制界面元素。
"""

import os
import sys
import re
from typing import Dict, List, Optional, Callable


class ANSITUIManager:
    """ANSI TUI管理器类 - 负责管理游戏的所有终端用户界面"""
    
    # 颜色定义 (使用ANSI颜色代码)
    COLOR_CODES = {
        'background': '',           # 默认背景色
        'foreground': '\033[37m',   # 白色
        'highlight': '\033[33m',    # 黄色
        'title': '\033[36m',        # 青色
        'info': '\033[32m',         # 绿色
        'error': '\033[31m',        # 红色
        'success': '\033[32m',      # 绿色
        'menu_item': '\033[37m',    # 白色
        'menu_selected': '\033[30;47m',  # 黑色文字，白色背景
        'reset': '\033[0m',         # 重置颜色
    }
    
    # ASCII艺术字 - TRG
    TRG_ASCII_ART = [
        "███████╗██████╗  ██████╗",
        "╚══██╔══╝██╔══██╗██╔════╝",
        "   ██║   ██████╔╝██║  ███╗",
        "   ██║   ██╔══██╗██║   ██║",
        "   ██║   ██║  ██║╚██████╔╝",
        "   ╚═╝   ╚═╝  ╚═╝ ╚═════╝"
    ]
    
    # 界面状态枚举
    class UIState:
        MAIN_MENU = 0
        GAME_PLAY = 1
        GAME_PAUSED = 2
        GAME_RESULT = 3
        SETTINGS = 4
    
    def __init__(self, settings: Optional[Dict] = None):
        """
        初始化ANSI TUI管理器
        
        Args:
            settings: 游戏设置字典
        """
        # 获取终端尺寸
        self.screen_height, self.screen_width = self._get_terminal_size()
        
        # 设置初始UI状态
        self.current_state = self.UIState.MAIN_MENU
        
        # 设置相关属性
        self.settings = settings if settings else {
            'music_volume': 0.7,      # 音乐音量 (0.0-1.0)
            'sfx_volume': 0.8,        # 音效音量 (0.0-1.0)
            'music_delay': 150,         # 音乐延迟 (ms, -1000 到 1000)
            'fps': 60,                # 帧率 (30, 60, 120, 144)
            'key_bindings': {         # 按键绑定
                'track_0': 'd',
                'track_1': 'f',
                'track_2': 'j',
                'track_3': 'k',
                'pause': ' '
            },
            'autoplay': False         # 自动判定模式
        }
        
        # 设置界面选项
        self.setting_options = [
            "音乐音量",
            "音效音量",
            "音乐延迟",
            "帧率设置",
            "AutoPlay",
            "调试计时器",
            "按键绑定 - 轨道0 (D)",
            "按键绑定 - 轨道1 (F)",
            "按键绑定 - 轨道2 (J)",
            "按键绑定 - 轨道3 (K)",
            "按键绑定 - 暂停 (空格)",
            "清空成绩",
            "返回主菜单"
        ]
        
        # 初始化设置选项的值显示格式
        self._update_setting_value_formats()
        
        # 清空成绩确认状态
        self.confirming_clear_scores = False
        
        # 初始化自动判定状态
        self.autoplay_enabled = self.settings.get('autoplay', False)
        
        # 选谱菜单状态
        self.selected_chart_index = 0
        self.current_page = 0
        self.charts_per_page = 4  # 修改为每页最多4个条目
        self.available_charts = []
        
        # 设置界面选项
        self.selected_setting_option = 0  # 当前选中的设置选项
        
        # 暂停菜单选项
        self.pause_menu_options = [
            "继续游戏",
            "重新开始",
            "返回主菜单"
        ]
        self.selected_pause_option = 0
        
        # 结算界面数据
        self.game_result_data = {
            'score': 0,
            'perfect': 0,
            'good': 0,
            'miss': 0,
            'max_combo': 0,
            'accuracy': 0.0
        }
        
        # 回调函数
        self.on_chart_select = None  # 选择谱面的回调
        self.on_pause_action = None  # 暂停菜单操作的回调
        self.on_settings_changed = None  # 设置更改的回调
        self.on_result_action = None  # 结算界面操作的回调
    
    def _get_terminal_size(self) -> tuple:
        """获取终端尺寸"""
        try:
            rows, columns = os.popen('stty size', 'r').read().split() if os.name != 'nt' else (24, 80)
            return int(rows), int(columns)
        except:
            return 24, 80  # 默认尺寸
    
    def _update_setting_value_formats(self) -> None:
        """
        更新设置选项的值显示格式
        """
        self.setting_value_formats = [
            lambda: f"{self.settings['music_volume']:.1f}",
            lambda: f"{self.settings['sfx_volume']:.1f}",
            lambda: f"{self.settings.get('music_delay', 0)}ms",
            lambda: f"{self.settings['fps']} FPS",
            lambda: "开启" if self.settings.get('autoplay', False) else "关闭",
            lambda: "开启" if self.settings.get('debug_timer', False) else "关闭",
            lambda: f"[{self.settings['key_bindings']['track_0']}]",
            lambda: f"[{self.settings['key_bindings']['track_1']}]",
            lambda: f"[{self.settings['key_bindings']['track_2']}]",
            lambda: f"[{self.settings['key_bindings']['track_3']}]",
            lambda: f"[{self.settings['key_bindings']['pause']}]",
            lambda: "确认清空" if self.confirming_clear_scores else "警告！",
            lambda: ""
        ]
    
    def _adjust_setting_value(self, option_index: int, direction: int) -> None:
        """
        调整设置选项的值
        
        Args:
            option_index: 选项索引
            direction: 调整方向 (-1 减少, 1 增加)
        """
        if option_index == 0:  # 音乐音量
            self.settings['music_volume'] = max(0.0, min(1.0, self.settings['music_volume'] + 0.1 * direction))
        elif option_index == 1:  # 音效音量
            self.settings['sfx_volume'] = max(0.0, min(1.0, self.settings['sfx_volume'] + 0.1 * direction))
        elif option_index == 2:  # 音乐延迟（每10ms为步长，范围-1000到1000）
            current_delay = self.settings.get('music_delay', 0)
            new_delay = current_delay + 10 * direction
            self.settings['music_delay'] = max(-1000, min(1000, new_delay))
        elif option_index == 3:  # 帧率设置
            fps_options = [30, 60, 120, 144]
            current_fps_index = fps_options.index(self.settings['fps']) if self.settings['fps'] in fps_options else 1
            new_fps_index = max(0, min(len(fps_options) - 1, current_fps_index + direction))
            self.settings['fps'] = fps_options[new_fps_index]
        elif option_index == 4:  # 自动判定模式
            # 切换自动判定模式状态
            self.settings['autoplay'] = not self.settings.get('autoplay', False)
            self.autoplay_enabled = self.settings['autoplay']
        elif option_index in [5, 6, 7, 8, 9]:  # 按键绑定
            # 按键绑定需要特殊处理，这里暂时不实现修改功能
            pass
            
        # 通知设置已更改
        self._notify_settings_changed()
        
    def _notify_settings_changed(self) -> None:
        """
        通知设置已更改
        """
        if self.on_settings_changed:
            self.on_settings_changed(self.settings)
    
    def set_charts(self, charts: List[Dict[str, str]]) -> None:
        """
        设置可用的谱面列表
        
        Args:
            charts (List[Dict[str, str]]): 谱面列表，每个谱面包含name、maker、level等信息
        """
        self.available_charts = charts
        self.selected_chart_index = 0
        self.current_page = 0
    
    def _get_visible_charts(self) -> List[Dict[str, str]]:
        """
        获取当前页面可见的谱面
        
        Returns:
            List[Dict[str, str]]: 当前页面可见的谱面列表
        """
        start_idx = self.current_page * self.charts_per_page
        end_idx = start_idx + self.charts_per_page
        return self.available_charts[start_idx:end_idx]
    
    def previous_chart_page(self) -> None:
        """翻到上一页谱面"""
        if self.current_page > 0:
            self.current_page -= 1
            # 更新选中的索引到当前页面的第一个，方便用户连续翻页浏览
            self.selected_chart_index = 0
    
    def next_chart_page(self) -> None:
        """翻到下一页谱面"""
        total_pages = max(1, (len(self.available_charts) + self.charts_per_page - 1) // self.charts_per_page)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            # 更新选中的索引到当前页面的第一个
            self.selected_chart_index = 0
    
    def _draw_trg_title(self, y: int, x: int) -> None:
        """
        绘制TRG标题ASCII艺术字
        
        Args:
            y (int): 起始Y坐标
            x (int): 起始X坐标
        """
        for i, line in enumerate(self.TRG_ASCII_ART):
            # 确保不会超出屏幕边界
            if y + i < self.screen_height:
                # 居中显示标题
                title_x = max(0, x)
                # 输出带颜色的标题行
                self._print_at(y + i, title_x, self.COLOR_CODES['title'] + line + self.COLOR_CODES['reset'])
    
    def _print_at(self, y: int, x: int, text: str) -> None:
        """
        在指定位置打印文本
        
        Args:
            y (int): Y坐标
            x (int): X坐标
            text (str): 要打印的文本
        """
        if 0 <= y < self.screen_height:
            # 移动光标到指定位置并打印文本
            sys.stdout.write(f"\033[{y + 1};{x + 1}H{text}")
    
    def _clear_screen(self) -> None:
        """清屏"""
        sys.stdout.write('\033[2J\033[H')  # ANSI清屏和光标回到左上角
    
    def draw_main_menu(self, save_manager=None) -> None:
        """绘制主菜单界面"""
        # 清屏
        self._clear_screen()
        
        # 绘制TRG标题在右上角
        title_y = 2
        title_x = max(0, self.screen_width - len(self.TRG_ASCII_ART[0]) - 2)
        self._draw_trg_title(title_y, title_x)
        
        # 绘制谱面列表在右侧
        charts_start_x = max(0, self.screen_width - 40)  # 谱面列表起始X坐标
        charts_y = title_y + len(self.TRG_ASCII_ART) + 2
        visible_charts = self._get_visible_charts()
        
        # 绘制谱面列表标题
        list_title = "谱面列表"
        list_title_x = max(0, charts_start_x + (40 - len(list_title)) // 2)
        self._print_at(charts_y - 1, list_title_x, self.COLOR_CODES['title'] + list_title + self.COLOR_CODES['reset'])
        
        # 绘制谱面列表
        for i, chart in enumerate(visible_charts):
            y_pos = charts_y + i
            if y_pos >= self.screen_height - 10:  # 为底部帮助信息和选中谱面详情留出更多空间
                break
                
            # 选择颜色（选中的谱面使用高亮色）
            color = self.COLOR_CODES['menu_selected'] if i == self.selected_chart_index else self.COLOR_CODES['menu_item']
            
            # 格式化谱面信息
            chart_info = f"{chart['name']:<20}"
            self._print_at(y_pos, charts_start_x, color + chart_info + self.COLOR_CODES['reset'])
            
            # 显示等级
            # 从chart中获取难度等级和名称信息
            level = chart['level']
            # 尝试从difficulty字段中提取难度名称，如果没有则使用默认值
            difficulty_name = "未知"
            if 'difficulty' in chart:
                # difficulty字段格式为 "等级 (难度名称)"
                match = re.search(r'\(([^)]+)\)', chart['difficulty'])
                if match:
                    difficulty_name = match.group(1)
            # 格式化为 "难度名称-等级"
            level_text = f"{difficulty_name}-{level}"
            self._print_at(y_pos, charts_start_x + 25, color + level_text + self.COLOR_CODES['reset'])
            
            # 如果有最高成绩，显示等级在选项旁边
            if save_manager and 'id' in chart:
                best_score = save_manager.get_best_score_raw(chart['id'])
                if best_score and 'grade' in best_score:
                    grade_text = f"[{best_score['grade']}]"
                    self._print_at(y_pos, charts_start_x + 35, color + grade_text + self.COLOR_CODES['reset'])
        
        # 绘制选中谱面的详细信息
            if visible_charts and 0 <= self.selected_chart_index < len(visible_charts):
                selected_chart = visible_charts[self.selected_chart_index]
                # 调整info_y计算方式，确保有足够空间显示信息
                info_y = min(charts_y + len(visible_charts) + 1, self.screen_height - 5)  # 确保至少保留5行空间
                
                try:
                    # 简化详细信息显示，适应不同屏幕尺寸
                    # 获取难度信息
                    level = selected_chart['level']
                    difficulty_name = "未知"
                    if 'difficulty' in selected_chart:
                        match = re.search(r'\(([^)]+)\)', selected_chart['difficulty'])
                        if match:
                            difficulty_name = match.group(1)
                    # 格式化为 "难度名称-等级"
                    level_text = f"{difficulty_name}-{level}"
                    basic_info_text = f"选中: {selected_chart['name']} | {level_text}"
                    self._print_at(info_y, charts_start_x, self.COLOR_CODES['info'] + basic_info_text + self.COLOR_CODES['reset'])
                    
                    # 添加更多基本信息（如果有空间）
                    if info_y + 1 < self.screen_height - 4:
                        maker_info_text = f"谱面: {selected_chart['maker']} | 音乐: {selected_chart.get('song_maker', '未知')}"
                        self._print_at(info_y + 1, charts_start_x, self.COLOR_CODES['info'] + maker_info_text + self.COLOR_CODES['reset'])
                    
                    # 显示最高成绩（如果有空间）
                    if save_manager and info_y + 2 < self.screen_height - 3:
                        chart_id = selected_chart.get('id', '')
                        try:
                            best_score = save_manager.get_best_score_raw(chart_id)
                            
                            # 应用颜色到文本
                            self._print_at(info_y + 2, charts_start_x, self.COLOR_CODES['highlight'] + "最高成绩:" + self.COLOR_CODES['reset'])
                            if best_score:
                                score = best_score.get('score', 0)
                                grade = best_score.get('grade', '无')
                                
                                # 格式化分数显示
                                formatted_score = f"{score:,}"  # 添加千位分隔符
                                
                                # 只显示总分和等级
                                self._print_at(info_y + 3, charts_start_x, self.COLOR_CODES['highlight'] + f"{grade} - {formatted_score}" + self.COLOR_CODES['reset'])
                            else:
                                self._print_at(info_y + 3, charts_start_x, self.COLOR_CODES['foreground'] + "暂无成绩记录" + self.COLOR_CODES['reset'])
                        except Exception as e:
                            # 如果获取成绩出错，仍然显示基本信息
                            pass
                except Exception as e:
                    # 即使发生错误，也尝试显示最基本的选中信息
                    try:
                        self._print_at(info_y, charts_start_x, self.COLOR_CODES['info'] + f"选中: {selected_chart['name']}" + self.COLOR_CODES['reset'])
                    except:
                        pass
        
        # 绘制翻页指示器
        total_pages = max(1, (len(self.available_charts) + self.charts_per_page - 1) // self.charts_per_page)
        if total_pages > 1:
            page_info_y = info_y + 4  # 在详细信息下方显示页码
            if page_info_y < self.screen_height - 3:
                page_text = f"页码: {self.current_page + 1}/{total_pages}"
                page_x = max(0, charts_start_x)
                self._print_at(page_info_y, page_x, self.COLOR_CODES['highlight'] + page_text + self.COLOR_CODES['reset'])
        
        # 绘制底部帮助信息
        help_y = self.screen_height - 2
        if help_y > 0:
            help_text = "上下方向键:选择谱面 | 左右方向键:翻页 | 回车键:开始游戏 | ESC键:退出 | DEL键:设置"
            help_x = max(0, (self.screen_width - len(help_text)) // 2)
            self._print_at(help_y, help_x, self.COLOR_CODES['foreground'] + help_text + self.COLOR_CODES['reset'])
        
        # 刷新输出
        sys.stdout.flush()
    
    def draw_game_result(self) -> None:
        """绘制游戏结算界面"""
        # 清屏
        self._clear_screen()
        
        # 绘制标题 - 根据autoplay状态显示不同的标题
        if self.autoplay_enabled:
            title_text = "AutoPlay"
        else:
            title_text = "游戏结算"
        title_y = 2
        title_x = max(0, (self.screen_width - len(title_text)) // 2)
        self._print_at(title_y, title_x, self.COLOR_CODES['title'] + title_text + self.COLOR_CODES['reset'])
        
        # 获取等级
        grade = self._get_grade_by_score(self.game_result_data['score'])
        
        # 绘制结算信息
        result_y = title_y + 3
        
        # 总成绩（等级和分数）
        score_text = f"总成绩: {grade} - {self.game_result_data['score']:,} "
        score_x = max(0, (self.screen_width - len(score_text)) // 2)
        self._print_at(result_y, score_x, self.COLOR_CODES['highlight'] + score_text + self.COLOR_CODES['reset'])
        
        # 判定统计
        stats_y = result_y + 2
        stats = [
            f"Perfect: {self.game_result_data['perfect']}",
            f"Good: {self.game_result_data['good']}",
            f"Bad: {self.game_result_data['bad']}",
            f"Miss: {self.game_result_data['miss']}",
            f"最大连击: {self.game_result_data['max_combo']}",
            f"准确率: {self.game_result_data['accuracy']:.2f}%"
        ]
        
        for i, stat in enumerate(stats):
            stat_y = stats_y + i
            if stat_y < self.screen_height - 3:  # 为底部帮助信息留出空间
                stat_x = max(0, (self.screen_width - len(stat)) // 2)
                self._print_at(stat_y, stat_x, self.COLOR_CODES['info'] + stat + self.COLOR_CODES['reset'])
        
        # 绘制底部帮助信息
        help_y = self.screen_height - 2
        if help_y > 0:
            help_text = "按回车键返回主界面"
            help_x = max(0, (self.screen_width - len(help_text)) // 2)
            self._print_at(help_y, help_x, self.COLOR_CODES['foreground'] + help_text + self.COLOR_CODES['reset'])
        
        # 刷新输出
        sys.stdout.flush()
    
    def draw_settings(self) -> None:
        """绘制设置界面"""
        # 清屏
        self._clear_screen()
        
        # 绘制标题
        title_text = "游戏设置"
        title_y = 1
        title_x = max(0, (self.screen_width - len(title_text)) // 2)
        self._print_at(title_y, title_x, self.COLOR_CODES['title'] + title_text + self.COLOR_CODES['reset'])
        
        # 检查是否处于确认清空成绩状态
        if self.confirming_clear_scores:
            # 显示二次确认界面
            confirm_y = self.screen_height // 2 - 3
            confirm_text = "⚠️  警告：清空所有成绩 ⚠️"
            confirm_x = max(0, (self.screen_width - len(confirm_text)) // 2)
            self._print_at(confirm_y, confirm_x, self.COLOR_CODES['error'] + confirm_text + self.COLOR_CODES['reset'])
            
            # 确认提示
            prompt1 = "此操作将删除所有谱面的最高分记录"
            prompt2 = "此操作不可撤销！"
            prompt1_x = max(0, (self.screen_width - len(prompt1)) // 2)
            prompt2_x = max(0, (self.screen_width - len(prompt2)) // 2)
            self._print_at(confirm_y + 2, prompt1_x, self.COLOR_CODES['highlight'] + prompt1 + self.COLOR_CODES['reset'])
            self._print_at(confirm_y + 3, prompt2_x, self.COLOR_CODES['error'] + prompt2 + self.COLOR_CODES['reset'])
            
            # 操作提示，包含具体的确认键
            confirm_key = getattr(self, 'clear_scores_confirm_key', '?')
            action1 = f"是：请按[{confirm_key}]"
            action2 = "否：请按[0]"
            action1_x = max(0, (self.screen_width - len(action1)) // 2)
            action2_x = max(0, (self.screen_width - len(action2)) // 2)
            self._print_at(confirm_y + 5, action1_x, self.COLOR_CODES['info'] + action1 + self.COLOR_CODES['reset'])
            self._print_at(confirm_y + 6, action2_x, self.COLOR_CODES['info'] + action2 + self.COLOR_CODES['reset'])
            
            # 底部帮助信息
            help_y = self.screen_height - 2
            if help_y > 0:
                help_text = "按ESC键也可取消操作"
                help_x = max(0, (self.screen_width - len(help_text)) // 2)
                self._print_at(help_y, help_x, self.COLOR_CODES['foreground'] + help_text + self.COLOR_CODES['reset'])
        else:
            # 正常显示设置选项
            # 绘制设置选项
            options_start_y = title_y + 2
            for i, option in enumerate(self.setting_options):
                y_pos = options_start_y + i
                if y_pos >= self.screen_height - 2:  # 为底部帮助信息留出空间
                    break
                    
                # 选择颜色（选中的选项使用高亮色）
                color = self.COLOR_CODES['menu_selected'] if i == self.selected_setting_option else self.COLOR_CODES['menu_item']
                
                # 为清空成绩选项添加特殊颜色
                if i == 9:  # 清空成绩选项
                    color = self.COLOR_CODES['error'] if i == self.selected_setting_option else color
                
                # 获取选项值
                try:
                    value = self.setting_value_formats[i]()
                except:
                    value = ""
                
                # 格式化显示
                display_text = f"{option:<30} {value}"
                self._print_at(y_pos, 4, color + display_text + self.COLOR_CODES['reset'])
            
            # 绘制底部帮助信息
            help_y = self.screen_height - 2
            if help_y > 0:
                help_text = "上下键选择选项, 左右键调整参数, Enter确认, ESC返回主界面"
                help_x = max(0, (self.screen_width - len(help_text)) // 2)
                self._print_at(help_y, help_x, self.COLOR_CODES['foreground'] + help_text + self.COLOR_CODES['reset'])
        
        # 刷新输出
        sys.stdout.flush()
    
    def draw_game_paused(self) -> None:
        """绘制游戏暂停界面"""
        # 清屏
        self._clear_screen()
        
        # 绘制暂停标题
        pause_text = "游戏已暂停"
        title_y = self.screen_height // 2 - 3
        title_x = max(0, (self.screen_width - len(pause_text)) // 2)
        self._print_at(title_y, title_x, self.COLOR_CODES['title'] + pause_text + self.COLOR_CODES['reset'])
        
        # 绘制暂停菜单选项
        menu_start_y = title_y + 2
        for i, option in enumerate(self.pause_menu_options):
            y_pos = menu_start_y + i
            if y_pos >= self.screen_height:
                break
                
            # 选择颜色（选中的选项使用高亮色）
            color = self.COLOR_CODES['menu_selected'] if i == self.selected_pause_option else self.COLOR_CODES['menu_item']
            
            # 居中显示选项
            option_x = max(0, (self.screen_width - len(option)) // 2)
            self._print_at(y_pos, option_x, color + option + self.COLOR_CODES['reset'])
        
        # 绘制底部帮助信息
        help_y = self.screen_height - 2
        if help_y > 0:
            help_text = "使用 W/S 键或上下方向键选择选项, 回车键确认"
            help_x = max(0, (self.screen_width - len(help_text)) // 2)
            self._print_at(help_y, help_x, self.COLOR_CODES['foreground'] + help_text + self.COLOR_CODES['reset'])
        
        # 刷新输出
        sys.stdout.flush()
    
    def draw_chart_settings(self) -> None:
        """绘制谱面设置界面"""
        # 清屏
        self._clear_screen()
        
        # 绘制标题
        title_text = "游戏设置"
        title_y = 1
        title_x = max(0, (self.screen_width - len(title_text)) // 2)
        self._print_at(title_y, title_x, self.COLOR_CODES['title'] + title_text + self.COLOR_CODES['reset'])
        
        # 绘制设置选项
        options_start_y = title_y + 2
        for i, option in enumerate(self.setting_options):
            y_pos = options_start_y + i
            if y_pos >= self.screen_height - 2:  # 为底部帮助信息留出空间
                break
                
            # 选择颜色（选中的选项使用高亮色）
            color = self.COLOR_CODES['menu_selected'] if i == self.selected_setting_option else self.COLOR_CODES['menu_item']
            
            # 获取选项值
            try:
                value = self.setting_value_formats[i]()
            except:
                value = ""
            
            # 格式化显示
            display_text = f"{option:<30} {value}"
            self._print_at(y_pos, 4, color + display_text + self.COLOR_CODES['reset'])
        
        # 绘制底部帮助信息
        help_y = self.screen_height - 2
        if help_y > 0:
            help_text = "使用 W/S 键选择选项, A/D 键调整数值, 回车键确认, ESC键返回"
            help_x = max(0, (self.screen_width - len(help_text)) // 2)
            self._print_at(help_y, help_x, self.COLOR_CODES['foreground'] + help_text + self.COLOR_CODES['reset'])
        
        # 刷新输出
        sys.stdout.flush()
    
    def set_state(self, state: 'UIState') -> None:
        """
        设置当前UI状态
        
        Args:
            state (UIState): 要设置的UI状态
        """
        self.current_state = state
    
    def set_on_chart_select_callback(self, callback: Callable) -> None:
        """
        设置选择谱面的回调函数
        
        Args:
            callback (Callable): 回调函数
        """
        self.on_chart_select = callback
    
    def set_on_pause_action_callback(self, callback: Callable) -> None:
        """
        设置暂停菜单操作的回调函数
        
        Args:
            callback (Callable): 回调函数
        """
        self.on_pause_action = callback
    
    def set_on_result_action_callback(self, callback: Callable) -> None:
        """
        设置结算界面操作的回调函数
        
        Args:
            callback (Callable): 回调函数
        """
        self.on_result_action = callback
    
    def set_game_result_data(self, score: int, perfect: int, good: int, bad: int, miss: int, max_combo: int, accuracy: float) -> None:
        """
        设置结算界面数据
        
        Args:
            score (int): 游戏分数
            perfect (int): Perfect判定数量
            good (int): Good判定数量
            bad (int): Bad判定数量
            miss (int): Miss判定数量
            max_combo (int): 最大连击数
            accuracy (float): 准确率
        """
        self.game_result_data = {
            'score': score,
            'perfect': perfect,
            'good': good,
            'bad': bad,
            'miss': miss,
            'max_combo': max_combo,
            'accuracy': accuracy
        }
    
    def _get_grade_by_score(self, score: int) -> str:
        """
        根据分数获取等级
        
        Args:
            score (int): 游戏分数
            
        Returns:
            str: 等级
        """
        if score >= 1000000:
            return "AP"
        elif score >= 950000:
            return "V"
        elif score >= 920000:
            return "S"
        elif score >= 880000:
            return "A"
        elif score >= 820000:
            return "B"
        elif score >= 720000:
            return "C"
        else:
            return "F"
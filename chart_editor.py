#!/usr/bin/env python3
"""
TRG (Terminal Rhythm Game) - 制谱器图形用户界面

这个模块提供了一个功能完整的制谱器GUI应用程序，用于创建和编辑TRG游戏的谱面文件。
"""

import os
import sys
import time
import json
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple

# 确保可以导入游戏模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# GUI相关导入
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import pygame

# 导入游戏相关模块
from chart_parser import ChartParser, NoteType, load_chart_by_id
from audio_manager import AudioManager

# 配置中文字体
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

class ChartEditor:
    """制谱器主类"""
    
    def __init__(self, root):
        """初始化制谱器GUI"""
        self.root = root
        self.root.title("TRG制谱器")
        self.root.geometry("1200x700")
        
        # 设置中文字体
        self.font_config = {
            'normal': ('SimHei', 10),
            'small': ('SimHei', 8),
            'medium': ('SimHei', 12),
            'large': ('SimHei', 14),
        }
        
        # 初始化数据模型
        self.chart_data = {
            'metadata': {
                'id': '',
                'title': '未命名曲目',
                'maker': '',
                'song_maker': '',
                'difficulty_level': 1,
                'difficulty_name': 'NORMAL',
                'audio_file': '',
                'speed': 5.0,
            },
            'notes': [],
            'text_events': []
        }
        
        self.current_file_path = None
        self.is_modified = False
        self.selected_note_index = -1
        
        # 初始化音频管理器
        self.audio_manager = AudioManager()
        self.is_playing = False
        self.current_time = 0
        self.playback_speed = 1.0
        
        # 轨道配置
        self.num_tracks = 4
        self.track_labels = ['轨道1', '轨道2', '轨道3', '轨道4']
        self.note_height = 20
        self.time_scale = 1.0  # 时间轴缩放比例
        self.vertical_scroll_offset = 0
        
        # 初始化UI
        self._init_ui()
        
        # 设置定时器更新播放进度
        self.update_timer = None
        self._schedule_time_update()
    
    def _init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 菜单栏
        self._create_menu_bar()
        
        # 工具栏
        self._create_toolbar()
        
        # 主内容区域 - 左右分割
        self.content_paned = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.content_paned.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 左侧面板 - 谱面配置
        self.left_panel = ttk.LabelFrame(self.content_paned, text="谱面配置", padding=(5, 5))
        self.content_paned.add(self.left_panel, weight=1)
        self._create_config_panel()
        
        # 右侧面板 - 轨道编辑
        self.right_panel = ttk.LabelFrame(self.content_paned, text="轨道编辑", padding=(5, 5))
        self.content_paned.add(self.right_panel, weight=3)
        self._create_track_editor()
        
        # 底部状态栏
        self.status_var = tk.StringVar(value="就绪")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        self.menu_bar = tk.Menu(self.root)
        
        # 文件菜单
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="新建", command=self._new_chart, accelerator="Ctrl+N")
        file_menu.add_command(label="打开", command=self._open_chart, accelerator="Ctrl+O")
        file_menu.add_command(label="保存", command=self._save_chart, accelerator="Ctrl+S")
        file_menu.add_command(label="另存为", command=self._save_chart_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self._exit_app, accelerator="Ctrl+Q")
        self.menu_bar.add_cascade(label="文件", menu=file_menu)
        
        # 编辑菜单
        edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        edit_menu.add_command(label="添加音符", command=self._add_note_at_current_time)
        edit_menu.add_command(label="删除选中音符", command=self._delete_selected_note)
        edit_menu.add_command(label="编辑选中音符", command=self._edit_selected_note)
        edit_menu.add_separator()
        edit_menu.add_command(label="清空所有音符", command=self._clear_all_notes)
        self.menu_bar.add_cascade(label="编辑", menu=edit_menu)
        
        # 音频菜单
        audio_menu = tk.Menu(self.menu_bar, tearoff=0)
        audio_menu.add_command(label="加载音频", command=self._load_audio)
        audio_menu.add_separator()
        audio_menu.add_command(label="播放/暂停", command=self._toggle_playback, accelerator="Space")
        audio_menu.add_command(label="停止", command=self._stop_playback)
        self.menu_bar.add_cascade(label="音频", menu=audio_menu)
        
        # 视图菜单
        view_menu = tk.Menu(self.menu_bar, tearoff=0)
        view_menu.add_command(label="放大时间轴", command=self._zoom_in_time)
        view_menu.add_command(label="缩小时间轴", command=self._zoom_out_time)
        view_menu.add_command(label="重置视图", command=self._reset_view)
        self.menu_bar.add_cascade(label="视图", menu=view_menu)
        
        # 帮助菜单
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="使用说明", command=self._show_help)
        help_menu.add_command(label="关于", command=self._show_about)
        self.menu_bar.add_cascade(label="帮助", menu=help_menu)
        
        # 设置菜单栏
        self.root.config(menu=self.menu_bar)
        
        # 绑定快捷键
        self.root.bind("<Control-n>", lambda e: self._new_chart())
        self.root.bind("<Control-o>", lambda e: self._open_chart())
        self.root.bind("<Control-s>", lambda e: self._save_chart())
        self.root.bind("<Control-Shift-S>", lambda e: self._save_chart_as())
        self.root.bind("<Control-q>", lambda e: self._exit_app())
        self.root.bind("<space>", lambda e: self._toggle_playback())
    
    def _create_toolbar(self):
        """创建工具栏"""
        self.toolbar = ttk.Frame(self.main_frame, padding=(5, 5))
        self.toolbar.pack(fill=tk.X, pady=2)
        
        # 文件操作按钮
        ttk.Button(self.toolbar, text="新建", command=self._new_chart).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="打开", command=self._open_chart).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="保存", command=self._save_chart).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        
        # 音频控制按钮
        self.play_button = ttk.Button(self.toolbar, text="播放", command=self._toggle_playback)
        self.play_button.pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="停止", command=self._stop_playback).pack(side=tk.LEFT, padx=2)
        
        # 时间显示
        self.time_var = tk.StringVar(value="00:00:000")
        ttk.Label(self.toolbar, text="当前时间:", font=self.font_config['normal']).pack(side=tk.LEFT, padx=10)
        ttk.Label(self.toolbar, textvariable=self.time_var, font=self.font_config['medium']).pack(side=tk.LEFT, padx=2)
        
        # 播放速度控制
        ttk.Label(self.toolbar, text="速度:", font=self.font_config['normal']).pack(side=tk.LEFT, padx=(20, 2))
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_frame = ttk.Frame(self.toolbar)
        speed_frame.pack(side=tk.LEFT)
        ttk.Scale(speed_frame, from_=0.5, to=2.0, variable=self.speed_var, orient=tk.HORIZONTAL, 
                  length=100, command=lambda s: self._update_playback_speed()).pack(side=tk.LEFT)
        self.speed_label = ttk.Label(speed_frame, text="1.0x", font=self.font_config['small'], width=5)
        self.speed_label.pack(side=tk.LEFT, padx=2)
    
    def _create_config_panel(self):
        """创建谱面配置面板"""
        # 创建配置表单
        config_frame = ttk.Frame(self.left_panel, padding=(5, 5))
        config_frame.pack(fill=tk.BOTH, expand=True)
        
        # 曲名
        ttk.Label(config_frame, text="曲名:", font=self.font_config['normal']).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.title_var = tk.StringVar(value=self.chart_data['metadata']['title'])
        ttk.Entry(config_frame, textvariable=self.title_var, font=self.font_config['normal']).grid(row=0, column=1, sticky=tk.EW, pady=2)
        self.title_var.trace_add("write", lambda *args: self._on_metadata_changed())
        
        # 谱面作者
        ttk.Label(config_frame, text="谱面作者:", font=self.font_config['normal']).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.maker_var = tk.StringVar(value=self.chart_data['metadata']['maker'])
        ttk.Entry(config_frame, textvariable=self.maker_var, font=self.font_config['normal']).grid(row=1, column=1, sticky=tk.EW, pady=2)
        self.maker_var.trace_add("write", lambda *args: self._on_metadata_changed())
        
        # 歌曲作者
        ttk.Label(config_frame, text="歌曲作者:", font=self.font_config['normal']).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.song_maker_var = tk.StringVar(value=self.chart_data['metadata']['song_maker'])
        ttk.Entry(config_frame, textvariable=self.song_maker_var, font=self.font_config['normal']).grid(row=2, column=1, sticky=tk.EW, pady=2)
        self.song_maker_var.trace_add("write", lambda *args: self._on_metadata_changed())
        
        # 难度等级
        ttk.Label(config_frame, text="难度等级:", font=self.font_config['normal']).grid(row=3, column=0, sticky=tk.W, pady=2)
        self.difficulty_level_var = tk.IntVar(value=self.chart_data['metadata']['difficulty_level'])
        ttk.Spinbox(config_frame, from_=1, to=10, textvariable=self.difficulty_level_var, font=self.font_config['normal'], 
                    width=5, command=self._on_metadata_changed).grid(row=3, column=1, sticky=tk.W, pady=2)
        
        # 难度名称
        ttk.Label(config_frame, text="难度名称:", font=self.font_config['normal']).grid(row=4, column=0, sticky=tk.W, pady=2)
        self.difficulty_name_var = tk.StringVar(value=self.chart_data['metadata']['difficulty_name'])
        difficulty_names = ['EASY', 'NORMAL', 'HARD', 'EXPERT', 'MASTER']
        ttk.Combobox(config_frame, textvariable=self.difficulty_name_var, values=difficulty_names, 
                     font=self.font_config['normal'], state='readonly').grid(row=4, column=1, sticky=tk.EW, pady=2)
        self.difficulty_name_var.trace_add("write", lambda *args: self._on_metadata_changed())
        
        # 游戏速度
        ttk.Label(config_frame, text="游戏速度:", font=self.font_config['normal']).grid(row=5, column=0, sticky=tk.W, pady=2)
        self.speed_var_game = tk.DoubleVar(value=self.chart_data['metadata']['speed'])
        speed_frame = ttk.Frame(config_frame)
        speed_frame.grid(row=5, column=1, sticky=tk.EW, pady=2)
        ttk.Scale(speed_frame, from_=1.0, to=20.0, variable=self.speed_var_game, orient=tk.HORIZONTAL, 
                  command=lambda s: self._on_speed_changed()).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.speed_value_label = ttk.Label(speed_frame, text=f"{self.speed_var_game.get():.1f}", 
                                          font=self.font_config['small'], width=5)
        self.speed_value_label.pack(side=tk.LEFT, padx=2)
        
        # 音频文件
        ttk.Label(config_frame, text="音频文件:", font=self.font_config['normal']).grid(row=6, column=0, sticky=tk.W, pady=2)
        audio_frame = ttk.Frame(config_frame)
        audio_frame.grid(row=6, column=1, sticky=tk.EW, pady=2)
        self.audio_file_var = tk.StringVar(value=self.chart_data['metadata']['audio_file'])
        ttk.Label(audio_frame, textvariable=self.audio_file_var, font=self.font_config['small'], 
                 width=20, anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(audio_frame, text="浏览", command=self._load_audio).pack(side=tk.RIGHT, padx=2)
        
        # 音符统计
        ttk.Separator(config_frame, orient=tk.HORIZONTAL).grid(row=7, column=0, columnspan=2, sticky=tk.EW, pady=10)
        ttk.Label(config_frame, text="音符统计:", font=self.font_config['medium']).grid(row=8, column=0, sticky=tk.W, pady=5)
        self.note_count_var = tk.StringVar(value="总音符数: 0")
        ttk.Label(config_frame, textvariable=self.note_count_var, font=self.font_config['normal']).grid(row=8, column=1, sticky=tk.W)
        
        # 配置列权重，使输入框可以扩展
        config_frame.columnconfigure(1, weight=1)
    
    def _create_track_editor(self):
        """创建轨道编辑器"""
        # 创建画布容器
        canvas_container = ttk.Frame(self.right_panel)
        canvas_container.pack(fill=tk.BOTH, expand=True)
        
        # 水平滚动条
        h_scrollbar = ttk.Scrollbar(canvas_container, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 垂直滚动条
        v_scrollbar = ttk.Scrollbar(canvas_container, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建画布
        self.track_canvas = tk.Canvas(canvas_container, background="#f0f0f0", 
                                     xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        self.track_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 配置滚动条
        h_scrollbar.config(command=self.track_canvas.xview)
        v_scrollbar.config(command=self.track_canvas.yview)
        
        # 绑定画布事件
        self.track_canvas.bind("<Button-1>", self._on_canvas_left_click)
        self.track_canvas.bind("<Button-2>", self._on_canvas_middle_click)  # 中键删除
        self.track_canvas.bind("<Button-3>", self._on_canvas_right_click)   # 右键添加
        self.track_canvas.bind("<MouseWheel>", self._on_mouse_wheel)        # 鼠标滚轮缩放
        
        # 绘制轨道
        self._draw_tracks()
    
    def _draw_tracks(self):
        """绘制轨道和音符"""
        # 清空画布
        self.track_canvas.delete("all")
        
        # 计算画布尺寸
        canvas_width = 2000  # 足够宽的画布
        canvas_height = (self.num_tracks + 2) * self.note_height  # 轨道高度
        
        # 设置画布滚动区域
        self.track_canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))
        
        # 绘制时间刻度
        self._draw_time_scale(canvas_width)
        
        # 绘制轨道
        for track_idx in range(self.num_tracks):
            y = (track_idx + 1) * self.note_height
            # 轨道背景
            self.track_canvas.create_rectangle(100, y, canvas_width, y + self.note_height, 
                                              fill="#e0e0e0", outline="#a0a0a0")
            # 轨道标签
            self.track_canvas.create_text(50, y + self.note_height/2, text=self.track_labels[track_idx],
                                         font=self.font_config['small'], anchor=tk.CENTER)
        
        # 绘制播放进度线
        progress_x = 100 + (self.current_time / 1000) * 100 * self.time_scale
        self.track_canvas.create_line(progress_x, 0, progress_x, canvas_height, 
                                     fill="#ff0000", width=2, dash=(2, 2))
        
        # 绘制音符
        self._draw_notes(canvas_width)
        
        # 更新音符计数
        self._update_note_count()
    
    def _draw_time_scale(self, canvas_width):
        """绘制时间刻度"""
        # 时间标题
        self.track_canvas.create_text(50, self.note_height/2, text="时间",
                                     font=self.font_config['small'], anchor=tk.CENTER)
        
        # 时间刻度线和标签（每1秒一个刻度）
        max_time = (canvas_width - 100) / (100 * self.time_scale)
        for sec in range(int(max_time) + 1):
            x = 100 + sec * 100 * self.time_scale
            # 刻度线
            self.track_canvas.create_line(x, 0, x, (self.num_tracks + 1) * self.note_height,
                                         fill="#d0d0d0", width=1)
            # 时间标签
            minutes = sec // 60
            seconds = sec % 60
            time_text = f"{minutes:02d}:{seconds:02d}"
            self.track_canvas.create_text(x, self.note_height/2, text=time_text,
                                         font=self.font_config['small'], anchor=tk.CENTER)
    
    def _draw_notes(self, canvas_width):
        """绘制音符"""
        for idx, note in enumerate(self.chart_data['notes']):
            track_idx = note['track_index']
            time_ms = note['perfect_time']
            note_type = note['type']
            
            # 计算音符位置
            x = 100 + (time_ms / 1000) * 100 * self.time_scale
            y = (track_idx + 1) * self.note_height
            
            # 根据音符类型设置颜色
            color_map = {
                NoteType.NORMAL.value: "#4a7c59",  # 普通音符 - 绿色
                NoteType.HOLD.value: "#f9c74f",    # 长按音符 - 黄色
                NoteType.DRAG.value: "#e76f51"     # 拖动音符 - 红色
            }
            color = color_map.get(note_type, "#333333")
            
            # 如果是选中的音符，使用不同的填充色
            fill_color = "#90be6d" if idx == self.selected_note_index else color
            
            # 绘制音符
            note_id = self.track_canvas.create_rectangle(x - 15, y, x + 15, y + self.note_height,
                                                        fill=fill_color, outline="#000000", width=2)
            
            # 存储音符ID和索引的映射
            self.track_canvas.itemconfig(note_id, tags=("note", f"note_{idx}"))
            
            # 对于长按音符，绘制持续时间
            if note_type == NoteType.HOLD.value and 'duration' in note:
                duration_pixels = (note['duration'] / 1000) * 100 * self.time_scale
                self.track_canvas.create_rectangle(x + 15, y + 5, x + 15 + duration_pixels, y + self.note_height - 5,
                                                  fill=fill_color, outline="#000000", width=1)
    
    def _on_canvas_left_click(self, event):
        """处理画布左键点击事件 - 选择音符"""
        # 获取点击位置
        x, y = event.x, event.y
        
        # 转换为画布坐标
        x = self.track_canvas.canvasx(x)
        y = self.track_canvas.canvasy(y)
        
        # 检查是否点击了音符
        self.selected_note_index = -1
        
        # 计算点击的轨道和时间
        track_idx = int((y - self.note_height) / self.note_height)
        time_ms = int(((x - 100) / (100 * self.time_scale)) * 1000)
        
        # 寻找最近的音符
        closest_note_idx = -1
        closest_distance = float('inf')
        
        for idx, note in enumerate(self.chart_data['notes']):
            if note['track_index'] == track_idx:
                note_time = note['perfect_time']
                time_diff = abs(note_time - time_ms)
                
                # 如果时间差在阈值内，认为点击了这个音符
                if time_diff < 200:  # 200ms阈值
                    if time_diff < closest_distance:
                        closest_distance = time_diff
                        closest_note_idx = idx
        
        if closest_note_idx >= 0:
            self.selected_note_index = closest_note_idx
            self.status_var.set(f"选中音符: 轨道{track_idx+1}, 时间{self._format_time(time_ms)}")
        else:
            # 如果没有选中音符，跳转到该时间位置
            self.current_time = time_ms
            self.time_var.set(self._format_time(time_ms))
            self.status_var.set(f"跳转到时间: {self._format_time(time_ms)}")
        
        # 重绘画布
        self._draw_tracks()
    
    def _on_canvas_middle_click(self, event):
        """处理画布中键点击事件 - 删除音符"""
        # 获取点击位置
        x, y = event.x, event.y
        
        # 转换为画布坐标
        x = self.track_canvas.canvasx(x)
        y = self.track_canvas.canvasy(y)
        
        # 计算点击的轨道和时间
        track_idx = int((y - self.note_height) / self.note_height)
        time_ms = int(((x - 100) / (100 * self.time_scale)) * 1000)
        
        # 查找要删除的音符
        to_delete = -1
        for idx, note in enumerate(self.chart_data['notes']):
            if note['track_index'] == track_idx:
                note_time = note['perfect_time']
                time_diff = abs(note_time - time_ms)
                
                if time_diff < 200:  # 200ms阈值
                    to_delete = idx
                    break
        
        if to_delete >= 0:
            del self.chart_data['notes'][to_delete]
            self.selected_note_index = -1
            self.is_modified = True
            self.status_var.set(f"删除音符: 轨道{track_idx+1}, 时间{self._format_time(time_ms)}")
            self._draw_tracks()
    
    def _on_canvas_right_click(self, event):
        """处理画布右键点击事件 - 添加音符"""
        # 获取点击位置
        x, y = event.x, event.y
        
        # 转换为画布坐标
        x = self.track_canvas.canvasx(x)
        y = self.track_canvas.canvasy(y)
        
        # 计算点击的轨道和时间
        track_idx = int((y - self.note_height) / self.note_height)
        time_ms = int(((x - 100) / (100 * self.time_scale)) * 1000)
        
        # 检查轨道索引是否有效
        if 0 <= track_idx < self.num_tracks:
            # 创建音符类型选择对话框
            type_window = tk.Toplevel(self.root)
            type_window.title("选择音符类型")
            type_window.geometry("300x200")
            type_window.transient(self.root)
            type_window.grab_set()
            
            # 设置窗口居中
            type_window.update_idletasks()
            width = type_window.winfo_width()
            height = type_window.winfo_height()
            x_offset = (self.root.winfo_width() // 2) - (width // 2)
            y_offset = (self.root.winfo_height() // 2) - (height // 2)
            type_window.geometry(f"+{self.root.winfo_x() + x_offset}+{self.root.winfo_y() + y_offset}")
            
            # 选择标签
            ttk.Label(type_window, text="请选择音符类型:", font=self.font_config['normal']).pack(pady=10)
            
            # 创建下拉选择框
            note_type_var = tk.StringVar(value=NoteType.NORMAL.value)
            note_type_frame = ttk.Frame(type_window)
            note_type_frame.pack(pady=5, fill=tk.X, padx=20)
            
            # 音符类型选项
            note_type_options = {
                "普通音符": NoteType.NORMAL.value,
                "长按音符": NoteType.HOLD.value,
                "拖动音符": NoteType.DRAG.value
            }
            
            # 创建RadioButton选择器
            for text, value in note_type_options.items():
                ttk.Radiobutton(note_type_frame, text=text, value=value, variable=note_type_var).pack(anchor=tk.W, pady=2)
            
            # 按钮框架
            button_frame = ttk.Frame(type_window)
            button_frame.pack(pady=20)
            
            def on_select():
                note_type = note_type_var.get()
                
                # 创建新音符
                new_note = {
                    'type': note_type,
                    'track_index': track_idx,
                    'perfect_time': time_ms,
                    'placement_time': time_ms
                }
                
                # 如果是长按音符，设置持续时间
                if note_type == NoteType.HOLD.value:
                    duration_window = tk.Toplevel(self.root)
                    duration_window.title("设置持续时间")
                    duration_window.geometry("300x150")
                    duration_window.transient(self.root)
                    duration_window.grab_set()
                    
                    # 设置居中
                    duration_window.update_idletasks()
                    width = duration_window.winfo_width()
                    height = duration_window.winfo_height()
                    x_offset = (self.root.winfo_width() // 2) - (width // 2)
                    y_offset = (self.root.winfo_height() // 2) - (height // 2)
                    duration_window.geometry(f"+{self.root.winfo_x() + x_offset}+{self.root.winfo_y() + y_offset}")
                    
                    # 持续时间输入
                    ttk.Label(duration_window, text="持续时间(秒):", font=self.font_config['normal']).pack(pady=10, padx=20, anchor=tk.W)
                    duration_var = tk.DoubleVar(value=1.0)
                    ttk.Entry(duration_window, textvariable=duration_var, font=self.font_config['normal'],
                              width=15).pack(pady=5)
                    
                    # 按钮
                    duration_button_frame = ttk.Frame(duration_window)
                    duration_button_frame.pack(pady=10)
                    
                    def on_duration_confirm():
                        duration = duration_var.get()
                        if duration > 0:
                            new_note['duration'] = int(duration * 1000)
                            
                            # 添加音符
                            self.chart_data['notes'].append(new_note)
                            
                            # 按时间排序音符
                            self.chart_data['notes'].sort(key=lambda n: n['perfect_time'])
                            
                            # 选中新添加的音符
                            for idx, note in enumerate(self.chart_data['notes']):
                                if note == new_note:
                                    self.selected_note_index = idx
                                    break
                            
                            self.is_modified = True
                            self.status_var.set(f"添加音符: {note_type}, 轨道{track_idx+1}, 时间{self._format_time(time_ms)}")
                            self._draw_tracks()
                        
                        duration_window.destroy()
                        type_window.destroy()
                    
                    ttk.Button(duration_button_frame, text="确定", command=on_duration_confirm).pack(side=tk.LEFT, padx=10)
                    ttk.Button(duration_button_frame, text="取消", command=lambda: (duration_window.destroy(), type_window.destroy())).pack(side=tk.LEFT, padx=10)
                else:
                    # 添加音符
                    self.chart_data['notes'].append(new_note)
                    
                    # 按时间排序音符
                    self.chart_data['notes'].sort(key=lambda n: n['perfect_time'])
                    
                    # 选中新添加的音符
                    for idx, note in enumerate(self.chart_data['notes']):
                        if note == new_note:
                            self.selected_note_index = idx
                            break
                    
                    self.is_modified = True
                    self.status_var.set(f"添加音符: {note_type}, 轨道{track_idx+1}, 时间{self._format_time(time_ms)}")
                    self._draw_tracks()
                    type_window.destroy()
            
            # 确认和取消按钮
            ttk.Button(button_frame, text="确定", command=on_select).pack(side=tk.LEFT, padx=10)
            ttk.Button(button_frame, text="取消", command=type_window.destroy).pack(side=tk.LEFT, padx=10)
    
    def _on_mouse_wheel(self, event):
        """处理鼠标滚轮事件 - 缩放时间轴"""
        # 获取当前缩放比例
        current_scale = self.time_scale
        
        # 根据滚轮方向调整缩放比例
        if event.delta > 0:
            # 向上滚轮 - 放大
            new_scale = min(current_scale * 1.1, 5.0)
        else:
            # 向下滚轮 - 缩小
            new_scale = max(current_scale / 1.1, 0.1)
        
        # 应用新的缩放比例
        self.time_scale = new_scale
        self._draw_tracks()
    
    def _update_note_count(self):
        """更新音符计数显示"""
        total_notes = len(self.chart_data['notes'])
        
        # 统计各类音符数量
        normal_count = 0
        hold_count = 0
        drag_count = 0
        
        for note in self.chart_data['notes']:
            if note['type'] == NoteType.NORMAL.value:
                normal_count += 1
            elif note['type'] == NoteType.HOLD.value:
                hold_count += 1
            elif note['type'] == NoteType.DRAG.value:
                drag_count += 1
        
        # 更新显示
        count_text = f"总音符数: {total_notes} (普通: {normal_count}, 长按: {hold_count}, 拖动: {drag_count})"
        self.note_count_var.set(count_text)
    
    def _update_playback_speed(self):
        """更新播放速度"""
        speed = self.speed_var.get()
        self.speed_label.config(text=f"{speed:.1f}x")
        self.playback_speed = speed
    
    def _on_speed_changed(self):
        """处理游戏速度变化"""
        speed = self.speed_var_game.get()
        self.speed_value_label.config(text=f"{speed:.1f}")
        self.chart_data['metadata']['speed'] = speed
        self.is_modified = True
    
    def _on_metadata_changed(self):
        """处理元数据变化"""
        # 更新元数据
        self.chart_data['metadata']['title'] = self.title_var.get()
        self.chart_data['metadata']['maker'] = self.maker_var.get()
        self.chart_data['metadata']['song_maker'] = self.song_maker_var.get()
        self.chart_data['metadata']['difficulty_level'] = self.difficulty_level_var.get()
        self.chart_data['metadata']['difficulty_name'] = self.difficulty_name_var.get()
        
        self.is_modified = True
    
    def _schedule_time_update(self):
        """安排时间更新定时器"""
        if self.is_playing and self.audio_manager.is_playing():
            # 更新当前时间
            self.current_time = self.audio_manager.get_position()
            self.time_var.set(self._format_time(self.current_time))
            
            # 重绘画布以更新播放进度线
            self._draw_tracks()
        
        # 继续安排下一次更新
        self.update_timer = self.root.after(50, self._schedule_time_update)
    
    def _format_time(self, time_ms):
        """格式化时间为分:秒:毫秒"""
        minutes = int(time_ms // 60000)
        seconds = int((time_ms % 60000) // 1000)
        milliseconds = int(time_ms % 1000)
        return f"{minutes:02d}:{seconds:02d}:{milliseconds:03d}"
    
    def _toggle_playback(self):
        """切换播放/暂停状态"""
        if not self.is_playing:
            # 开始播放
            if self.chart_data['metadata']['audio_file']:
                audio_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio', 
                                         self.chart_data['metadata']['audio_file'])
                if os.path.exists(audio_path):
                    # 设置播放位置
                    # 注意：pygame.mixer不支持直接设置播放位置，这里使用我们的模拟时间
                    self.audio_manager.play()
                    self.is_playing = True
                    self.play_button.config(text="暂停")
                    self.status_var.set("正在播放")
                else:
                    messagebox.showerror("错误", f"找不到音频文件: {audio_path}")
            else:
                # 没有音频文件，只播放模拟时间
                self.audio_manager.play()
                self.is_playing = True
                self.play_button.config(text="暂停")
                self.status_var.set("正在播放（无音频）")
        else:
            # 暂停播放
            self.audio_manager.pause()
            self.is_playing = False
            self.play_button.config(text="播放")
            self.status_var.set(f"已暂停: {self._format_time(self.current_time)}")
    
    def _stop_playback(self):
        """停止播放"""
        self.audio_manager.stop()
        self.is_playing = False
        self.current_time = 0
        self.time_var.set("00:00:000")
        self.play_button.config(text="播放")
        self.status_var.set("已停止")
        self._draw_tracks()
    
    def _load_audio(self):
        """加载音频文件"""
        # 打开文件选择对话框
        file_types = [
            ("音频文件", "*.mp3 *.wav *.ogg *.flac"),
            ("MP3文件", "*.mp3"),
            ("WAV文件", "*.wav"),
            ("所有文件", "*.*")
        ]
        
        # 获取默认音频目录
        audio_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio')
        if not os.path.exists(audio_dir):
            os.makedirs(audio_dir)
        default_dir = audio_dir
        
        # 打开文件选择器
        file_path = filedialog.askopenfilename(title="选择音频文件", 
                                             filetypes=file_types,
                                             initialdir=default_dir)
        
        if file_path:
            # 提取文件名（不包含路径）
            file_name = os.path.basename(file_path)
            
            # 检查文件是否已经在audio目录中
            destination_path = os.path.join(audio_dir, file_name)
            
            # 如果文件不在audio目录中，或者目标文件与源文件不同
            if not os.path.exists(destination_path) or os.path.abspath(file_path) != os.path.abspath(destination_path):
                import shutil
                try:
                    # 首先检查目标文件是否存在，如果存在先删除（避免文件占用）
                    if os.path.exists(destination_path):
                        try:
                            os.remove(destination_path)
                        except Exception as e:
                            self.status_var.set(f"警告: 无法删除已存在的目标文件: {e}")
                    
                    # 使用copy2复制文件
                    shutil.copy2(file_path, audio_dir)
                    self.status_var.set(f"音频文件已复制到项目audio目录")
                except Exception as e:
                    # 如果复制失败，尝试使用原始路径（不复制）
                    self.status_var.set(f"警告: 无法复制音频文件，将使用原始路径: {e}")
                    destination_path = file_path  # 使用原始路径
            
            # 更新音频文件信息 - 只保存文件名（如果在audio目录中）
            if destination_path.startswith(audio_dir):
                self.chart_data['metadata']['audio_file'] = file_name
                self.audio_file_var.set(file_name)
                load_path = destination_path
            else:
                # 如果不在audio目录中，保存完整路径
                self.chart_data['metadata']['audio_file'] = file_path
                self.audio_file_var.set(file_path)
                load_path = file_path
            
            # 尝试加载音频
            if self.audio_manager.load_music(load_path):
                self.status_var.set(f"成功加载音频: {file_name}")
                self.is_modified = True
            else:
                messagebox.showerror("错误", f"加载音频文件失败")
    
    def _new_chart(self):
        """新建谱面"""
        # 检查是否需要保存当前谱面
        if self.is_modified:
            response = messagebox.askyesnocancel("保存提示", "当前谱面已修改，是否保存？")
            if response is None:  # 取消操作
                return
            if response:  # 保存
                if not self._save_chart():
                    return
        
        # 重置谱面数据
        self.chart_data = {
            'metadata': {
                'id': '',
                'title': '未命名曲目',
                'maker': '',
                'song_maker': '',
                'difficulty_level': 1,
                'difficulty_name': 'NORMAL',
                'audio_file': '',
                'speed': 5.0,
            },
            'notes': [],
            'text_events': []
        }
        
        # 更新UI
        self.title_var.set(self.chart_data['metadata']['title'])
        self.maker_var.set(self.chart_data['metadata']['maker'])
        self.song_maker_var.set(self.chart_data['metadata']['song_maker'])
        self.difficulty_level_var.set(self.chart_data['metadata']['difficulty_level'])
        self.difficulty_name_var.set(self.chart_data['metadata']['difficulty_name'])
        self.speed_var_game.set(self.chart_data['metadata']['speed'])
        self.audio_file_var.set(self.chart_data['metadata']['audio_file'])
        self.speed_value_label.config(text=f"{self.chart_data['metadata']['speed']:.1f}")
        
        # 重置状态
        self.current_file_path = None
        self.is_modified = False
        self.selected_note_index = -1
        self.current_time = 0
        self.time_var.set("00:00:000")
        
        # 停止播放
        self._stop_playback()
        
        # 重绘画布
        self._draw_tracks()
        self.status_var.set("已新建谱面")
    
    def _open_chart(self):
        """打开谱面文件"""
        # 检查是否需要保存当前谱面
        if self.is_modified:
            response = messagebox.askyesnocancel("保存提示", "当前谱面已修改，是否保存？")
            if response is None:  # 取消操作
                return
            if response:  # 保存
                if not self._save_chart():
                    return
        
        # 打开文件选择对话框
        file_types = [
            ("TRG谱面文件", "*.chart"),
            ("所有文件", "*.*")
        ]
        
        # 获取默认charts目录
        default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'charts')
        if not os.path.exists(default_dir):
            default_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 打开文件选择器
        file_path = filedialog.askopenfilename(title="打开谱面文件", 
                                             filetypes=file_types,
                                             initialdir=default_dir)
        
        if file_path:
            try:
                # 使用ChartParser解析谱面文件
                parser = ChartParser()
                chart_data = parser.parse_chart_file(file_path)
                
                # 更新谱面数据
                self.chart_data = chart_data
                
                # 更新UI
                if 'metadata' in self.chart_data:
                    self.title_var.set(self.chart_data['metadata'].get('title', '未命名曲目'))
                    self.maker_var.set(self.chart_data['metadata'].get('maker', ''))
                    self.song_maker_var.set(self.chart_data['metadata'].get('song_maker', ''))
                    self.difficulty_level_var.set(self.chart_data['metadata'].get('difficulty_level', 1))
                    self.difficulty_name_var.set(self.chart_data['metadata'].get('difficulty_name', 'NORMAL'))
                    self.speed_var_game.set(self.chart_data['metadata'].get('speed', 5.0))
                    self.audio_file_var.set(self.chart_data['metadata'].get('audio_file', ''))
                    self.speed_value_label.config(text=f"{self.chart_data['metadata'].get('speed', 5.0):.1f}")
                
                # 更新状态
                self.current_file_path = file_path
                self.is_modified = False
                self.selected_note_index = -1
                self.current_time = 0
                self.time_var.set("00:00:000")
                
                # 停止播放
                self._stop_playback()
                
                # 尝试加载音频（如果有）
                if self.chart_data['metadata'].get('audio_file', ''):
                    audio_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio', 
                                             self.chart_data['metadata']['audio_file'])
                    if os.path.exists(audio_path):
                        self.audio_manager.load_music(audio_path)
                
                # 重绘画布
                self._draw_tracks()
                self.status_var.set(f"已打开谱面: {os.path.basename(file_path)}")
                
            except Exception as e:
                messagebox.showerror("错误", f"打开谱面文件失败: {e}")
    
    def _save_chart(self):
        """保存谱面文件"""
        if not self.current_file_path:
            return self._save_chart_as()
        
        try:
            # 确保目录存在
            dir_path = os.path.dirname(self.current_file_path)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            
            # 写入谱面文件
            with open(self.current_file_path, 'w', encoding='utf-8') as f:
                # 写入元数据
                f.write(f"name-{self.chart_data['metadata']['title']}\n")
                f.write(f"maker-{self.chart_data['metadata']['maker']}-{self.chart_data['metadata']['song_maker']}\n")
                f.write(f"level-{self.chart_data['metadata']['difficulty_level']}-{self.chart_data['metadata']['difficulty_name']}\n")
                f.write(f"audio-{self.chart_data['metadata']['audio_file']}\n")
                f.write(f"speed-{self.chart_data['metadata']['speed']}\n")
                
                # 按时间排序音符
                sorted_notes = sorted(self.chart_data['notes'], key=lambda n: n['perfect_time'])
                
                # 写入音符
                for note in sorted_notes:
                    # 格式化时间
                    time_ms = note['perfect_time']
                    minutes = time_ms // 60000
                    seconds = (time_ms % 60000) // 1000
                    ms = time_ms % 1000
                    time_str = f"{minutes:d}:{seconds:02d}:{ms:03d}"
                    
                    # 写入时间标记
                    f.write(f"{time_str}\n")
                    
                    # 写入音符数据
                    track_index = note['track_index'] + 1  # 转换为1-based索引
                    
                    if note['type'] == NoteType.NORMAL.value:
                        f.write(f"tab-{track_index}\n")
                    elif note['type'] == NoteType.HOLD.value:
                        duration = note.get('duration', 1000)  # 默认1秒
                        # 转换为行数
                        speed = self.chart_data['metadata'].get('speed', 5.0)
                        duration_lines = duration * speed / 1000
                        f.write(f"hold-{track_index}-{duration_lines:.2f}\n")
                    elif note['type'] == NoteType.DRAG.value:
                        f.write(f"drag-{track_index}\n")
                
                # 写入结束标记
                f.write("&\n")
            
            self.is_modified = False
            self.status_var.set(f"已保存谱面: {os.path.basename(self.current_file_path)}")
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"保存谱面文件失败: {e}")
            return False
    
    def _save_chart_as(self):
        """另存为谱面文件"""
        # 打开文件保存对话框
        file_types = [
            ("TRG谱面文件", "*.chart"),
            ("所有文件", "*.*")
        ]
        
        # 获取默认charts目录
        default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'charts')
        if not os.path.exists(default_dir):
            os.makedirs(default_dir)
        
        # 默认文件名
        default_filename = self.chart_data['metadata']['title'] or "未命名曲目"
        default_filename = default_filename.replace(' ', '_') + ".chart"
        
        # 打开文件保存器
        file_path = filedialog.asksaveasfilename(title="另存为", 
                                               filetypes=file_types,
                                               defaultextension=".chart",
                                               initialdir=default_dir,
                                               initialfile=default_filename)
        
        if file_path:
            # 更新文件路径
            self.current_file_path = file_path
            
            # 提取文件名作为ID
            self.chart_data['metadata']['id'] = os.path.splitext(os.path.basename(file_path))[0]
            
            # 保存文件
            return self._save_chart()
        
        return False
    
    def _add_note_at_current_time(self):
        """在当前时间添加音符"""
        # 获取当前时间
        current_time = self.current_time
        
        # 弹出轨道和类型选择对话框
        track_idx = simpledialog.askinteger("选择轨道", "输入轨道号(1-4):", minvalue=1, maxvalue=4)
        if track_idx is None:
            return
        
        track_idx -= 1  # 转换为0-based索引
        
        note_type = simpledialog.askstring("选择音符类型", "输入音符类型(normal/hold/drag):", initialvalue="normal")
        if not note_type:
            return
        
        note_type = note_type.lower()
        
        # 验证音符类型
        valid_types = [NoteType.NORMAL.value, NoteType.HOLD.value, NoteType.DRAG.value]
        if note_type not in valid_types:
            messagebox.showerror("错误", "无效的音符类型")
            return
        
        # 创建新音符
        new_note = {
            'type': note_type,
            'track_index': track_idx,
            'perfect_time': current_time,
            'placement_time': current_time
        }
        
        # 如果是长按音符，设置持续时间
        if note_type == NoteType.HOLD.value:
            duration = simpledialog.askfloat("设置持续时间", "输入持续时间(秒):", initialvalue=1.0, minvalue=0.1)
            if duration is not None:
                new_note['duration'] = int(duration * 1000)
            else:
                return
        
        # 添加音符
        self.chart_data['notes'].append(new_note)
        
        # 按时间排序音符
        self.chart_data['notes'].sort(key=lambda n: n['perfect_time'])
        
        # 选中新添加的音符
        for idx, note in enumerate(self.chart_data['notes']):
            if note == new_note:
                self.selected_note_index = idx
                break
        
        self.is_modified = True
        self.status_var.set(f"添加音符: {note_type}, 轨道{track_idx+1}, 时间{self._format_time(current_time)}")
        self._draw_tracks()
    
    def _delete_selected_note(self):
        """删除选中的音符"""
        if self.selected_note_index >= 0 and self.selected_note_index < len(self.chart_data['notes']):
            note = self.chart_data['notes'][self.selected_note_index]
            track_idx = note['track_index']
            time_ms = note['perfect_time']
            
            del self.chart_data['notes'][self.selected_note_index]
            self.selected_note_index = -1
            self.is_modified = True
            self.status_var.set(f"删除音符: 轨道{track_idx+1}, 时间{self._format_time(time_ms)}")
            self._draw_tracks()
        else:
            messagebox.showinfo("提示", "请先选择一个音符")
    
    def _edit_selected_note(self):
        """编辑选中的音符"""
        if self.selected_note_index >= 0 and self.selected_note_index < len(self.chart_data['notes']):
            note = self.chart_data['notes'][self.selected_note_index]
            
            # 创建编辑对话框
            edit_window = tk.Toplevel(self.root)
            edit_window.title("编辑音符")
            edit_window.geometry("300x250")
            edit_window.transient(self.root)
            edit_window.grab_set()
            
            # 轨道选择
            ttk.Label(edit_window, text="轨道:", font=self.font_config['normal']).grid(row=0, column=0, sticky=tk.W, pady=5, padx=10)
            track_var = tk.IntVar(value=note['track_index'] + 1)
            ttk.Spinbox(edit_window, from_=1, to=4, textvariable=track_var, font=self.font_config['normal'], 
                        width=5).grid(row=0, column=1, sticky=tk.W, pady=5)
            
            # 时间设置
            ttk.Label(edit_window, text="时间(秒):", font=self.font_config['normal']).grid(row=1, column=0, sticky=tk.W, pady=5, padx=10)
            time_var = tk.DoubleVar(value=note['perfect_time'] / 1000)
            ttk.Entry(edit_window, textvariable=time_var, font=self.font_config['normal'], 
                      width=10).grid(row=1, column=1, sticky=tk.W, pady=5)
            
            # 音符类型
            ttk.Label(edit_window, text="类型:", font=self.font_config['normal']).grid(row=2, column=0, sticky=tk.W, pady=5, padx=10)
            type_var = tk.StringVar(value=note['type'])
            type_frame = ttk.Frame(edit_window)
            type_frame.grid(row=2, column=1, sticky=tk.W, pady=5)
            ttk.Radiobutton(type_frame, text="普通", variable=type_var, value=NoteType.NORMAL.value).pack(side=tk.LEFT)
            ttk.Radiobutton(type_frame, text="长按", variable=type_var, value=NoteType.HOLD.value).pack(side=tk.LEFT)
            ttk.Radiobutton(type_frame, text="拖动", variable=type_var, value=NoteType.DRAG.value).pack(side=tk.LEFT)
            
            # 持续时间（仅长按音符）
            duration_var = tk.DoubleVar(value=note.get('duration', 1000) / 1000)
            duration_frame = ttk.Frame(edit_window)
            duration_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5, padx=10)
            ttk.Label(duration_frame, text="持续时间(秒):", font=self.font_config['normal']).pack(side=tk.LEFT)
            duration_entry = ttk.Entry(duration_frame, textvariable=duration_var, font=self.font_config['normal'], 
                                      width=10)
            duration_entry.pack(side=tk.LEFT, padx=5)
            
            # 根据初始类型显示/隐藏持续时间
            def update_duration_visibility():
                if type_var.get() == NoteType.HOLD.value:
                    duration_frame.grid()
                else:
                    duration_frame.grid_remove()
            
            type_var.trace_add("write", lambda *args: update_duration_visibility())
            update_duration_visibility()
            
            # 按钮
            button_frame = ttk.Frame(edit_window)
            button_frame.grid(row=4, column=0, columnspan=2, pady=20)
            
            def on_save():
                # 更新音符数据
                note['track_index'] = track_var.get() - 1
                note['perfect_time'] = int(time_var.get() * 1000)
                note['placement_time'] = int(time_var.get() * 1000)
                note['type'] = type_var.get()
                
                if type_var.get() == NoteType.HOLD.value:
                    note['duration'] = int(duration_var.get() * 1000)
                elif 'duration' in note:
                    del note['duration']
                
                # 按时间排序音符
                self.chart_data['notes'].sort(key=lambda n: n['perfect_time'])
                
                # 重新选中编辑后的音符
                for idx, n in enumerate(self.chart_data['notes']):
                    if n is note:
                        self.selected_note_index = idx
                        break
                
                self.is_modified = True
                self._draw_tracks()
                edit_window.destroy()
            
            ttk.Button(button_frame, text="保存", command=on_save).pack(side=tk.LEFT, padx=10)
            ttk.Button(button_frame, text="取消", command=edit_window.destroy).pack(side=tk.LEFT, padx=10)
        else:
            messagebox.showinfo("提示", "请先选择一个音符")
    
    def _clear_all_notes(self):
        """清空所有音符"""
        if len(self.chart_data['notes']) > 0:
            if messagebox.askyesno("确认", "确定要清空所有音符吗？此操作不可撤销。"):
                self.chart_data['notes'] = []
                self.selected_note_index = -1
                self.is_modified = True
                self._draw_tracks()
                self.status_var.set("已清空所有音符")
    
    def _zoom_in_time(self):
        """放大时间轴"""
        self.time_scale = min(self.time_scale * 1.5, 5.0)
        self._draw_tracks()
    
    def _zoom_out_time(self):
        """缩小时间轴"""
        self.time_scale = max(self.time_scale / 1.5, 0.1)
        self._draw_tracks()
    
    def _reset_view(self):
        """重置视图"""
        self.time_scale = 1.0
        self.vertical_scroll_offset = 0
        self._draw_tracks()
    
    def _show_help(self):
        """显示帮助信息"""
        help_text = """
制谱器使用说明：

文件操作：
  - 新建：创建新的谱面文件
  - 打开：打开已有的谱面文件
  - 保存：保存当前谱面
  - 另存为：将当前谱面另存为新文件

音符编辑：
  - 左键单击：选择单个音符（选中状态高亮显示）
  - 右键单击：在点击位置创建新音符（自动进入选中状态）
  - 中键单击：直接删除光标位置音符（无需预先选中）
  - 选中音符后可使用编辑菜单修改音符属性

音频控制：
  - 加载音频：选择并加载音频文件
  - 播放/暂停：播放或暂停音频
  - 停止：停止播放并重置到开始位置
  - 速度控制：调整播放速度

视图控制：
  - 鼠标滚轮：缩放时间轴
  - 视图菜单：提供快速缩放和重置选项
  - 水平/垂直滚动条：移动视图位置

谱面配置：
  - 左侧面板可设置曲名、作者、难度等谱面属性
  - 游戏速度影响音符下落速度
        """
        
        help_window = tk.Toplevel(self.root)
        help_window.title("使用说明")
        help_window.geometry("600x500")
        help_window.transient(self.root)
        
        # 创建文本框显示帮助信息
        text_widget = tk.Text(help_window, wrap=tk.WORD, font=self.font_config['normal'], padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(text_widget, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)
    
    def _show_about(self):
        """显示关于信息"""
        about_text = """
TRG制谱器 v1.0

用于创建和编辑Terminal Rhythm Game的谱面文件。
支持多种音符类型和音频同步功能。

© 2024 TRG开发团队
        """
        messagebox.showinfo("关于", about_text)
    
    def _exit_app(self):
        """退出应用程序"""
        # 检查是否需要保存
        if self.is_modified:
            response = messagebox.askyesnocancel("保存提示", "当前谱面已修改，是否保存？")
            if response is None:  # 取消操作
                return
            if response:  # 保存
                if not self._save_chart():
                    return
        
        # 停止音频播放
        self.audio_manager.quit()
        
        # 取消定时器
        if self.update_timer:
            self.root.after_cancel(self.update_timer)
        
        # 退出应用
        self.root.destroy()

def main():
    """主函数"""
    # 初始化pygame（用于音频）
    pygame.init()
    
    # 创建主窗口
    root = tk.Tk()
    
    # 设置窗口图标（可选）
    # root.iconbitmap("path/to/icon.ico")
    
    # 创建制谱器实例
    editor = ChartEditor(root)
    
    # 设置窗口关闭事件
    root.protocol("WM_DELETE_WINDOW", editor._exit_app)
    
    # 运行主循环
    root.mainloop()

if __name__ == "__main__":
    main()
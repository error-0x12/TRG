#!/usr/bin/env python3
"""
TRG (Terminal Rhythm Game) - 音频管理器模块

这个模块负责处理游戏中的音频播放和精确的时间同步，使用pygame.mixer库实现。
"""

import pygame
import time
import os
from typing import Optional, Dict


class AudioManager:
    """音频管理器类 - 负责音乐播放和精确的时间同步"""
    
    def __init__(self):
        """初始化音频管理器和pygame.mixer"""
        # 音频状态变量
        self.music_loaded = False  # 是否已加载音乐
        self.music_playing = False  # 音乐是否正在播放
        self.audio_available = False  # 音频是否可用
        
        # 时间同步变量 - 关键修复：确保时间能够正确递增
        self.play_start_time = 0.0  # 音乐开始播放的系统时间戳（毫秒）
        self.pause_start_time = 0.0  # 暂停开始的系统时间戳（毫秒）
        self.total_paused_time = 0.0  # 总共暂停的时间（毫秒）
        self.last_position = 0.0  # 上一次记录的位置
        self.music_delay = 0.0  # 音乐延迟（毫秒）
        
        # 音效相关变量
        self.notes_sfx: Dict[str, pygame.mixer.Sound] = {}  # 存储note音效
        self.sfx_volume = 1.0  # 音效音量（0.0到1.0之间）
        
        # 尝试初始化pygame.mixer模块
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.audio_available = True
            # 初始化完成后加载notes音效
            self._load_notes_sfx()
        except pygame.error as e:
            print(f"音频初始化失败: {e}")
            print("游戏将在无音频模式下运行")
            self.audio_available = False
    
    def load_music(self, filepath: str) -> bool:
        """
        加载音乐文件
        
        Args:
            filepath (str): 音乐文件的路径
            
        Returns:
            bool: 加载是否成功
        """
        print(f"尝试加载音乐文件: {filepath}")
        
        # 如果音频不可用，直接返回False
        if not self.audio_available:
            print("音频系统不可用，跳过加载")
            return False
            
        # 检查文件是否存在
        import os
        if not os.path.exists(filepath):
            print(f"错误: 文件不存在 - {filepath}")
            return False
        
        try:
            # Windows环境下中文文件名处理增强
            # 使用原始文件路径尝试加载
            pygame.mixer.music.load(filepath)
            self.music_loaded = True
            self.music_playing = False
            self.reset_time_variables()
            print(f"成功加载音乐文件: {filepath}")
            return True
        except pygame.error as e:
            print(f"加载音乐文件失败: {e}")
            # 尝试使用文件的绝对路径（有时能解决路径问题）
            abs_path = os.path.abspath(filepath)
            if abs_path != filepath:
                print(f"尝试使用绝对路径: {abs_path}")
                try:
                    pygame.mixer.music.load(abs_path)
                    self.music_loaded = True
                    self.music_playing = False
                    self.reset_time_variables()
                    print(f"成功加载音乐文件(绝对路径): {abs_path}")
                    return True
                except pygame.error as e2:
                    print(f"使用绝对路径加载失败: {e2}")
            
            self.music_loaded = False
            return False
    
    def reset_time_variables(self):
        """重置所有时间相关的变量"""
        self.play_start_time = 0.0
        self.pause_start_time = 0.0
        self.total_paused_time = 0.0
        self.last_position = 0.0
    
    def play(self) -> float:
        """
        开始播放音乐
        
        Returns:
            float: 播放开始时的精确时间戳（毫秒）
        """
        # 即使没有加载实际音乐文件，也允许模拟播放
        # 这对于开发和测试非常有用
        current_time = time.time() * 1000
        
        if self.music_playing:
            return self.get_position()
            
        if self.music_loaded and self.audio_available:
            try:
                # 无论之前是否暂停，都从头开始播放
                # 实际游戏中可以根据需要修改此逻辑
                pygame.mixer.music.play()
            except pygame.error as e:
                print(f"播放音乐失败: {e}")
                
        # 关键修复：设置播放开始时间
        self.play_start_time = current_time
        self.music_playing = True
        self.pause_start_time = 0.0
        
        return self.play_start_time
    
    def get_position(self) -> float:
        """
        获取当前播放位置（毫秒）
        
        关键实现说明：
        - 使用系统时间作为主要时间源，确保在没有实际音乐文件时也能正常工作
        - 即使没有加载音乐文件，也能返回基于系统时间的模拟播放位置
        - 考虑音乐延迟，返回实际应该显示的播放位置
        
        Returns:
            float: 当前播放位置（毫秒）
        """
        if not self.music_playing:
            return self.last_position
        
        # 计算当前系统时间
        current_time = time.time() * 1000
        
        # 计算已播放的时间（减去暂停时间和延迟时间）
        played_time = current_time - self.play_start_time - self.total_paused_time
        
        # 应用音乐延迟，返回实际应该显示的播放位置
        position = max(0.0, played_time - self.music_delay)
        
        # 更新上一次记录的位置
        self.last_position = position
        
        return position
    
    def stop(self) -> None:
        """
        停止音乐播放
        """
        try:
            if self.music_loaded and self.audio_available:
                pygame.mixer.music.stop()
            self.music_playing = False
            self.reset_time_variables()
        except pygame.error as e:
            print(f"停止音乐播放失败: {e}")
    
    def pause(self) -> None:
        """
        暂停音乐播放
        """
        if not self.music_playing:
            return
        
        try:
            if self.music_loaded and self.audio_available:
                pygame.mixer.music.pause()
            
            # 记录暂停开始时间
            self.pause_start_time = time.time() * 1000
            self.music_playing = False
            
            # 保存当前位置
            self.last_position = self.get_position()
        except pygame.error as e:
            print(f"暂停音乐播放失败: {e}")
    
    def resume(self) -> None:
        """
        恢复音乐播放
        """
        if self.music_playing:
            return
        
        try:
            if self.music_loaded and self.audio_available:
                pygame.mixer.music.unpause()
            
            # 计算暂停的时间并添加到总暂停时间中
            if self.pause_start_time > 0:
                current_time = time.time() * 1000
                paused_duration = current_time - self.pause_start_time
                self.total_paused_time += paused_duration
                self.pause_start_time = 0.0
            
            # 重新开始播放时更新播放开始时间，保持时间连续性
            current_time = time.time() * 1000
            self.play_start_time = current_time - self.last_position - self.total_paused_time
            
            self.music_playing = True
        except pygame.error as e:
            print(f"恢复音乐播放失败: {e}")
    
    def set_volume(self, volume: float) -> None:
        """
        设置音乐音量
        
        Args:
            volume (float): 音量值（0.0到1.0之间）
        """
        if not self.audio_available:
            return
            
        try:
            if self.music_loaded:
                # 确保音量在有效范围内
                volume = max(0.0, min(1.0, volume))
                pygame.mixer.music.set_volume(volume)
        except pygame.error as e:
            print(f"设置音量失败: {e}")
    
    def set_music_volume(self, volume: float) -> None:
        """
        设置音乐音量（兼容方法）
        
        Args:
            volume (float): 音量值（0.0到1.0之间）
        """
        # 直接调用set_volume方法
        self.set_volume(volume)
    
    def set_music_delay(self, delay: float) -> None:
        """
        设置音乐延迟
        
        Args:
            delay (float): 延迟值（毫秒）
        """
        # 确保延迟在有效范围内
        self.music_delay = max(-1000.0, min(1000.0, delay))
        print(f"设置音乐延迟: {self.music_delay}ms")
    
    def _load_notes_sfx(self) -> None:
        """
        加载audio/notes/目录下的所有音效文件
        """
        if not self.audio_available:
            return
            
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建notes音效目录路径
        notes_dir = os.path.join(current_dir, 'audio', 'notes')
        
        # 检查目录是否存在
        if not os.path.exists(notes_dir):
            print(f"警告: notes音效目录不存在 - {notes_dir}")
            return
        
        try:
            # 遍历目录下的所有.wav文件
            for filename in os.listdir(notes_dir):
                if filename.endswith('.wav'):
                    # 构建完整路径
                    filepath = os.path.join(notes_dir, filename)
                    # 获取音效名称（不包含扩展名）
                    sound_name = os.path.splitext(filename)[0]
                    
                    # 加载音效
                    sound = pygame.mixer.Sound(filepath)
                    # 设置音量
                    sound.set_volume(self.sfx_volume)
                    # 存储音效
                    self.notes_sfx[sound_name] = sound
                    print(f"成功加载音效: {sound_name}")
        except Exception as e:
            print(f"加载notes音效失败: {e}")
    
    def play_note_sfx(self, sfx_name: str) -> None:
        """
        播放指定的note音效
        
        Args:
            sfx_name (str): 音效名称（不包含扩展名）
        """
        if not self.audio_available or sfx_name not in self.notes_sfx:
            return
        
        # 当延迟的绝对值大于200ms时，禁用notes音效
        if abs(self.music_delay) > 200:
            return
        
        try:
            # 播放音效（只播放一次，不循环）
            self.notes_sfx[sfx_name].play()
        except Exception as e:
            print(f"播放音效 '{sfx_name}' 失败: {e}")
    
    def set_sfx_volume(self, volume: float) -> None:
        """
        设置音效音量
        
        Args:
            volume (float): 音量值（0.0到1.0之间）
        """
        if not self.audio_available:
            return
            
        # 确保音量在有效范围内
        self.sfx_volume = max(0.0, min(1.0, volume))
        
        # 更新所有已加载音效的音量
        for sound_name, sound in self.notes_sfx.items():
            try:
                sound.set_volume(self.sfx_volume)
            except Exception as e:
                print(f"设置音效 '{sound_name}' 音量失败: {e}")
    
    def is_playing(self) -> bool:
        """
        检查音乐是否正在播放
        
        Returns:
            bool: 音乐是否正在播放
        """
        return self.music_playing
    
    def quit(self) -> None:
        """
        清理音频资源
        """
        try:
            if self.music_loaded and self.audio_available:
                pygame.mixer.music.stop()
            if self.audio_available:
                pygame.mixer.quit()
        except pygame.error as e:
            print(f"清理音频资源失败: {e}")
#!/usr/bin/env python3
"""
TRG (Terminal Rhythm Game) - 存档管理模块（单文件版）

这个模块负责游戏成绩的保存、加密和读取功能，采用单文件存储所有谱面的最高分。
"""

import os
import json
import base64
import hashlib
import time
from typing import Dict, Any, List, Optional
import logging

# 配置日志
logger = logging.getLogger('TRG.SaveManager')
logger.setLevel(logging.INFO)

# 清除现有的处理器
if logger.handlers:
    logger.handlers.clear()

# 创建文件处理器 - 使用覆盖模式('w')
log_file = os.path.join(os.path.dirname(__file__), 'save_log.log')
file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
file_handler.setLevel(logging.INFO)

# 设置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# 添加处理器到logger
logger.addHandler(file_handler)


class ChecksumError(Exception):
    """校验和错误异常"""
    pass


class SaveManager:
    """单文件存档管理器 - 仅保存每个谱面的最高分"""
    
    def __init__(self, save_dir: str = None):
        """初始化存档管理器"""
        self._save_dir = save_dir or os.path.join(os.path.dirname(__file__), 'saves')
        self._save_file = os.path.join(self._save_dir, 'highscores.trgs')
        self._encryption_key = self._generate_encryption_key()
        
        # 创建存档目录
        if not os.path.exists(self._save_dir):
            os.makedirs(self._save_dir)
        
        # 如果存档文件不存在，创建一个空的存档文件
        if not os.path.exists(self._save_file):
            self._save_all_scores({})
    
    def _generate_encryption_key(self) -> bytes:
        """生成加密密钥"""
        # 使用系统信息生成相对稳定的密钥
        system_info = os.name.encode()
        base_key = hashlib.sha256(system_info).digest()[:16]  # 使用固定长度的密钥
        return base_key
    
    def _calculate_checksum(self, data: bytes) -> str:
        """计算数据校验和"""
        return hashlib.md5(data).hexdigest()
    
    def _xor_encrypt(self, data: bytes, key: bytes) -> bytes:
        """简单的XOR加密"""
        result = bytearray()
        key_len = len(key)
        for i, byte in enumerate(data):
            result.append(byte ^ key[i % key_len])
        return bytes(result)
    
    def _encrypt_data(self, data: Dict[str, Any]) -> bytes:
        """加密数据"""
        try:
            # 1. 转换为JSON字符串 (确保序列化一致)
            json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
            json_bytes = json_str.encode('utf-8')
            
            # 2. 计算校验和
            checksum = self._calculate_checksum(json_bytes)
            
            # 3. 创建包含数据和校验和的包
            package = {
                'data': json.loads(json_str),  # 重新解析确保类型正确
                'checksum': checksum,
                'timestamp': int(time.time())  # 添加时间戳用于版本控制
            }
            
            # 4. 转换包为JSON并加密
            package_bytes = json.dumps(package, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            encrypted = self._xor_encrypt(package_bytes, self._encryption_key)
            
            # 5. Base64编码
            encoded = base64.b64encode(encrypted)
            
            return encoded
        except Exception as e:
            logger.error(f"加密数据时出错: {e}")
            raise
    
    def _decrypt_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        """解密数据"""
        try:
            # 1. Base64解码
            decoded = base64.b64decode(encrypted_data)
            
            # 2. XOR解密
            decrypted = self._xor_encrypt(decoded, self._encryption_key)
            
            # 3. 解析JSON
            package = json.loads(decrypted.decode('utf-8'))
            
            # 4. 验证包结构
            if not isinstance(package, dict) or 'data' not in package or 'checksum' not in package:
                raise ValueError("无效的存档格式")
            
            # 5. 提取数据和校验和
            data = package['data']
            stored_checksum = package['checksum']
            
            # 6. 验证校验和
            json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
            calculated_checksum = self._calculate_checksum(json_str.encode('utf-8'))
            
            if calculated_checksum != stored_checksum:
                logger.error("校验和不匹配: 计算值=%s, 期望值=%s", 
                             calculated_checksum, stored_checksum)
                raise ChecksumError("存档数据校验失败，可能已被修改")
            
            return data
        except ChecksumError:
            raise
        except Exception as e:
            logger.error(f"解密存档失败: {e}")
            raise
    
    def _load_all_scores(self) -> Dict[str, Dict[str, Any]]:
        """加载所有最高分数据"""
        try:
            if not os.path.exists(self._save_file):
                return {}
            
            with open(self._save_file, 'rb') as f:
                encrypted_data = f.read()
            
            data = self._decrypt_data(encrypted_data)
            return data.get('highscores', {})
        except Exception as e:
            logger.error(f"加载存档失败: {e}")
            return {}
    
    def _save_all_scores(self, highscores: Dict[str, Dict[str, Any]]) -> bool:
        """保存所有最高分数据"""
        try:
            data = {
                'highscores': highscores,
                'version': '2.0',  # 版本号标识单文件格式
                'last_modified': int(time.time())
            }
            
            encrypted_data = self._encrypt_data(data)
            
            # 写入文件
            with open(self._save_file, 'wb') as f:
                f.write(encrypted_data)
            
            logger.info(f"成功保存所有最高分数据到 {self._save_file}")
            return True
        except Exception as e:
            logger.error(f"保存存档失败: {e}")
            return False
    
    def save_score(self, chart_id: str, score_data: Dict[str, Any]) -> bool:
        """
        保存游戏成绩（仅当是新的最高分时）
        
        Args:
            chart_id (str): 谱面ID
            score_data (Dict[str, Any]): 成绩数据，包含分数、判定等信息
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 确保数据包含必要的字段
            if 'score' not in score_data:
                raise ValueError("成绩数据必须包含分数")
            
            # 添加时间戳
            score_data['timestamp'] = int(time.time())
            
            # 加载现有最高分
            highscores = self._load_all_scores()
            
            # 检查是否是新的最高分
            current_best = highscores.get(chart_id, {})
            if current_best.get('score', 0) >= score_data['score']:
                logger.info(f"不是新高分，无需保存。当前最高分: {current_best.get('score', 0)}, 新分数: {score_data['score']}")
                return True  # 返回True表示操作成功，即使没有更新分数
            
            # 更新为新的最高分
            highscores[chart_id] = score_data
            
            # 保存到文件
            success = self._save_all_scores(highscores)
            
            if success:
                grade = score_data.get('grade', '')
                logger.info(f"成功保存新高分: {chart_id} - {score_data['score']} (Grade: {grade})")
            
            return success
        except Exception as e:
            logger.error(f"保存成绩失败: {e}")
            return False
    
    def get_scores(self, chart_id: str = None) -> List[Dict[str, Any]]:
        """
        获取成绩列表（单文件版）
        
        Args:
            chart_id (str, optional): 谱面ID，如果为None则获取所有成绩
            
        Returns:
            List[Dict[str, Any]]: 成绩列表
        """
        try:
            highscores = self._load_all_scores()
            
            if chart_id is not None:
                # 获取特定谱面的最高分
                if chart_id in highscores:
                    # 包装成绩数据，保持向后兼容
                    return [{
                        'chart_id': chart_id,
                        'score_data': highscores[chart_id],
                        'timestamp': highscores[chart_id].get('timestamp', 0)
                    }]
                return []
            else:
                # 获取所有谱面的最高分
                scores = []
                for cid, score_data in highscores.items():
                    scores.append({
                        'chart_id': cid,
                        'score_data': score_data,
                        'timestamp': score_data.get('timestamp', 0)
                    })
                
                # 按分数降序排序
                scores.sort(key=lambda x: x['score_data'].get('score', 0), reverse=True)
                
                return scores
        except Exception as e:
            logger.error(f"获取成绩列表失败: {e}")
            return []
    
    def get_best_score(self, chart_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定谱面的最高分
        
        Args:
            chart_id (str): 谱面ID
            
        Returns:
            Optional[Dict[str, Any]]: 最高分数据，如果没有则返回None
        """
        try:
            highscores = self._load_all_scores()
            if chart_id in highscores:
                # 包装返回格式，保持向后兼容
                return {
                    'chart_id': chart_id,
                    'score_data': highscores[chart_id],
                    'timestamp': highscores[chart_id].get('timestamp', 0)
                }
            return None
        except Exception as e:
            logger.error(f"获取最高分失败: {e}")
            return None
    
    def delete_score(self, chart_id: str) -> bool:
        """
        删除指定谱面的最高分
        
        Args:
            chart_id (str): 谱面ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            highscores = self._load_all_scores()
            
            if chart_id in highscores:
                del highscores[chart_id]
                success = self._save_all_scores(highscores)
                if success:
                    logger.info(f"成功删除谱面 {chart_id} 的最高分")
                return success
            return False
        except Exception as e:
            logger.error(f"删除成绩失败: {e}")
            return False
    
    def clear_all_scores(self) -> bool:
        """
        清空所有成绩记录
        
        Returns:
            bool: 是否清空成功
        """
        try:
            # 创建一个空的成绩字典并保存
            success = self._save_all_scores({})
            if success:
                logger.info("成功清空所有成绩记录")
            return success
        except Exception as e:
            logger.error(f"清空成绩失败: {e}")
            return False
    
    def get_best_score_raw(self, chart_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定谱面的最高分（原始数据格式，不进行包装）
        
        Args:
            chart_id (str): 谱面ID
            
        Returns:
            Optional[Dict[str, Any]]: 最高分原始数据，如果没有则返回None
        """
        try:
            highscores = self._load_all_scores()
            return highscores.get(chart_id)
        except Exception as e:
            logger.error(f"获取原始最高分失败: {e}")
            return None
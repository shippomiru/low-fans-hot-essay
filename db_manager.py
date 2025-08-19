#!/usr/bin/env python3
"""
数据库操作管理类
处理所有数据库相关操作，确保数据完整性和事务一致性
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from database import get_connection, init_database, check_database_exists


class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self):
        """初始化数据库管理器"""
        if not check_database_exists():
            init_database()
        self.ensure_database_ready()
    
    def ensure_database_ready(self):
        """确保数据库已准备好"""
        conn = get_connection()
        cursor = conn.cursor()
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        
        if len(tables) < 6:  # 应该有6个表
            init_database()
    
    # ==================== 原始数据操作 ====================
    
    def save_raw_response(self, api_type: str, request_key: str, 
                          request_params: Dict, response_data: Dict) -> bool:
        """
        保存API原始响应（最重要！）
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO api_raw_responses 
                (api_type, request_key, request_params, response_data, 
                 response_code, cost_money, remain_money)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                api_type,
                request_key,
                json.dumps(request_params, ensure_ascii=False),
                json.dumps(response_data, ensure_ascii=False),
                response_data.get('code', -1),
                response_data.get('cost_money', 0),
                response_data.get('remain_money', 0)
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ 保存原始响应失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_raw_response(self, api_type: str, request_key: str) -> Optional[Dict]:
        """获取原始响应数据"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT response_data FROM api_raw_responses
            WHERE api_type = ? AND request_key = ?
        ''', (api_type, request_key))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row['response_data'])
        return None
    
    # ==================== 公众号操作 ====================
    
    def save_account(self, biz: str, nick_name: str, ghid: str = None) -> int:
        """保存或更新公众号信息"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO accounts (biz, nick_name, ghid)
                VALUES (?, ?, ?)
            ''', (biz, nick_name, ghid))
            
            if cursor.rowcount == 0:
                # 已存在，更新信息
                cursor.execute('''
                    UPDATE accounts 
                    SET nick_name = ?, ghid = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE biz = ?
                ''', (nick_name, ghid, biz))
            
            conn.commit()
            
            # 获取account_id
            cursor.execute('SELECT id FROM accounts WHERE biz = ?', (biz,))
            result = cursor.fetchone()
            return result['id']
        except Exception as e:
            print(f"❌ 保存公众号失败: {e}")
            conn.rollback()
            return -1
        finally:
            conn.close()
    
    def update_account_progress(self, biz: str, last_page: int, 
                                stop_flag: bool = False) -> bool:
        """更新公众号采集进度"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE accounts 
                SET last_page = ?, stop_flag = ?, 
                    last_fetch_time = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE biz = ?
            ''', (last_page, stop_flag, biz))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ 更新公众号进度失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_account_info(self, biz: str) -> Optional[Dict]:
        """获取公众号信息"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM accounts WHERE biz = ?', (biz,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_pending_accounts(self) -> List[Dict]:
        """获取待处理的公众号列表"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM accounts 
            WHERE status != 'completed' AND stop_flag = 0
            ORDER BY updated_at
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ==================== 文章操作 ====================
    
    def save_article_from_list(self, account_id: int, article_data: Dict) -> int:
        """
        从接口一保存文章基本信息
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # 提取核心字段
            url = article_data.get('url')
            title = article_data.get('title')
            digest = article_data.get('digest')
            post_time_str = article_data.get('post_time_str')
            post_time = article_data.get('post_time')
            original = article_data.get('original', 0)
            
            cursor.execute('''
                INSERT OR IGNORE INTO articles 
                (account_id, url, title, digest, post_time_str, post_time, 
                 original, position, cover_url, appmsgid, fetch_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'list_only')
            ''', (
                account_id, url, title, digest, post_time_str, post_time,
                original, 
                article_data.get('position'),
                article_data.get('cover_url'),
                article_data.get('appmsgid')
            ))
            
            if cursor.rowcount == 0:
                # 文章已存在，获取其ID
                cursor.execute('SELECT id FROM articles WHERE url = ?', (url,))
                result = cursor.fetchone()
                article_id = result['id']
            else:
                article_id = cursor.lastrowid
            
            conn.commit()
            return article_id
        except Exception as e:
            print(f"❌ 保存文章失败: {e}")
            conn.rollback()
            return -1
        finally:
            conn.close()
    
    def save_article_stats(self, article_url: str, stats_data: Dict) -> bool:
        """
        保存文章统计数据（接口二）
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # 先获取article_id
            cursor.execute('SELECT id FROM articles WHERE url = ?', (article_url,))
            article = cursor.fetchone()
            
            if not article:
                print(f"⚠️ 文章不存在: {article_url}")
                return False
            
            article_id = article['id']
            
            # 保存统计数据
            cursor.execute('''
                INSERT OR REPLACE INTO article_stats 
                (article_id, read_num, zan, looking, share_num, 
                 collect_num, comment_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                article_id,
                stats_data.get('read', 0),
                stats_data.get('zan', 0),
                stats_data.get('looking', 0),
                stats_data.get('share_num', 0),
                stats_data.get('collect_num', 0),
                stats_data.get('comment_count', 0)
            ))
            
            # 更新文章状态
            cursor.execute('''
                UPDATE articles 
                SET fetch_status = 'stats_fetched', 
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (article_id,))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ 保存文章统计失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def save_article_content(self, article_url: str, content_data: Dict) -> bool:
        """
        保存文章内容（接口三）
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # 先获取article_id
            cursor.execute('SELECT id FROM articles WHERE url = ?', (article_url,))
            article = cursor.fetchone()
            
            if not article:
                print(f"⚠️ 文章不存在: {article_url}")
                return False
            
            article_id = article['id']
            
            # 保存内容
            cursor.execute('''
                INSERT OR REPLACE INTO article_contents 
                (article_id, title, content, content_html, 
                 copyright_stat, source_url, ip_wording)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                article_id,
                content_data.get('title'),
                content_data.get('content'),
                content_data.get('content_multi_text'),
                content_data.get('copyright_stat'),
                content_data.get('source_url'),
                content_data.get('ip_wording')
            ))
            
            # 更新文章状态
            cursor.execute('''
                UPDATE articles 
                SET fetch_status = 'content_fetched', 
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (article_id,))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ 保存文章内容失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_articles_by_status(self, account_id: int, status: str) -> List[Dict]:
        """获取指定状态的文章列表"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM articles 
            WHERE account_id = ? AND fetch_status = ?
            ORDER BY post_time_str DESC
        ''', (account_id, status))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_unfetched_articles(self, account_id: int) -> List[Dict]:
        """获取未完成采集的文章"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM articles 
            WHERE account_id = ? AND fetch_status != 'content_fetched'
            ORDER BY post_time_str DESC
        ''', (account_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ==================== 进度管理 ====================
    
    def save_progress(self, task_id: str, account_biz: str = None, 
                      current_page: int = 0, current_article_url: str = None,
                      current_step: str = None, remain_money: float = None) -> bool:
        """保存采集进度"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO fetch_progress 
                (task_id, account_biz, current_page, current_article_url, 
                 current_step, last_remain_money, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (task_id, account_biz, current_page, current_article_url, 
                  current_step, remain_money))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ 保存进度失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_last_progress(self, task_id: str) -> Optional[Dict]:
        """获取最后的进度"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM fetch_progress 
            WHERE task_id = ? 
            ORDER BY updated_at DESC 
            LIMIT 1
        ''', (task_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    # ==================== 统计查询 ====================
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        conn = get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # 公众号统计
        cursor.execute('SELECT COUNT(*) as total FROM accounts')
        stats['total_accounts'] = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as completed FROM accounts WHERE status = 'completed'")
        stats['completed_accounts'] = cursor.fetchone()['completed']
        
        # 文章统计
        cursor.execute('SELECT COUNT(*) as total FROM articles')
        stats['total_articles'] = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as fetched FROM articles WHERE fetch_status = 'content_fetched'")
        stats['fetched_articles'] = cursor.fetchone()['fetched']
        
        # API调用统计
        cursor.execute('SELECT SUM(cost_money) as total_cost FROM api_raw_responses')
        result = cursor.fetchone()
        stats['total_cost'] = result['total_cost'] if result['total_cost'] else 0
        
        cursor.execute('SELECT remain_money FROM api_raw_responses ORDER BY created_at DESC LIMIT 1')
        result = cursor.fetchone()
        stats['current_balance'] = result['remain_money'] if result else 0
        
        conn.close()
        return stats
    
    def check_article_exists(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        检查文章是否存在及其状态
        返回: (是否存在, 采集状态)
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT fetch_status FROM articles WHERE url = ?', (url,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return True, row['fetch_status']
        return False, None


if __name__ == "__main__":
    # 测试数据库管理器
    db = DatabaseManager()
    stats = db.get_statistics()
    print(f"数据库统计: {stats}")
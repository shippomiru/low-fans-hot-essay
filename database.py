#!/usr/bin/env python3
"""
数据库初始化和连接管理
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
import os

DATABASE_PATH = "wechat_articles.db"


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # 返回字典格式
    return conn


def init_database():
    """初始化数据库，创建所有表"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. 原始响应数据表（最重要！完整保存所有API响应）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_raw_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_type TEXT NOT NULL,  -- post_history/read_zan_pro/article_detail
            request_key TEXT NOT NULL,  -- biz+page 或 article_url
            request_params TEXT NOT NULL,  -- 请求参数JSON
            response_data TEXT NOT NULL,  -- 完整原始响应JSON
            response_code INTEGER,
            cost_money REAL,
            remain_money REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(api_type, request_key)  -- 避免重复存储
        )
    ''')
    
    # 创建索引
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_api_raw_type_key 
        ON api_raw_responses(api_type, request_key)
    ''')
    
    # 2. 公众号表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            biz TEXT NOT NULL UNIQUE,
            nick_name TEXT NOT NULL,
            ghid TEXT,
            head_img TEXT,
            signature TEXT,
            status TEXT DEFAULT 'pending',  -- pending/processing/completed
            last_page INTEGER DEFAULT 0,
            total_articles INTEGER DEFAULT 0,
            fetched_articles INTEGER DEFAULT 0,
            stop_flag BOOLEAN DEFAULT 0,  -- 是否已到达2025年前
            last_fetch_time TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 3. 文章表（核心信息）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            url TEXT NOT NULL UNIQUE,
            appmsgid TEXT,
            title TEXT NOT NULL,
            digest TEXT,
            author TEXT,
            post_time_str TEXT,  -- 发布时间字符串
            post_time INTEGER,  -- 时间戳
            position INTEGER,
            cover_url TEXT,
            original INTEGER DEFAULT 0,  -- 1原创 0未声明 2转载
            fetch_status TEXT DEFAULT 'list_only',  -- list_only/stats_fetched/content_fetched
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    ''')
    
    # 创建索引
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_articles_post_time ON articles(post_time_str)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_articles_fetch_status ON articles(fetch_status)
    ''')
    
    # 4. 文章统计数据表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS article_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL UNIQUE,
            read_num INTEGER DEFAULT 0,
            zan INTEGER DEFAULT 0,  -- 点赞
            looking INTEGER DEFAULT 0,  -- 在看
            share_num INTEGER DEFAULT 0,  -- 转发
            collect_num INTEGER DEFAULT 0,  -- 收藏
            comment_count INTEGER DEFAULT 0,  -- 评论
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (article_id) REFERENCES articles(id)
        )
    ''')
    
    # 5. 文章内容表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS article_contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL UNIQUE,
            title TEXT,  -- 接口三返回的标题
            content TEXT,  -- 纯文本内容
            content_html TEXT,  -- HTML内容
            copyright_stat INTEGER,
            source_url TEXT,
            ip_wording TEXT,
            picture_urls TEXT,  -- JSON数组
            video_urls TEXT,  -- JSON数组
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (article_id) REFERENCES articles(id)
        )
    ''')
    
    # 6. 采集进度表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fetch_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            account_biz TEXT,
            current_page INTEGER DEFAULT 0,
            current_article_url TEXT,
            current_step TEXT,  -- list/stats/content
            status TEXT DEFAULT 'running',  -- running/paused/completed/error
            error_count INTEGER DEFAULT 0,
            last_error TEXT,
            last_remain_money REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成: {DATABASE_PATH}")


def check_database_exists():
    """检查数据库是否存在"""
    return os.path.exists(DATABASE_PATH)


if __name__ == "__main__":
    init_database()
#!/usr/bin/env python3
"""
配置文件 - 从环境变量加载配置
"""

import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# API配置
API_KEY = os.getenv('API_KEY', '')
MIN_BALANCE = float(os.getenv('MIN_BALANCE', '0.2'))

# 数据库配置
DATABASE_PATH = "wechat_articles.db"

# API基础URL
BASE_URL = "https://www.dajiala.com/fbmain/monitor/v3"

# 目标公众号列表
TARGET_ACCOUNTS = [
    ("MzIxOTAzOTE4NQ==", "江涌的心理研习堂"),
    ("MzkyNjc0Mjg0NA==", "里小克的心理拓荒笔记"),
    ("Mzg4MzY3MDEwMw==", "若琳亲子"),
    ("MzU1ODc0OTA1MQ==", "芳心可悦"),
    ("MzkzNTY1NjgwMw==", "栗子在吗"),
    ("MzI0NTcxMTE1Mg==", "婉又成长社"),
    ("MzUyNDgwNDM0MQ==", "梁芝心理话"),
    ("MzkwNjYyMDg5OQ==", "彤彤的成长空间"),
    ("MzkzMzc0NjYwNA==", "心理咨询师高薇")
]
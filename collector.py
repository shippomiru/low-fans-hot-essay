#!/usr/bin/env python3
"""
微信公众号文章采集器
核心采集逻辑，确保数据完整性和断点续传
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from db_manager import DatabaseManager


class WechatArticleCollector:
    """微信公众号文章采集器"""
    
    def __init__(self, api_key: str = None, min_balance: float = None):
        """
        初始化采集器
        Args:
            api_key: API密钥（如果不提供，从config导入）
            min_balance: 最小余额阈值（如果不提供，从config导入）
        """
        if api_key is None:
            from config import API_KEY
            api_key = API_KEY
        if min_balance is None:
            from config import MIN_BALANCE
            min_balance = MIN_BALANCE
            
        self.api_key = api_key
        self.base_url = "https://www.dajiala.com/fbmain/monitor/v3"
        self.min_balance = min_balance
        self.db = DatabaseManager()
        self.current_balance = 0
        self.task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 初始化时获取当前余额
        self.update_balance()
    
    # ==================== 余额查询 ====================
    
    def get_remain_money(self) -> float:
        """
        调用接口获取当前余额（不消耗费用）
        Returns:
            当前余额，失败返回0
        """
        url = f"{self.base_url}/get_remain_money"
        payload = {
            "key": self.api_key,
            "verifycode": ""
        }
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') == 0:
                return result.get('remain_money', 0)
            else:
                print(f"  ⚠️ 获取余额失败: {result.get('msg', '未知错误')}")
                return 0
        except Exception as e:
            print(f"  ⚠️ 获取余额异常: {e}")
            return 0
    
    def update_balance(self):
        """更新当前余额"""
        self.current_balance = self.get_remain_money()
        print(f"  💰 当前余额: {self.current_balance} 元")
    
    # ==================== API调用方法 ====================
    
    def call_api_1_post_history(self, biz: str, page: int = 1) -> Optional[Dict]:
        """
        调用接口一：获取公众号文章列表
        """
        url = f"{self.base_url}/post_history"
        request_key = f"{biz}_{page}"
        
        # 先检查是否已有缓存
        cached = self.db.get_raw_response("post_history", request_key)
        if cached:
            print(f"  📦 使用缓存数据 (biz={biz}, page={page})")
            # 只有成功的响应才更新余额
            if cached.get('code') == 0 and cached.get('remain_money') is not None:
                self.current_balance = cached.get('remain_money', 0)
            return cached
        
        # 请求参数
        payload = {
            "biz": biz,
            "url": "",
            "name": "",
            "page": page,
            "key": self.api_key,
            "verifycode": ""
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            print(f"  🔄 调用接口一 (biz={biz}, page={page})")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            # 保存原始响应
            self.db.save_raw_response("post_history", request_key, payload, result)
            
            # 更新余额
            self.current_balance = result.get('remain_money', 0)
            
            return result
        except Exception as e:
            print(f"  ❌ 接口一调用失败: {e}")
            return None
    
    def call_api_2_read_zan(self, article_url: str) -> Optional[Dict]:
        """
        调用接口二：获取文章数据
        """
        url = f"{self.base_url}/read_zan_pro"
        request_key = article_url
        
        # 先检查是否已有缓存
        cached = self.db.get_raw_response("read_zan_pro", request_key)
        if cached:
            print(f"    📦 使用缓存数据")
            # 只有成功的响应才更新余额，错误响应（如文章已删除）不更新
            if cached.get('code') == 0 and cached.get('remain_money') is not None:
                self.current_balance = cached.get('remain_money', 0)
            elif cached.get('code') == 101:
                # 文章已删除或违规，不需要重试
                print(f"    ⚠️ 文章不可访问: {cached.get('msg', '未知原因')}")
            return cached
        
        payload = {
            "url": article_url,
            "key": self.api_key,
            "verifycode": ""
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            print(f"    🔄 调用接口二")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            # 保存原始响应
            self.db.save_raw_response("read_zan_pro", request_key, payload, result)
            
            # 更新余额
            self.current_balance = result.get('remain_money', 0)
            
            return result
        except Exception as e:
            print(f"    ❌ 接口二调用失败: {e}")
            return None
    
    def call_api_3_article_detail(self, article_url: str) -> Optional[Dict]:
        """
        调用接口三：获取文章全文
        """
        url = f"{self.base_url}/article_detail"
        request_key = article_url
        
        # 先检查是否已有缓存
        cached = self.db.get_raw_response("article_detail", request_key)
        if cached:
            print(f"    📦 使用缓存数据")
            # 只有成功的响应才更新余额，错误响应（如文章已删除）不更新
            if cached.get('code') == 0 and cached.get('remain_money') is not None:
                self.current_balance = cached.get('remain_money', 0)
            elif cached.get('code') == 101:
                # 文章已删除或违规，不需要重试
                print(f"    ⚠️ 文章不可访问: {cached.get('msg', '未知原因')}")
            return cached
        
        params = {
            "url": article_url,
            "key": self.api_key,
            "mode": 2
        }
        
        try:
            print(f"    🔄 调用接口三")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            # 保存原始响应
            self.db.save_raw_response("article_detail", request_key, params, result)
            
            # 更新余额
            self.current_balance = result.get('remain_money', 0)
            
            return result
        except Exception as e:
            print(f"    ❌ 接口三调用失败: {e}")
            return None
    
    # ==================== 余额检查 ====================
    
    def check_balance(self) -> bool:
        """检查余额是否充足"""
        if self.current_balance < self.min_balance:
            print(f"\n⚠️ 余额不足！当前余额: {self.current_balance}元")
            print("请充值后继续...")
            # 保存进度
            self.db.save_progress(
                self.task_id, 
                remain_money=self.current_balance
            )
            return False
        return True
    
    # ==================== 核心采集流程 ====================
    
    def collect_account_articles(self, biz: str, nick_name: str = None) -> bool:
        """
        采集单个公众号的所有2025年文章
        """
        print(f"\n{'='*60}")
        print(f"开始采集公众号: {nick_name or biz}")
        print(f"BIZ: {biz}")
        print(f"{'='*60}")
        
        # 保存或更新公众号信息
        account_info = self.db.get_account_info(biz)
        if not account_info:
            account_id = self.db.save_account(biz, nick_name or "未知", None)
            last_page = 0
            stop_flag = False
        else:
            account_id = account_info['id']
            last_page = account_info['last_page']
            stop_flag = account_info['stop_flag']
            
            if stop_flag:
                print(f"  ⏹️ 该公众号已完成采集（已到达2025年前）")
                return True
        
        # 从上次中断的页面继续
        current_page = last_page + 1 if last_page > 0 else 1
        
        while True:
            print(f"\n📄 获取第 {current_page} 页文章列表...")
            
            # 保存进度
            self.db.save_progress(self.task_id, biz, current_page, None, "list")
            
            # 调用接口一
            result = self.call_api_1_post_history(biz, current_page)
            
            if not result or result.get('code') != 0:
                print(f"  ❌ 获取文章列表失败")
                break
            
            # 检查余额
            if not self.check_balance():
                return False
            
            articles = result.get('data', [])
            if not articles:
                print(f"  ✅ 已获取所有文章")
                self.db.update_account_progress(biz, current_page, True)
                break
            
            print(f"  📊 本页获取 {len(articles)} 篇文章")
            
            # 检查是否有2025年之前的文章
            has_old_article = False
            articles_2025 = []
            
            for article in articles:
                post_time_str = article.get('post_time_str', '')
                if post_time_str and post_time_str < '2025-01-01':
                    has_old_article = True
                    print(f"  ⏹️ 发现2025年前文章({post_time_str})，停止获取")
                    break
                articles_2025.append(article)
            
            # 保存2025年的文章
            for article in articles_2025:
                article_id = self.db.save_article_from_list(account_id, article)
                if article_id > 0:
                    print(f"  ✅ 保存文章: {article.get('title')[:30]}...")
            
            # 更新公众号进度
            self.db.update_account_progress(biz, current_page, has_old_article)
            
            if has_old_article:
                print(f"  ✅ 已到达2025年前，停止获取列表")
                break
            
            # 继续下一页
            current_page += 1
            time.sleep(0.5)  # 避免请求过快
        
        # 获取该公众号所有未完成的文章
        print(f"\n📊 开始获取文章详细数据...")
        self.fetch_articles_details(account_id)
        
        return True
    
    def fetch_articles_details(self, account_id: int):
        """
        获取文章的统计数据和全文内容
        """
        # 获取所有未完成的文章
        unfetched_articles = self.db.get_unfetched_articles(account_id)
        
        if not unfetched_articles:
            print(f"  ✅ 所有文章已完成采集")
            return
        
        print(f"  📊 需要获取详情的文章数: {len(unfetched_articles)}")
        
        for idx, article in enumerate(unfetched_articles, 1):
            article_url = article['url']
            title = article['title']
            status = article['fetch_status']
            
            print(f"\n  [{idx}/{len(unfetched_articles)}] {title[:30]}...")
            
            # 保存进度
            self.db.save_progress(
                self.task_id, 
                current_article_url=article_url,
                current_step="stats" if status == "list_only" else "content"
            )
            
            # 1. 获取统计数据（如果还没获取）
            if status == 'list_only':
                result = self.call_api_2_read_zan(article_url)
                if result and result.get('code') == 0:
                    data = result.get('data', {})
                    self.db.save_article_stats(article_url, data)
                    print(f"    ✅ 统计数据: 阅读{data.get('read',0)} 点赞{data.get('zan',0)}")
                    
                    if not self.check_balance():
                        return
                    
                    status = 'stats_fetched'
                    time.sleep(0.3)
                elif result and result.get('code') == 101:
                    # 文章已删除或违规，标记为特殊状态，不再重试
                    print(f"    ⏭️ 跳过不可访问的文章")
                    # 可以考虑更新文章状态为'unavailable'或直接跳过
                    continue
                else:
                    print(f"    ❌ 获取统计数据失败")
                    continue
            
            # 2. 获取文章全文（如果还没获取）
            if status == 'stats_fetched':
                result = self.call_api_3_article_detail(article_url)
                if result and result.get('code') == 0:
                    self.db.save_article_content(article_url, result)
                    content = result.get('content', '')
                    print(f"    ✅ 文章内容: {len(content)}字符")
                    
                    if not self.check_balance():
                        return
                    
                    time.sleep(0.3)
                else:
                    print(f"    ❌ 获取文章内容失败")
    
    def collect_multiple_accounts(self, accounts: List[Tuple[str, str]]):
        """
        批量采集多个公众号
        Args:
            accounts: [(biz, nick_name), ...]
        """
        print(f"\n{'='*60}")
        print(f"批量采集任务")
        print(f"任务ID: {self.task_id}")
        print(f"公众号数量: {len(accounts)}")
        print(f"{'='*60}")
        
        for idx, (biz, nick_name) in enumerate(accounts, 1):
            print(f"\n[{idx}/{len(accounts)}] 处理公众号: {nick_name}")
            
            success = self.collect_account_articles(biz, nick_name)
            
            if not success:
                print(f"\n⚠️ 采集中断，请充值后继续")
                break
            
            if idx < len(accounts):
                time.sleep(1)  # 公众号之间的延迟
        
        # 输出统计信息
        self.print_statistics()
    
    def resume_collection(self):
        """
        从断点恢复采集
        """
        print(f"\n{'='*60}")
        print(f"恢复采集任务")
        print(f"{'='*60}")
        
        # 1. 获取所有公众号的状态
        from database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # 获取所有公众号及其文章状态统计
        cursor.execute("""
            SELECT 
                a.id, 
                a.biz, 
                a.nick_name, 
                a.stop_flag, 
                a.last_page,
                COUNT(art.id) as total_articles,
                COUNT(CASE WHEN art.fetch_status = 'list_only' THEN 1 END) as list_only_count,
                COUNT(CASE WHEN art.fetch_status = 'stats_fetched' THEN 1 END) as stats_fetched_count,
                COUNT(CASE WHEN art.fetch_status = 'content_fetched' THEN 1 END) as content_fetched_count
            FROM accounts a
            LEFT JOIN articles art ON art.account_id = a.id
            GROUP BY a.id, a.biz, a.nick_name, a.stop_flag, a.last_page
            ORDER BY a.stop_flag, a.updated_at
        """)
        all_accounts = cursor.fetchall()
        conn.close()
        
        if not all_accounts:
            print("没有公众号数据")
            return
        
        # 2. 分类统计
        need_list = []  # A类：需要继续获取列表的
        need_details_only = []  # B类：只需要获取文章详情的
        completed = []  # C类：已完成的
        
        for acc in all_accounts:
            unfetched = acc['list_only_count'] + acc['stats_fetched_count']
            
            if acc['stop_flag'] == 0:
                # 列表未完成（无论文章是否完成都要继续）
                need_list.append({
                    'id': acc['id'],
                    'biz': acc['biz'],
                    'nick_name': acc['nick_name'],
                    'last_page': acc['last_page'],
                    'total_articles': acc['total_articles'],
                    'unfetched_articles': unfetched
                })
            elif unfetched > 0:
                # 列表已完成但有文章未完成
                need_details_only.append({
                    'id': acc['id'],
                    'biz': acc['biz'],
                    'nick_name': acc['nick_name'],
                    'unfetched_articles': unfetched,
                    'list_only': acc['list_only_count'],
                    'stats_fetched': acc['stats_fetched_count']
                })
            else:
                # 完全完成
                completed.append(acc['nick_name'])
        
        # 3. 检查是否有未开始的公众号
        from config import TARGET_ACCOUNTS
        collected_biz = [acc['biz'] for acc in all_accounts]
        not_started = []
        for biz, nick_name in TARGET_ACCOUNTS:
            if biz not in collected_biz:
                not_started.append((biz, nick_name))
        
        # 4. 显示采集状态
        print(f"\n📊 采集状态统计:")
        print(f"  配置的公众号总数: {len(TARGET_ACCOUNTS)}")
        print(f"  数据库中的公众号: {len(all_accounts)}")
        print(f"  未开始采集: {len(not_started)} 个")
        print(f"  需继续获取列表: {len(need_list)} 个")
        print(f"  仅需获取文章详情: {len(need_details_only)} 个")
        print(f"  已完成: {len(completed)} 个")
        
        if not_started:
            print("\n未开始采集的公众号:")
            for biz, name in not_started:
                print(f"  - {name}")
        
        if not need_list and not need_details_only and not not_started:
            print("\n✅ 所有采集任务已完成！")
            if completed:
                print("已完成的公众号:")
                for name in completed:
                    print(f"  - {name}")
            return
        
        # 4. 处理A类：需要继续获取列表的公众号
        if need_list:
            print(f"\n📋 第一步：继续获取文章列表")
            for acc in need_list:
                print(f"\n  [{need_list.index(acc)+1}/{len(need_list)}] {acc['nick_name']}")
                print(f"    从第 {acc['last_page']+1} 页继续")
                print(f"    已有 {acc['total_articles']} 篇文章，{acc['unfetched_articles']} 篇未完成")
                
                # 继续采集（会自动处理列表和文章详情）
                success = self.collect_account_articles(acc['biz'], acc['nick_name'])
                
                if not success:
                    print("\n⚠️ 采集中断（余额不足或错误）")
                    return
        
        # 5. 处理B类：只需要获取文章详情的公众号
        if need_details_only:
            print(f"\n📊 第二步：获取文章详情")
            for acc in need_details_only:
                print(f"\n  [{need_details_only.index(acc)+1}/{len(need_details_only)}] {acc['nick_name']}")
                print(f"    需要获取 {acc['unfetched_articles']} 篇文章详情")
                print(f"    其中：仅列表 {acc['list_only']} 篇，已获统计 {acc['stats_fetched']} 篇")
                
                # 获取文章详情
                self.fetch_articles_details(acc['id'])
                
                # 检查余额
                if not self.check_balance():
                    print("\n⚠️ 余额不足，采集中断")
                    return
        
        # 6. 处理未开始的公众号
        if not_started:
            print(f"\n📝 第三步：开始新的公众号采集")
            print(f"  需要采集 {len(not_started)} 个新公众号")
            
            for idx, (biz, nick_name) in enumerate(not_started, 1):
                print(f"\n  [{idx}/{len(not_started)}] 开始采集: {nick_name}")
                
                success = self.collect_account_articles(biz, nick_name)
                
                if not success:
                    print("\n⚠️ 采集中断（余额不足或错误）")
                    return
                
                if idx < len(not_started):
                    time.sleep(1)  # 公众号之间的延迟
        
        # 7. 显示最终统计
        print("\n" + "="*60)
        self.print_statistics()
    
    def print_statistics(self):
        """打印统计信息"""
        stats = self.db.get_statistics()
        
        print(f"\n{'='*60}")
        print(f"采集统计")
        print(f"{'='*60}")
        print(f"公众号总数: {stats['total_accounts']}")
        print(f"已完成公众号: {stats['completed_accounts']}")
        print(f"文章总数: {stats['total_articles']}")
        print(f"已完成文章: {stats['fetched_articles']}")
        print(f"总消耗金额: {stats['total_cost']:.2f}元")
        print(f"当前余额: {stats['current_balance']:.2f}元")


if __name__ == "__main__":
    # 测试采集器
    API_KEY = "JZL52e2eabf3082bd9b"
    
    collector = WechatArticleCollector(API_KEY)
    
    # 测试单个公众号
    # collector.collect_account_articles("MzkyNjc0Mjg0NA==", "里小克的心理拓荒笔记")
#!/usr/bin/env python3
"""
测试采集流程
"""

from collector import WechatArticleCollector
from db_manager import DatabaseManager

def test_collection():
    """测试采集流程"""
    from config import API_KEY
    
    # 创建采集器
    collector = WechatArticleCollector(API_KEY)
    
    # 测试采集里小克的心理拓荒笔记的第一页
    biz = "MzkyNjc0Mjg0NA=="
    name = "里小克的心理拓荒笔记"
    
    print(f"测试采集: {name}")
    print(f"BIZ: {biz}")
    print("="*60)
    
    # 只获取第一页文章列表
    result = collector.call_api_1_post_history(biz, 1)
    
    if result and result.get('code') == 0:
        print(f"✅ 成功获取文章列表")
        print(f"  余额: {result.get('remain_money')}元")
        print(f"  消耗: {result.get('cost_money')}元")
        
        articles = result.get('data', [])
        print(f"  文章数: {len(articles)}")
        
        # 保存公众号信息
        account_id = collector.db.save_account(biz, name, "gh_bb1aa8c4ec8a")
        print(f"  公众号ID: {account_id}")
        
        # 保存第一篇文章并获取其详细信息
        if articles:
            first_article = articles[0]
            print(f"\n测试第一篇文章:")
            print(f"  标题: {first_article.get('title')}")
            print(f"  时间: {first_article.get('post_time_str')}")
            print(f"  URL: {first_article.get('url')}")
            
            # 保存文章
            article_id = collector.db.save_article_from_list(account_id, first_article)
            print(f"  文章ID: {article_id}")
            
            # 获取文章统计数据
            article_url = first_article.get('url')
            print(f"\n获取文章统计数据...")
            stats_result = collector.call_api_2_read_zan(article_url)
            
            if stats_result and stats_result.get('code') == 0:
                data = stats_result.get('data', {})
                print(f"  ✅ 成功获取统计数据")
                print(f"    阅读: {data.get('read', 0)}")
                print(f"    点赞: {data.get('zan', 0)}")
                print(f"    在看: {data.get('looking', 0)}")
                print(f"    转发: {data.get('share_num', 0)}")
                print(f"    收藏: {data.get('collect_num', 0)}")
                print(f"    评论: {data.get('comment_count', 0)}")
                
                # 保存统计数据
                collector.db.save_article_stats(article_url, data)
                
                # 获取文章全文
                print(f"\n获取文章全文...")
                content_result = collector.call_api_3_article_detail(article_url)
                
                if content_result and content_result.get('code') == 0:
                    print(f"  ✅ 成功获取文章内容")
                    content = content_result.get('content', '')
                    print(f"    内容长度: {len(content)}字符")
                    print(f"    内容预览: {content[:100]}...")
                    
                    # 保存内容
                    collector.db.save_article_content(article_url, content_result)
    
    # 查看统计信息
    print("\n" + "="*60)
    print("数据库统计:")
    stats = collector.db.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    test_collection()
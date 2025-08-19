#!/usr/bin/env python3
"""
主程序入口
"""

import json
import os
from collector import WechatArticleCollector
from db_manager import DatabaseManager
from config import API_KEY, MIN_BALANCE, TARGET_ACCOUNTS


def main():
    """主函数"""
    print("="*60)
    print("微信公众号文章采集系统")
    print("="*60)
    print("\n请选择操作:")
    print("1. 开始新的采集任务")
    print("2. 从断点恢复采集")
    print("3. 查看采集统计")
    print("4. 测试单个公众号")
    print("5. 退出")
    
    choice = input("\n请输入选项 (1-5): ").strip()
    
    if choice == "1":
        start_new_collection()
    elif choice == "2":
        resume_collection()
    elif choice == "3":
        show_statistics()
    elif choice == "4":
        test_single_account()
    elif choice == "5":
        print("退出程序")
    else:
        print("无效选项")


def start_new_collection():
    """开始新的采集任务"""
    print("\n开始批量采集任务...")
    print(f"目标公众号数量: {len(TARGET_ACCOUNTS)}")
    
    # 显示公众号列表
    print("\n公众号列表:")
    for idx, (biz, name) in enumerate(TARGET_ACCOUNTS, 1):
        print(f"  {idx}. {name}")
    
    confirm = input("\n确认开始采集? (y/n): ").strip().lower()
    if confirm != 'y':
        print("取消采集")
        return
    
    # 创建采集器并开始采集
    collector = WechatArticleCollector(API_KEY, MIN_BALANCE)
    collector.collect_multiple_accounts(TARGET_ACCOUNTS)


def resume_collection():
    """恢复采集"""
    print("\n恢复上次的采集任务...")
    
    collector = WechatArticleCollector(API_KEY, MIN_BALANCE)
    collector.resume_collection()


def show_statistics():
    """显示统计信息"""
    db = DatabaseManager()
    stats = db.get_statistics()
    
    print("\n" + "="*60)
    print("采集统计信息")
    print("="*60)
    print(f"公众号总数: {stats['total_accounts']}")
    print(f"已完成公众号: {stats['completed_accounts']}")
    print(f"文章总数: {stats['total_articles']}")
    print(f"已完成文章: {stats['fetched_articles']}")
    print(f"完成率: {stats['fetched_articles']/stats['total_articles']*100:.1f}%" if stats['total_articles'] > 0 else "0%")
    print(f"总消耗金额: ¥{stats['total_cost']:.2f}")
    print(f"当前余额: ¥{stats['current_balance']:.2f}")
    
    # 显示每个公众号的进度
    print("\n各公众号进度:")
    for biz, name in TARGET_ACCOUNTS:
        account_info = db.get_account_info(biz)
        if account_info:
            status = "✅ 已完成" if account_info['stop_flag'] else "⏳ 进行中"
            print(f"  {name}: {status} (第{account_info['last_page']}页)")
        else:
            print(f"  {name}: 未开始")


def test_single_account():
    """测试单个公众号"""
    print("\n测试单个公众号采集")
    print("\n可选公众号:")
    for idx, (biz, name) in enumerate(TARGET_ACCOUNTS, 1):
        print(f"  {idx}. {name}")
    
    try:
        choice = int(input("\n请选择公众号编号: ").strip())
        if 1 <= choice <= len(TARGET_ACCOUNTS):
            biz, name = TARGET_ACCOUNTS[choice - 1]
            print(f"\n开始采集: {name}")
            
            collector = WechatArticleCollector(API_KEY, MIN_BALANCE)
            collector.collect_account_articles(biz, name)
        else:
            print("无效的编号")
    except ValueError:
        print("请输入有效的数字")


if __name__ == "__main__":
    main()
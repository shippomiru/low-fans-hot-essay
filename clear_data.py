#!/usr/bin/env python3
"""
清空数据库中的所有数据，但保留表结构
"""

import sqlite3

def clear_all_data():
    """清空所有表的数据"""
    conn = sqlite3.connect('wechat_articles.db')
    cursor = conn.cursor()
    
    try:
        # 禁用外键约束（方便删除）
        cursor.execute('PRAGMA foreign_keys = OFF')
        
        # 清空所有表（注意顺序，先清空有外键的表）
        tables = [
            'article_contents',   # 依赖 articles
            'article_stats',      # 依赖 articles  
            'articles',          # 依赖 accounts
            'accounts',
            'api_raw_responses',
            'fetch_progress'
        ]
        
        print("清空数据库中的所有数据...")
        for table in tables:
            cursor.execute(f'DELETE FROM {table}')
            # 重置自增主键
            cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
            print(f"  ✅ 清空表: {table}")
        
        # 重新启用外键约束
        cursor.execute('PRAGMA foreign_keys = ON')
        
        conn.commit()
        print("\n✅ 所有数据已清空，表结构保留")
        
        # 验证
        print("\n验证结果:")
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} 条记录")
            
    except Exception as e:
        print(f"❌ 清空数据失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    # 确认操作
    print("⚠️  警告：此操作将清空数据库中的所有数据！")
    print("表结构将保留，但所有记录将被删除。")
    confirm = input("\n确认清空? (输入 yes 确认): ").strip().lower()
    
    if confirm == 'yes':
        clear_all_data()
    else:
        print("取消操作")
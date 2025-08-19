# 微信公众号文章数据采集系统

## 项目概述
本系统用于批量采集指定微信公众号2025年所有历史文章的完整数据，包括文章基本信息、互动数据（阅读、点赞等）和全文内容。系统支持断点续传，能够在任务中断后从精确位置恢复，避免重复API调用造成费用浪费。

## 目标公众号列表

通过文章链接获取的公众号信息（2025-08-19获取）：

| 序号 | 公众号名称 | BIZ字段 | GHID | 示例文章 |
|------|------------|---------|------|----------|
| 1 | 江涌的心理研习堂 | MzIxOTAzOTE4NQ== | gh_93da8b8efc28 | 你的感受才是关系的真相 |
| 2 | 里小克的心理拓荒笔记 | MzkyNjc0Mjg0NA== | gh_bb1aa8c4ec8a | 费斯汀格法则 |
| 3 | 若琳亲子 | Mzg4MzY3MDEwMw== | gh_e6773679f8ab | 你操心什么，孩子就失去什么 |
| 4 | 芳心可悦 | MzU1ODc0OTA1MQ== | gh_cd066d2535d3 | "允许"的三重境界 |
| 5 | 栗子在吗 | MzkzNTY1NjgwMw== | gh_e0fbed63d271 | 养育怪象：溺爱与打压 |
| 6 | 婉又成长社 | MzI0NTcxMTE1Mg== | gh_c2ba45fd7ff5 | 焦虑抑郁的四个方法 |
| 7 | 梁芝心理话 | MzUyNDgwNDM0MQ== | gh_833cef38ff68 | 最容易把关系处烂的行为 |
| 8 | 彤彤的成长空间 | MzkwNjYyMDg5OQ== | gh_e3a9360de499 | 不要轻易给别人提供情绪价值 |
| 9 | 心理咨询师高薇 | MzkzMzc0NjYwNA== | gh_9c44ce58d801 | 抑郁症恶化的3种变化 |

**注意**：使用BIZ字段调用接口一比使用公众号名称更准确可靠。

## 核心功能

### 1. 数据采集范围
- **时间范围**：仅采集2025年内发布的文章
- **数据维度**：
  - 文章基本信息（标题、链接、发布时间、封面等）
  - 互动数据（阅读数、点赞数、在看数、分享数、收藏数、评论数）
  - 文章全文内容（HTML格式和纯文本）

### 2. 三级断点续传机制

#### 2.1 公众号级别
- 记录每个公众号的处理状态
- 状态类型：`未开始` → `进行中` → `已完成`
- 支持从未完成的公众号继续处理

#### 2.2 文章列表级别
- 记录每个公众号已获取的页数
- 记录是否已到达2025年之前的文章（停止标记）
- 恢复时从上次中断的页码继续

#### 2.3 文章详情级别
- 每篇文章的三阶段状态：
  - `仅列表`：通过接口一获取了基本信息
  - `已获数据`：通过接口二获取了互动数据
  - `已获全文`：通过接口三获取了完整内容
- 状态流转：`仅列表` → `已获数据` → `已获全文`

### 3. 费用控制
- 实时监控API余额（remain_money字段）
- 余额低于1元时自动暂停
- 提醒用户充值
- 充值后可从中断位置继续

## 系统架构

### 数据库设计

#### 1. 公众号表 (accounts)
```sql
- id: 主键
- name: 公众号名称
- biz: 公众号biz标识
- ghid: 公众号ghid
- status: 处理状态 (pending/processing/completed)
- last_page: 最后获取的页码
- stop_flag: 是否已到达2025年前文章
- created_at: 创建时间
- updated_at: 更新时间
```

#### 2. 文章表 (articles)
```sql
- id: 主键
- account_id: 关联公众号ID
- url: 文章链接
- title: 标题
- post_time: 发布时间
- position: 文章位置
- digest: 摘要
- cover_url: 封面图
- original: 是否原创
- fetch_status: 获取状态 (list_only/data_fetched/content_fetched)
- created_at: 创建时间
- updated_at: 更新时间
```

#### 3. 文章数据表 (article_stats)
```sql
- id: 主键
- article_id: 关联文章ID
- read_num: 阅读数
- like_num: 点赞数
- watch_num: 在看数
- share_num: 分享数
- collect_num: 收藏数
- comment_count: 评论数
- fetched_at: 获取时间
```

#### 4. 文章内容表 (article_contents)
```sql
- id: 主键
- article_id: 关联文章ID
- content: 纯文本内容
- content_html: HTML格式内容
- author: 作者
- copyright_stat: 版权状态
- source_url: 原文链接
- fetched_at: 获取时间
```

#### 5. API调用记录表 (api_logs)
```sql
- id: 主键
- api_type: API类型 (list/stats/content)
- request_params: 请求参数
- response_data: 响应数据
- cost_money: 消耗金额
- remain_money: 剩余金额
- status: 调用状态
- created_at: 调用时间
```

## 工作流程

### 1. 主流程
```
1. 读取公众号列表
2. 检查进度记录，确定起始位置
3. 对每个公众号：
   a. 获取文章列表（分页）
   b. 检测是否到达2025年前
   c. 对每篇2025年文章获取详细数据
4. 实时保存进度
5. 监控余额状态
```

### 2. 文章列表获取流程（接口一）
```
1. 从last_page开始请求
2. 解析返回的文章列表
3. 检查每篇文章的发布时间
4. 如果发现2025年前的文章：
   - 标记stop_flag = true
   - 停止该公众号的列表获取
5. 否则继续下一页
```

### 3. 文章详情获取流程（接口二、三）
```
1. 筛选fetch_status != 'content_fetched'的文章
2. 对每篇文章：
   a. 如果status = 'list_only'，调用接口二
   b. 如果status = 'data_fetched'，跳过接口二
   c. 调用接口三获取全文
   d. 更新fetch_status
```

### 4. 异常处理
- API调用失败：记录错误，等待重试
- 余额不足：保存当前进度，通知用户
- 程序中断：下次启动自动恢复

## 使用说明

### 1. 配置
```python
# config.py
API_KEY = "your_api_key"
API_BASE_URL = "https://www.dajiala.com/fbmain/monitor/v3"
MIN_BALANCE = 1.0  # 最小余额阈值
DATABASE_PATH = "wechat_articles.db"
```

### 2. 添加公众号
```python
# 单个添加
add_account("公众号名称")

# 批量添加
add_accounts(["公众号1", "公众号2", "公众号3"])
```

### 3. 启动采集
```python
# 开始采集
start_collection()

# 从断点恢复
resume_collection()
```

### 4. 数据导出
```python
# 导出为CSV
export_to_csv("output.csv")

# 导出为JSON
export_to_json("output.json")

# 自定义字段导出
export_custom_fields(["title", "read_num", "like_num"])
```

## 注意事项

1. **API调用优化**
   - 每次调用后立即保存进度
   - 使用数据库事务确保数据一致性
   - 避免重复调用已获取的数据

2. **费用管理**
   - 设置合理的余额阈值
   - 及时响应余额不足提醒
   - 定期检查API消耗统计

3. **数据完整性**
   - 所有原始响应数据都会保存
   - 支持数据重新解析
   - 便于后续数据校验

## 技术栈
- Python 3.8+
- SQLite（本地数据库）
- Requests（HTTP请求）
- SQLAlchemy（ORM）

## 项目结构
```
low-fans-hot-article/
├── README.md
├── requirements.txt
├── config.py           # 配置文件
├── models.py          # 数据库模型
├── collector.py       # 采集核心逻辑
├── api_client.py      # API调用封装
├── database.py        # 数据库操作
├── progress.py        # 进度管理
├── exporter.py        # 数据导出
└── main.py           # 主程序入口
```
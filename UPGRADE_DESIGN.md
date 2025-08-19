# 微信公众号文章采集系统 - 改版设计方案

## 概述

### 主要变化
1. **引入批次管理**：每次采集任务作为独立批次，数据隔离，便于管理和对比
2. **新增两阶段采集模式**：先获取所有文章列表→费用预估确认→批量获取详情
3. **模式灵活切换**：继续批次时可自由选择标准模式或两阶段模式
4. **完全兼容现有数据**：现有数据迁移为默认批次，支持断点续传

### 核心改进目标
- **费用透明可控**：采集前知道准确费用，可选择是否继续
- **灵活性最大化**：任何时候可切换执行策略
- **数据管理清晰**：批次隔离，历史可追溯

---

## 一、系统架构

### 1.1 核心概念

#### 批次（Batch）
- 一次采集任务的数据容器
- 每个批次有唯一ID（如 `batch_20250819_001`）
- 批次之间数据完全隔离
- 可同时存在多个批次，便于数据对比

#### 采集模式（Mode）
- **标准模式（Standard）**
  - 逐个公众号完整采集
  - 获取列表后立即获取该公众号所有文章详情
  - 适合：数据量小或不关心总费用时
  
- **两阶段模式（Two-Phase）**
  - 第一阶段：获取所有公众号的文章列表
  - 确认阶段：统计文章数量，计算费用，等待用户确认
  - 第二阶段：批量获取所有文章的详情
  - 适合：需要控制费用或数据量大时

#### 操作类型
- **新建批次**：创建全新的采集任务
- **继续批次**：基于现有批次数据断点续传

### 1.2 关键设计原则

1. **批次与模式分离**
   - 批次只是数据归属标记
   - 模式只是执行策略
   - 可以用不同模式操作同一批次

2. **完全兼容性**
   - 支持从标准模式切换到两阶段模式
   - 支持从两阶段模式切换到标准模式
   - 不破坏已有数据

3. **状态基于数据**
   - 不记录"用什么模式采集的"
   - 只记录客观数据状态
   - 根据数据状态决定下一步操作

---

## 二、用户界面设计

### 2.1 主菜单

```
========================================
微信公众号文章采集系统 v2.0
========================================

当前批次: batch_20250819_001
批次名称: 8月完整采集
创建时间: 2025-08-19 10:00:00
初始模式: 标准模式
当前进度: 3/9 个公众号, 131/173 篇文章
费用统计: 已消耗 14.07元, 当前余额 0.94元

请选择操作:
1. 新建批次（标准模式）
2. 新建批次（两阶段模式）
3. 继续当前批次（标准模式）
4. 继续当前批次（两阶段模式）
5. 查看批次列表
6. 切换批次
7. 批次统计对比
8. 退出

请输入选项 (1-8): 
```

### 2.2 批次列表界面

```
========================================
批次列表
========================================

ID    批次号                 名称          模式      状态    进度
1     batch_20250815_001    首次采集      标准      完成    9/9, 523/523
2     batch_20250819_001    8月采集       标准      进行中  3/9, 131/173
3     batch_20250820_001    测试采集      两阶段    暂停    9/9, 0/186

选择批次号切换，或输入 0 返回主菜单: 
```

---

## 三、数据库设计

### 3.1 新增批次表

```sql
CREATE TABLE batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT UNIQUE NOT NULL,        -- 批次唯一标识
    name TEXT,                            -- 用户自定义名称
    initial_mode TEXT,                    -- 创建时的模式(仅作记录)
    last_mode TEXT,                       -- 最后使用的模式
    status TEXT DEFAULT 'running',        -- running/paused/completed
    
    -- 进度统计
    total_accounts INTEGER DEFAULT 0,
    completed_accounts INTEGER DEFAULT 0,
    total_articles INTEGER DEFAULT 0,
    fetched_articles INTEGER DEFAULT 0,
    
    -- 费用统计
    estimated_cost REAL DEFAULT 0,        -- 预估费用(两阶段模式)
    actual_cost REAL DEFAULT 0,           -- 实际消耗
    initial_balance REAL,                 -- 开始时余额
    current_balance REAL,                 -- 当前余额
    
    -- 两阶段模式专用字段
    phase TEXT DEFAULT 'list',            -- list/confirm/detail/completed
    user_confirmed BOOLEAN DEFAULT 0,     -- 是否已确认费用
    confirm_time TIMESTAMP,               -- 确认时间
    unfetched_count INTEGER DEFAULT 0,    -- 待获取文章数
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_batch_status ON batches(status);
CREATE INDEX idx_batch_created ON batches(created_at);
```

### 3.2 现有表调整

```sql
-- accounts表增加批次字段
ALTER TABLE accounts ADD COLUMN batch_id TEXT;
CREATE INDEX idx_accounts_batch ON accounts(batch_id);

-- articles表增加批次字段
ALTER TABLE articles ADD COLUMN batch_id TEXT;
CREATE INDEX idx_articles_batch ON articles(batch_id);

-- api_raw_responses表增加批次字段
ALTER TABLE api_raw_responses ADD COLUMN batch_id TEXT;
CREATE INDEX idx_api_batch ON api_raw_responses(batch_id);
```

### 3.3 数据迁移策略

```sql
-- 将现有数据迁移到默认批次
UPDATE accounts SET batch_id = 'batch_default' WHERE batch_id IS NULL;
UPDATE articles SET batch_id = 'batch_default' WHERE batch_id IS NULL;
UPDATE api_raw_responses SET batch_id = 'batch_default' WHERE batch_id IS NULL;

-- 创建默认批次记录
INSERT INTO batches (batch_id, name, initial_mode, status, created_at)
VALUES ('batch_default', '历史数据', 'standard', 'paused', '2025-08-01 00:00:00');
```

---

## 四、核心流程设计

### 4.1 新建批次流程

#### 标准模式
```
用户选择"新建批次(标准模式)"
    ↓
输入批次名称（可选）
    ↓
创建批次记录，设为当前批次
    ↓
对每个公众号循环:
    1. 获取文章列表（接口一）
    2. 立即获取该公众号所有文章详情（接口二、三）
    3. 如果余额不足，保存进度，提示充值
    ↓
批次完成
```

#### 两阶段模式
```
用户选择"新建批次(两阶段模式)"
    ↓
输入批次名称（可选）
    ↓
创建批次记录，设为当前批次
    ↓
【第一阶段】获取所有公众号文章列表
    ↓
【确认阶段】
- 统计：共X篇文章需要获取详情
- 费用：X * 0.09 = Y元
- 显示：当前余额Z元
- 询问：是否继续？
    ↓
用户确认？
    否 → 保存状态，批次暂停
    是 ↓
【第二阶段】批量获取所有文章详情
    ↓
批次完成
```

### 4.2 继续批次流程

#### 继续批次（标准模式）
```python
def resume_batch_standard(batch_id):
    """用标准模式继续批次"""
    
    # 1. 获取批次内所有公众号状态
    accounts = get_batch_accounts(batch_id)
    
    # 2. 逐个处理
    for account in accounts:
        if account.stop_flag == 0:
            # 继续获取列表
            continue_from_page = account.last_page + 1
            fetch_lists(account, continue_from_page)
        
        # 获取该公众号未完成的文章
        unfetched = get_unfetched_articles(account.id, batch_id)
        if unfetched:
            # 立即获取详情
            for article in unfetched:
                if article.fetch_status == 'list_only':
                    call_api_2(article)  # 获取统计
                    call_api_3(article)  # 获取内容
                elif article.fetch_status == 'stats_fetched':
                    call_api_3(article)  # 只获取内容
```

#### 继续批次（两阶段模式）
```python
def resume_batch_two_phase(batch_id):
    """用两阶段模式继续批次"""
    
    batch = get_batch(batch_id)
    
    # 1. 根据批次当前阶段处理
    if batch.phase == 'list':
        # 完成所有列表获取
        accounts_need_list = get_accounts_need_list(batch_id)
        for account in accounts_need_list:
            fetch_lists_only(account)
        batch.phase = 'confirm'
    
    # 2. 确认阶段
    if batch.phase == 'confirm':
        unfetched = count_unfetched_articles(batch_id)
        cost = unfetched * 0.09
        
        print(f"批次 {batch.name} 统计：")
        print(f"  需获取文章详情：{unfetched} 篇")
        print(f"  预计费用：{cost:.2f} 元")
        print(f"  当前余额：{batch.current_balance} 元")
        
        if user_confirm():
            batch.phase = 'detail'
            batch.user_confirmed = True
        else:
            return  # 等待下次
    
    # 3. 详情获取阶段
    if batch.phase == 'detail':
        articles = get_all_unfetched_articles(batch_id)
        for article in articles:
            if article.fetch_status == 'list_only':
                call_api_2(article)
                call_api_3(article)
            elif article.fetch_status == 'stats_fetched':
                call_api_3(article)
```

### 4.3 模式切换场景

#### 场景1：标准模式 → 两阶段模式
```
初始：用标准模式采集了3个公众号
现状：里小克有42篇未完成，若琳未开始

选择"继续批次(两阶段模式)"：
1. 完成所有列表获取（若琳+其他6个）
2. 统计所有未完成文章（42+新增）
3. 显示总费用，等待确认
4. 批量获取所有详情
```

#### 场景2：两阶段模式 → 标准模式
```
初始：用两阶段模式获取了所有列表
现状：在确认阶段暂停（显示需186篇，16.74元）

选择"继续批次(标准模式)"：
1. 不再等待整体确认
2. 逐个公众号获取详情
3. 可以选择性处理部分公众号
```

---

## 五、实现要点

### 5.1 批次管理器

```python
class BatchManager:
    def create_batch(self, name: str, mode: str) -> str:
        """创建新批次"""
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        # 创建批次记录
        # 设为当前批次
        return batch_id
    
    def get_current_batch(self) -> Optional[Dict]:
        """获取当前活跃批次"""
        # 返回status='running'的最新批次
        
    def switch_batch(self, batch_id: str):
        """切换到指定批次"""
        # 暂停当前批次
        # 激活目标批次
    
    def analyze_batch_status(self, batch_id: str) -> Dict:
        """分析批次状态"""
        # 返回：
        # - 需要列表的公众号
        # - 需要详情的文章数
        # - 已完成的统计
```

### 5.2 采集器改造

```python
class WechatArticleCollector:
    def __init__(self, batch_id: str = None):
        """初始化时可指定批次"""
        if batch_id is None:
            batch_id = BatchManager().get_current_batch()
        self.batch_id = batch_id
    
    def collect_with_mode(self, mode: str):
        """根据模式执行采集"""
        if mode == 'standard':
            self.collect_standard()
        else:
            self.collect_two_phase()
    
    def collect_list_only(self, account):
        """只获取列表，不获取详情"""
        # 设置标记，跳过详情获取
        
    def batch_fetch_details(self):
        """批量获取所有未完成文章的详情"""
        # 用于两阶段模式第二阶段
```

### 5.3 数据隔离

```python
# 所有查询都要加上batch_id条件
def get_unfetched_articles(batch_id: str):
    return db.query("""
        SELECT * FROM articles 
        WHERE batch_id = ? 
        AND fetch_status != 'content_fetched'
    """, batch_id)

# API缓存也要考虑批次
def get_cached_response(api_type: str, key: str, batch_id: str):
    # 同一批次内使用缓存
    # 不同批次重新调用
```

---

## 六、兼容性保证

### 6.1 现有数据处理
- 所有现有数据自动迁移到 `batch_default`
- 可以选择"继续批次"操作默认批次
- 支持用任何模式继续

### 6.2 向后兼容
- 保留原有的所有功能
- 数据库表只增不改
- API调用逻辑不变

### 6.3 平滑升级路径
1. 运行升级脚本，迁移现有数据
2. 用户可继续使用原有数据
3. 新功能可选使用

---

## 七、优势总结

1. **费用完全可控**
   - 两阶段模式让用户预知费用
   - 可在任何阶段停止

2. **灵活性最大化**
   - 批次与模式完全解耦
   - 支持随时切换策略

3. **数据管理清晰**
   - 批次隔离，便于管理
   - 历史数据可追溯对比

4. **用户体验优化**
   - 清晰的进度展示
   - 智能的模式建议
   - 完善的断点续传

5. **扩展性良好**
   - 便于后续添加新模式
   - 支持批次间数据对比分析

---

## 八、实施计划

### 第一阶段：基础改造
1. 实现批次管理功能
2. 数据库表结构调整
3. 现有数据迁移

### 第二阶段：两阶段模式
1. 实现两阶段采集逻辑
2. 费用预估和确认功能
3. 批量详情获取

### 第三阶段：模式切换
1. 实现模式自由切换
2. 优化用户界面
3. 添加智能建议

### 第四阶段：高级功能
1. 批次对比分析
2. 数据导出功能
3. 定时任务支持
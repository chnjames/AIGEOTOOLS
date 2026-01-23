# 数据持久化方案对比

## 为什么不能用 IndexedDB？

**IndexedDB 是浏览器 API**，只能在 JavaScript 前端使用。  
**Streamlit 是 Python 后端应用**，运行在服务器端，无法使用 IndexedDB。

---

## 方案对比

### 方案1：SQLite（⭐ 推荐）

**优点：**
- ✅ Python 内置支持（`sqlite3`），无需安装额外依赖
- ✅ 单文件数据库，易于备份和迁移
- ✅ 查询性能好，支持复杂查询
- ✅ 支持事务，数据安全
- ✅ 支持 SQL 查询，灵活强大
- ✅ 适合 MVP 到生产环境的平滑升级

**缺点：**
- ⚠️ 需要学习基本的 SQL（但很简单）
- ⚠️ 多进程写入需要处理锁（Streamlit 单进程，无此问题）

**代码复杂度：** ⭐⭐（非常简单）

**适用场景：** MVP 和生产环境都适用

---

### 方案2：JSON 文件

**优点：**
- ✅ 最简单，无需学习 SQL
- ✅ 人类可读，易于调试
- ✅ 无需数据库知识

**缺点：**
- ❌ 查询性能差（需要加载整个文件）
- ❌ 数据量大时很慢
- ❌ 并发写入可能丢失数据
- ❌ 不支持复杂查询

**代码复杂度：** ⭐（极简单）

**适用场景：** 仅适合数据量很小（<1000条）的 MVP

---

## 推荐方案：SQLite

### 为什么推荐 SQLite？

1. **其实很简单**：只需要几行代码
   ```python
   import sqlite3
   conn = sqlite3.connect('data.db')
   cursor = conn.cursor()
   cursor.execute("INSERT INTO table VALUES (?)", (value,))
   conn.commit()
   conn.close()
   ```

2. **性能好**：即使数据量增长到几万条，依然很快

3. **功能强大**：支持统计、查询、分析，为后续功能扩展打好基础

4. **零依赖**：Python 内置，无需安装任何包

---

## 快速开始

### 1. 使用已封装好的 DataStorage 类

我已经为你创建了 `data_storage.py`，提供了统一的接口：

```python
from data_storage import DataStorage

# 初始化（SQLite方式）
storage = DataStorage(storage_type="sqlite", db_path="geo_data.db")

# 保存关键词
storage.save_keywords(["关键词1", "关键词2"], "品牌名")

# 获取关键词
keywords = storage.get_keywords("品牌名")

# 保存文章
storage.save_article("关键词", "平台", "内容", "文件名", "品牌名")

# 获取统计数据
stats = storage.get_stats("品牌名")
```

### 2. 最小改动集成

在 `geo_tool.py` 中，只需要在关键位置添加几行保存代码：

```python
# 文件顶部
from data_storage import DataStorage
storage = DataStorage(storage_type="sqlite", db_path="geo_data.db")

# 关键词生成后（约第533行）
if cleaned:
    st.session_state.keywords = cleaned
    storage.save_keywords(cleaned, brand)  # 新增这一行
    st.success(f"生成完成（{len(cleaned)} 条）")

# 内容生成后（约第714行）
st.session_state.generated_contents = contents
storage.save_article(keyword, plat, content, filename, brand)  # 在循环中添加

# 优化后（约第838行）
st.session_state.optimized_article = optimized_article
storage.save_optimization(
    original_article, optimized_article, changes, target_platform, brand
)  # 新增

# 验证后（约第932行）
st.session_state.verify_combined = combined
storage.save_verify_results(all_results)  # 新增
```

### 3. 添加历史记录查看功能（可选）

可以新增一个 Tab 来查看历史数据：

```python
tab5 = st.tabs([..., "5 历史记录"])

with tab5:
    st.header("历史记录")
    
    # 统计数据
    stats = storage.get_stats(brand)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("关键词", stats["keywords_count"])
    col2.metric("文章", stats["articles_count"])
    col3.metric("优化", stats["optimizations_count"])
    col4.metric("验证", stats["verify_results_count"])
    
    # 历史文章列表
    articles = storage.get_articles(brand=brand)
    if articles:
        df = pd.DataFrame(articles)
        st.dataframe(df[["keyword", "platform", "created_at"]])
```

---

## 数据库文件位置

- **SQLite 文件**：`geo_data.db`（项目根目录）
- **JSON 文件**：`data/` 目录（如果使用 JSON 方式）

**建议：** 将 `geo_data.db` 添加到 `.gitignore`，避免提交到版本控制。

---

## 性能对比（参考）

| 数据量 | SQLite | JSON文件 |
|--------|--------|----------|
| 100条 | <10ms | <10ms |
| 1000条 | <50ms | ~100ms |
| 10000条 | ~200ms | ~5秒 |
| 100000条 | ~1秒 | 很慢 |

---

## 总结

**对于 MVP 版本，强烈推荐使用 SQLite：**

1. ✅ 简单：使用封装好的 `DataStorage` 类，只需几行代码
2. ✅ 高效：性能好，支持未来扩展
3. ✅ 可靠：数据安全，支持事务
4. ✅ 零依赖：Python 内置，无需安装

**如果数据量真的非常小（<100条），可以考虑 JSON 文件。**

---

## 下一步

1. 查看 `data_storage.py` 了解实现细节
2. 查看 `storage_example.py` 了解使用方法
3. 在 `geo_tool.py` 中集成（参考上面的最小改动示例）

需要我帮你直接集成到 `geo_tool.py` 吗？

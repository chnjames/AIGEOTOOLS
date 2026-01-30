"""
数据持久化集成示例
展示如何在 geo_tool.py 中集成 DataStorage
"""

# ==================== 方式1：SQLite（推荐，简单高效） ====================
from modules.data_storage import DataStorage

# 初始化存储（SQLite方式，单文件数据库）
storage = DataStorage(storage_type="sqlite", db_path="geo_data.db")

# 或者使用JSON方式（更简单，但查询性能差）
# storage = DataStorage(storage_type="json", db_path="data")

# ==================== 在关键词模块中使用 ====================
def save_keywords_example(keywords: list, brand: str):
    """保存关键词到数据库"""
    storage.save_keywords(keywords, brand)

def load_keywords_example(brand: str) -> list:
    """从数据库加载关键词"""
    return storage.get_keywords(brand)

# ==================== 在内容生成模块中使用 ====================
def save_article_example(keyword: str, platform: str, content: str, 
                         filename: str, brand: str):
    """保存生成的文章"""
    storage.save_article(keyword, platform, content, filename, brand)

def get_article_history_example(brand: str, platform: str = None):
    """获取历史文章"""
    return storage.get_articles(brand=brand, platform=platform)

# ==================== 在优化模块中使用 ====================
def save_optimization_example(original: str, optimized: str, 
                              changes: str, platform: str, brand: str):
    """保存优化记录"""
    storage.save_optimization(original, optimized, changes, platform, brand)

# ==================== 在验证模块中使用 ====================
def save_verify_example(results: list):
    """保存验证结果"""
    storage.save_verify_results(results)

def get_verify_history_example(brand: str):
    """获取历史验证结果"""
    return storage.get_verify_results(brand=brand)

# ==================== 统计功能 ====================
def get_stats_example(brand: str):
    """获取统计数据"""
    return storage.get_stats(brand=brand)

# ==================== 完整集成示例 ====================
"""
在 geo_tool.py 中的集成方式：

1. 在文件顶部添加：
   from modules.data_storage import DataStorage
   storage = DataStorage(storage_type="sqlite", db_path="geo_data.db")

2. 在关键词生成后保存：
   if cleaned:
       st.session_state.keywords = cleaned
       storage.save_keywords(cleaned, brand)  # 新增：保存到数据库
       st.success(f"生成完成（{len(cleaned)} 条）")

3. 在内容生成后保存：
   for keyword, plat in keywords_to_generate:
       # ... 生成内容 ...
       storage.save_article(keyword, plat, content, filename, brand)  # 新增

4. 在优化后保存：
   storage.save_optimization(
       original_article, 
       optimized_article, 
       changes, 
       target_platform, 
       brand
   )  # 新增

5. 在验证后保存：
   storage.save_verify_results(all_results)  # 新增

6. 可选：添加"历史记录"Tab，查看已保存的数据
"""

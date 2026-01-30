"""
轻量级数据持久化模块 - MVP版本
支持 SQLite 和 JSON 两种存储方式
"""
import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
import pandas as pd


class DataStorage:
    """统一的数据存储接口，支持SQLite和JSON两种后端"""
    
    def __init__(self, storage_type: str = "sqlite", db_path: str = "geo_data.db"):
        """
        Args:
            storage_type: "sqlite" 或 "json"
            db_path: SQLite数据库路径，或JSON文件目录
        """
        self.storage_type = storage_type
        self.db_path = db_path
        
        if storage_type == "sqlite":
            self._init_sqlite()
        else:
            self._init_json()
    
    def _init_sqlite(self):
        """初始化SQLite数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 关键词表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    brand TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 内容表（生成的文章）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT,
                    platform TEXT,
                    content TEXT,
                    filename TEXT,
                    brand TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 优化记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS optimizations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_content TEXT,
                    optimized_content TEXT,
                    changes TEXT,
                    platform TEXT,
                    brand TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 验证结果表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS verify_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT,
                    brand TEXT,
                    verify_model TEXT,
                    mention_count INTEGER,
                    mention_position TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # API 调用记录表（用于成本统计）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    provider TEXT,
                    model TEXT,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0.0,
                    cost_cny REAL DEFAULT 0.0,
                    keyword TEXT,
                    platform TEXT,
                    brand TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 工作流表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    steps TEXT NOT NULL,
                    schedule TEXT,
                    conditions TEXT,
                    enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 工作流执行记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    error TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
                )
            """)
            
            # 工作流模板表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    steps TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 平台账号表（用于存储各平台的账号配置）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS platform_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    account_type TEXT NOT NULL,
                    account_name TEXT,
                    api_key TEXT,
                    api_secret TEXT,
                    access_token TEXT,
                    refresh_token TEXT,
                    token_expires_at TIMESTAMP,
                    config_json TEXT,
                    is_active INTEGER DEFAULT 1,
                    brand TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(platform, brand, account_name)
                )
            """)
            
            # 发布记录表（用于存储文章发布记录）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS publish_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER,
                    platform TEXT NOT NULL,
                    publish_method TEXT NOT NULL,
                    publish_status TEXT NOT NULL,
                    publish_url TEXT,
                    publish_id TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    published_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (article_id) REFERENCES articles(id)
                )
            """)
            
            # 扩展articles表，添加发布状态字段
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN publish_status TEXT DEFAULT 'draft'")
            except sqlite3.OperationalError:
                # 字段已存在等预期情况，忽略
                pass
            
            try:
                cursor.execute("ALTER TABLE articles ADD COLUMN publish_urls TEXT")
            except sqlite3.OperationalError:
                # 字段已存在等预期情况，忽略
                pass
    
    def _init_json(self):
        """初始化JSON存储目录"""
        Path(self.db_path).mkdir(parents=True, exist_ok=True)
    
    # ==================== 关键词相关 ====================
    
    def save_keywords(self, keywords: List[str], brand: str):
        """保存关键词列表"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for keyword in keywords:
                    cursor.execute(
                        "INSERT INTO keywords (keyword, brand) VALUES (?, ?)",
                        (keyword, brand)
                    )
                conn.commit()
        else:
            # JSON方式：追加到文件
            json_file = Path(self.db_path) / "keywords.json"
            data = []
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            for keyword in keywords:
                data.append({
                    "keyword": keyword,
                    "brand": brand,
                    "created_at": datetime.now().isoformat()
                })
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_keywords(self, brand: Optional[str] = None) -> List[str]:
        """获取关键词列表"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if brand:
                    cursor.execute("SELECT keyword FROM keywords WHERE brand = ?", (brand,))
                else:
                    cursor.execute("SELECT keyword FROM keywords")
                keywords = [row[0] for row in cursor.fetchall()]
                return keywords
        else:
            json_file = Path(self.db_path) / "keywords.json"
            if not json_file.exists():
                return []
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if brand:
                return [item["keyword"] for item in data if item.get("brand") == brand]
            return [item["keyword"] for item in data]
    
    # ==================== 文章内容相关 ====================
    
    def save_article(self, keyword: str, platform: str, content: str, 
                     filename: str, brand: str):
        """保存生成的文章"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO articles (keyword, platform, content, filename, brand)
                    VALUES (?, ?, ?, ?, ?)
                """, (keyword, platform, content, filename, brand))
                conn.commit()
        else:
            json_file = Path(self.db_path) / "articles.json"
            data = []
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            data.append({
                "keyword": keyword,
                "platform": platform,
                "content": content,
                "filename": filename,
                "brand": brand,
                "created_at": datetime.now().isoformat()
            })
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_articles(self, brand: Optional[str] = None, 
                     platform: Optional[str] = None) -> List[Dict]:
        """获取文章列表"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                if brand and platform:
                    df = pd.read_sql_query(
                        "SELECT * FROM articles WHERE brand = ? AND platform = ?",
                        conn, params=(brand, platform)
                    )
                elif brand:
                    df = pd.read_sql_query(
                        "SELECT * FROM articles WHERE brand = ?",
                        conn, params=(brand,)
                    )
                else:
                    df = pd.read_sql_query("SELECT * FROM articles", conn)
                return df.to_dict('records')
        else:
            json_file = Path(self.db_path) / "articles.json"
            if not json_file.exists():
                return []
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if brand and platform:
                return [item for item in data 
                       if item.get("brand") == brand and item.get("platform") == platform]
            elif brand:
                return [item for item in data if item.get("brand") == brand]
            return data
    
    # ==================== 优化记录相关 ====================
    
    def save_optimization(self, original_content: str, optimized_content: str,
                         changes: str, platform: str, brand: str):
        """保存优化记录"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO optimizations 
                    (original_content, optimized_content, changes, platform, brand)
                    VALUES (?, ?, ?, ?, ?)
                """, (original_content, optimized_content, changes, platform, brand))
                conn.commit()
        else:
            json_file = Path(self.db_path) / "optimizations.json"
            data = []
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            data.append({
                "original_content": original_content,
                "optimized_content": optimized_content,
                "changes": changes,
                "platform": platform,
                "brand": brand,
                "created_at": datetime.now().isoformat()
            })
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_optimizations(self, brand: Optional[str] = None) -> List[Dict]:
        """获取优化记录"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                if brand:
                    df = pd.read_sql_query(
                        "SELECT * FROM optimizations WHERE brand = ? ORDER BY created_at DESC",
                        conn, params=(brand,)
                    )
                else:
                    df = pd.read_sql_query(
                        "SELECT * FROM optimizations ORDER BY created_at DESC",
                        conn
                    )
                return df.to_dict('records')
        else:
            json_file = Path(self.db_path) / "optimizations.json"
            if not json_file.exists():
                return []
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if brand:
                return [item for item in data if item.get("brand") == brand]
            return data
    
    # ==================== 验证结果相关 ====================
    
    def save_verify_results(self, results: List[Dict]):
        """批量保存验证结果"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for result in results:
                    cursor.execute("""
                        INSERT INTO verify_results 
                        (query, brand, verify_model, mention_count, mention_position)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        result.get("问题"),
                        result.get("品牌"),
                        result.get("验证模型"),
                        result.get("提及次数"),
                        result.get("位置")
                    ))
                conn.commit()
        else:
            json_file = Path(self.db_path) / "verify_results.json"
            data = []
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            for result in results:
                data.append({
                    "query": result.get("问题"),
                    "brand": result.get("品牌"),
                    "verify_model": result.get("验证模型"),
                    "mention_count": result.get("提及次数"),
                    "mention_position": result.get("位置"),
                    "created_at": datetime.now().isoformat()
                })
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_verify_results(self, brand: Optional[str] = None, include_timestamp: bool = False) -> pd.DataFrame:
        """获取验证结果（返回DataFrame）
        
        Args:
            brand: 品牌名称，如果为None则返回所有品牌
            include_timestamp: 是否包含时间戳字段
        """
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                if include_timestamp:
                    if brand:
                        df = pd.read_sql_query(
                            """SELECT query as "问题", brand as "品牌", verify_model as "验证模型",
                               mention_count as "提及次数", mention_position as "位置",
                               created_at as "验证时间"
                               FROM verify_results WHERE brand = ? ORDER BY created_at DESC""",
                            conn, params=(brand,)
                        )
                    else:
                        df = pd.read_sql_query(
                            """SELECT query as "问题", brand as "品牌", verify_model as "验证模型",
                               mention_count as "提及次数", mention_position as "位置",
                               created_at as "验证时间"
                               FROM verify_results ORDER BY created_at DESC""",
                            conn
                        )
                else:
                    if brand:
                        df = pd.read_sql_query(
                            """SELECT query as "问题", brand as "品牌", verify_model as "验证模型",
                               mention_count as "提及次数", mention_position as "位置"
                               FROM verify_results WHERE brand = ?""",
                            conn, params=(brand,)
                        )
                    else:
                        df = pd.read_sql_query(
                            """SELECT query as "问题", brand as "品牌", verify_model as "验证模型",
                               mention_count as "提及次数", mention_position as "位置"
                               FROM verify_results""",
                            conn
                        )
            if include_timestamp and not df.empty and "验证时间" in df.columns:
                df["验证时间"] = pd.to_datetime(df["验证时间"])
            return df
        else:
            json_file = Path(self.db_path) / "verify_results.json"
            if not json_file.exists():
                return pd.DataFrame()
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if brand:
                data = [item for item in data if item.get("brand") == brand]
            
            # 转换为DataFrame格式
            records = []
            for item in data:
                record = {
                    "问题": item.get("query"),
                    "品牌": item.get("brand"),
                    "验证模型": item.get("verify_model"),
                    "提及次数": item.get("mention_count"),
                    "位置": item.get("mention_position")
                }
                if include_timestamp and "created_at" in item:
                    record["验证时间"] = pd.to_datetime(item.get("created_at"))
                records.append(record)
            
            df = pd.DataFrame(records)
            if include_timestamp and not df.empty and "验证时间" in df.columns:
                df = df.sort_values("验证时间", ascending=False)
            return df
    
    # ==================== 统计功能 ====================
    
    def get_stats(self, brand: Optional[str] = None) -> Dict[str, Any]:
        """获取统计数据"""
        stats = {}
        
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 关键词数量
                if brand:
                    cursor.execute("SELECT COUNT(*) FROM keywords WHERE brand = ?", (brand,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM keywords")
                stats["keywords_count"] = cursor.fetchone()[0]
                
                # 文章数量
                if brand:
                    cursor.execute("SELECT COUNT(*) FROM articles WHERE brand = ?", (brand,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM articles")
                stats["articles_count"] = cursor.fetchone()[0]
                
                # 优化记录数量
                if brand:
                    cursor.execute("SELECT COUNT(*) FROM optimizations WHERE brand = ?", (brand,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM optimizations")
                stats["optimizations_count"] = cursor.fetchone()[0]
                
                # 验证结果数量
                if brand:
                    cursor.execute("SELECT COUNT(*) FROM verify_results WHERE brand = ?", (brand,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM verify_results")
                stats["verify_results_count"] = cursor.fetchone()[0]
        else:
            # JSON方式统计
            keywords_file = Path(self.db_path) / "keywords.json"
            articles_file = Path(self.db_path) / "articles.json"
            optimizations_file = Path(self.db_path) / "optimizations.json"
            verify_file = Path(self.db_path) / "verify_results.json"
            
            def count_json(file_path, brand_filter=None):
                if not file_path.exists():
                    return 0
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if brand_filter:
                    return len([item for item in data if item.get("brand") == brand_filter])
                return len(data)
            
            stats["keywords_count"] = count_json(keywords_file, brand)
            stats["articles_count"] = count_json(articles_file, brand)
            stats["optimizations_count"] = count_json(optimizations_file, brand)
            stats["verify_results_count"] = count_json(verify_file, brand)
        
        return stats
    
    # ==================== API 调用记录相关 ====================
    
    def save_api_call(
        self,
        operation_type: str,
        provider: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        cost_usd: float = 0.0,
        cost_cny: float = 0.0,
        keyword: Optional[str] = None,
        platform: Optional[str] = None,
        brand: Optional[str] = None
    ):
        """保存 API 调用记录"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO api_calls 
                    (operation_type, provider, model, input_tokens, output_tokens, total_tokens,
                     cost_usd, cost_cny, keyword, platform, brand)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    operation_type, provider, model, input_tokens, output_tokens, total_tokens,
                    cost_usd, cost_cny, keyword, platform, brand
                ))
                conn.commit()
        else:
            json_file = Path(self.db_path) / "api_calls.json"
            data = []
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            data.append({
                "operation_type": operation_type,
                "provider": provider,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
                "cost_cny": cost_cny,
                "keyword": keyword,
                "platform": platform,
                "brand": brand,
                "created_at": datetime.now().isoformat()
            })
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_api_calls(
        self,
        brand: Optional[str] = None,
        operation_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """获取 API 调用记录（返回 DataFrame）"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                query = """
                    SELECT 
                        operation_type as "操作类型",
                        provider as "提供商",
                        model as "模型",
                        input_tokens as "输入Token",
                        output_tokens as "输出Token",
                        total_tokens as "总Token",
                        cost_usd as "成本(USD)",
                        cost_cny as "成本(CNY)",
                        keyword as "关键词",
                        platform as "平台",
                        brand as "品牌",
                        created_at as "调用时间"
                    FROM api_calls
                    WHERE 1=1
                """
                params = []
                
                if brand:
                    query += " AND brand = ?"
                    params.append(brand)
                if operation_type:
                    query += " AND operation_type = ?"
                    params.append(operation_type)
                if start_date:
                    query += " AND DATE(created_at) >= ?"
                    params.append(start_date)
                if end_date:
                    query += " AND DATE(created_at) <= ?"
                    params.append(end_date)
                
                query += " ORDER BY created_at DESC"
                
                df = pd.read_sql_query(query, conn, params=params)
                return df
        else:
            json_file = Path(self.db_path) / "api_calls.json"
            if not json_file.exists():
                return pd.DataFrame()
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 过滤数据
            if brand:
                data = [item for item in data if item.get("brand") == brand]
            if operation_type:
                data = [item for item in data if item.get("operation_type") == operation_type]
            if start_date:
                data = [item for item in data if item.get("created_at", "") >= start_date]
            if end_date:
                data = [item for item in data if item.get("created_at", "") <= end_date]
            
            # 转换为 DataFrame
            records = []
            for item in data:
                records.append({
                    "操作类型": item.get("operation_type"),
                    "提供商": item.get("provider"),
                    "模型": item.get("model"),
                    "输入Token": item.get("input_tokens", 0),
                    "输出Token": item.get("output_tokens", 0),
                    "总Token": item.get("total_tokens", 0),
                    "成本(USD)": item.get("cost_usd", 0.0),
                    "成本(CNY)": item.get("cost_cny", 0.0),
                    "关键词": item.get("keyword"),
                    "平台": item.get("platform"),
                    "品牌": item.get("brand"),
                    "调用时间": item.get("created_at")
                })
            
            df = pd.DataFrame(records)
            if not df.empty and "调用时间" in df.columns:
                df = df.sort_values("调用时间", ascending=False)
            return df
    
    def get_cost_stats(self, brand: Optional[str] = None) -> Dict[str, Any]:
        """获取成本统计"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if brand:
                    cursor.execute("""
                        SELECT 
                            SUM(cost_usd) as total_usd,
                            SUM(cost_cny) as total_cny,
                            SUM(total_tokens) as total_tokens,
                            COUNT(*) as total_calls
                        FROM api_calls WHERE brand = ?
                    """, (brand,))
                else:
                    cursor.execute("""
                        SELECT 
                            SUM(cost_usd) as total_usd,
                            SUM(cost_cny) as total_cny,
                            SUM(total_tokens) as total_tokens,
                            COUNT(*) as total_calls
                        FROM api_calls
                    """)
                
                row = cursor.fetchone()
                
                return {
                    "total_cost_usd": row[0] or 0.0,
                    "total_cost_cny": row[1] or 0.0,
                    "total_tokens": row[2] or 0,
                    "total_calls": row[3] or 0
                }
        else:
            json_file = Path(self.db_path) / "api_calls.json"
            if not json_file.exists():
                return {
                    "total_cost_usd": 0.0,
                    "total_cost_cny": 0.0,
                    "total_tokens": 0,
                    "total_calls": 0
                }
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if brand:
                data = [item for item in data if item.get("brand") == brand]
            
            return {
                "total_cost_usd": sum(item.get("cost_usd", 0.0) for item in data),
                "total_cost_cny": sum(item.get("cost_cny", 0.0) for item in data),
                "total_tokens": sum(item.get("total_tokens", 0) for item in data),
                "total_calls": len(data)
            }
    
    # ==================== 工作流相关 ====================
    
    def save_workflow(self, workflow: Dict[str, Any]) -> str:
        """保存工作流"""
        import uuid
        workflow_id = workflow.get("id") or str(uuid.uuid4())
        workflow["id"] = workflow_id
        
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO workflows 
                    (id, name, steps, schedule, conditions, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    workflow_id,
                    workflow.get("name", ""),
                    json.dumps(workflow.get("steps", []), ensure_ascii=False),
                    json.dumps(workflow.get("schedule", {}), ensure_ascii=False),
                    json.dumps(workflow.get("conditions", []), ensure_ascii=False),
                    1 if workflow.get("enabled", True) else 0,
                    workflow.get("created_at", datetime.now().isoformat()),
                    workflow.get("updated_at", datetime.now().isoformat())
                ))
                conn.commit()
        else:
            json_file = Path(self.db_path) / "workflows.json"
            data = []
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # 检查是否已存在
            existing = [i for i, w in enumerate(data) if w.get("id") == workflow_id]
            if existing:
                data[existing[0]] = workflow
            else:
                data.append(workflow)
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return workflow_id
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
                row = cursor.fetchone()
            
            if not row:
                return None
            
            return {
                "id": row[0],
                "name": row[1],
                "steps": json.loads(row[2]),
                "schedule": json.loads(row[3]) if row[3] else {},
                "conditions": json.loads(row[4]) if row[4] else [],
                "enabled": bool(row[5]),
                "created_at": row[6],
                "updated_at": row[7]
            }
        else:
            json_file = Path(self.db_path) / "workflows.json"
            if not json_file.exists():
                return None
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for workflow in data:
                if workflow.get("id") == workflow_id:
                    return workflow
            return None
    
    def list_workflows(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """列出所有工作流"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                if enabled_only:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM workflows WHERE enabled = 1 ORDER BY updated_at DESC")
                else:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM workflows ORDER BY updated_at DESC")
                
                rows = cursor.fetchall()
            
            workflows = []
            for row in rows:
                workflows.append({
                    "id": row[0],
                    "name": row[1],
                    "steps": json.loads(row[2]),
                    "schedule": json.loads(row[3]) if row[3] else {},
                    "conditions": json.loads(row[4]) if row[4] else [],
                    "enabled": bool(row[5]),
                    "created_at": row[6],
                    "updated_at": row[7]
                })
            return workflows
        else:
            json_file = Path(self.db_path) / "workflows.json"
            if not json_file.exists():
                return []
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if enabled_only:
                return [w for w in data if w.get("enabled", True)]
            return data
    
    def update_workflow(self, workflow_id: str, workflow: Dict[str, Any]) -> bool:
        """更新工作流"""
        workflow["id"] = workflow_id
        workflow["updated_at"] = datetime.now().isoformat()
        
        try:
            self.save_workflow(workflow)
            return True
        except Exception:
            return False
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """删除工作流"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
                conn.commit()
            return True
        else:
            json_file = Path(self.db_path) / "workflows.json"
            if not json_file.exists():
                return False
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data = [w for w in data if w.get("id") != workflow_id]
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
    
    def save_workflow_execution(self, execution: Dict[str, Any]):
        """保存工作流执行记录"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO workflow_executions 
                    (workflow_id, status, result, started_at, completed_at, error)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    execution.get("workflow_id"),
                    execution.get("status"),
                    json.dumps(execution.get("result", {}), ensure_ascii=False),
                    execution.get("started_at"),
                    execution.get("completed_at"),
                    execution.get("error")
                ))
                conn.commit()
        else:
            json_file = Path(self.db_path) / "workflow_executions.json"
            data = []
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            data.append(execution)
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_workflow_executions(self, workflow_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取工作流执行记录"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                if workflow_id:
                    df = pd.read_sql_query(
                        "SELECT * FROM workflow_executions WHERE workflow_id = ? ORDER BY started_at DESC LIMIT ?",
                        conn, params=(workflow_id, limit)
                    )
                else:
                    df = pd.read_sql_query(
                        "SELECT * FROM workflow_executions ORDER BY started_at DESC LIMIT ?",
                        conn, params=(limit,)
                    )
            return df.to_dict('records')
        else:
            json_file = Path(self.db_path) / "workflow_executions.json"
            if not json_file.exists():
                return []
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if workflow_id:
                data = [e for e in data if e.get("workflow_id") == workflow_id]
            
            return sorted(data, key=lambda x: x.get("started_at", ""), reverse=True)[:limit]
    
    def save_workflow_template(self, template: Dict[str, Any]) -> str:
        """保存工作流模板"""
        import uuid
        template_id = template.get("id") or str(uuid.uuid4())
        template["id"] = template_id
        
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO workflow_templates 
                    (id, name, description, steps, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    template_id,
                    template.get("name", ""),
                    template.get("description", ""),
                    json.dumps(template.get("steps", []), ensure_ascii=False),
                    template.get("created_at", datetime.now().isoformat())
                ))
                conn.commit()
        else:
            json_file = Path(self.db_path) / "workflow_templates.json"
            data = []
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            existing = [i for i, t in enumerate(data) if t.get("id") == template_id]
            if existing:
                data[existing[0]] = template
            else:
                data.append(template)
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return template_id
    
    def get_workflow_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流模板"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM workflow_templates WHERE id = ?", (template_id,))
                row = cursor.fetchone()
            
            if not row:
                return None
            
            return {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "steps": json.loads(row[3]),
                "created_at": row[4]
            }
        else:
            json_file = Path(self.db_path) / "workflow_templates.json"
            if not json_file.exists():
                return None
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for template in data:
                if template.get("id") == template_id:
                    return template
            return None
    
    def get_workflow_templates(self) -> List[Dict[str, Any]]:
        """获取所有工作流模板"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query("SELECT * FROM workflow_templates ORDER BY created_at DESC", conn)
            return df.to_dict('records')
        else:
            json_file = Path(self.db_path) / "workflow_templates.json"
            if not json_file.exists():
                return []
            
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    # ==================== 平台账号相关 ====================
    
    def save_platform_account(self, platform: str, account_config: Dict[str, Any], brand: str):
        """保存平台账号配置"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO platform_accounts 
                    (platform, account_type, account_name, api_key, api_secret, access_token, 
                     refresh_token, token_expires_at, config_json, brand, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    platform,
                    account_config.get('account_type', 'api'),
                    account_config.get('account_name', ''),
                    account_config.get('api_key', ''),
                    account_config.get('api_secret', ''),
                    account_config.get('access_token', ''),
                    account_config.get('refresh_token', ''),
                    account_config.get('token_expires_at'),
                    json.dumps(account_config.get('config', {}), ensure_ascii=False),
                    brand,
                    datetime.now().isoformat()
                ))
                conn.commit()
        else:
            json_file = Path(self.db_path) / "platform_accounts.json"
            data = []
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # 检查是否已存在
            existing = [i for i, acc in enumerate(data) 
                       if acc.get('platform') == platform and acc.get('brand') == brand]
            if existing:
                data[existing[0]] = {
                    'platform': platform,
                    'brand': brand,
                    **account_config,
                    'updated_at': datetime.now().isoformat()
                }
            else:
                data.append({
                    'platform': platform,
                    'brand': brand,
                    **account_config,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                })
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_platform_account(self, platform: str, brand: str) -> Optional[Dict[str, Any]]:
        """获取平台账号配置"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM platform_accounts 
                    WHERE platform = ? AND brand = ? AND is_active = 1
                    ORDER BY updated_at DESC LIMIT 1
                """, (platform, brand))
                row = cursor.fetchone()
            
            if row:
                return {
                    'account_type': row[2],
                    'account_name': row[3],
                    'api_key': row[4],
                    'api_secret': row[5],
                    'access_token': row[6],
                    'refresh_token': row[7],
                    'token_expires_at': row[8],
                    'config': json.loads(row[9] or '{}')
                }
        else:
            json_file = Path(self.db_path) / "platform_accounts.json"
            if not json_file.exists():
                return None
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for acc in data:
                if acc.get('platform') == platform and acc.get('brand') == brand:
                    return {k: v for k, v in acc.items() if k not in ['platform', 'brand', 'created_at', 'updated_at']}
        
        return None
    
    def list_platform_accounts(self, brand: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有平台账号"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                if brand:
                    df = pd.read_sql_query(
                        "SELECT * FROM platform_accounts WHERE brand = ? AND is_active = 1 ORDER BY updated_at DESC",
                        conn, params=(brand,)
                    )
                else:
                    df = pd.read_sql_query(
                        "SELECT * FROM platform_accounts WHERE is_active = 1 ORDER BY updated_at DESC",
                        conn
                    )
            return df.to_dict('records')
        else:
            json_file = Path(self.db_path) / "platform_accounts.json"
            if not json_file.exists():
                return []
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if brand:
                return [acc for acc in data if acc.get('brand') == brand and acc.get('is_active', True)]
            return [acc for acc in data if acc.get('is_active', True)]
    
    # ==================== 发布记录相关 ====================
    
    def save_publish_record(self, article_id: int, platform: str, publish_method: str,
                           publish_status: str, publish_url: str = '', publish_id: str = '',
                           error_message: str = '', retry_count: int = 0):
        """保存发布记录"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO publish_records 
                    (article_id, platform, publish_method, publish_status, publish_url, 
                     publish_id, error_message, retry_count, published_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article_id, platform, publish_method, publish_status,
                    publish_url, publish_id, error_message, retry_count,
                    datetime.now().isoformat() if publish_status == 'success' else None
                ))
                conn.commit()
        else:
            json_file = Path(self.db_path) / "publish_records.json"
            data = []
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            data.append({
                'article_id': article_id,
                'platform': platform,
                'publish_method': publish_method,
                'publish_status': publish_status,
                'publish_url': publish_url,
                'publish_id': publish_id,
                'error_message': error_message,
                'retry_count': retry_count,
                'published_at': datetime.now().isoformat() if publish_status == 'success' else None,
                'created_at': datetime.now().isoformat()
            })
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_publish_records(self, article_id: Optional[int] = None,
                           platform: Optional[str] = None,
                           brand: Optional[str] = None) -> List[Dict]:
        """获取发布记录"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT pr.*, a.brand FROM publish_records pr LEFT JOIN articles a ON pr.article_id = a.id WHERE 1=1"
                params = []
                
                if article_id:
                    query += " AND pr.article_id = ?"
                    params.append(article_id)
                if platform:
                    query += " AND pr.platform = ?"
                    params.append(platform)
                if brand:
                    query += " AND a.brand = ?"
                    params.append(brand)
                
                query += " ORDER BY pr.created_at DESC"
                
                df = pd.read_sql_query(query, conn, params=params)
            return df.to_dict('records')
        else:
            json_file = Path(self.db_path) / "publish_records.json"
            if not json_file.exists():
                return []
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 过滤
            if article_id:
                data = [r for r in data if r.get('article_id') == article_id]
            if platform:
                data = [r for r in data if r.get('platform') == platform]
            
            return data
    
    def get_article_by_id(self, article_id: int) -> Optional[Dict]:
        """根据ID获取文章"""
        if self.storage_type == "sqlite":
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(
                    "SELECT * FROM articles WHERE id = ?",
                    conn, params=(article_id,)
                )
            if not df.empty:
                return df.iloc[0].to_dict()
        else:
            json_file = Path(self.db_path) / "articles.json"
            if not json_file.exists():
                return None
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for article in data:
                if article.get('id') == article_id:
                    return article
        
        return None

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
        conn = sqlite3.connect(self.db_path)
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
        
        conn.commit()
        conn.close()
    
    def _init_json(self):
        """初始化JSON存储目录"""
        Path(self.db_path).mkdir(parents=True, exist_ok=True)
    
    # ==================== 关键词相关 ====================
    
    def save_keywords(self, keywords: List[str], brand: str):
        """保存关键词列表"""
        if self.storage_type == "sqlite":
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for keyword in keywords:
                cursor.execute(
                    "INSERT INTO keywords (keyword, brand) VALUES (?, ?)",
                    (keyword, brand)
                )
            conn.commit()
            conn.close()
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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            if brand:
                cursor.execute("SELECT keyword FROM keywords WHERE brand = ?", (brand,))
            else:
                cursor.execute("SELECT keyword FROM keywords")
            keywords = [row[0] for row in cursor.fetchall()]
            conn.close()
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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO articles (keyword, platform, content, filename, brand)
                VALUES (?, ?, ?, ?, ?)
            """, (keyword, platform, content, filename, brand))
            conn.commit()
            conn.close()
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
            conn = sqlite3.connect(self.db_path)
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
            conn.close()
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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO optimizations 
                (original_content, optimized_content, changes, platform, brand)
                VALUES (?, ?, ?, ?, ?)
            """, (original_content, optimized_content, changes, platform, brand))
            conn.commit()
            conn.close()
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
            conn = sqlite3.connect(self.db_path)
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
            conn.close()
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
            conn = sqlite3.connect(self.db_path)
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
            conn.close()
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
            conn = sqlite3.connect(self.db_path)
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
            conn.close()
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
            conn = sqlite3.connect(self.db_path)
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
            
            conn.close()
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

"""
更新文档中对工具脚本的引用路径
将旧路径更新为 scripts/ 前缀
"""
import re
from pathlib import Path

# 项目根目录
root = Path(__file__).parent

# 工具脚本列表
scripts = [
    "cleanup_duplicate_docs.py",
    "move_reorganization_docs.py",
    "reorganize_files.py",
    "update_imports.py",
    "update_doc_references.py",
]

# 路径更新映射
path_mappings = {
    # 旧路径 -> 新路径
    r'`(cleanup_duplicate_docs\.py)`': r'`scripts/\1`',
    r'`(move_reorganization_docs\.py)`': r'`scripts/\1`',
    r'`(reorganize_files\.py)`': r'`scripts/\1`',
    r'`(update_imports\.py)`': r'`scripts/\1`',
    r'`(update_doc_references\.py)`': r'`scripts/\1`',
    
    # 命令中的路径
    r'python (cleanup_duplicate_docs\.py)': r'python scripts/\1',
    r'python (move_reorganization_docs\.py)': r'python scripts/\1',
    r'python (reorganize_files\.py)': r'python scripts/\1',
    r'python (update_imports\.py)': r'python scripts/\1',
    r'python (update_doc_references\.py)': r'python scripts/\1',
    
    # 文档中的描述
    r'- `(cleanup_duplicate_docs\.py)`': r'- `scripts/\1`',
    r'- `(move_reorganization_docs\.py)`': r'- `scripts/\1`',
    r'- `(reorganize_files\.py)`': r'- `scripts/\1`',
    r'- `(update_imports\.py)`': r'- `scripts/\1`',
    r'- `(update_doc_references\.py)`': r'- `scripts/\1`',
}

def update_script_references(file_path: Path):
    """更新单个文件中的脚本引用路径"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        updated = False
        
        # 更新脚本路径引用
        for pattern, replacement in path_mappings.items():
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                updated = True
        
        if updated and content != original_content:
            file_path.write_text(content, encoding='utf-8')
            print(f"✓ Updated: {file_path.relative_to(root)}")
            return True
        return False
    except Exception as e:
        print(f"✗ Error updating {file_path.name}: {e}")
        return False

def main():
    """更新所有文档中的脚本引用路径"""
    updated_count = 0
    
    # 更新根目录的文档
    root_docs = [
        "FINAL_OPTIMIZATION_GUIDE.md",
        "ADVANCED_OPTIMIZATION_PLAN.md",
    ]
    
    for doc_file in root_docs:
        doc_path = root / doc_file
        if doc_path.exists():
            if update_script_references(doc_path):
                updated_count += 1
    
    # 更新 docs/ 目录下的所有 .md 文件
    docs_dir = root / "docs"
    if docs_dir.exists():
        for md_file in docs_dir.rglob("*.md"):
            if update_script_references(md_file):
                updated_count += 1
    
    print(f"\n✅ Updated {updated_count} documentation files")

if __name__ == "__main__":
    main()

"""
移动重组相关文档到 docs/guides/ 目录
"""
from pathlib import Path
import shutil

# 项目根目录
root = Path(__file__).parent

# 需要移动的重组相关文档
reorganization_docs = [
    "DOCUMENTATION_CLEANUP_GUIDE.md",
    "PROJECT_STRUCTURE_ANALYSIS.md",
    "QUICK_REORGANIZE.md",
    "REORGANIZATION_SUMMARY.md",
]

# 目标目录
target_dir = root / "docs" / "guides"
target_dir.mkdir(parents=True, exist_ok=True)

def move_reorganization_docs():
    """移动重组相关文档到 docs/guides/"""
    moved_count = 0
    
    print("开始移动重组相关文档到 docs/guides/...\n")
    
    for doc_file in reorganization_docs:
        src = root / doc_file
        dest = target_dir / doc_file
        
        if src.exists():
            if dest.exists():
                print(f"⚠ 跳过: {doc_file} (目标位置已存在)")
            else:
                try:
                    shutil.move(str(src), str(dest))
                    print(f"✓ 已移动: {doc_file} -> docs/guides/")
                    moved_count += 1
                except Exception as e:
                    print(f"✗ 移动失败: {doc_file} - {e}")
        else:
            print(f"ℹ 不存在: {doc_file}")
    
    print(f"\n✅ 移动完成！")
    print(f"   - 已移动: {moved_count} 个文件")
    print(f"\n📌 这些文档现在位于: docs/guides/")

if __name__ == "__main__":
    move_reorganization_docs()

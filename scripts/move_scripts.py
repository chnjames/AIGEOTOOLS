"""
移动工具脚本到 scripts/ 目录
"""
from pathlib import Path
import shutil

# 项目根目录
root = Path(__file__).parent

# 需要移动的工具脚本
scripts_to_move = [
    "cleanup_duplicate_docs.py",
    "move_reorganization_docs.py",
    "reorganize_files.py",
    "update_imports.py",
    "update_doc_references.py",
]

# 目标目录
target_dir = root / "scripts"
target_dir.mkdir(parents=True, exist_ok=True)

def move_scripts():
    """移动工具脚本到 scripts/ 目录"""
    moved_count = 0
    
    print("开始移动工具脚本到 scripts/ 目录...\n")
    
    for script_file in scripts_to_move:
        src = root / script_file
        dest = target_dir / script_file
        
        if src.exists():
            if dest.exists():
                print(f"⚠ 跳过: {script_file} (目标位置已存在)")
            else:
                try:
                    shutil.move(str(src), str(dest))
                    print(f"✓ 已移动: {script_file} -> scripts/")
                    moved_count += 1
                except Exception as e:
                    print(f"✗ 移动失败: {script_file} - {e}")
        else:
            print(f"ℹ 不存在: {script_file}")
    
    print(f"\n✅ 移动完成！")
    print(f"   - 已移动: {moved_count} 个文件")
    print(f"\n📌 这些脚本现在位于: scripts/")
    print(f"   使用方式: python scripts/script_name.py")

if __name__ == "__main__":
    move_scripts()

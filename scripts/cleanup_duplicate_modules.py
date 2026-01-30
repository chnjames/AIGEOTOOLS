"""
清理根目录中的重复模块文件
保留 modules/ 目录中的版本，删除根目录的重复文件
"""
from pathlib import Path

# 项目根目录
root = Path(__file__).parent

# 需要保留在根目录的文件（不删除）
keep_in_root = {
    "README.md",
    "DOCS.md",
    "requirements.txt",
    ".gitignore",
    "geo_tool.py",  # 主程序
}

# 需要删除的重复模块文件（已在 modules/ 目录下）
duplicate_modules = [
    "config_optimizer.py",
    "content_metrics.py",
    "content_scorer.py",
    "data_storage.py",
    "eeat_enhancer.py",
    "fact_density_enhancer.py",
    "keyword_mining.py",
    "keyword_tool.py",
    "multimodal_prompt.py",
    "negative_monitor.py",
    "optimization_techniques.py",
    "resource_recommender.py",
    "roi_analyzer.py",
    "schema_generator.py",
    "semantic_expander.py",
    "storage_example.py",
    "technical_config_generator.py",
    "topic_cluster.py",
    "workflow_automation.py",
]

def cleanup_duplicates():
    """清理根目录中的重复模块文件"""
    removed_count = 0
    skipped_count = 0
    error_count = 0
    
    print("开始清理根目录中的重复模块文件...\n")
    print("⚠️  警告：此操作将删除根目录的模块文件，请确保：")
    print("   1. modules/ 目录中已有完整版本")
    print("   2. geo_tool.py 中的导入路径已更新为 modules.xxx")
    print("   3. 已测试程序可以正常运行\n")
    
    for module_file in duplicate_modules:
        root_file = root / module_file
        modules_file = root / "modules" / module_file
        
        if root_file.exists():
            # 检查 modules/ 目录下是否存在
            if modules_file.exists():
                try:
                    root_file.unlink()
                    print(f"✓ 已删除: {module_file} (modules/ 中已有)")
                    removed_count += 1
                except Exception as e:
                    print(f"✗ 删除失败: {module_file} - {e}")
                    error_count += 1
            else:
                print(f"⚠ 跳过: {module_file} (modules/ 中不存在，保留根目录版本)")
                skipped_count += 1
        else:
            print(f"ℹ 不存在: {module_file}")
    
    print(f"\n✅ 清理完成！")
    print(f"   - 已删除: {removed_count} 个文件")
    print(f"   - 已跳过: {skipped_count} 个文件")
    print(f"   - 错误: {error_count} 个文件")
    
    if removed_count > 0:
        print(f"\n📌 重要提醒：")
        print(f"   1. 请运行 'streamlit run geo_tool.py' 测试程序")
        print(f"   2. 确认所有功能正常工作")
        print(f"   3. 如有问题，可从 Git 历史恢复文件")

if __name__ == "__main__":
    import sys
    response = input("\n确认要删除根目录的重复模块文件吗？(yes/no): ")
    if response.lower() in ['yes', 'y']:
        cleanup_duplicates()
    else:
        print("操作已取消")

"""
临时脚本：重组项目文件结构
"""
import os
import shutil
from pathlib import Path

# 项目根目录
root = Path(__file__).parent

# 文档分类映射
doc_mapping = {
    # 功能文档
    "features": [
        "*_FEATURE.md"
    ],
    # 分析报告
    "analysis": [
        "ANALYSIS_ACCURACY_REPORT.md",
        "CODE_DOCUMENTATION_ANALYSIS.md",
        "DOCUMENTATION_REVERSE_VERIFICATION.md",
        "FEATURE_ANALYSIS.md",
        "FEATURE_PRIORITY_ANALYSIS.md",
        "FUNCTION_VERIFICATION_REPORT.md",
        "GEO_COMPLIANCE_ANALYSIS.md",
    ],
    # 指南文档
    "guides": [
        "QUICK_START_GUIDE.md",
        "STORAGE_GUIDE.md",
        "PLATFORM_SETUP.md",
        "LAYOUT_UPGRADE_GUIDE.md",
        "DECISION_GUIDE.md",
    ],
    # 实现文档
    "implementation": [
        "IMPLEMENTATION_SUMMARY.md",
        "PLATFORM_SYNC_ANALYSIS.md",
        "PLATFORM_SYNC_IMPLEMENTATION.md",
        "PLATFORM_SYNC_TEST.md",
        "INTEGRATION_NOTES.md",
        "FEATURES_COMPLETE_LIST.md",
        "ADVANCED_FEATURES.md",
    ],
}

# 功能模块文件列表
module_files = [
    "data_storage.py",
    "keyword_tool.py",
    "content_scorer.py",
    "eeat_enhancer.py",
    "semantic_expander.py",
    "fact_density_enhancer.py",
    "schema_generator.py",
    "topic_cluster.py",
    "multimodal_prompt.py",
    "roi_analyzer.py",
    "workflow_automation.py",
    "keyword_mining.py",
    "optimization_techniques.py",
    "content_metrics.py",
    "technical_config_generator.py",
    "negative_monitor.py",
    "resource_recommender.py",
    "config_optimizer.py",
    "storage_example.py",
]

def move_files():
    """移动文件到对应目录"""
    moved_count = 0
    
    # 移动功能文档（*_FEATURE.md）
    features_dir = root / "docs" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    for file in root.glob("*_FEATURE.md"):
        try:
            dest = features_dir / file.name
            if not dest.exists():
                shutil.move(str(file), str(dest))
                print(f"✓ Moved {file.name} -> docs/features/")
                moved_count += 1
            else:
                print(f"⚠ Skipped {file.name} (already exists)")
        except Exception as e:
            print(f"✗ Failed to move {file.name}: {e}")
    
    # 移动其他文档
    for category, files in doc_mapping.items():
        if category == "features":
            continue  # 已经处理过了
        
        target_dir = root / "docs" / category
        target_dir.mkdir(parents=True, exist_ok=True)
        
        for filename in files:
            src = root / filename
            if src.exists():
                try:
                    dest = target_dir / filename
                    if not dest.exists():
                        shutil.move(str(src), str(dest))
                        print(f"✓ Moved {filename} -> docs/{category}/")
                        moved_count += 1
                    else:
                        print(f"⚠ Skipped {filename} (already exists)")
                except Exception as e:
                    print(f"✗ Failed to move {filename}: {e}")
            else:
                print(f"⚠ File not found: {filename}")
    
    # 移动功能模块
    modules_dir = root / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)
    
    for filename in module_files:
        src = root / filename
        if src.exists():
            try:
                dest = modules_dir / filename
                if not dest.exists():
                    shutil.move(str(src), str(dest))
                    print(f"✓ Moved {filename} -> modules/")
                    moved_count += 1
                else:
                    print(f"⚠ Skipped {filename} (already exists)")
            except Exception as e:
                print(f"✗ Failed to move {filename}: {e}")
        else:
            print(f"⚠ File not found: {filename}")
    
    print(f"\n✅ Total moved: {moved_count} files")

if __name__ == "__main__":
    move_files()

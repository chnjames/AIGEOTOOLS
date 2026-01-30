"""
更新所有文档文件中的路径引用
"""
import re
from pathlib import Path

# 项目根目录
root = Path(__file__).parent

# 文档路径映射（旧路径 -> 新路径）
doc_path_mappings = {
    # 功能文档
    r'`([A-Z_]+_FEATURE\.md)`': r'`docs/features/\1`',
    r'\(([A-Z_]+_FEATURE\.md)\)': r'(docs/features/\1)',
    r'([A-Z_]+_FEATURE\.md)': r'docs/features/\1',
    
    # 分析报告
    r'`(ANALYSIS_ACCURACY_REPORT\.md)`': r'`docs/analysis/\1`',
    r'`(CODE_DOCUMENTATION_ANALYSIS\.md)`': r'`docs/analysis/\1`',
    r'`(DOCUMENTATION_REVERSE_VERIFICATION\.md)`': r'`docs/analysis/\1`',
    r'`(FEATURE_ANALYSIS\.md)`': r'`docs/analysis/\1`',
    r'`(FEATURE_PRIORITY_ANALYSIS\.md)`': r'`docs/analysis/\1`',
    r'`(FUNCTION_VERIFICATION_REPORT\.md)`': r'`docs/analysis/\1`',
    r'`(GEO_COMPLIANCE_ANALYSIS\.md)`': r'`docs/analysis/\1`',
    
    # 指南文档
    r'`(QUICK_START_GUIDE\.md)`': r'`docs/guides/\1`',
    r'`(STORAGE_GUIDE\.md)`': r'`docs/guides/\1`',
    r'`(PLATFORM_SETUP\.md)`': r'`docs/guides/\1`',
    r'`(LAYOUT_UPGRADE_GUIDE\.md)`': r'`docs/guides/\1`',
    r'`(DECISION_GUIDE\.md)`': r'`docs/guides/\1`',
    
    # 实现文档
    r'`(IMPLEMENTATION_SUMMARY\.md)`': r'`docs/implementation/\1`',
    r'`(PLATFORM_SYNC_ANALYSIS\.md)`': r'`docs/implementation/\1`',
    r'`(PLATFORM_SYNC_IMPLEMENTATION\.md)`': r'`docs/implementation/\1`',
    r'`(PLATFORM_SYNC_TEST\.md)`': r'`docs/implementation/\1`',
    r'`(INTEGRATION_NOTES\.md)`': r'`docs/implementation/\1`',
    r'`(FEATURES_COMPLETE_LIST\.md)`': r'`docs/implementation/\1`',
    r'`(ADVANCED_FEATURES\.md)`': r'`docs/implementation/\1`',
    
    # 模块文件路径
    r'`([a-z_]+\.py)`': r'`modules/\1`',
    r'\(([a-z_]+\.py)\)': r'(modules/\1)',
}

# 需要更新的模块文件名
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
]

def update_doc_references(file_path: Path):
    """更新单个文档文件中的路径引用"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        updated = False
        
        # 更新文档路径引用
        for pattern, replacement in doc_path_mappings.items():
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                updated = True
        
        # 更新模块文件路径（更精确的匹配）
        for module_file in module_files:
            # 匹配 `module_file` 或 (module_file) 格式
            patterns = [
                (rf'`{re.escape(module_file)}`', f'`modules/{module_file}`'),
                (rf'\({re.escape(module_file)}\)', f'(modules/{module_file})'),
                (rf'([^/]){re.escape(module_file)}', rf'\1modules/{module_file}'),
            ]
            for pattern, replacement in patterns:
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
    """更新所有文档文件中的路径引用"""
    updated_count = 0
    
    # 更新README.md
    readme = root / "README.md"
    if readme.exists():
        if update_doc_references(readme):
            updated_count += 1
    
    # 更新docs目录下的所有.md文件
    docs_dir = root / "docs"
    if docs_dir.exists():
        for md_file in docs_dir.rglob("*.md"):
            if update_doc_references(md_file):
                updated_count += 1
    
    print(f"\n✅ Updated {updated_count} documentation files")

if __name__ == "__main__":
    main()

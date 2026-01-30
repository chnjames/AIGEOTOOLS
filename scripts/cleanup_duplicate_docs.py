"""
清理根目录中的重复文档文件
保留 docs/ 目录下的分类版本，删除根目录的重复文件
"""
from pathlib import Path

# 项目根目录
root = Path(__file__).parent

# 需要保留在根目录的文档（不删除）
keep_in_root = {
    "README.md",
    "DOCS.md",  # 文档索引
}

# 需要删除的文档文件（已在 docs/ 目录下）
docs_to_remove = [
    # 功能文档
    "CONFIG_OPTIMIZER_FEATURE.md",
    "CONTENT_METRICS_FEATURE.md",
    "CONTENT_SCORER_FEATURE.md",
    "EEAT_FEATURE.md",
    "FACT_DENSITY_FEATURE.md",
    "JSON_LD_SCHEMA_FEATURE.md",
    "KEYWORD_MINING_FEATURE.md",
    "MULTIMODAL_FEATURE.md",
    "NEGATIVE_MONITOR_FEATURE.md",
    "OPTIMIZATION_TECHNIQUES_FEATURE.md",
    "RESOURCE_RECOMMENDER_FEATURE.md",
    "ROI_ANALYSIS_FEATURE.md",
    "SEMANTIC_EXPANSION_FEATURE.md",
    "TECHNICAL_CONFIG_FEATURE.md",
    "TOPIC_CLUSTER_FEATURE.md",
    "WORKFLOW_AUTOMATION_FEATURE.md",
    
    # 分析报告
    "ANALYSIS_ACCURACY_REPORT.md",
    "CODE_DOCUMENTATION_ANALYSIS.md",
    "DOCUMENTATION_REVERSE_VERIFICATION.md",
    "FEATURE_ANALYSIS.md",
    "FEATURE_PRIORITY_ANALYSIS.md",
    "FUNCTION_VERIFICATION_REPORT.md",
    "GEO_COMPLIANCE_ANALYSIS.md",
    
    # 指南文档
    "QUICK_START_GUIDE.md",
    "STORAGE_GUIDE.md",
    "PLATFORM_SETUP.md",
    "LAYOUT_UPGRADE_GUIDE.md",
    "DECISION_GUIDE.md",
    
    # 实现文档
    "IMPLEMENTATION_SUMMARY.md",
    "PLATFORM_SYNC_ANALYSIS.md",
    "PLATFORM_SYNC_IMPLEMENTATION.md",
    "PLATFORM_SYNC_TEST.md",
    "INTEGRATION_NOTES.md",
    "FEATURES_COMPLETE_LIST.md",
    "ADVANCED_FEATURES.md",
    
    # 重组相关文档（已移动到 docs/guides/）
    "DOCUMENTATION_CLEANUP_GUIDE.md",
    "PROJECT_STRUCTURE_ANALYSIS.md",
    "QUICK_REORGANIZE.md",
    "REORGANIZATION_SUMMARY.md",
]

def cleanup_duplicates():
    """清理根目录中的重复文档"""
    removed_count = 0
    skipped_count = 0
    
    print("开始清理根目录中的重复文档...\n")
    
    for doc_file in docs_to_remove:
        file_path = root / doc_file
        
        if file_path.exists():
            # 检查是否在 docs/ 目录下存在
            found_in_docs = False
            for docs_subdir in ["features", "analysis", "guides", "implementation"]:
                docs_path = root / "docs" / docs_subdir / doc_file
                if docs_path.exists():
                    found_in_docs = True
                    break
            
            if found_in_docs:
                try:
                    file_path.unlink()
                    print(f"✓ 已删除: {doc_file} (已在 docs/ 目录下)")
                    removed_count += 1
                except Exception as e:
                    print(f"✗ 删除失败: {doc_file} - {e}")
            else:
                print(f"⚠ 跳过: {doc_file} (docs/ 目录下未找到对应文件)")
                skipped_count += 1
        else:
            print(f"ℹ 不存在: {doc_file}")
    
    print(f"\n✅ 清理完成！")
    print(f"   - 已删除: {removed_count} 个文件")
    print(f"   - 已跳过: {skipped_count} 个文件")
    print(f"\n📌 保留在根目录的文档：")
    for doc in sorted(keep_in_root):
        doc_path = root / doc
        if doc_path.exists():
            print(f"   ✓ {doc}")
        else:
            print(f"   ⚠ {doc} (不存在)")

if __name__ == "__main__":
    cleanup_duplicates()

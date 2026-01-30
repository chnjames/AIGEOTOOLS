"""
更新所有Python文件中的导入路径
"""
import re
from pathlib import Path

# 项目根目录
root = Path(__file__).parent

# 需要更新的导入映射
import_mappings = {
    "from data_storage": "from modules.data_storage",
    "from keyword_tool": "from modules.keyword_tool",
    "from content_scorer": "from modules.content_scorer",
    "from eeat_enhancer": "from modules.eeat_enhancer",
    "from semantic_expander": "from modules.semantic_expander",
    "from fact_density_enhancer": "from modules.fact_density_enhancer",
    "from schema_generator": "from modules.schema_generator",
    "from topic_cluster": "from modules.topic_cluster",
    "from multimodal_prompt": "from modules.multimodal_prompt",
    "from roi_analyzer": "from modules.roi_analyzer",
    "from workflow_automation": "from modules.workflow_automation",
    "from keyword_mining": "from modules.keyword_mining",
    "from optimization_techniques": "from modules.optimization_techniques",
    "from content_metrics": "from modules.content_metrics",
    "from technical_config_generator": "from modules.technical_config_generator",
    "from negative_monitor": "from modules.negative_monitor",
    "from resource_recommender": "from modules.resource_recommender",
    "from config_optimizer": "from modules.config_optimizer",
    "import data_storage": "import modules.data_storage",
    "import keyword_tool": "import modules.keyword_tool",
    "import content_scorer": "import modules.content_scorer",
    "import eeat_enhancer": "import modules.eeat_enhancer",
    "import semantic_expander": "import modules.semantic_expander",
    "import fact_density_enhancer": "import modules.fact_density_enhancer",
    "import schema_generator": "import modules.schema_generator",
    "import topic_cluster": "import modules.topic_cluster",
    "import multimodal_prompt": "import modules.multimodal_prompt",
    "import roi_analyzer": "import modules.roi_analyzer",
    "import workflow_automation": "import modules.workflow_automation",
    "import keyword_mining": "import modules.keyword_mining",
    "import optimization_techniques": "import modules.optimization_techniques",
    "import content_metrics": "import modules.content_metrics",
    "import technical_config_generator": "import modules.technical_config_generator",
    "import negative_monitor": "import modules.negative_monitor",
    "import resource_recommender": "import modules.resource_recommender",
    "import config_optimizer": "import modules.config_optimizer",
}

def update_file_imports(file_path: Path):
    """更新单个文件中的导入路径"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        updated = False
        
        for old_import, new_import in import_mappings.items():
            # 使用正则表达式匹配完整的导入语句
            pattern = rf'({re.escape(old_import)})(\s+import|\s+as|\s+)'
            if re.search(pattern, content):
                content = re.sub(pattern, rf'{new_import}\2', content)
                updated = True
        
        if updated:
            file_path.write_text(content, encoding='utf-8')
            print(f"✓ Updated: {file_path.name}")
            return True
        return False
    except Exception as e:
        print(f"✗ Error updating {file_path.name}: {e}")
        return False

def main():
    """更新所有Python文件中的导入路径"""
    # 需要更新的文件列表
    files_to_update = [
        root / "geo_tool.py",
        root / "modules" / "storage_example.py",
    ]
    
    # 如果modules目录存在，也检查其中的文件
    modules_dir = root / "modules"
    if modules_dir.exists():
        for py_file in modules_dir.glob("*.py"):
            if py_file.name != "__init__.py":
                files_to_update.append(py_file)
    
    updated_count = 0
    for file_path in files_to_update:
        if file_path.exists():
            if update_file_imports(file_path):
                updated_count += 1
        else:
            print(f"⚠ File not found: {file_path}")
    
    print(f"\n✅ Updated {updated_count} files")

if __name__ == "__main__":
    main()

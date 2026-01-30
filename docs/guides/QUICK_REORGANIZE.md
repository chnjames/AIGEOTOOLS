# 快速重组项目目录结构

## ⚡ 快速执行步骤

### 步骤1：关闭所有打开的文件
**重要**：在移动文件之前，请关闭所有在IDE或编辑器中打开的文件，否则会出现"文件被占用"的错误。

### 步骤2：执行文件移动

#### 方法A：使用PowerShell脚本（推荐）

在项目根目录打开PowerShell，执行：

```powershell
# 移动功能模块
$modules = @(
    "data_storage.py", "keyword_tool.py", "content_scorer.py", "eeat_enhancer.py",
    "semantic_expander.py", "fact_density_enhancer.py", "schema_generator.py",
    "topic_cluster.py", "multimodal_prompt.py", "roi_analyzer.py",
    "workflow_automation.py", "keyword_mining.py", "optimization_techniques.py",
    "content_metrics.py", "technical_config_generator.py", "negative_monitor.py",
    "resource_recommender.py", "config_optimizer.py", "storage_example.py"
)
foreach ($file in $modules) {
    if (Test-Path $file) {
        Move-Item $file -Destination "modules\" -Force -ErrorAction SilentlyContinue
        Write-Host "✓ $file"
    }
}

# 移动功能文档
Get-ChildItem -Filter "*_FEATURE.md" | ForEach-Object {
    Move-Item $_.FullName -Destination "docs\features\" -Force -ErrorAction SilentlyContinue
    Write-Host "✓ $($_.Name)"
}

# 移动分析报告
$analysis = @(
    "ANALYSIS_ACCURACY_REPORT.md", "CODE_DOCUMENTATION_ANALYSIS.md",
    "DOCUMENTATION_REVERSE_VERIFICATION.md", "FEATURE_ANALYSIS.md",
    "FEATURE_PRIORITY_ANALYSIS.md", "FUNCTION_VERIFICATION_REPORT.md",
    "GEO_COMPLIANCE_ANALYSIS.md"
)
foreach ($file in $analysis) {
    if (Test-Path $file) {
        Move-Item $file -Destination "docs\analysis\" -Force -ErrorAction SilentlyContinue
        Write-Host "✓ $file"
    }
}

# 移动指南文档
$guides = @(
    "QUICK_START_GUIDE.md", "STORAGE_GUIDE.md", "PLATFORM_SETUP.md",
    "LAYOUT_UPGRADE_GUIDE.md", "DECISION_GUIDE.md"
)
foreach ($file in $guides) {
    if (Test-Path $file) {
        Move-Item $file -Destination "docs\guides\" -Force -ErrorAction SilentlyContinue
        Write-Host "✓ $file"
    }
}

# 移动实现文档
$implementation = @(
    "IMPLEMENTATION_SUMMARY.md", "PLATFORM_SYNC_ANALYSIS.md",
    "PLATFORM_SYNC_IMPLEMENTATION.md", "PLATFORM_SYNC_TEST.md",
    "INTEGRATION_NOTES.md", "FEATURES_COMPLETE_LIST.md", "ADVANCED_FEATURES.md"
)
foreach ($file in $implementation) {
    if (Test-Path $file) {
        Move-Item $file -Destination "docs\implementation\" -Force -ErrorAction SilentlyContinue
        Write-Host "✓ $file"
    }
}

Write-Host "`n✅ 文件移动完成！"
```

#### 方法B：手动移动（如果脚本失败）

如果PowerShell脚本因为文件被占用而失败，请：

1. 关闭所有IDE和编辑器
2. 手动将文件拖拽到对应目录
3. 参考 `PROJECT_STRUCTURE_ANALYSIS.md` 中的文件清单

### 步骤3：更新导入路径

```powershell
python scripts/update_imports.py
```

### 步骤4：更新文档引用

```powershell
python scripts/update_doc_references.py
```

### 步骤5：验证

```powershell
# 测试导入是否正常
python -c "from modules.data_storage import DataStorage; print('✓ 导入成功')"
```

## 📋 完整执行清单

- [ ] 关闭所有打开的文件（IDE、编辑器等）
- [ ] 执行文件移动（PowerShell脚本或手动）
- [ ] 运行 `python scripts/update_imports.py`
- [ ] 运行 `python scripts/update_doc_references.py`
- [ ] 测试导入：`python -c "from modules.data_storage import DataStorage"`
- [ ] 运行主程序：`streamlit run geo_tool.py`
- [ ] 检查文档链接是否正常

## 🆘 遇到问题？

### 问题1：文件被占用
**解决方案**：
1. 关闭所有IDE和编辑器
2. 检查是否有Python进程在运行：`tasklist | findstr python`
3. 如果仍有问题，重启计算机后再试

### 问题2：导入错误
**解决方案**：
1. 确认文件已移动到 `modules/` 目录
2. 确认 `modules/__init__.py` 存在
3. 检查 `geo_tool.py` 中的导入路径是否正确

### 问题3：文档链接失效
**解决方案**：
1. 运行 `python scripts/update_doc_references.py`
2. 手动检查 `README.md` 中的链接
3. 使用相对路径而不是绝对路径

## 📚 相关文档

- `PROJECT_STRUCTURE_ANALYSIS.md` - 详细的项目结构分析
- `docs/DIRECTORY_STRUCTURE_OPTIMIZATION.md` - 完整的优化方案

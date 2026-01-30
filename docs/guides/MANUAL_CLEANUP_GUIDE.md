# 手动清理指南

## ⚠️ 当前状态

由于文件被占用（可能被IDE或其他程序打开），自动脚本无法执行删除/移动操作。

## 📋 需要手动完成的操作

### 步骤1：关闭所有打开的文件

**重要**：在执行清理前，请：
1. 关闭所有IDE和编辑器
2. 关闭可能占用文件的程序
3. 确保没有Python进程在运行

### 步骤2：清理重复模块文件（19个）

这些文件在根目录和 `modules/` 目录都存在，**删除根目录版本**：

**需要删除的文件**：
1. `config_optimizer.py`
2. `content_metrics.py`
3. `content_scorer.py`
4. `data_storage.py`
5. `eeat_enhancer.py`
6. `fact_density_enhancer.py`
7. `keyword_mining.py`
8. `keyword_tool.py`
9. `multimodal_prompt.py`
10. `negative_monitor.py`
11. `optimization_techniques.py`
12. `resource_recommender.py`
13. `roi_analyzer.py`
14. `schema_generator.py`
15. `semantic_expander.py`
16. `storage_example.py`
17. `technical_config_generator.py`
18. `topic_cluster.py`
19. `workflow_automation.py`

**验证**：删除前确认 `modules/` 目录中有对应文件

### 步骤3：整理优化相关文件（可选）

**移动到 `docs/guides/` 的文档**：
- `ADVANCED_OPTIMIZATION_PLAN.md`
- `FINAL_OPTIMIZATION_GUIDE.md`
- `REFERENCE_UPDATE_SUMMARY.md`
- `OPTIMIZATION_STATUS.md`

**移动到 `scripts/` 的脚本**：
- `cleanup_duplicate_modules.py`
- `move_scripts.py`
- `update_script_references.py`
- `cleanup_optimization_files.py`

## 🚀 快速执行（PowerShell）

### 方法1：使用脚本（推荐）

关闭所有文件后，运行：

```powershell
# 清理重复模块
python cleanup_duplicate_modules.py
# 输入 yes

# 整理优化文件
python cleanup_optimization_files.py
```

### 方法2：手动删除/移动

```powershell
# 删除重复模块文件
$modules = @(
    "config_optimizer.py", "content_metrics.py", "content_scorer.py",
    "data_storage.py", "eeat_enhancer.py", "fact_density_enhancer.py",
    "keyword_mining.py", "keyword_tool.py", "multimodal_prompt.py",
    "negative_monitor.py", "optimization_techniques.py", "resource_recommender.py",
    "roi_analyzer.py", "schema_generator.py", "semantic_expander.py",
    "storage_example.py", "technical_config_generator.py", "topic_cluster.py",
    "workflow_automation.py"
)

foreach ($file in $modules) {
    if (Test-Path $file) {
        Remove-Item $file -Force
        Write-Host "✓ 已删除: $file"
    }
}

# 移动优化文档
$docs = @(
    "ADVANCED_OPTIMIZATION_PLAN.md",
    "FINAL_OPTIMIZATION_GUIDE.md",
    "REFERENCE_UPDATE_SUMMARY.md",
    "OPTIMIZATION_STATUS.md"
)

foreach ($doc in $docs) {
    if (Test-Path $doc) {
        Move-Item $doc -Destination "docs\guides\" -Force
        Write-Host "✓ 已移动: $doc"
    }
}

# 移动优化脚本
$scripts = @(
    "cleanup_duplicate_modules.py",
    "move_scripts.py",
    "update_script_references.py",
    "cleanup_optimization_files.py"
)

foreach ($script in $scripts) {
    if (Test-Path $script) {
        Move-Item $script -Destination "scripts\" -Force
        Write-Host "✓ 已移动: $script"
    }
}
```

## ✅ 验证清单

清理完成后，请验证：

- [ ] 根目录只有5个核心文件：
  - README.md
  - DOCS.md
  - geo_tool.py
  - requirements.txt
  - .gitignore
- [ ] 所有模块文件在 `modules/` 目录中
- [ ] 所有工具脚本在 `scripts/` 目录中
- [ ] 所有文档在 `docs/` 子目录中
- [ ] 测试导入：`python -c "from modules.data_storage import DataStorage"`
- [ ] 测试主程序：`streamlit run geo_tool.py`

## 🎯 优化后的最终结构

```
geo_tool/
├── README.md                    # ✅ 项目主文档
├── DOCS.md                      # ✅ 文档索引
├── geo_tool.py                  # ✅ 主程序
├── requirements.txt             # ✅ 依赖文件
├── .gitignore                   # ✅ Git配置
│
├── modules/                     # ✅ 功能模块（19个文件）
├── platform_sync/               # ✅ 平台同步模块
├── scripts/                     # ✅ 工具脚本（9个文件）
└── docs/                        # ✅ 文档目录
    ├── features/                # 功能文档（15个）
    ├── analysis/                 # 分析报告（7个）
    ├── guides/                  # 指南文档（13个）
    └── implementation/           # 实现文档（7个）
```

## 📊 优化效果

- **根目录文件**：从 50+ 个减少到 5 个（减少 90%）
- **文档分类**：34个文档按类型分类存放
- **模块组织**：19个模块集中在 `modules/` 目录
- **脚本整理**：9个工具脚本集中在 `scripts/` 目录

## 🆘 遇到问题？

### 问题1：文件仍被占用
**解决方案**：
1. 检查是否有Python进程：`tasklist | findstr python`
2. 关闭所有IDE和编辑器
3. 重启计算机后再试

### 问题2：删除后程序无法运行
**解决方案**：
1. 从Git恢复：`git checkout HEAD -- filename.py`
2. 检查 `modules/` 目录：确认文件存在
3. 检查导入路径：确认使用 `modules.xxx` 格式

### 问题3：不确定是否安全删除
**解决方案**：
1. 先备份：`git add . && git commit -m "备份：清理前"`
2. 再删除：如有问题可回滚
3. 验证：删除后立即测试程序

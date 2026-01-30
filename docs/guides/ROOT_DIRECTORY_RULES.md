# 根目录文件管理规则

## 📋 根目录文件规范

### ✅ 允许在根目录的文件

**核心文件（必须保留）**：
1. `README.md` - 项目主文档
2. `DOCS.md` - 文档索引
3. `geo_tool.py` - 主程序
4. `requirements.txt` - 依赖文件
5. `.gitignore` - Git配置
6. `.streamlit/` - Streamlit配置目录

### ❌ 禁止在根目录创建的文件

1. **文档文件（.md）**
   - ❌ 禁止在根目录创建任何新的 `.md` 文档
   - ✅ 所有文档应放在 `docs/` 的相应子目录中

2. **功能模块文件（.py）**
   - ❌ 禁止在根目录创建功能模块文件
   - ✅ 所有功能模块应放在 `modules/` 目录

3. **工具脚本文件（.py）**
   - ❌ 禁止在根目录创建工具脚本
   - ✅ 所有工具脚本应放在 `scripts/` 目录

## 📁 文件位置规则

### 文档文件

| 文档类型 | 位置 | 示例 |
|---------|------|------|
| 功能文档 | `docs/features/` | `docs/features/CONFIG_OPTIMIZER_FEATURE.md` |
| 分析报告 | `docs/analysis/` | `docs/analysis/FEATURE_ANALYSIS.md` |
| 使用指南 | `docs/guides/` | `docs/guides/QUICK_START_GUIDE.md` |
| 实现文档 | `docs/implementation/` | `docs/implementation/IMPLEMENTATION_SUMMARY.md` |

### Python 文件

| 文件类型 | 位置 | 示例 |
|---------|------|------|
| 功能模块 | `modules/` | `modules/data_storage.py` |
| 工具脚本 | `scripts/` | `scripts/update_imports.py` |
| 主程序 | 根目录 | `geo_tool.py` |
| 平台同步 | `platform_sync/` | `platform_sync/github_publisher.py` |

## 🎯 创建新文件时的检查

创建新文件前，请确认：

1. **如果是文档文件**：
   - [ ] 是否放在了正确的 `docs/` 子目录？
   - [ ] 是否更新了 `DOCS.md` 的索引？

2. **如果是功能模块**：
   - [ ] 是否放在了 `modules/` 目录？
   - [ ] 是否更新了导入路径？

3. **如果是工具脚本**：
   - [ ] 是否放在了 `scripts/` 目录？

## 📝 当前需要清理的根目录文件

以下文件应删除或移动到合适位置：

### 需要删除的重复文档（docs/guides/中已有）：
- `ADVANCED_OPTIMIZATION_PLAN.md`
- `FINAL_OPTIMIZATION_GUIDE.md`
- `REFERENCE_UPDATE_SUMMARY.md`
- `OPTIMIZATION_STATUS.md`

### 需要移动的文档：
- `MANUAL_CLEANUP_GUIDE.md` → `docs/guides/`

## 🚀 快速清理命令

```powershell
# 删除重复文档
Remove-Item ADVANCED_OPTIMIZATION_PLAN.md -Force
Remove-Item FINAL_OPTIMIZATION_GUIDE.md -Force
Remove-Item REFERENCE_UPDATE_SUMMARY.md -Force
Remove-Item OPTIMIZATION_STATUS.md -Force

# 移动文档
Move-Item MANUAL_CLEANUP_GUIDE.md -Destination "docs\guides\" -Force
```

## ✅ 清理后的根目录

清理完成后，根目录应该只有：
- `README.md`
- `DOCS.md`
- `geo_tool.py`
- `requirements.txt`
- `.gitignore`
- `.streamlit/` (目录)

**总计：5个核心文件 + 1个配置目录**

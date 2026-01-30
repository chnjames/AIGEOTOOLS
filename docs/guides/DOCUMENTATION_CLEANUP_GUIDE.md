# 文档清理指南

## 📋 根目录文档保留策略

### ✅ 必须保留在根目录的文档

1. **README.md** - 项目主文档（GitHub/GitLab 标准要求）
2. **DOCS.md** - 文档索引（方便快速查找所有文档）

### 📌 重组相关文档（建议移动到 docs/guides/）

以下重组相关的文档建议移动到 `docs/guides/` 目录：

- `PROJECT_STRUCTURE_ANALYSIS.md` - 项目结构分析
- `QUICK_REORGANIZE.md` - 快速重组指南
- `REORGANIZATION_SUMMARY.md` - 重组总结
- `DOCUMENTATION_CLEANUP_GUIDE.md` - 文档清理指南

**建议**：这些文档可以移动到 `docs/guides/` 目录，保持根目录整洁。使用 `scripts/move_reorganization_docs.py` 脚本可以自动移动。

### ❌ 需要删除的文档（已在 docs/ 目录下）

所有以下文档在根目录的重复版本都应该删除，因为已经在 `docs/` 目录下分类存放：

#### 功能文档（15个）
- `*_FEATURE.md` 文件（已在 `docs/features/`）

#### 分析报告（7个）
- `*_ANALYSIS.md` 和 `*_REPORT.md` 文件（已在 `docs/analysis/`）

#### 指南文档（5个）
- `*_GUIDE.md` 文件（已在 `docs/guides/`）

#### 实现文档（7个）
- 实现相关文档（已在 `docs/implementation/`）

## 🚀 执行清理

### 方法1：使用自动清理脚本（推荐）

```powershell
python scripts/cleanup_duplicate_docs.py
```

这个脚本会：
- 自动检查根目录中的重复文档
- 确认 `docs/` 目录下存在对应文件
- 安全删除根目录的重复版本
- 保留必要的文档（README.md, DOCS.md 等）

### 方法2：手动清理

如果脚本执行失败（文件被占用），可以：

1. **关闭所有打开的文件**（IDE、编辑器等）
2. **手动删除**根目录中的重复文档文件
3. **验证** `docs/` 目录下存在对应文件

## 📁 清理后的根目录结构

```
geo_tool/
├── README.md                    # ✅ 保留
├── DOCS.md                      # ✅ 保留（文档索引）
│
├── geo_tool.py                  # 主程序
├── requirements.txt             # 依赖文件
├── .gitignore                   # Git配置
│
├── modules/                     # 功能模块
├── platform_sync/               # 平台同步
└── docs/                        # 所有文档（分类存放）
    ├── features/
    ├── analysis/
    ├── guides/                  # 包含重组相关文档
    └── implementation/
```

## ✅ 清理验证清单

清理完成后，请验证：

- [ ] `README.md` 仍在根目录
- [ ] `DOCS.md` 已在根目录创建
- [ ] 根目录不再有 `*_FEATURE.md` 文件
- [ ] 根目录不再有 `*_ANALYSIS.md` 文件
- [ ] 根目录不再有 `*_GUIDE.md` 文件（除了可选保留的）
- [ ] 所有文档在 `docs/` 目录下可以找到
- [ ] `DOCS.md` 中的链接都能正常访问

## 💡 最佳实践

1. **README.md** 应该简洁，包含：
   - 项目简介
   - 快速开始
   - 主要功能概览
   - 链接到 DOCS.md 获取详细文档

2. **DOCS.md** 作为文档索引，提供：
   - 所有文档的分类导航
   - 快速查找功能
   - 清晰的文档结构说明

3. **详细文档** 放在 `docs/` 目录下分类管理，保持根目录整洁

## 🆘 遇到问题？

### 问题1：文件被占用无法删除
**解决方案**：
1. 关闭所有IDE和编辑器
2. 检查是否有Python进程在运行
3. 如果仍有问题，重启计算机后再试

### 问题2：误删了重要文档
**解决方案**：
1. 检查 `docs/` 目录下是否有对应文件
2. 如果有，说明只是删除了重复版本
3. 如果没有，可以从Git历史恢复

### 问题3：文档链接失效
**解决方案**：
1. 运行 `python scripts/update_doc_references.py` 更新文档引用
2. 检查 `DOCS.md` 中的链接是否正确
3. 使用相对路径而不是绝对路径

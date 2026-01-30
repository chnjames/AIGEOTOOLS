# 平台同步功能测试指南

## ✅ 已实现功能

### 1. GitHub发布功能
- ✅ 数据库扩展（platform_accounts、publish_records表）
- ✅ GitHub发布器（platform_sync/github_publisher.py）
- ✅ DataStorage扩展（平台账号和发布记录管理）
- ✅ UI界面（Tab 9：平台同步）

## 🚀 快速测试

### 步骤1：安装依赖

```bash
pip install httpx pyperclip
```

或安装所有依赖：

```bash
pip install -r requirements.txt
```

### 步骤2：获取GitHub Token

1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token" -> "Generate new token (classic)"
3. 填写Token名称（如：GEO Tool）
4. 选择权限：勾选 `repo`（完整仓库访问权限）
5. 点击 "Generate token"
6. **重要**：复制Token（只显示一次）

### 步骤3：运行应用

```bash
streamlit run geo_tool.py
```

### 步骤4：配置GitHub账号

1. 在侧边栏设置品牌信息
2. 进入 **Tab 9：平台同步**
3. 在 "GitHub 配置" 中填写：
   - GitHub Personal Access Token
   - 仓库所有者（用户名）
   - 仓库名称
4. 点击 "💾 保存配置"

### 步骤5：发布文章

1. 在 **Tab 2：自动创作** 中生成一篇文章（选择GitHub平台）
2. 进入 **Tab 9：平台同步**
3. 选择要发布的文章
4. 选择平台：GitHub
5. （可选）修改文件路径
6. 点击 "🚀 发布到GitHub"
7. 等待发布完成，查看结果

### 步骤6：查看发布记录

在 **Tab 9：平台同步** 的 "发布记录" 部分查看：
- 总发布数
- 成功/失败统计
- 最近发布记录列表

## 🔍 验证发布成功

1. 访问GitHub仓库
2. 检查 `content/` 目录（或你指定的路径）
3. 确认文件已创建或更新
4. 点击文件查看内容是否正确

## ⚠️ 常见问题

### 1. Token验证失败
- 检查Token是否正确复制
- 确认Token有 `repo` 权限
- 检查Token是否过期

### 2. 发布失败：404 Not Found
- 检查仓库所有者名称是否正确
- 检查仓库名称是否正确
- 确认仓库存在且有访问权限

### 3. 发布失败：403 Forbidden
- 检查Token权限是否足够
- 确认Token未过期
- 检查仓库是否为私有（需要相应权限）

### 4. 文件路径错误
- 路径不能以 `/` 开头
- 路径中不能包含特殊字符
- 建议使用 `content/文件名.md` 格式

## 📝 下一步

如果GitHub发布功能正常工作，可以：

1. **扩展其他平台**：
   - 微信公众号
   - B站
   - 知乎
   - CSDN

2. **添加一键复制功能**：
   - 头条号
   - 小红书
   - 抖音
   - 其他无API平台

3. **批量发布功能**：
   - 支持一次发布到多个平台
   - 发布队列管理
   - 定时发布

## 🎉 完成！

如果测试成功，说明架构是正确的，可以按照相同模式实现其他平台。

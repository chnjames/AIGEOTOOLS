# 平台扩展安装说明

## 已支持的平台

### 基础平台（已包含依赖）
- DeepSeek
- OpenAI (GPT)
- Tongyi (通义千问)
- Groq
- Moonshot (Kimi)

### 新增平台（需要额外安装）

#### 1. 豆包（字节跳动）

**安装命令：**
```bash
pip install 'volcengine-python-sdk[ark]'
```

**API Key 格式：**
```
access_key:secret_key:endpoint_id
```
用冒号分隔三个值：
- `access_key`: 火山引擎 Access Key
- `secret_key`: 火山引擎 Secret Key
- `endpoint_id`: 接入点名称（Endpoint ID）

**获取方式：**
1. 访问 [火山引擎官网](https://www.volcengine.com/)
2. 注册账号并完成实名认证
3. 在控制台获取 Access Key 和 Secret Key
4. 创建模型接入点，获取 Endpoint ID

**使用示例：**
在侧边栏"生成&优化 LLM"或"验证用LLM"中选择"豆包（字节跳动）"，输入格式化的 API Key。

---

#### 2. 文心一言（百度）

**安装命令：**
```bash
pip install qianfan
```

**API Key 格式：**
```
app_key:app_secret
```
用冒号分隔两个值：
- `app_key`: 百度智能云 App Key
- `app_secret`: 百度智能云 App Secret

**获取方式：**
1. 访问 [百度智能云千帆平台](https://cloud.baidu.com/product/qianfan.html)
2. 注册账号并完成认证
3. 创建应用，获取 App Key 和 App Secret

**使用示例：**
在侧边栏"生成&优化 LLM"或"验证用LLM"中选择"文心一言（百度）"，输入格式化的 API Key。

---

## 快速安装所有平台

如果需要使用所有平台，可以运行：

```bash
pip install 'volcengine-python-sdk[ark]' qianfan
```

---

## 注意事项

1. **API Key 格式**：豆包和文心一言的 API Key 需要使用冒号分隔多个值
2. **依赖冲突**：某些包可能有版本冲突，如遇到问题请单独安装
3. **可选安装**：这些平台是可选的，如果不使用可以不安装，不影响其他功能

---

## 故障排除

### 豆包安装失败
- 确保 Python 版本 >= 3.7
- Windows 系统可能需要启用长路径支持
- 尝试：`pip install 'volcengine-python-sdk[ark]' -U`

### 文心一言初始化失败
- 确保已安装 `qianfan` 包
- 检查 API Key 格式是否正确（app_key:app_secret）
- 确认环境变量或参数中的 AK/SK 是否正确

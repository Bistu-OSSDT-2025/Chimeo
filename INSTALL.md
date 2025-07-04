## 系统要求

- Python 3.7 或更高版本
- pip（Python 包管理器）

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/Bistu-OSSDT-2025/Chimeo
cd Chimeo
```

### 2. 创建虚拟环境（推荐）

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

创建 `.env` 文件并配置以下变量：

```env
# 邮件配置
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password

# OpenAI API 配置
OPENAI_API_KEY=your_openai_api_key
```

### 5. 初始化数据库

```bash
python app.py
```

数据库文件 `users.db` 会在首次运行时自动创建。

## 运行项目

```bash
python app.py
```

访问 http://localhost:5000 开始使用。

## 故障排除

### 常见问题

1. **依赖安装失败**
   - 确保使用 Python 3.7+
   - 尝试升级 pip: `pip install --upgrade pip`

2. **邮件发送失败**
   - 检查邮箱配置是否正确
   - 确保开启了 SMTP 访问权限
   - Gmail 用户需要使用应用专用密码

3. **OpenAI API 错误**
   - 检查 API 密钥是否正确
   - 确保账户有足够的余额

## 开发环境

### 启用调试模式

```bash
export FLASK_ENV=development
python app.py
``` 
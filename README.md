# 智能日程管理系统

一个基于 Flask 的智能日程管理 Web 应用，集成了任务拆分、日历导入导出、邮件提醒等功能。

## 主要功能

### 日程管理
- **创建和管理事件**：支持全天事件、重复事件、分类管理
- **编辑和删除**：灵活的事件编辑和删除功能

### AI 任务拆分
- **智能任务分解**：使用 OpenAI API 将复杂任务拆分为具体步骤
- **多语言支持**：支持中文和英文任务描述
- **步骤管理**：保存和管理拆分后的子任务

### 邮件提醒
- **自动提醒**：系统自动检查并发送邮件提醒
- **自定义提醒时间**：支持设置提醒时间
- **邮件通知**：重要事件自动发送邮件通知

### 数据导入导出
- **ICS 格式支持**：导入/导出标准日历格式
- **数据备份**：支持日历数据的备份和恢复
- **跨平台兼容**：与主流日历应用兼容

### 用户管理
- **用户注册登录**：简单的用户注册和登录系统
- **个人日历**：每个用户独立的日程管理
- **数据隔离**：用户数据安全隔离

## 技术栈

- **后端框架**：Flask 3.1.1
- **数据库**：SQLite
- **AI 集成**：OpenAI API
- **前端模板**：Jinja2
- **邮件服务**：SMTP
- **日历格式**：iCalendar (ICS)

## 系统要求

- Python 3.7+
- pip
- 网络连接（用于 AI 功能）

## 安装和运行

### 1. 克隆项目
```bash
git clone <你的仓库地址>
cd wq
```

### 2. 创建虚拟环境
```bash
python -m venv venv
```

### 3. 激活虚拟环境
**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 4. 安装依赖
```bash
cd main
pip install -r requirements.txt
```

### 5. 配置环境变量
创建 `.env` 文件并配置以下变量：
```env
OPENAI_BASE_URL=你的OpenAI API地址
OPENAI_API_KEY=你的OpenAI API密钥
OPENAI_MODEL_ID=deepseek32b
```

### 6. 初始化数据库
```bash
python app.py
```
首次运行会自动创建数据库表结构。

### 7. 启动应用
```bash
python app.py
```



## 使用指南

### 用户注册/登录
1. 访问应用首页
2. 输入用户名、邮箱和密码
3. 如果是新用户，系统会自动注册
4. 登录后进入个人日程管理界面

### 创建事件
1. 点击"创建事件"按钮
2. 填写事件标题、开始时间、结束时间
3. 选择是否为全天事件
4. 设置重复规则（可选）
5. 添加分类和备注（可选）
6. 保存事件

### 使用任务拆分
1. 进入"任务拆分"页面
2. 输入要拆分的任务描述
3. 选择语言（中文/英文）
4. 点击"拆分任务"
5. 查看 AI 生成的步骤
6. 保存步骤到日程中

### 导入/导出日历
1. **导出**：点击"导出 ICS"下载日历文件
2. **导入**：在导入页面选择 ICS 文件上传

## 配置说明

### 数据库配置
- 默认使用 SQLite 数据库 (`users.db`)
- 数据库文件位置：`main/users.db`

### 邮件配置
- 邮件发送功能在 `mail_sender.py` 中配置
- 支持 SMTP 邮件服务器

### AI 配置
- 支持自定义 OpenAI API 地址
- 可配置不同的 AI 模型
- 支持温度参数调整

## 项目结构

```
wq/
├── main/                    # 主应用目录
│   ├── app.py              # Flask 主应用
│   ├── requirements.txt    # Python 依赖
│   ├── templates/          # HTML 模板
│   │   ├── base.html       # 基础模板
│   │   ├── index.html      # 主页
│   │   ├── login.html      # 登录页面
│   │   ├── create_event.html    # 创建事件
│   │   ├── task_splitter.html   # 任务拆分
│   │   ├── import_ics.html      # 导入页面
│   │   └── text_input.html      # 文本输入
│   ├── users.db            # SQLite 数据库
│   └── venv/               # 虚拟环境
└── README.md               # 项目说明
```

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 常见问题

### Q: 如何修改端口号？
A: 在 `app.py` 中修改 `app.run()` 的 port 参数。

### Q: 如何备份数据？
A: 复制 `users.db` 文件即可备份所有用户数据。

### Q: AI 功能无法使用？
A: 检查 `.env` 文件中的 API 配置是否正确。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 Issue
- 发送邮件
- 创建 Pull Request

---

**注意**：首次使用需要配置 OpenAI API 密钥才能使用 AI 任务拆分功能。 

import smtplib
from email.mime.text import MIMEText
from email.header import Header

def send_email(subject, content, to_email):
    from_email = '1827764696@qq.com'  # ⚠️ 替换为你的QQ邮箱
    password = 'yiydllkqbndceefa'           # ⚠️ 替换为你开启SMTP服务后获得的授权码
    smtp_server = 'smtp.qq.com'
    smtp_port = 587

    message = MIMEText(content, 'plain', 'utf-8')
    message['From'] = Header(from_email)
    message['To'] = Header(to_email)
    message['Subject'] = Header(subject)

    try:
        print("开始连接SMTP服务器...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.set_debuglevel(1)  # 显示SMTP交互
        server.starttls()
        server.login(from_email, password)
        server.sendmail(from_email, [to_email], message.as_string())
        server.quit()
        print(f"✅ 成功发送邮件至 {to_email}")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")

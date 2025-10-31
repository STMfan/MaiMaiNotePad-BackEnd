/**
 * 邮件模板模块
 * 提供各种邮件通知的HTML模板
 */

/**
 * 基础邮件模板
 */
const baseTemplate = (title, content) => `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            margin: 0;
            padding: 20px 0;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }
        .content {
            padding: 30px 20px;
        }
        .footer {
            background-color: #f8f9fa;
            padding: 20px;
            text-align: center;
            border-top: 1px solid #e9ecef;
        }
        .button {
            display: inline-block;
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            margin: 10px 5px;
            transition: all 0.3s ease;
        }
        .button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        .info-box {
            background-color: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }
        .success-box {
            background-color: #e8f5e8;
            border-left: 4px solid #4caf50;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }
        .warning-box {
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }
        .error-box {
            background-color: #f8d7da;
            border-left: 4px solid #dc3545;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }
        .code-box {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            font-size: 16px;
            text-align: center;
            letter-spacing: 2px;
            margin: 20px 0;
        }
        .social-links {
            margin: 20px 0;
        }
        .social-links a {
            display: inline-block;
            margin: 0 10px;
            color: #666;
            text-decoration: none;
            font-size: 14px;
        }
        .unsubscribe {
            color: #6c757d;
            font-size: 12px;
            margin-top: 15px;
        }
        .unsubscribe a {
            color: #6c757d;
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📝 MaiMaiNotePad</h1>
        </div>
        <div class="content">
            ${content}
        </div>
        <div class="footer">
            <p style="margin: 0 0 10px 0; color: #6c757d;">
                此邮件由 <strong>MaiMaiNotePad</strong> (maimnp.tech) 自动发送
            </p>
            <div class="social-links">
                <a href="https://maimnp.tech">🏠 官网</a>
                <a href="https://maimnp.tech/docs">📚 文档</a>
                <a href="mailto:official@maimnp.tech">📧 联系我们</a>
            </div>
            <div class="unsubscribe">
                <p>如果您不希望收到此类邮件，请<a href="https://maimnp.tech/settings/notifications">点击这里取消订阅</a></p>
            </div>
        </div>
    </div>
</body>
</html>
`;

/**
 * 注册验证邮件模板
 */
export const registrationTemplate = (username, verificationCode) => {
    const content = `
        <h2>👋 欢迎加入 MaiMaiNotePad！</h2>
        <p>亲爱的 <strong>${username}</strong>，</p>
        <p>感谢您注册我们的服务！为了确保账户安全，请使用以下验证码完成邮箱验证：</p>
        
        <div class="code-box">
            <strong>${verificationCode}</strong>
        </div>
        
        <div class="info-box">
            <strong>⏰ 验证码有效期：</strong>15分钟<br>
            <strong>💡 安全提示：</strong>请勿将此验证码告知他人
        </div>
        
        <p>如果这不是您的操作，请忽略此邮件。</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://maimnp.tech/verify-email?code=${verificationCode}" class="button">
                🔐 验证邮箱地址
            </a>
        </div>
        
        <p>如果您在验证过程中遇到任何问题，请随时联系我们的客服团队。</p>
        
        <p>期待与您一起创造美好的笔记体验！</p>
    `;
    
    return baseTemplate('邮箱验证 - MaiMaiNotePad', content);
};

/**
 * 密码重置邮件模板
 */
export const passwordResetTemplate = (username, resetToken) => {
    const resetUrl = `https://maimnp.tech/reset-password?token=${resetToken}`;
    
    const content = `
        <h2>🔑 密码重置请求</h2>
        <p>亲爱的 <strong>${username}</strong>，</p>
        <p>我们收到了您的密码重置请求。为了保护您的账户安全，请点击下方链接重置密码：</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="${resetUrl}" class="button">
                🔄 重置密码
            </a>
        </div>
        
        <p>或者复制以下链接到浏览器地址栏：</p>
        <div class="code-box" style="font-size: 12px; word-break: break-all;">
            ${resetUrl}
        </div>
        
        <div class="warning-box">
            <strong>⚠️ 重要提醒：</strong>
            <ul style="margin: 10px 0;">
                <li>此链接将在 <strong>1小时</strong> 后过期</li>
                <li>为了安全起见，请勿将此链接分享给他人</li>
                <li>如果您没有发起此请求，请立即忽略此邮件</li>
            </ul>
        </div>
        
        <p>重置密码后，建议您：</p>
        <ul>
            <li>使用包含大小写字母、数字和特殊字符的强密码</li>
            <li>不要在多个网站使用相同的密码</li>
            <li>定期更新您的密码</li>
        </ul>
    `;
    
    return baseTemplate('密码重置 - MaiMaiNotePad', content);
};

/**
 * 人设卡审核通过邮件模板
 */
export const characterApprovedTemplate = (username, characterName, characterUrl) => {
    const content = `
        <h2>🎉 恭喜！您的人设卡已通过审核</h2>
        <p>亲爱的 <strong>${username}</strong>，</p>
        <p>很高兴地通知您，您上传的人设卡已经通过我们的审核！</p>
        
        <div class="success-box">
            <h4 style="margin-top: 0;">✅ 审核通过的人设卡：</h4>
            <p style="margin: 0;"><strong>${characterName}</strong></p>
        </div>
        
        <p>您的人设卡现已公开可见，其他用户可以查看和使用。这是您创作旅程中的重要一步！</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="${characterUrl}" class="button">
                👀 查看我的人设卡
            </a>
        </div>
        
        <div class="info-box">
            <strong>💡 温馨提示：</strong>
            <ul style="margin: 10px 0;">
                <li>您可以随时编辑和更新您的人设卡</li>
                <li>建议定期检查和维护您的创作内容</li>
                <li>如有任何问题，欢迎随时联系我们</li>
            </ul>
        </div>
        
        <p>感谢您的创作和分享，期待看到更多您的精彩作品！</p>
    `;
    
    return baseTemplate('人设卡审核通过 - MaiMaiNotePad', content);
};

/**
 * 人设卡审核不通过邮件模板
 */
export const characterRejectedTemplate = (username, characterName, reason) => {
    const content = `
        <h2>😔 人设卡审核结果通知</h2>
        <p>亲爱的 <strong>${username}</strong>，</p>
        <p>很遗憾地通知您，您上传的人设卡未能通过我们的审核。</p>
        
        <div class="error-box">
            <h4 style="margin-top: 0;">❌ 未通过审核的人设卡：</h4>
            <p style="margin: 0 0 10px 0;"><strong>${characterName}</strong></p>
            <h4 style="margin: 15px 0 5px 0;">审核意见：</h4>
            <p style="margin: 0;">${reason}</p>
        </div>
        
        <p>我们理解这可能让您感到失望，但请根据审核意见进行修改后重新上传。我们的审核标准旨在维护平台内容质量和用户体验。</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://maimnp.tech/upload-character" class="button">
                🔄 重新上传人设卡
            </a>
        </div>
        
        <div class="info-box">
            <strong>💡 常见修改建议：</strong>
            <ul style="margin: 10px 0;">
                <li>确保内容符合社区准则和使用条款</li>
                <li>检查是否有版权问题或不当内容</li>
                <li>完善人设卡的描述和标签信息</li>
                <li>确保图片质量和格式符合要求</li>
            </ul>
        </div>
        
        <p>如果您对审核结果有疑问，或需要帮助改进您的人设卡，请随时联系我们的客服团队。我们很乐意为您提供指导和建议。</p>
        
        <p>请不要气馁，期待看到您改进后的作品！</p>
    `;
    
    return baseTemplate('人设卡审核未通过 - MaiMaiNotePad', content);
};

/**
 * 系统通知邮件模板
 */
export const systemNotificationTemplate = (username, title, message, actionUrl = null, actionText = null) => {
    const content = `
        <h2>📢 系统通知</h2>
        <p>亲爱的 <strong>${username}</strong>，</p>
        <div class="info-box">
            <h4 style="margin-top: 0;">${title}</h4>
            <p style="margin: 0;">${message}</p>
        </div>
        
        ${actionUrl ? `
            <div style="text-align: center; margin: 30px 0;">
                <a href="${actionUrl}" class="button">
                    ${actionText || '查看详情'}
                </a>
            </div>
        ` : ''}
        
        <p>如果您对此通知有任何疑问，请随时联系我们的客服团队。</p>
    `;
    
    return baseTemplate(`系统通知 - ${title}`, content);
};

/**
 * 安全警告邮件模板
 */
export const securityAlertTemplate = (username, alertType, details) => {
    const content = `
        <h2>🚨 安全警告</h2>
        <p>亲爱的 <strong>${username}</strong>，</p>
        <p>我们检测到您的账户存在异常活动，为了保护您的账户安全，请及时关注以下信息：</p>
        
        <div class="error-box">
            <h4 style="margin-top: 0;">⚠️ ${alertType}</h4>
            <p style="margin: 0;">${details}</p>
        </div>
        
        <div class="warning-box">
            <strong>🔒 安全建议：</strong>
            <ul style="margin: 10px 0;">
                <li>立即更改您的密码</li>
                <li>检查最近的登录活动</li>
                <li>启用两步验证（如果尚未启用）</li>
                <li>检查账户设置和授权应用</li>
            </ul>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://maimnp.tech/security" class="button">
                🔐 检查账户安全
            </a>
        </div>
        
        <p>如果您没有进行相关操作，或认为账户可能已被盗用，请立即联系我们的客服团队。</p>
        
        <p><strong>紧急联系方式：</strong></p>
        <ul>
            <li>邮箱：<a href="mailto:security@maimnp.tech">security@maimnp.tech</a></li>
            <li>官网：<a href="https://maimnp.tech/support">https://maimnp.tech/support</a></li>
        </ul>
    `;
    
    return baseTemplate('安全警告 - MaiMaiNotePad', content);
};

// 导出所有模板
export default {
    baseTemplate,
    registrationTemplate,
    passwordResetTemplate,
    characterApprovedTemplate,
    characterRejectedTemplate,
    systemNotificationTemplate,
    securityAlertTemplate
};
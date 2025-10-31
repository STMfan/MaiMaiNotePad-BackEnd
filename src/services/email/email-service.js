/**
 * 邮件服务模块
 * 提供邮件发送功能，支持多种邮件模板
 */

export class EmailService {
    constructor(config = {}) {
        this.config = config;
        this.enabled = config.EMAIL_ENABLED || false;
        this.from = config.EMAIL_FROM || 'official@maimnp.tech';
        this.provider = config.EMAIL_PROVIDER || 'smtp';
        
        if (this.enabled) {
            this.initializeTransport();
        }
    }

    /**
     * 初始化邮件传输器
     */
    initializeTransport() {
        try {
            if (this.provider === 'sendgrid') {
                // SendGrid 配置
                this.transport = {
                    type: 'sendgrid',
                    apiKey: config.SENDGRID_API_KEY
                };
            } else {
                // SMTP 配置
                this.transport = {
                    type: 'smtp',
                    host: config.SMTP_HOST || 'smtp.gmail.com',
                    port: config.SMTP_PORT || 587,
                    secure: config.SMTP_SECURE || false,
                    auth: {
                        user: config.SMTP_USER,
                        pass: config.SMTP_PASS
                    }
                };
            }
        } catch (error) {
            console.error('邮件服务初始化失败:', error);
            this.enabled = false;
        }
    }

    /**
     * 发送邮件
     * @param {Object} options - 邮件选项
     * @param {string} options.to - 收件人
     * @param {string} options.subject - 主题
     * @param {string} options.html - HTML内容
     * @param {string} options.text - 纯文本内容
     */
    async sendEmail(options) {
        if (!this.enabled) {
            console.warn('邮件服务未启用');
            return { success: false, message: '邮件服务未启用' };
        }

        try {
            const emailData = {
                from: this.from,
                to: options.to,
                subject: options.subject,
                html: options.html,
                text: options.text
            };

            if (this.provider === 'sendgrid') {
                return await this.sendViaSendGrid(emailData);
            } else {
                return await this.sendViaSMTP(emailData);
            }
        } catch (error) {
            console.error('发送邮件失败:', error);
            return { success: false, message: error.message };
        }
    }

    /**
     * 通过SendGrid发送邮件
     */
    async sendViaSendGrid(emailData) {
        // 这里实现SendGrid API调用
        // 由于Cloudflare Workers环境限制，需要使用fetch API
        const response = await fetch('https://api.sendgrid.com/v3/mail/send', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.transport.apiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                personalizations: [{
                    to: [{ email: emailData.to }]
                }],
                from: { email: emailData.from },
                subject: emailData.subject,
                content: [
                    {
                        type: 'text/html',
                        value: emailData.html
                    }
                ]
            })
        });

        if (response.ok) {
            return { success: true, message: '邮件发送成功' };
        } else {
            const error = await response.text();
            throw new Error(`SendGrid API错误: ${error}`);
        }
    }

    /**
     * 通过SMTP发送邮件
     */
    async sendViaSMTP(emailData) {
        // 在Cloudflare Workers环境中，我们需要使用第三方服务或Web API
        // 这里提供一个模拟实现
        console.log('SMTP邮件发送模拟:', emailData);
        return { success: true, message: 'SMTP邮件发送成功（模拟）' };
    }

    /**
     * 发送注册验证邮件
     */
    async sendRegistrationEmail(to, verificationCode) {
        const subject = '欢迎注册 MaiMaiNotePad - 邮箱验证';
        const html = `
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #333;">欢迎注册 MaiMaiNotePad！</h2>
                <p>感谢您注册我们的服务。请使用以下验证码完成邮箱验证：</p>
                <div style="background-color: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0;">
                    <h3 style="color: #007bff; margin: 0;">${verificationCode}</h3>
                </div>
                <p>验证码将在 15 分钟后过期。如果这不是您的操作，请忽略此邮件。</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    此邮件由 MaiMaiNotePad (maimnp.tech) 自动发送，请勿回复。
                </p>
            </div>
        `;
        
        return await this.sendEmail({ to, subject, html });
    }

    /**
     * 发送密码重置邮件
     */
    async sendPasswordResetEmail(to, resetToken) {
        const subject = 'MaiMaiNotePad - 密码重置请求';
        const resetUrl = `https://maimnp.tech/reset-password?token=${resetToken}`;
        const html = `
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #333;">密码重置请求</h2>
                <p>我们收到了您的密码重置请求。请点击下方链接重置密码：</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="${resetUrl}" 
                       style="background-color: #007bff; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 4px; display: inline-block;">
                        重置密码
                    </a>
                </div>
                <p>或者复制以下链接到浏览器地址栏：</p>
                <p style="word-break: break-all; color: #007bff;">${resetUrl}</p>
                <p>此链接将在 1 小时后过期。如果这不是您的操作，请忽略此邮件。</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    此邮件由 MaiMaiNotePad (maimnp.tech) 自动发送，请勿回复。
                </p>
            </div>
        `;
        
        return await this.sendEmail({ to, subject, html });
    }

    /**
     * 发送人设卡审核通过邮件
     */
    async sendCharacterApprovedEmail(to, characterName) {
        const subject = 'MaiMaiNotePad - 人设卡审核通过';
        const html = `
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #28a745;">🎉 恭喜！您的人设卡已通过审核</h2>
                <p>您上传的人设卡 <strong>${characterName}</strong> 已经通过审核，现在可以在平台上使用了。</p>
                <div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0; color: #155724;">您的人设卡现已公开可见，其他用户可以查看和使用。</p>
                </div>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="https://maimnp.tech/characters" 
                       style="background-color: #28a745; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 4px; display: inline-block;">
                        查看我的人设卡
                    </a>
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    此邮件由 MaiMaiNotePad (maimnp.tech) 自动发送，请勿回复。
                </p>
            </div>
        `;
        
        return await this.sendEmail({ to, subject, html });
    }

    /**
     * 发送人设卡审核不通过邮件
     */
    async sendCharacterRejectedEmail(to, characterName, reason) {
        const subject = 'MaiMaiNotePad - 人设卡审核未通过';
        const html = `
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #dc3545;">😔 人设卡审核未通过</h2>
                <p>很遗憾地通知您，您上传的人设卡 <strong>${characterName}</strong> 未能通过审核。</p>
                
                <div style="background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; padding: 15px; margin: 20px 0;">
                    <h4 style="margin-top: 0; color: #721c24;">审核意见：</h4>
                    <p style="margin: 0; color: #721c24;">${reason}</p>
                </div>
                
                <p>请根据审核意见修改后重新上传。如有疑问，请联系我们的客服团队。</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://maimnp.tech/upload-character" 
                       style="background-color: #007bff; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 4px; display: inline-block;">
                        重新上传人设卡
                    </a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    此邮件由 MaiMaiNotePad (maimnp.tech) 自动发送，请勿回复。
                </p>
            </div>
        `;
        
        return await this.sendEmail({ to, subject, html });
    }

    /**
     * 发送系统通知邮件
     */
    async sendSystemNotification(to, title, message) {
        const subject = `MaiMaiNotePad - ${title}`;
        const html = `
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #333;">${title}</h2>
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 4px; margin: 20px 0;">
                    <p>${message}</p>
                </div>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    此邮件由 MaiMaiNotePad (maimnp.tech) 自动发送，请勿回复。
                </p>
            </div>
        `;
        
        return await this.sendEmail({ to, subject, html });
    }
}

export default EmailService;
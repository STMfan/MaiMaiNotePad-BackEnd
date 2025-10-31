/**
 * 邮件服务模块
 * 提供统一的邮件发送接口和模板功能
 */

import EmailService from './email-service.js';
import emailTemplates from './email-templates.js';

// 导出邮件服务和模板
export {
    EmailService,
    emailTemplates
};

// 默认导出邮件服务类
export default EmailService;
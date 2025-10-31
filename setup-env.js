#!/usr/bin/env node

const fs = require('fs').promises;
const path = require('path');
const readline = require('readline');

// 创建读取接口
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

// 询问函数
function askQuestion(question) {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      resolve(answer.trim());
    });
  });
}

// 主要配置向导
async function setupEnvironment() {
  console.log('🚀 MaiMaiNotePad 环境配置向导');
  console.log('=' .repeat(50));
  console.log('这个向导将帮助您配置项目所需的环境变量。\n');

  const config = {
    NODE_ENV: 'development',
    PORT: '8787',
    JWT_SECRET: generateRandomString(32),
    JWT_EXPIRES_IN: '7d',
    DB_TYPE: 'D1',
    CLOUDFLARE_ACCOUNT_ID: '',
    CLOUDFLARE_DATABASE_ID: '',
    CLOUDFLARE_API_TOKEN: '',
    EMAIL_SERVICE: 'resend',
    RESEND_API_KEY: '',
    RESEND_FROM_EMAIL: '',
    RESEND_FROM_NAME: 'MaiMaiNotePad',
    RATE_LIMIT_WINDOW_MS: '900000',
    RATE_LIMIT_MAX_REQUESTS: '100',
    LOG_LEVEL: 'info',
    CORS_ORIGIN: 'http://localhost:3000',
    MAX_FILE_SIZE_MB: '10',
    UPLOAD_DIR: './uploads',
    BACKUP_DIR: './backups',
    CACHE_TTL_SECONDS: '3600',
    REDIS_URL: '',
    REDIS_PASSWORD: '',
    REDIS_DB: '0'
  };

  try {
    // 基础配置
    console.log('\n📋 基础配置');
    console.log('-'.repeat(30));
    
    const nodeEnv = await askQuestion('运行环境 (development/production) [development]: ');
    if (nodeEnv) config.NODE_ENV = nodeEnv;

    const port = await askQuestion(`端口号 [${config.PORT}]: `);
    if (port) config.PORT = port;

    // JWT配置
    console.log('\n🔐 JWT配置');
    console.log('-'.repeat(30));
    console.log(`已生成JWT密钥: ${config.JWT_SECRET}`);
    
    const jwtExpires = await askQuestion(`JWT过期时间 [${config.JWT_EXPIRES_IN}]: `);
    if (jwtExpires) config.JWT_EXPIRES_IN = jwtExpires;

    // 数据库配置
    console.log('\n💾 数据库配置');
    console.log('-'.repeat(30));
    console.log('支持的数据库类型: D1 (Cloudflare D1), MONGODB');
    
    const dbType = await askQuestion(`数据库类型 [${config.DB_TYPE}]: `);
    if (dbType) config.DB_TYPE = dbType.toUpperCase();

    if (config.DB_TYPE === 'D1') {
      console.log('\n请从Cloudflare Dashboard获取以下信息:');
      console.log('1. 登录 https://dash.cloudflare.com');
      console.log('2. 选择您的账户');
      console.log('3. 进入 Workers & Pages > D1');
      console.log('4. 选择或创建数据库');
      console.log('5. 在设置页面找到 Account ID 和 Database ID');
      console.log('6. 创建 API Token (使用 Custom token，权限需要包括: Cloudflare D1:Edit)');
      console.log('');

      config.CLOUDFLARE_ACCOUNT_ID = await askQuestion('Cloudflare Account ID: ');
      config.CLOUDFLARE_DATABASE_ID = await askQuestion('Cloudflare Database ID: ');
      config.CLOUDFLARE_API_TOKEN = await askQuestion('Cloudflare API Token: ');
    }

    // 邮件服务配置
    console.log('\n📧 邮件服务配置');
    console.log('-'.repeat(30));
    console.log('支持邮件服务: resend, sendgrid, smtp');
    
    const emailService = await askQuestion(`邮件服务类型 [${config.EMAIL_SERVICE}]: `);
    if (emailService) config.EMAIL_SERVICE = emailService.toLowerCase();

    if (config.EMAIL_SERVICE === 'resend') {
      console.log('\n请从 https://resend.com 获取 API Key');
      config.RESEND_API_KEY = await askQuestion('Resend API Key: ');
      config.RESEND_FROM_EMAIL = await askQuestion('发件人邮箱: ');
      
      const fromName = await askQuestion(`发件人名称 [${config.RESEND_FROM_NAME}]: `);
      if (fromName) config.RESEND_FROM_NAME = fromName;
    }

    // 高级配置
    console.log('\n⚙️ 高级配置');
    console.log('-'.repeat(30));
    
    const corsOrigin = await askQuestion(`CORS允许的来源 [${config.CORS_ORIGIN}]: `);
    if (corsOrigin) config.CORS_ORIGIN = corsOrigin;

    const maxFileSize = await askQuestion(`最大文件大小(MB) [${config.MAX_FILE_SIZE_MB}]: `);
    if (maxFileSize) config.MAX_FILE_SIZE_MB = maxFileSize;

    const rateLimitWindow = await askQuestion(`速率限制时间窗口(毫秒) [${config.RATE_LIMIT_WINDOW_MS}]: `);
    if (rateLimitWindow) config.RATE_LIMIT_WINDOW_MS = rateLimitWindow;

    const rateLimitMax = await askQuestion(`速率限制最大请求数 [${config.RATE_LIMIT_MAX_REQUESTS}]: `);
    if (rateLimitMax) config.RATE_LIMIT_MAX_REQUESTS = rateLimitMax;

    // 生成 .env 文件内容
    const envContent = Object.entries(config)
      .map(([key, value]) => {
        if (value === '') {
          return `# ${key}=`;
        }
        return `${key}=${value}`;
      })
      .join('\n');

    // 添加注释
    const finalContent = `# MaiMaiNotePad 环境配置文件
# 生成时间: ${new Date().toISOString()}
# 
# 重要说明：
# 1. 请确保所有必填字段都已正确配置
# 2. 生产环境请使用强密码和密钥
# 3. 定期更新敏感信息
# 4. 不要将此文件提交到版本控制
#
# 配置说明：
# NODE_ENV: 运行环境 (development/production)
# JWT_SECRET: JWT签名密钥，请保持安全
# DB_TYPE: 数据库类型 (D1/MONGODB)
# EMAIL_SERVICE: 邮件服务类型 (resend/sendgrid/smtp)
# CORS_ORIGIN: 允许的跨域来源
# MAX_FILE_SIZE_MB: 最大文件上传大小
# RATE_LIMIT_*: 速率限制配置

${envContent}`;

    // 写入文件
    const envPath = path.join(process.cwd(), '.env');
    await fs.writeFile(envPath, finalContent);

    console.log('\n✅ 环境配置完成！');
    console.log('=' .repeat(50));
    console.log(`配置文件已保存到: ${envPath}`);
    console.log('\n下一步:');
    console.log('1. 检查 .env 文件中的配置是否正确');
    console.log('2. 运行数据库迁移: npm run db:generate');
    console.log('3. 启动开发服务器: npm run dev');
    console.log('\n如有问题，请查看 README.md 或联系技术支持。');

  } catch (error) {
    console.error('❌ 配置过程中出现错误:', error.message);
    process.exit(1);
  } finally {
    rl.close();
  }
}

// 生成随机字符串
function generateRandomString(length) {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

// 运行配置向导
if (require.main === module) {
  setupEnvironment().catch(console.error);
}

module.exports = { setupEnvironment };
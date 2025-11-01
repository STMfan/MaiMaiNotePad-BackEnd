#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('=== GitHub Secrets 配置助手 ===\n');

// 读取.env.local文件
const envPath = path.join(__dirname, '.env.local');
const envContent = fs.readFileSync(envPath, 'utf8');
const envLines = envContent.split('\n');

// 解析环境变量
const envVars = {};
envLines.forEach(line => {
  const trimmedLine = line.trim();
  if (trimmedLine && !trimmedLine.startsWith('#')) {
    const [key, ...valueParts] = trimmedLine.split('=');
    if (key && valueParts.length > 0) {
      envVars[key.trim()] = valueParts.join('=').trim();
    }
  }
});

// 必需的环境变量
const requiredVars = [
  'CLOUDFLARE_API_TOKEN',
  'CLOUDFLARE_ACCOUNT_ID',
  'JWT_SECRET'
];

console.log('📋 以下是在GitHub仓库中配置secrets的步骤:\n');

console.log('1. 访问您的GitHub仓库');
console.log('2. 进入 "Settings" > "Secrets and variables" > "Actions"');
console.log('3. 点击 "New repository secret" 添加以下secrets:\n');

requiredVars.forEach(varName => {
  const value = envVars[varName] || '';
  const isSet = value !== '';
  console.log(`${isSet ? '✅' : '❌'} ${varName}`);
  if (!isSet) {
    console.log(`   状态: 需要配置 (在.env.local中也未设置)`);
  } else {
    console.log(`   状态: 已在.env.local中设置，可以复制到GitHub`);
    console.log(`   值: ${value.substring(0, 10)}${value.length > 10 ? '...' : ''}`);
  }
  console.log('');
});

console.log('4. 对于其他可选的secrets，您也可以按照相同方式添加:\n');

// 列出其他已设置的可选变量
const optionalVars = [
  'JWT_EXPIRE',
  'ALLOWED_ORIGINS',
  'EMAIL_ENABLED',
  'EMAIL_PROVIDER',
  'EMAIL_FROM',
  'ANALYTICS_ENABLED',
  'ANALYTICS_PROVIDER',
  'BACKUP_ENABLED',
  'RATE_LIMIT_ENABLED',
  'CACHE_ENABLED',
  'CACHE_TTL',
  'R2_ACCESS_KEY_ID',
  'R2_SECRET_ACCESS_KEY',
  'R2_BUCKET_NAME',
  'R2_ENDPOINT',
  'D1_DATABASE_ID',
  'KV_NAMESPACE_ID'
];

optionalVars.forEach(varName => {
  const value = envVars[varName] || '';
  if (value !== '') {
    console.log(`✅ ${varName}: 已在.env.local中设置`);
  }
});

console.log('\n🔧 获取Cloudflare API Token的步骤:\n');
console.log('1. 登录Cloudflare仪表板');
console.log('2. 进入 "My Profile" > "API Tokens"');
console.log('3. 点击 "Create Token"');
console.log('4. 使用 "Custom token" 模板');
console.log('5. 配置权限:');
console.log('   - Account: Cloudflare Account:Read');
console.log('   - Zone: Zone:Read');
console.log('   - Zone Resources: Include All zones');
console.log('6. 复制生成的token作为CLOUDFLARE_API_TOKEN的值');

console.log('\n🔧 获取Cloudflare Account ID的步骤:\n');
console.log('1. 登录Cloudflare仪表板');
console.log('2. 在右侧边栏找到 "Account ID"');
console.log('3. 复制该ID作为CLOUDFLARE_ACCOUNT_ID的值');

console.log('\n⚠️ 注意事项:\n');
console.log('1. Fork仓库不会继承原仓库的secrets');
console.log('2. 确保工作流文件中的permissions配置正确');
console.log('3. 配置完成后，GitHub Actions会自动使用新的secrets');

console.log('\n=== 配置完成 ===');
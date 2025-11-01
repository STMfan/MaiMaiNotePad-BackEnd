#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('=== GitHub Secrets Configuration Checker ===\n');

// 检查.env.local文件是否存在
const envPath = path.join(__dirname, '.env.local');
if (!fs.existsSync(envPath)) {
  console.log('❌ .env.local 文件不存在');
  console.log('请复制 .env.example 为 .env.local 并填写您的配置\n');
  
  // 检查.env.example是否存在
  const examplePath = path.join(__dirname, '.env.example');
  if (fs.existsSync(examplePath)) {
    console.log('📄 找到 .env.example 文件，您可以基于它创建 .env.local');
    console.log('命令: cp .env.example .env.local\n');
  } else {
    console.log('❌ .env.example 文件也不存在');
  }
  process.exit(1);
}

// 读取.env.local文件
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

// 可选但推荐的环境变量
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

console.log('📋 检查必需的环境变量:\n');
let allRequiredSet = true;

requiredVars.forEach(varName => {
  const isSet = envVars[varName] && envVars[varName] !== '';
  console.log(`${isSet ? '✅' : '❌'} ${varName}: ${isSet ? '已设置' : '未设置'}`);
  if (!isSet) allRequiredSet = false;
});

console.log('\n📋 检查可选的环境变量:\n');

optionalVars.forEach(varName => {
  const isSet = envVars[varName] && envVars[varName] !== '';
  console.log(`${isSet ? '✅' : '⚠️'} ${varName}: ${isSet ? '已设置' : '未设置'}`);
});

console.log('\n📊 配置摘要:');
console.log(`必需变量: ${requiredVars.filter(v => envVars[v] && envVars[v] !== '').length}/${requiredVars.length}`);
console.log(`可选变量: ${optionalVars.filter(v => envVars[v] && envVars[v] !== '').length}/${optionalVars.length}`);

if (allRequiredSet) {
  console.log('\n✅ 所有必需的环境变量都已设置，可以继续部署');
  
  console.log('\n🔧 GitHub Secrets 配置建议:');
  console.log('1. 确保在GitHub仓库中添加了以下secrets:');
  requiredVars.forEach(varName => {
    console.log(`   - ${varName}`);
  });
  
  console.log('\n2. 检查GitHub Actions工作流日志中的"Debug environment variables"步骤');
  console.log('3. 确认secrets在GitHub Actions中正确加载');
} else {
  console.log('\n❌ 存在未设置的必需环境变量，请先完成配置');
  console.log('\n🔧 修复步骤:');
  console.log('1. 编辑 .env.local 文件');
  console.log('2. 添加缺失的必需环境变量');
  console.log('3. 重新运行此脚本验证');
}

console.log('\n=== 检查完成 ===');
#!/usr/bin/env node

/**
 * GitHub Actions 环境模拟测试
 * 模拟GitHub Actions中的secrets可用性检查
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

console.log('=== GitHub Actions 环境模拟测试 ===\n');

// 模拟GitHub Actions中的secrets检查逻辑
function simulateGitHubActionsCheck() {
  console.log('🔍 模拟GitHub Actions中的secrets检查...\n');
  
  // 模拟从环境变量获取secrets（GitHub Actions中的行为）
  const secrets = {
    CLOUDFLARE_API_TOKEN: process.env.CLOUDFLARE_API_TOKEN || '',
    CLOUDFLARE_ACCOUNT_ID: process.env.CLOUDFLARE_ACCOUNT_ID || '',
    JWT_SECRET: process.env.JWT_SECRET || '',
    JWT_EXPIRE: process.env.JWT_EXPIRE || '',
    ALLOWED_ORIGINS: process.env.ALLOWED_ORIGINS || '',
    // 添加其他可能的secrets
    ...process.env
  };
  
  console.log('当前环境变量状态:');
  console.log(`CLOUDFLARE_API_TOKEN: ${secrets.CLOUDFLARE_API_TOKEN ? '已设置' : '未设置'} (${secrets.CLOUDFLARE_API_TOKEN ? secrets.CLOUDFLARE_API_TOKEN.substring(0, 8) + '...' : '空'})`);
  console.log(`CLOUDFLARE_ACCOUNT_ID: ${secrets.CLOUDFLARE_ACCOUNT_ID ? '已设置' : '未设置'} (${secrets.CLOUDFLARE_ACCOUNT_ID ? secrets.CLOUDFLARE_ACCOUNT_ID.substring(0, 8) + '...' : '空'})`);
  console.log(`JWT_SECRET: ${secrets.JWT_SECRET ? '已设置' : '未设置'} (${secrets.JWT_SECRET ? secrets.JWT_SECRET.substring(0, 8) + '...' : '空'})`);
  console.log('');
  
  // 模拟GitHub Actions中的检查逻辑
  const hasApiToken = secrets.CLOUDFLARE_API_TOKEN && secrets.CLOUDFLARE_API_TOKEN !== '';
  const hasAccountId = secrets.CLOUDFLARE_ACCOUNT_ID && secrets.CLOUDFLARE_ACCOUNT_ID !== '';
  const hasJwtSecret = secrets.JWT_SECRET && secrets.JWT_SECRET !== '';
  
  console.log('🔍 模拟GitHub Actions检查逻辑:');
  console.log(`secrets.CLOUDFLARE_API_TOKEN != '' : ${secrets.CLOUDFLARE_API_TOKEN !== ''}`);
  console.log(`secrets.CLOUDFLARE_ACCOUNT_ID != '' : ${secrets.CLOUDFLARE_ACCOUNT_ID !== ''}`);
  console.log(`secrets.JWT_SECRET != '' : ${secrets.JWT_SECRET !== ''}`);
  console.log('');
  
  // 模拟工作流中的条件检查
  if (!hasApiToken || !hasAccountId) {
    console.log('❌ 模拟结果: Required secrets are not available. Cannot proceed with deployment.');
    console.log('   这与GitHub Actions中的行为一致');
    return false;
  } else {
    console.log('✅ 模拟结果: All required secrets are available.');
    return true;
  }
}

// 测试本地环境变量文件
function checkLocalEnvFiles() {
  console.log('\n📄 检查本地环境文件...');
  
  const envFiles = ['.env', '.env.local', '.env.production'];
  let foundConfig = false;
  
  envFiles.forEach(file => {
    try {
      const content = readFileSync(join(__dirname, file), 'utf8');
      console.log(`✅ ${file} 存在`);
      
      // 检查是否包含必需的变量
      const hasApiToken = content.includes('CLOUDFLARE_API_TOKEN=') && !content.includes('CLOUDFLARE_API_TOKEN=');
      const hasAccountId = content.includes('CLOUDFLARE_ACCOUNT_ID=') && !content.includes('CLOUDFLARE_ACCOUNT_ID=');
      const hasJwtSecret = content.includes('JWT_SECRET=') && !content.includes('JWT_SECRET=');
      
      if (hasApiToken || hasAccountId || hasJwtSecret) {
        foundConfig = true;
        console.log(`   找到配置变量`);
      }
    } catch (error) {
      console.log(`⚠️  ${file} 不存在`);
    }
  });
  
  if (!foundConfig) {
    console.log('⚠️  未在任何环境文件中找到有效的secrets配置');
  }
}

// 检查wrangler配置
function checkWranglerConfig() {
  console.log('\n⚙️  检查wrangler配置...');
  
  try {
    const wranglerContent = readFileSync(join(__dirname, 'wrangler.toml'), 'utf8');
    
    // 检查是否使用了环境变量引用
    if (wranglerContent.includes('CLOUDFLARE_API_TOKEN')) {
      console.log('⚠️  wrangler.toml中直接引用了CLOUDFLARE_API_TOKEN');
      console.log('   这可能导致问题，因为wrangler.toml不应该包含敏感信息');
    }
    
    if (wranglerContent.includes('JWT_SECRET')) {
      console.log('⚠️  wrangler.toml中直接引用了JWT_SECRET');
      console.log('   这可能导致安全问题');
    }
    
    // 检查是否使用了占位符
    if (wranglerContent.includes('your-')) {
      console.log('⚠️  wrangler.toml中包含占位符配置');
      console.log('   这些需要在部署时替换为实际值');
    }
    
  } catch (error) {
    console.log('❌ 无法读取wrangler.toml文件');
  }
}

// 模拟GitHub Actions环境变量注入
function simulateGitHubActionsEnvInjection() {
  console.log('\n🔄 模拟GitHub Actions环境变量注入...');
  
  // GitHub Actions中，secrets通过环境变量注入
  // 工作流文件中的 env: 部分会将secrets转换为环境变量
  
  console.log('在GitHub Actions中，工作流文件的这部分:');
  console.log('```yaml');
  console.log('env:');
  console.log('  CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}');
  console.log('  CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}');
  console.log('  JWT_SECRET: ${{ secrets.JWT_SECRET }}');
  console.log('```');
  console.log('');
  console.log('会将GitHub Secrets注入为环境变量，使得:');
  console.log('- process.env.CLOUDFLARE_API_TOKEN 可用');
  console.log('- process.env.CLOUDFLARE_ACCOUNT_ID 可用');
  console.log('- process.env.JWT_SECRET 可用');
  console.log('');
  
  if (!process.env.CLOUDFLARE_API_TOKEN) {
    console.log('❌ 当前环境中缺少 CLOUDFLARE_API_TOKEN');
    console.log('   这意味着要么:');
    console.log('   1. GitHub Secrets未正确配置');
    console.log('   2. 工作流文件未正确传递secrets');
    console.log('   3. 环境变量名称不匹配');
  }
}

// 运行所有检查
console.log('开始模拟GitHub Actions环境...\n');

const secretsAvailable = simulateGitHubActionsCheck();
checkLocalEnvFiles();
checkWranglerConfig();
simulateGitHubActionsEnvInjection();

console.log('\n=== 测试完成 ===');
console.log('');
console.log('💡 关键发现:');
console.log('');

if (!secretsAvailable) {
  console.log('🚨 问题确认: GitHub Actions会因为缺少secrets而失败');
  console.log('');
  console.log('🔧 解决方案:');
  console.log('1. 确保在GitHub仓库中配置了所有必需的secrets');
  console.log('2. 检查工作流文件中的secrets名称是否完全匹配');
  console.log('3. 确认工作流文件的env部分正确传递了所有secrets');
  console.log('');
  console.log('📋 需要配置的secrets:');
  console.log('- CLOUDFLARE_API_TOKEN');
  console.log('- CLOUDFLARE_ACCOUNT_ID');
  console.log('- JWT_SECRET');
  console.log('- 以及其他在.env.example中列出的变量');
} else {
  console.log('✅ 环境变量配置看起来是正确的');
  console.log('如果GitHub Actions仍然失败，问题可能在:');
  console.log('- Cloudflare账户权限');
  console.log('- Workers服务配置');
  console.log('- 网络连接问题');
  console.log('- wrangler配置问题');
}
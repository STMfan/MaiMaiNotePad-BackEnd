#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('=== GitHub Actions 验证清单 ===\n');

// 读取工作流文件
const workflowPath = path.join(__dirname, '.github', 'workflows', 'deploy-to-cloudflare.yml');
const workflowContent = fs.readFileSync(workflowPath, 'utf8');

console.log('1. 工作流文件检查:');
console.log(`   ✅ 工作流文件存在: ${workflowPath}`);

// 检查permissions配置
const hasCorrectPermissions = workflowContent.includes('permissions:') && 
                            workflowContent.includes('contents: read') && 
                            workflowContent.includes('id-token: write');
console.log(`   ${hasCorrectPermissions ? '✅' : '❌'} 权限配置正确`);

// 检查secrets使用
const usesCloudflareApiToken = workflowContent.includes('CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}');
const usesCloudflareAccountId = workflowContent.includes('CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}');
const usesJwtSecret = workflowContent.includes('JWT_SECRET: ${{ secrets.JWT_SECRET }}');

console.log(`   ${usesCloudflareApiToken ? '✅' : '❌'} 使用 CLOUDFLARE_API_TOKEN`);
console.log(`   ${usesCloudflareAccountId ? '✅' : '❌'} 使用 CLOUDFLARE_ACCOUNT_ID`);
console.log(`   ${usesJwtSecret ? '✅' : '❌'} 使用 JWT_SECRET`);

// 检查调试步骤
const hasDebugStep = workflowContent.includes('Debug environment variables');
console.log(`   ${hasDebugStep ? '✅' : '❌'} 包含调试步骤`);

console.log('\n2. GitHub仓库检查:');
console.log('   请手动检查以下项目:');
console.log('   ✅ 仓库不是fork (fork仓库不会继承原仓库的secrets)');
console.log('   ✅ Actions权限已启用');
console.log('   ✅ 分支保护规则允许直接推送或已创建PR');

console.log('\n3. GitHub Secrets配置:');
console.log('   请在GitHub仓库中检查以下secrets是否已配置:');
console.log('   ✅ CLOUDFLARE_API_TOKEN');
console.log('   ✅ CLOUDFLARE_ACCOUNT_ID');
console.log('   ✅ JWT_SECRET');
console.log('   ✅ 其他必需的secrets');

console.log('\n4. 验证步骤:');
console.log('   1. 推送代码到GitHub触发工作流');
console.log('   2. 查看"Debug environment variables"步骤的输出');
console.log('   3. 确认secrets是否正确加载');
console.log('   4. 检查部署步骤是否成功');

console.log('\n5. 常见问题解决方案:');
console.log('   问题: Fork仓库无法访问secrets');
console.log('   解决: 在fork仓库中重新配置所有secrets');
console.log('');
console.log('   问题: 工作流因权限问题失败');
console.log('   解决: 检查仓库的Actions权限设置');
console.log('');
console.log('   问题: secrets未正确加载');
console.log('   解决: 确认secrets名称完全匹配，区分大小写');

console.log('\n=== 验证完成 ===');
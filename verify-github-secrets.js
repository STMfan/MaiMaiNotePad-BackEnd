#!/usr/bin/env node

/**
 * GitHub Secrets 验证工具
 * 通过GitHub API检查仓库中的secrets配置
 */

import { execSync } from 'child_process';

console.log('=== GitHub Secrets 验证工具 ===\n');

// 获取GitHub仓库信息
function getGitHubRepoInfo() {
  try {
    // 获取远程仓库URL
    const remoteUrl = execSync('git remote get-url origin', { encoding: 'utf8' }).trim();
    console.log(`📍 远程仓库URL: ${remoteUrl}`);
    
    // 解析仓库信息
    const match = remoteUrl.match(/github\.com[:/]([^/]+)\/([^/.]+)/);
    if (match) {
      const [, owner, repo] = match;
      console.log(`📂 仓库: ${owner}/${repo}`);
      return { owner, repo };
    }
  } catch (error) {
    console.log('❌ 无法获取GitHub仓库信息');
    return null;
  }
}

// 检查GitHub CLI是否可用
function checkGitHubCLI() {
  try {
    execSync('gh --version', { encoding: 'utf8' });
    return true;
  } catch (error) {
    return false;
  }
}

// 通过GitHub CLI检查secrets
function checkGitHubSecrets(owner, repo) {
  console.log('\n🔍 检查GitHub Secrets...\n');
  
  const requiredSecrets = [
    'CLOUDFLARE_API_TOKEN',
    'CLOUDFLARE_ACCOUNT_ID', 
    'JWT_SECRET',
    'JWT_EXPIRE',
    'ALLOWED_ORIGINS'
  ];
  
  const optionalSecrets = [
    'GITHUB_TOKEN',
    'ENVIRONMENT',
    'NODE_ENV'
  ];
  
  try {
    // 尝试列出仓库的secrets
    const result = execSync(`gh secret list --repo ${owner}/${repo}`, { encoding: 'utf8' });
    
    console.log('📋 GitHub Secrets列表:');
    console.log(result);
    
    // 分析结果
    const lines = result.split('\n').filter(line => line.trim());
    const foundSecrets = lines.map(line => line.split('\t')[0]).filter(name => name);
    
    console.log('\n🔍 Secrets分析:');
    
    requiredSecrets.forEach(secret => {
      if (foundSecrets.includes(secret)) {
        console.log(`✅ ${secret}: 已配置`);
      } else {
        console.log(`❌ ${secret}: 未配置`);
      }
    });
    
    optionalSecrets.forEach(secret => {
      if (foundSecrets.includes(secret)) {
        console.log(`✅ ${secret}: 已配置 (可选)`);
      } else {
        console.log(`⚠️  ${secret}: 未配置 (可选)`);
      }
    });
    
    // 检查是否所有必需secrets都已配置
    const missingRequired = requiredSecrets.filter(secret => !foundSecrets.includes(secret));
    
    if (missingRequired.length === 0) {
      console.log('\n🎉 所有必需secrets都已配置！');
      return true;
    } else {
      console.log(`\n❌ 缺少以下必需secrets: ${missingRequired.join(', ')}`);
      return false;
    }
    
  } catch (error) {
    console.log('❌ 无法获取GitHub Secrets信息');
    console.log('可能的原因:');
    console.log('- GitHub CLI未安装或未登录');
    console.log('- 没有仓库访问权限');
    console.log('- 网络连接问题');
    return false;
  }
}

// 提供手动检查指南
function provideManualCheckGuide(owner, repo) {
  console.log('\n📖 手动检查指南:');
  console.log('');
  console.log('1. 访问GitHub仓库页面:');
  console.log(`   https://github.com/${owner}/${repo}/settings/secrets/actions`);
  console.log('');
  console.log('2. 检查是否包含以下secrets:');
  console.log('   - CLOUDFLARE_API_TOKEN');
  console.log('   - CLOUDFLARE_ACCOUNT_ID');
  console.log('   - JWT_SECRET');
  console.log('   - JWT_EXPIRE');
  console.log('   - ALLOWED_ORIGINS');
  console.log('');
  console.log('3. 如果缺少任何secret，请点击"New repository secret"添加');
  console.log('');
  console.log('4. 获取Cloudflare凭据:');
  console.log('   - API Token: https://dash.cloudflare.com/profile/api-tokens');
  console.log('   - Account ID: https://dash.cloudflare.com/ → 右侧栏');
  console.log('');
  console.log('5. JWT_SECRET应该是随机生成的安全字符串');
  console.log('');
}

// 检查工作流文件
function checkWorkflowFile() {
  console.log('\n📄 检查工作流文件...');
  
  try {
    const fs = require('fs');
    const workflowContent = fs.readFileSync('.github/workflows/deploy-to-cloudflare.yml', 'utf8');
    
    // 检查env部分
    const envMatches = workflowContent.match(/env:\s*\n((?:\s+\w+:\s*\$\{\{[^}]+\}\}\s*\n)*)/g);
    
    if (envMatches) {
      console.log('✅ 工作流文件包含env配置');
      console.log('📋 找到的环境变量配置:');
      envMatches.forEach(match => console.log(match));
    } else {
      console.log('⚠️  工作流文件可能缺少env配置');
    }
    
    // 检查secrets引用
    const secretMatches = workflowContent.match(/\$\{\{\s*secrets\.\w+\s*\}\}/g);
    if (secretMatches) {
      console.log('\n📋 找到的secrets引用:');
      secretMatches.forEach(secret => console.log(`   ${secret}`));
    }
    
  } catch (error) {
    console.log('❌ 无法读取工作流文件');
  }
}

// 主函数
function main() {
  const repoInfo = getGitHubRepoInfo();
  
  if (!repoInfo) {
    console.log('❌ 无法确定GitHub仓库信息');
    return;
  }
  
  const hasGitHubCLI = checkGitHubCLI();
  
  if (hasGitHubCLI) {
    console.log('✅ GitHub CLI已安装');
    const secretsConfigured = checkGitHubSecrets(repoInfo.owner, repoInfo.repo);
    
    if (!secretsConfigured) {
      provideManualCheckGuide(repoInfo.owner, repoInfo.repo);
    }
  } else {
    console.log('⚠️  GitHub CLI未安装');
    console.log('请安装GitHub CLI或使用手动检查:');
    provideManualCheckGuide(repoInfo.owner, repoInfo.repo);
  }
  
  checkWorkflowFile();
  
  console.log('\n=== 验证完成 ===');
}

main();
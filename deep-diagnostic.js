#!/usr/bin/env node

/**
 * GitHub Actions 深度诊断工具
 * 用于排查Cloudflare Workers部署问题
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

console.log('=== GitHub Actions 深度诊断工具 ===\n');

// 1. 检查工作流文件语法
console.log('1. 检查工作流文件语法...');
try {
  const workflowContent = readFileSync(join(__dirname, '.github', 'workflows', 'deploy-to-cloudflare.yml'), 'utf8');
  
  // 检查YAML语法问题
  if (workflowContent.includes('${{ secrets.CLOUDFLARE_API_TOKEN }}')) {
    console.log('✅ CLOUDFLARE_API_TOKEN 引用正确');
  } else {
    console.log('❌ CLOUDFLARE_API_TOKEN 引用可能有问题');
  }
  
  if (workflowContent.includes('cloudflare/wrangler-action@v3')) {
    console.log('✅ 使用正确的wrangler-action版本');
  } else {
    console.log('❌ wrangler-action版本可能有问题');
  }
  
  // 检查环境变量传递
  if (workflowContent.includes('env:')) {
    console.log('✅ 工作流文件包含环境变量配置');
  } else {
    console.log('❌ 工作流文件缺少环境变量配置');
  }
  
} catch (error) {
  console.log('❌ 无法读取工作流文件:', error.message);
}

// 2. 检查wrangler.toml配置
console.log('\n2. 检查wrangler.toml配置...');
try {
  const wranglerContent = readFileSync(join(__dirname, 'wrangler.toml'), 'utf8');
  
  // 检查必需的配置项
  if (wranglerContent.includes('name =')) {
    console.log('✅ Worker名称已配置');
  } else {
    console.log('❌ Worker名称未配置');
  }
  
  if (wranglerContent.includes('compatibility_date =')) {
    console.log('✅ 兼容性日期已配置');
  } else {
    console.log('❌ 兼容性日期未配置');
  }
  
  if (wranglerContent.includes('compatibility_flags =')) {
    console.log('✅ 兼容性标志已配置');
  } else {
    console.log('❌ 兼容性标志未配置');
  }
  
  // 检查KV命名空间
  const kvMatches = wranglerContent.match(/\[\[kv_namespaces\]\]/g);
  if (kvMatches && kvMatches.length > 0) {
    console.log(`✅ 找到 ${kvMatches.length} 个KV命名空间配置`);
  } else {
    console.log('⚠️  未找到KV命名空间配置');
  }
  
  // 检查D1数据库
  if (wranglerContent.includes('[[d1_databases]]')) {
    console.log('✅ D1数据库已配置');
  } else {
    console.log('⚠️  D1数据库未配置');
  }
  
  // 检查R2存储
  if (wranglerContent.includes('[[r2_buckets]]')) {
    console.log('✅ R2存储已配置');
  } else {
    console.log('⚠️  R2存储未配置');
  }
  
} catch (error) {
  console.log('❌ 无法读取wrangler.toml文件:', error.message);
}

// 3. 检查package.json
console.log('\n3. 检查package.json配置...');
try {
  const packageContent = JSON.parse(readFileSync(join(__dirname, 'package.json'), 'utf8'));
  
  if (packageContent.scripts && packageContent.scripts.build) {
    console.log('✅ 构建脚本已配置');
  } else {
    console.log('❌ 构建脚本未配置');
  }
  
  if (packageContent.scripts && packageContent.scripts.deploy) {
    console.log('✅ 部署脚本已配置');
  } else {
    console.log('⚠️  部署脚本未配置');
  }
  
  if (packageContent.dependencies && packageContent.dependencies.wrangler) {
    console.log('✅ Wrangler CLI已安装');
  } else {
    console.log('❌ Wrangler CLI未安装');
  }
  
} catch (error) {
  console.log('❌ 无法读取package.json文件:', error.message);
}

// 4. 检查环境文件
console.log('\n4. 检查环境文件...');
const envFiles = ['.env', '.env.local', '.env.production'];
envFiles.forEach(file => {
  try {
    const envContent = readFileSync(join(__dirname, file), 'utf8');
    console.log(`✅ ${file} 文件存在`);
    
    // 检查关键环境变量
    if (envContent.includes('CLOUDFLARE_API_TOKEN=')) {
      console.log(`✅ ${file} 包含CLOUDFLARE_API_TOKEN`);
    } else {
      console.log(`⚠️  ${file} 不包含CLOUDFLARE_API_TOKEN`);
    }
    
    if (envContent.includes('CLOUDFLARE_ACCOUNT_ID=')) {
      console.log(`✅ ${file} 包含CLOUDFLARE_ACCOUNT_ID`);
    } else {
      console.log(`⚠️  ${file} 不包含CLOUDFLARE_ACCOUNT_ID`);
    }
    
  } catch (error) {
    console.log(`⚠️  ${file} 文件不存在或无法读取`);
  }
});

// 5. 检查Cloudflare Workers入口文件
console.log('\n5. 检查Cloudflare Workers入口文件...');
try {
  const workerEntry = readFileSync(join(__dirname, 'src', 'workers', 'index.js'), 'utf8');
  console.log('✅ Workers入口文件存在');
  
  if (workerEntry.includes('export default')) {
    console.log('✅ 使用ES模块导出');
  } else if (workerEntry.includes('module.exports')) {
    console.log('✅ 使用CommonJS导出');
  } else {
    console.log('⚠️  未找到标准导出方式');
  }
  
  if (workerEntry.includes('addEventListener') || workerEntry.includes('fetch')) {
    console.log('✅ 包含事件监听器或fetch处理');
  } else {
    console.log('⚠️  未找到事件监听器或fetch处理');
  }
  
} catch (error) {
  console.log('❌ Workers入口文件不存在:', error.message);
}

// 6. 提供建议
console.log('\n6. 常见问题排查建议:');
console.log('');
console.log('🔍 如果GitHub Actions仍然失败，请检查:');
console.log('   1. 确认GitHub Secrets名称完全匹配（区分大小写）');
console.log('   2. 检查Cloudflare账户是否有权限创建Workers');
console.log('   3. 确认wrangler.toml中的配置与实际环境匹配');
console.log('   4. 检查是否启用了Cloudflare Workers服务');
console.log('   5. 确认D1数据库和R2存储已在Cloudflare控制台中创建');
console.log('   6. 检查KV命名空间ID是否正确');
console.log('');
console.log('🛠️  调试步骤:');
console.log('   1. 在本地运行: npm run build');
console.log('   2. 尝试本地部署: npx wrangler deploy --dry-run');
console.log('   3. 检查Cloudflare控制台中的Workers日志');
console.log('   4. 使用wrangler tail查看实时日志');
console.log('');
console.log('📋 需要手动验证的项目:');
console.log('   - Cloudflare账户是否验证');
console.log('   - Workers服务是否启用');
console.log('   - 域名是否已添加到Cloudflare');
console.log('   - DNS记录是否正确配置');
console.log('   - SSL证书是否有效');

console.log('\n=== 诊断完成 ===');
#!/usr/bin/env node

/**
 * 后端健康状况检查脚本
 * 测试已部署的backend.maimnp.tech各项功能
 */

import https from 'https';
import http from 'http';

// 配置
const BASE_URL = 'https://backend.maimnp.tech';
const TIMEOUT = 10000; // 10秒超时

// 颜色输出
const colors = {
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[36m',
  reset: '\x1b[0m'
};

// 测试结果存储
const results = {
  passed: 0,
  failed: 0,
  tests: []
};

/**
 * HTTP请求工具函数
 */
function makeRequest(url, options = {}) {
  return new Promise((resolve, reject) => {
    const isHttps = url.startsWith('https');
    const client = isHttps ? https : http;
    
    const req = client.request(url, {
      method: options.method || 'GET',
      headers: {
        'User-Agent': 'HealthCheck/1.0',
        'Content-Type': 'application/json',
        ...options.headers
      },
      timeout: TIMEOUT
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        resolve({
          status: res.statusCode,
          headers: res.headers,
          data: data,
          json: () => {
            try {
              return JSON.parse(data);
            } catch (e) {
              return null;
            }
          }
        });
      });
    });
    
    req.on('error', reject);
    req.on('timeout', () => reject(new Error('Request timeout')));
    
    if (options.body) {
      req.write(typeof options.body === 'string' ? options.body : JSON.stringify(options.body));
    }
    
    req.end();
  });
}

/**
 * 运行单个测试
 */
async function runTest(name, testFn) {
  process.stdout.write(`${colors.blue}Testing ${name}...${colors.reset} `);
  
  try {
    const startTime = Date.now();
    const result = await testFn();
    const duration = Date.now() - startTime;
    
    if (result.success) {
      console.log(`${colors.green}✅ PASSED${colors.reset} (${duration}ms)`);
      results.passed++;
      results.tests.push({ name, status: 'passed', duration, message: result.message });
    } else {
      console.log(`${colors.red}❌ FAILED${colors.reset} (${duration}ms)`);
      console.log(`  ${colors.red}Error: ${result.message}${colors.reset}`);
      results.failed++;
      results.tests.push({ name, status: 'failed', duration, message: result.message });
    }
  } catch (error) {
    console.log(`${colors.red}❌ FAILED${colors.reset}`);
    console.log(`  ${colors.red}Error: ${error.message}${colors.reset}`);
    results.failed++;
    results.tests.push({ name, status: 'failed', message: error.message });
  }
}

/**
 * 测试套件
 */
const tests = [
  {
    name: '基本连接性',
    fn: async () => {
      try {
        const response = await makeRequest(`${BASE_URL}/health`);
        return {
          success: response.status === 200,
          message: `Status: ${response.status}, Response: ${response.data}`
        };
      } catch (error) {
        return { success: false, message: `Connection failed: ${error.message}` };
      }
    }
  },
  
  {
    name: 'API根端点',
    fn: async () => {
      try {
        const response = await makeRequest(`${BASE_URL}/api`);
        const data = response.json();
        return {
          success: response.status === 200 && data && data.message,
          message: data ? `API响应: ${JSON.stringify(data)}` : '无有效响应数据'
        };
      } catch (error) {
        return { success: false, message: `API请求失败: ${error.message}` };
      }
    }
  },
  
  {
    name: '用户认证端点',
    fn: async () => {
      try {
        const response = await makeRequest(`${BASE_URL}/api/auth/status`);
        return {
          success: response.status === 200 || response.status === 401,
          message: `认证端点响应状态: ${response.status}`
        };
      } catch (error) {
        return { success: false, message: `认证端点请求失败: ${error.message}` };
      }
    }
  },
  
  {
    name: '笔记列表端点',
    fn: async () => {
      try {
        const response = await makeRequest(`${BASE_URL}/api/notes`);
        return {
          success: response.status === 200 || response.status === 401,
          message: `笔记端点响应状态: ${response.status}`
        };
      } catch (error) {
        return { success: false, message: `笔记端点请求失败: ${error.message}` };
      }
    }
  },
  
  {
    name: '系统状态端点',
    fn: async () => {
      try {
        const response = await makeRequest(`${BASE_URL}/api/system/status`);
        const data = response.json();
        return {
          success: response.status === 200 && data && data.status,
          message: data ? `系统状态: ${JSON.stringify(data)}` : '无有效响应数据'
        };
      } catch (error) {
        return { success: false, message: `系统状态端点请求失败: ${error.message}` };
      }
    }
  },
  
  {
    name: 'CORS头检查',
    fn: async () => {
      try {
        const response = await makeRequest(`${BASE_URL}/api`, {
          method: 'OPTIONS',
          headers: {
            'Origin': 'https://example.com',
            'Access-Control-Request-Method': 'GET'
          }
        });
        const hasCorsHeaders = response.headers['access-control-allow-origin'] || 
                              response.headers['Access-Control-Allow-Origin'];
        return {
          success: !!hasCorsHeaders,
          message: hasCorsHeaders ? 'CORS头已正确设置' : '缺少CORS头'
        };
      } catch (error) {
        return { success: false, message: `CORS检查失败: ${error.message}` };
      }
    }
  },
  
  {
    name: '响应时间测试',
    fn: async () => {
      try {
        const startTime = Date.now();
        await makeRequest(`${BASE_URL}/health`);
        const responseTime = Date.now() - startTime;
        return {
          success: responseTime < 5000, // 5秒内响应
          message: `响应时间: ${responseTime}ms`
        };
      } catch (error) {
        return { success: false, message: `响应时间测试失败: ${error.message}` };
      }
    }
  },
  
  {
    name: 'SSL证书检查',
    fn: async () => {
      try {
        const response = await makeRequest(`${BASE_URL}/health`);
        return {
          success: true, // 如果能成功连接HTTPS，说明SSL正常
          message: 'SSL证书有效'
        };
      } catch (error) {
        if (error.message.includes('certificate')) {
          return { success: false, message: `SSL证书问题: ${error.message}` };
        }
        return { success: false, message: `SSL检查失败: ${error.message}` };
      }
    }
  }
];

/**
 * 主函数
 */
async function main() {
  console.log(`${colors.blue}🚀 开始测试 backend.maimnp.tech 健康状况${colors.reset}`);
  console.log(`${colors.blue}测试URL: ${BASE_URL}${colors.reset}`);
  console.log(`${colors.blue}超时时间: ${TIMEOUT/1000}秒${colors.reset}`);
  console.log('');
  
  // 运行所有测试
  for (const test of tests) {
    await runTest(test.name, test.fn);
  }
  
  // 显示总结
  console.log('');
  console.log(`${colors.blue}📊 测试总结:${colors.reset}`);
  console.log(`${colors.green}✅ 通过: ${results.passed}${colors.reset}`);
  console.log(`${colors.red}❌ 失败: ${results.failed}${colors.reset}`);
  console.log(`总计: ${results.passed + results.failed} 项测试`);
  
  // 显示失败的测试详情
  if (results.failed > 0) {
    console.log('');
    console.log(`${colors.red}🔍 失败测试详情:${colors.reset}`);
    results.tests
      .filter(test => test.status === 'failed')
      .forEach(test => {
        console.log(`${colors.red}- ${test.name}: ${test.message}${colors.reset}`);
      });
  }
  
  // 显示通过的测试详情
  if (results.passed > 0) {
    console.log('');
    console.log(`${colors.green}✅ 通过测试详情:${colors.reset}`);
    results.tests
      .filter(test => test.status === 'passed')
      .forEach(test => {
        console.log(`${colors.green}- ${test.name}: ${test.message}${colors.reset}`);
      });
  }
  
  // 总体评估
  console.log('');
  if (results.failed === 0) {
    console.log(`${colors.green}🎉 所有测试通过！后端服务运行正常。${colors.reset}`);
    process.exit(0);
  } else if (results.failed <= 2) {
    console.log(`${colors.yellow}⚠️  部分测试失败，但服务基本可用。${colors.reset}`);
    process.exit(0);
  } else {
    console.log(`${colors.red}❌ 多项测试失败，服务可能存在问题。${colors.reset}`);
    process.exit(1);
  }
}

// 运行主函数
main().catch(error => {
  console.error(`${colors.red}测试运行失败: ${error.message}${colors.reset}`);
  process.exit(1);
});
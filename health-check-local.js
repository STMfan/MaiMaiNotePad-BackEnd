/**
 * Local health check for KV-based API
 */

const API_BASE_URL = 'http://localhost:8787';

async function testHealth() {
  console.log('🏥 运行本地健康检查...');
  console.log(`测试URL: ${API_BASE_URL}`);
  
  const tests = [
    {
      name: '基本连接性',
      test: async () => {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        return {
          passed: response.status === 200 && data.checks.kv.status === 'healthy',
          message: `状态: ${response.status}, KV: ${data.checks.kv.status}`
        };
      }
    },
    {
      name: 'API根端点',
      test: async () => {
        const response = await fetch(`${API_BASE_URL}/api`);
        const data = await response.json();
        return {
          passed: response.status === 200 && data.name === 'MaiMaiNotePad API',
          message: `API名称: ${data.name}, 端点: ${data.endpoints.length}个`
        };
      }
    },
    {
      name: '系统状态端点',
      test: async () => {
        const response = await fetch(`${API_BASE_URL}/api/system/status`);
        const data = await response.json();
        return {
          passed: response.status === 200 && data.status === 'operational',
          message: `服务状态: ${data.status}`
        };
      }
    },
    {
      name: '用户认证端点',
      test: async () => {
        const response = await fetch(`${API_BASE_URL}/api/users/profile`);
        const data = await response.json();
        return {
          passed: response.status === 200 && data.username === 'demo_user',
          message: `用户名: ${data.username}`
        };
      }
    },
    {
      name: '笔记列表端点',
      test: async () => {
        const response = await fetch(`${API_BASE_URL}/api/notes`);
        const data = await response.json();
        return {
          passed: response.status === 200 && Array.isArray(data.notes),
          message: `笔记数量: ${data.total}`
        };
      }
    },
    {
      name: '创建笔记功能',
      test: async () => {
        const response = await fetch(`${API_BASE_URL}/api/notes`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: '健康检查测试笔记',
            content: '这是健康检查创建的测试笔记'
          })
        });
        const data = await response.json();
        return {
          passed: response.status === 201 && data.id,
          message: `创建笔记ID: ${data.id}`
        };
      }
    },
    {
      name: 'CORS头检查',
      test: async () => {
        const response = await fetch(`${API_BASE_URL}/api`, {
          method: 'OPTIONS'
        });
        const corsHeader = response.headers.get('Access-Control-Allow-Origin');
        return {
          passed: !!corsHeader,
          message: `CORS头: ${corsHeader || '未设置'}`
        };
      }
    },
    {
      name: '响应时间测试',
      test: async () => {
        const start = Date.now();
        const response = await fetch(`${API_BASE_URL}/health`);
        const duration = Date.now() - start;
        return {
          passed: response.status === 200 && duration < 1000,
          message: `响应时间: ${duration}ms`
        };
      }
    }
  ];
  
  let passed = 0;
  let failed = 0;
  
  for (const testCase of tests) {
    try {
      process.stdout.write(`Testing ${testCase.name}... `);
      const result = await testCase.test();
      
      if (result.passed) {
        console.log(`✅ PASSED (${result.message})`);
        passed++;
      } else {
        console.log(`❌ FAILED (${result.message})`);
        failed++;
      }
    } catch (error) {
      console.log(`❌ FAILED (${error.message})`);
      failed++;
    }
  }
  
  console.log('\n📊 测试总结:');
  console.log(`✅ 通过: ${passed}`);
  console.log(`❌ 失败: ${failed}`);
  console.log(`总计: ${tests.length} 项测试`);
  
  if (failed === 0) {
    console.log('\n🎉 所有测试通过！服务运行正常。');
  } else {
    console.log('\n⚠️  部分测试失败，请检查服务配置。');
  }
  
  return failed === 0;
}

// 运行测试
testHealth().catch(console.error);
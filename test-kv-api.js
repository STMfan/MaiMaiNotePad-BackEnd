/**
 * Test script for KV-based API
 */

const API_BASE_URL = 'https://maimai-notepad-workers-development.lxy13142mnsj.workers.dev';

async function testAPI() {
  console.log('🚀 测试KV-based API功能');
  console.log(`测试URL: ${API_BASE_URL}`);
  
  try {
    // Test 1: Health check
    console.log('\n📊 测试健康检查端点...');
    const healthResponse = await fetch(`${API_BASE_URL}/health`);
    const healthData = await healthResponse.json();
    console.log(`状态: ${healthResponse.status}`);
    console.log(`KV状态: ${healthData.checks.kv.status}`);
    
    // Test 2: API根端点
    console.log('\n📡 测试API根端点...');
    const apiResponse = await fetch(`${API_BASE_URL}/api`);
    const apiData = await apiResponse.json();
    console.log(`状态: ${apiResponse.status}`);
    console.log(`API名称: ${apiData.name}`);
    console.log(`可用端点: ${apiData.endpoints.join(', ')}`);
    
    // Test 3: 系统状态
    console.log('\n⚙️ 测试系统状态端点...');
    const statusResponse = await fetch(`${API_BASE_URL}/api/system/status`);
    const statusData = await statusResponse.json();
    console.log(`状态: ${statusResponse.status}`);
    console.log(`服务状态: ${statusData.status}`);
    
    // Test 4: 用户资料
    console.log('\n👤 测试用户资料端点...');
    const profileResponse = await fetch(`${API_BASE_URL}/api/users/profile`);
    const profileData = await profileResponse.json();
    console.log(`状态: ${profileResponse.status}`);
    console.log(`用户名: ${profileData.username}`);
    
    // Test 5: 笔记列表
    console.log('\n📝 测试笔记列表端点...');
    const notesResponse = await fetch(`${API_BASE_URL}/api/notes`);
    const notesData = await notesResponse.json();
    console.log(`状态: ${notesResponse.status}`);
    console.log(`笔记数量: ${notesData.total}`);
    
    // Test 6: 创建笔记
    console.log('\n➕ 测试创建笔记...');
    const createResponse = await fetch(`${API_BASE_URL}/api/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: '测试笔记',
        content: '这是通过KV API创建的测试笔记'
      })
    });
    const createdNote = await createResponse.json();
    console.log(`状态: ${createResponse.status}`);
    console.log(`创建笔记ID: ${createdNote.id}`);
    
    // Test 7: 再次获取笔记列表
    console.log('\n📋 验证笔记创建...');
    const notesResponse2 = await fetch(`${API_BASE_URL}/api/notes`);
    const notesData2 = await notesResponse2.json();
    console.log(`状态: ${notesResponse2.status}`);
    console.log(`新笔记数量: ${notesData2.total}`);
    
    console.log('\n✅ 所有测试完成！');
    
  } catch (error) {
    console.error('❌ 测试失败:', error.message);
    console.error('错误详情:', error);
  }
}

// 运行测试
testAPI();
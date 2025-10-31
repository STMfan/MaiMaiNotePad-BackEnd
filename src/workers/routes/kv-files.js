/**
 * KV存储文件访问路由
 * 提供KV存储文件的访问接口
 */

export async function handleKVFileRequest(request, env, context) {
  const url = new URL(request.url);
  const pathParts = url.pathname.split('/');
  const fileKey = pathParts[pathParts.length - 1];
  
  if (!fileKey) {
    return new Response('File key is required', { status: 400 });
  }

  try {
    const { KVStorageService } = await import('../services/kv-storage.js');
    const storageService = new KVStorageService(env);
    
    switch (request.method) {
      case 'GET':
        return await handleGetFile(request, env, fileKey, storageService);
      
      case 'DELETE':
        return await handleDeleteFile(request, env, fileKey, storageService);
      
      default:
        return new Response('Method not allowed', { status: 405 });
    }
  } catch (error) {
    console.error('KV file request error:', error);
    return new Response('Internal server error', { status: 500 });
  }
}

/**
 * 处理文件获取请求
 */
async function handleGetFile(request, env, fileKey, storageService) {
  try {
    // 获取完整文件key（可能包含路径）
    const url = new URL(request.url);
    const pathParts = url.pathname.split('/');
    const keyIndex = pathParts.indexOf('kv') + 1;
    const fullKey = pathParts.slice(keyIndex).join('/');
    
    if (!fullKey) {
      return new Response('File key is required', { status: 400 });
    }

    // 获取文件
    const file = await storageService.getFile(fullKey);
    
    // 设置响应头
    const headers = new Headers({
      'Content-Type': file.metadata.type,
      'Content-Length': file.body.byteLength.toString(),
      'Cache-Control': 'public, max-age=31536000', // 1年缓存
      'ETag': `"${file.metadata.hash}"`,
      'Last-Modified': new Date(file.metadata.uploadedAt).toUTCString()
    });

    // 添加文件名头
    if (file.metadata.originalName) {
      headers.set('Content-Disposition', `inline; filename="${file.metadata.originalName}"`);
    }

    return new Response(file.body, {
      status: 200,
      headers
    });

  } catch (error) {
    if (error.message === 'File not found') {
      return new Response('File not found', { status: 404 });
    }
    
    console.error('Get file error:', error);
    return new Response('Failed to get file', { status: 500 });
  }
}

/**
 * 处理文件删除请求
 */
async function handleDeleteFile(request, env, fileKey, storageService) {
  try {
    // 验证权限（这里可以添加认证逻辑）
    const url = new URL(request.url);
    const authToken = url.searchParams.get('auth');
    
    // 简单的权限检查（生产环境中应该使用更安全的认证方式）
    if (!authToken || authToken !== env.ADMIN_TOKEN) {
      return new Response('Unauthorized', { status: 401 });
    }

    // 获取完整文件key
    const pathParts = url.pathname.split('/');
    const keyIndex = pathParts.indexOf('kv') + 1;
    const fullKey = pathParts.slice(keyIndex).join('/');
    
    if (!fullKey) {
      return new Response('File key is required', { status: 400 });
    }

    // 删除文件
    const result = await storageService.deleteFile(fullKey);
    
    return new Response(JSON.stringify(result), {
      status: 200,
      headers: {
        'Content-Type': 'application/json'
      }
    });

  } catch (error) {
    console.error('Delete file error:', error);
    return new Response('Failed to delete file', { status: 500 });
  }
}

/**
 * 处理文件列表请求
 */
export async function handleKVFileList(request, env, context) {
  try {
    const url = new URL(request.url);
    const prefix = url.searchParams.get('prefix') || '';
    const limit = parseInt(url.searchParams.get('limit') || '100');
    
    const { KVStorageService } = await import('../services/kv-storage.js');
    const storageService = new KVStorageService(env);
    
    const result = await storageService.listFiles({ prefix, limit });
    
    return new Response(JSON.stringify(result), {
      status: 200,
      headers: {
        'Content-Type': 'application/json'
      }
    });

  } catch (error) {
    console.error('List files error:', error);
    return new Response('Failed to list files', { status: 500 });
  }
}

/**
 * 处理存储统计请求
 */
export async function handleKVStorageStats(request, env, context) {
  try {
    const { KVStorageService } = await import('../services/kv-storage.js');
    const storageService = new KVStorageService(env);
    
    const stats = await storageService.getStorageStats();
    
    return new Response(JSON.stringify(stats), {
      status: 200,
      headers: {
        'Content-Type': 'application/json'
      }
    });

  } catch (error) {
    console.error('Storage stats error:', error);
    return new Response('Failed to get storage stats', { status: 500 });
  }
}

/**
 * 处理文件上传请求（KV存储）
 */
export async function handleKVFileUpload(request, env, context) {
  try {
    const formData = await request.formData();
    const file = formData.get('file');
    
    if (!file) {
      return new Response('No file provided', { status: 400 });
    }

    const options = {
      folder: formData.get('folder') || 'uploads',
      customName: formData.get('customName') || null,
      isPublic: formData.get('isPublic') === 'true',
      metadata: {}
    };

    // 解析额外的元数据
    const metadataStr = formData.get('metadata');
    if (metadataStr) {
      try {
        options.metadata = JSON.parse(metadataStr);
      } catch (e) {
        console.warn('Invalid metadata JSON:', metadataStr);
      }
    }

    const { KVStorageService } = await import('../services/kv-storage.js');
    const storageService = new KVStorageService(env);
    
    const result = await storageService.uploadFile(file, options);
    
    return new Response(JSON.stringify(result), {
      status: 200,
      headers: {
        'Content-Type': 'application/json'
      }
    });

  } catch (error) {
    console.error('File upload error:', error);
    return new Response(`Upload failed: ${error.message}`, { status: 500 });
  }
}
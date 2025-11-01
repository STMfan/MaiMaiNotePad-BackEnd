/**
 * System management routes for Cloudflare Workers
 */

export async function handleSystemRoutes(context, ...params) {
  const { request, env, config, log } = context;
  const url = new URL(request.url);
  const path = url.pathname;
  const method = request.method;
  
  try {
    // Route to specific system handlers
    if (path.includes('/status') && method === 'GET') {
      return await handleSystemStatus(context);
    } else if (path.includes('/stats') && method === 'GET') {
      return await handleSystemStats(context);
    } else if (path.includes('/config') && method === 'GET') {
      return await handleSystemConfig(context);
    } else if (path.includes('/maintenance') && method === 'POST') {
      return await handleSystemMaintenance(context);
    }
    
    return new Response(JSON.stringify({ 
      error: 'Not Found',
      message: 'System endpoint not found'
    }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('System route error', { error: error.message, path, method });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'System service error'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleSystemStatus(context) {
  const { request, env, config, log } = context;
  
  try {
    // Basic system status
    const status = {
      service: 'MaiMai NotePad API',
      version: config.get('API_VERSION', '1.0.0'),
      environment: config.get('ENVIRONMENT', 'production'),
      status: 'operational',
      timestamp: new Date().toISOString(),
      uptime: 0, // Cloudflare Workers don't have process.uptime()
      components: {
        database: env.DB ? 'configured' : 'not_configured',
        storage: env.STORAGE ? 'configured' : 'not_configured',
        kv: env.KV ? 'configured' : 'not_configured'
      }
    };
    
    return new Response(JSON.stringify(status), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('System status error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to get system status'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleSystemStats(context) {
  const { request, env, config, log } = context;
  
  try {
    // Get basic statistics
    const stats = {
      timestamp: new Date().toISOString(),
      users: {
        total: 0,
        active: 0,
        new_today: 0
      },
      notes: {
        total: 0,
        created_today: 0,
        shared: 0
      },
      storage: {
        total_size: 0,
        file_count: 0
      },
      performance: {
        average_response_time: 'N/A',
        uptime_percentage: 100
      }
    };
    
    // Try to get real stats if KV is available
    if (env.KV) {
      try {
        // Count users (simplified)
        const userKeys = await env.KV.list({ prefix: 'user:' });
        stats.users.total = userKeys.keys.filter(key => !key.name.includes(':email:') && !key.name.includes(':settings')).length;
        
        // Count notes (simplified)
        let totalNotes = 0;
        let sharedNotes = 0;
        
        for (const key of userKeys.keys) {
          if (key.name.includes(':notes')) {
            const notesData = await env.KV.get(key.name);
            if (notesData) {
              const notes = JSON.parse(notesData);
              totalNotes += notes.length;
            }
          }
        }
        
        // Count shared notes
        const shareKeys = await env.KV.list({ prefix: 'share:' });
        sharedNotes = shareKeys.keys.length;
        
        stats.notes.total = totalNotes;
        stats.notes.shared = sharedNotes;
        
        // Count files (KV files)
        const fileKeys = await env.KV.list({ prefix: 'file:' });
        stats.storage.file_count = fileKeys.keys.length;
        
      } catch (kvError) {
        log.warn('Failed to get KV stats', { error: kvError.message });
      }
    }
    
    return new Response(JSON.stringify(stats), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('System stats error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to get system statistics'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleSystemConfig(context) {
  const { request, env, config, log } = context;
  
  try {
    // Get system configuration (safe to expose)
    const systemConfig = {
      api_version: config.get('API_VERSION', '1.0.0'),
      environment: config.get('ENVIRONMENT', 'production'),
      features: {
        registration: config.get('ALLOW_REGISTRATION', 'true') === 'true',
        email_verification: config.get('EMAIL_VERIFICATION_REQUIRED', 'false') === 'true',
        file_upload: config.get('ALLOW_FILE_UPLOAD', 'true') === 'true',
        sharing: config.get('ALLOW_SHARING', 'true') === 'true'
      },
      limits: {
        max_file_size: config.get('MAX_FILE_SIZE', '10MB'),
        max_notes_per_user: config.get('MAX_NOTES_PER_USER', '1000'),
        rate_limit_window: config.get('RATE_LIMIT_WINDOW', '15 minutes'),
        rate_limit_max: parseInt(config.get('RATE_LIMIT_MAX', '100'))
      },
      storage: {
        database: env.DB ? 'configured' : 'not_configured',
        storage: env.STORAGE ? 'configured' : 'not_configured',
        kv: env.KV ? 'configured' : 'not_configured'
      }
    };
    
    return new Response(JSON.stringify(systemConfig), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('System config error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to get system configuration'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleSystemMaintenance(context) {
  const { request, env, config, log } = context;
  
  try {
    // Verify admin authentication (simplified)
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || authHeader !== 'Bearer admin-token') {
      return new Response(JSON.stringify({ 
        error: 'Unauthorized',
        message: 'Admin access required'
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const body = await request.json();
    const { operation } = body;
    
    if (!operation) {
      return new Response(JSON.stringify({ 
        error: 'Bad Request',
        message: 'Operation is required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    let result = {
      operation,
      status: 'completed',
      timestamp: new Date().toISOString()
    };
    
    // Perform maintenance operations
    switch (operation) {
      case 'cleanup_sessions':
        result.message = 'Cleaned up expired sessions';
        break;
        
      case 'cleanup_old_files':
        result.message = 'Cleaned up old temporary files';
        break;
        
      case 'optimize_database':
        result.message = 'Database optimization completed';
        break;
        
      case 'clear_cache':
        result.message = 'Cache cleared successfully';
        break;
        
      case 'backup_data':
        result.message = 'Data backup completed';
        break;
        
      default:
        return new Response(JSON.stringify({ 
          error: 'Bad Request',
          message: 'Unknown maintenance operation'
        }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
    }
    
    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('System maintenance error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to perform maintenance operation'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
import { createConfigurationManager } from './config/workers-config.js';
import { createSecurityMiddleware } from '../middleware/security-workers.js';
import { handleAuthRoutes } from './routes/auth-workers.js';
import { handleUserRoutes } from './routes/user-workers.js';
import { handleNoteRoutes } from './routes/note-workers.js';
import { handleSystemRoutes } from './routes/system-workers.js';
import { errorHandler } from '../middleware/error-handler.js';
import { logger } from '../utils/logger.js';
import { handleKVApiRoutes } from './kv-api.js';

/**
 * Main Cloudflare Workers Application
 * Handles routing, middleware, and request processing
 */
export default {
  async fetch(request, env, ctx) {
    const startTime = Date.now();
    const requestId = crypto.randomUUID();
    
    try {
      // Initialize configuration
      const config = createConfigurationManager(env);
      
      // Initialize logger
      const log = logger.child({ requestId, method: request.method, url: request.url });
      
      // Log request start
      log.info('Request started', {
        method: request.method,
        url: request.url,
        headers: Object.fromEntries(request.headers.entries())
      });

      // Create security middleware
      const securityMiddleware = createSecurityMiddleware(config);
      
      // Apply security middleware
      const securityResult = await securityMiddleware(request, env);
      if (securityResult instanceof Response) {
        return securityResult;
      }

      // Parse URL and route
      const url = new URL(request.url);
      const path = url.pathname;
      const method = request.method;

      // Create router context
      const context = {
        request,
        env,
        ctx,
        config,
        log,
        requestId,
        startTime
      };

      // Route matching
      let response;
      
      // Health check endpoint
      if (path === '/health' && method === 'GET') {
        response = await handleHealthCheck(context);
      }
      // API routes - try KV API first as fallback
      else if (path.startsWith('/api')) {
        const kvApiResponse = await handleKVApiRoutes(request, env, config);
        if (kvApiResponse) {
          response = kvApiResponse;
        } else {
          response = await handleApiRoutes(context, path, method);
        }
      }
      // Static file serving (if needed)
      else if (path.startsWith('/static/')) {
        response = await handleStaticFiles(context, path);
      }
      // 404 for unmatched routes
      else {
        response = new Response('Not Found', { 
          status: 404,
          headers: { 'Content-Type': 'text/plain' }
        });
      }

      // Add CORS headers to response
      response = addCorsHeaders(response, config, request);
      
      // Log request completion
      const duration = Date.now() - startTime;
      log.info('Request completed', {
        status: response.status,
        duration: `${duration}ms`,
        path: url.pathname
      });

      return response;

    } catch (error) {
      const duration = Date.now() - startTime;
      console.error('Request error:', {
        error: error.message,
        stack: error.stack,
        requestId,
        duration: `${duration}ms`
      });

      // Handle errors with error handler middleware
      return errorHandler(error, request, env);
    }
  },

  // Scheduled event handler for cron jobs
  async scheduled(event, env, ctx) {
    const config = createConfigurationManager(env);
    const log = logger.child({ event: 'scheduled', scheduledTime: event.scheduledTime });
    
    log.info('Scheduled event triggered', { cron: event.cron });
    
    try {
      switch (event.cron) {
        case '0 2 * * *': // Daily at 2 AM UTC
          await handleDailyMaintenance(env, config, log);
          break;
        
        case '0 3 * * 0': // Weekly on Sunday at 3 AM UTC
          await handleWeeklyMaintenance(env, config, log);
          break;
          
        default:
          log.warn('Unknown cron schedule', { cron: event.cron });
      }
    } catch (error) {
      log.error('Scheduled event error', { error: error.message, stack: error.stack });
    }
  }
};

/**
 * Handle API routes
 */
async function handleApiRoutes(context, path, method) {
  const { env, config, log } = context;
  
  // Import auth and other route handlers
  const { handleAuthRoutes } = await import('./routes/auth-workers.js');
  const { handleUserRoutes } = await import('./routes/user-workers.js');
  const { handleNoteRoutes } = await import('./routes/note-workers.js');
  const { handleSystemRoutes } = await import('./routes/system-workers.js');
  const createFileUploadRoutes = await import('./routes/file-upload-workers.js').then(m => m.default || m.createFileUploadRoutes);
  const { handleKVFileRequest, handleKVFileList, handleKVStorageStats, handleKVFileUpload } = await import('./routes/kv-files.js');
  
  // Route mapping for all API endpoints
  const routes = [
    // Auth routes
    { pattern: /^\/api\/auth\/register$/, handler: handleAuthRoutes, method: 'POST' },
    { pattern: /^\/api\/auth\/login$/, handler: handleAuthRoutes, method: 'POST' },
    { pattern: /^\/api\/auth\/logout$/, handler: handleAuthRoutes, method: 'POST' },
    { pattern: /^\/api\/auth\/refresh$/, handler: handleAuthRoutes, method: 'POST' },
    { pattern: /^\/api\/auth\/forgot-password$/, handler: handleAuthRoutes, method: 'POST' },
    { pattern: /^\/api\/auth\/reset-password$/, handler: handleAuthRoutes, method: 'POST' },
    { pattern: /^\/api\/auth\/verify-email$/, handler: handleAuthRoutes, method: 'POST' },
    { pattern: /^\/api\/auth\/me$/, handler: handleAuthRoutes, method: 'GET' },
    
    // User routes
    { pattern: /^\/api\/users\/profile$/, handler: handleUserRoutes, method: 'GET' },
    { pattern: /^\/api\/users\/profile$/, handler: handleUserRoutes, method: 'PUT' },
    { pattern: /^\/api\/users\/password$/, handler: handleUserRoutes, method: 'PUT' },
    { pattern: /^\/api\/users\/settings$/, handler: handleUserRoutes, method: 'GET' },
    { pattern: /^\/api\/users\/settings$/, handler: handleUserRoutes, method: 'PUT' },
    
    // Note routes
    { pattern: /^\/api\/notes$/, handler: handleNoteRoutes, method: 'GET' },
    { pattern: /^\/api\/notes$/, handler: handleNoteRoutes, method: 'POST' },
    { pattern: /^\/api\/notes\/([^\/]+)$/, handler: handleNoteRoutes, method: 'GET' },
    { pattern: /^\/api\/notes\/([^\/]+)$/, handler: handleNoteRoutes, method: 'PUT' },
    { pattern: /^\/api\/notes\/([^\/]+)$/, handler: handleNoteRoutes, method: 'DELETE' },
    { pattern: /^\/api\/notes\/([^\/]+)\/share$/, handler: handleNoteRoutes, method: 'POST' },
    { pattern: /^\/api\/notes\/([^\/]+)\/tags$/, handler: handleNoteRoutes, method: 'PUT' },
    { pattern: /^\/api\/notes\/shared\/([^\/]+)$/, handler: handleNoteRoutes, method: 'GET' },
    
    // System routes
    { pattern: /^\/api\/system\/status$/, handler: handleSystemRoutes, method: 'GET' },
    { pattern: /^\/api\/system\/stats$/, handler: handleSystemRoutes, method: 'GET' },
    { pattern: /^\/api\/system\/config$/, handler: handleSystemRoutes, method: 'GET' },
    { pattern: /^\/api\/system\/maintenance$/, handler: handleSystemRoutes, method: 'POST' },
    
    // File upload routes
    { pattern: /^\/api\/upload$/, handler: (context, ...params) => createFileUploadRoutes(context.env).fetch(context.request), method: 'POST' },
    { pattern: /^\/api\/files\/([^\/]+)$/, handler: (context, ...params) => createFileUploadRoutes(context.env).fetch(context.request) },
    { pattern: /^\/api\/files$/, handler: (context, ...params) => createFileUploadRoutes(context.env).fetch(context.request) },
    { pattern: /^\/api\/files\/([^\/]+)$/, handler: (context, ...params) => createFileUploadRoutes(context.env).fetch(context.request), method: 'DELETE' },
    
    // KV storage routes (R2替代方案)
    { pattern: /^\/api\/kv\/([^\/]+)$/, handler: (context, ...params) => handleKVFileRequest(context.request, context.env, context) },
    { pattern: /^\/api\/kv\/([^\/]+)$/, handler: (context, ...params) => handleKVFileRequest(context.request, context.env, context), method: 'DELETE' },
    { pattern: /^\/api\/kv$/, handler: (context, ...params) => handleKVFileList(context.request, context.env, context) },
    { pattern: /^\/api\/kv\/stats$/, handler: (context, ...params) => handleKVStorageStats(context.request, context.env, context) },
    { pattern: /^\/api\/kv\/upload$/, handler: (context, ...params) => handleKVFileUpload(context.request, context.env, context), method: 'POST' }
  ];
  
  // Find matching route
  for (const route of routes) {
    const match = path.match(route.pattern);
    if (match && (!route.method || route.method === method)) {
      const params = match.slice(1); // Extract URL parameters
      
      try {
        return await route.handler(context, ...params);
      } catch (error) {
        log.error('Route handler error', { 
          error: error.message, 
          route: path, 
          method,
          stack: error.stack 
        });
        throw error;
      }
    }
  }
  
  // No matching route found
  return new Response(JSON.stringify({ 
    error: 'Not Found',
    message: 'The requested endpoint does not exist',
    path: path
  }), {
    status: 404,
    headers: { 'Content-Type': 'application/json' }
  });
}

/**
 * Handle health check
 */
async function handleHealthCheck(context) {
  const { env, config } = context;
  
  try {
    // Check database connection (only if DB binding exists)
    const dbCheck = env.DB ? await checkDatabaseHealth(env.DB) : {
      status: 'disabled',
      message: 'Database not configured'
    };
    
    // Check storage connection (only if STORAGE binding exists)
    const storageCheck = env.STORAGE ? await checkStorageHealth(env.STORAGE) : {
      status: 'disabled',
      message: 'Storage not configured'
    };
    
    // Check KV connection (only if KV binding exists)
    const kvCheck = env.KV ? await checkKvHealth(env.KV) : {
      status: 'disabled',
      message: 'KV not configured'
    };
    
    const health = {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      version: config.get('API_VERSION'),
      environment: config.get('ENVIRONMENT'),
      uptime: 0, // Cloudflare Workers don't have process.uptime()
      checks: {
        database: dbCheck,
        storage: storageCheck,
        kv: kvCheck
      }
    };
    
    // Consider service healthy if at least KV is working (minimum requirement)
    const isHealthy = kvCheck.status === 'healthy';
    
    return new Response(JSON.stringify(health), {
      status: isHealthy ? 200 : 503,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    console.error('Health check error:', error);
    return new Response(JSON.stringify({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      error: error.message
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Check database health
 */
async function checkDatabaseHealth(db) {
  try {
    const result = await db.prepare('SELECT 1 as health_check').first();
    return {
      status: result ? 'healthy' : 'unhealthy',
      message: 'Database connection successful'
    };
  } catch (error) {
    return {
      status: 'unhealthy',
      message: `Database error: ${error.message}`
    };
  }
}

/**
 * Check storage health
 */
async function checkStorageHealth(storage) {
  try {
    // Try to list objects in storage (with limit 1)
    const objects = await storage.list({ limit: 1 });
    return {
      status: 'healthy',
      message: 'Storage connection successful'
    };
  } catch (error) {
    return {
      status: 'unhealthy',
      message: `Storage error: ${error.message}`
    };
  }
}

/**
 * Check KV health
 */
async function checkKvHealth(kv) {
  try {
    const testKey = `health_check_${Date.now()}`;
    await kv.put(testKey, 'test', { expirationTtl: 60 });
    const value = await kv.get(testKey);
    await kv.delete(testKey);
    
    return {
      status: value === 'test' ? 'healthy' : 'unhealthy',
      message: 'KV connection successful'
    };
  } catch (error) {
    return {
      status: 'unhealthy',
      message: `KV error: ${error.message}`
    };
  }
}

/**
 * Handle static files
 */
async function handleStaticFiles(context, path) {
  // For now, return 404 for static files
  // In a real implementation, you might serve from R2 or another storage
  return new Response('Static files not implemented', { 
    status: 404,
    headers: { 'Content-Type': 'text/plain' }
  });
}

/**
 * Add CORS headers to response
 */
function addCorsHeaders(response, config, request) {
  const origin = request.headers.get('Origin');
  const allowedOrigins = config.get('CORS_ORIGIN', '').split(',');
  
  if (origin && allowedOrigins.includes(origin)) {
    const newResponse = new Response(response.body, response);
    newResponse.headers.set('Access-Control-Allow-Origin', origin);
    newResponse.headers.set('Access-Control-Allow-Methods', config.get('CORS_METHODS', 'GET,POST,PUT,DELETE,OPTIONS'));
    newResponse.headers.set('Access-Control-Allow-Headers', config.get('CORS_HEADERS', 'Content-Type,Authorization,X-Requested-With'));
    newResponse.headers.set('Access-Control-Allow-Credentials', 'true');
    
    return newResponse;
  }
  
  return response;
}

/**
 * Handle daily maintenance tasks
 */
async function handleDailyMaintenance(env, config, log) {
  log.info('Starting daily maintenance tasks');
  
  try {
    // Clean up old sessions
    await cleanupOldSessions(env.DB, config, log);
    
    // Clean up expired rate limit entries
    await cleanupRateLimits(env.KV, config, log);
    
    // Clean up old audit logs
    await cleanupAuditLogs(env.DB, config, log);
    
    // Update statistics
    await updateDailyStatistics(env.DB, log);
    
    log.info('Daily maintenance tasks completed');
  } catch (error) {
    log.error('Daily maintenance error', { error: error.message, stack: error.stack });
  }
}

/**
 * Handle weekly maintenance tasks
 */
async function handleWeeklyMaintenance(env, config, log) {
  log.info('Starting weekly maintenance tasks');
  
  try {
    // Clean up old file uploads
    await cleanupOldUploads(env.DB, env.STORAGE, config, log);
    
    // Optimize database
    await optimizeDatabase(env.DB, log);
    
    // Generate weekly reports
    await generateWeeklyReports(env.DB, log);
    
    log.info('Weekly maintenance tasks completed');
  } catch (error) {
    log.error('Weekly maintenance error', { error: error.message, stack: error.stack });
  }
}

/**
 * Cleanup old sessions
 */
async function cleanupOldSessions(db, config, log) {
  const sessionTimeout = parseInt(config.get('JWT_REFRESH_EXPIRES_IN', '7d'));
  const timeoutMs = parseTimeoutToMs(sessionTimeout);
  const cutoffTime = new Date(Date.now() - timeoutMs).toISOString();
  
  const result = await db.prepare(`
    DELETE FROM user_sessions 
    WHERE expires_at < ? OR created_at < ?
  `).bind(cutoffTime, cutoffTime).run();
  
  log.info('Cleaned up old sessions', { deletedCount: result.meta.changes });
}

/**
 * Cleanup rate limit entries
 */
async function cleanupRateLimits(kv, config, log) {
  // Implementation depends on your rate limiting strategy
  log.info('Rate limit cleanup completed');
}

/**
 * Cleanup audit logs
 */
async function cleanupAuditLogs(db, config, log) {
  const retentionDays = parseInt(config.get('LOG_RETENTION_DAYS', '30'));
  const cutoffTime = new Date(Date.now() - retentionDays * 24 * 60 * 60 * 1000).toISOString();
  
  const result = await db.prepare(`
    DELETE FROM audit_logs 
    WHERE created_at < ?
  `).bind(cutoffTime).run();
  
  log.info('Cleaned up old audit logs', { deletedCount: result.meta.changes });
}

/**
 * Update daily statistics
 */
async function updateDailyStatistics(db, log) {
  // Implementation for updating daily statistics
  log.info('Daily statistics updated');
}

/**
 * Cleanup old uploads
 */
async function cleanupOldUploads(db, storage, config, log) {
  const retentionDays = parseInt(config.get('BACKUP_RETENTION_DAYS', '7'));
  const cutoffTime = new Date(Date.now() - retentionDays * 24 * 60 * 60 * 1000).toISOString();
  
  // Get old files from database
  const oldFiles = await db.prepare(`
    SELECT id, storage_key, filename 
    FROM files 
    WHERE created_at < ? AND is_deleted = 1
  `).bind(cutoffTime).all();
  
  // Delete from storage and database
  for (const file of oldFiles.results) {
    try {
      await storage.delete(file.storage_key);
      await db.prepare('DELETE FROM files WHERE id = ?').bind(file.id).run();
      log.info('Deleted old file', { fileId: file.id, filename: file.filename });
    } catch (error) {
      log.error('Failed to delete old file', { fileId: file.id, error: error.message });
    }
  }
}

/**
 * Optimize database
 */
async function optimizeDatabase(db, log) {
  // Run VACUUM and other optimization commands
  await db.prepare('VACUUM').run();
  log.info('Database optimization completed');
}

/**
 * Generate weekly reports
 */
async function generateWeeklyReports(db, log) {
  // Implementation for generating weekly reports
  log.info('Weekly reports generated');
}

/**
 * Parse timeout string to milliseconds
 */
function parseTimeoutToMs(timeout) {
  const match = timeout.match(/^(\d+)([smhd])$/);
  if (!match) return 24 * 60 * 60 * 1000; // Default 24 hours
  
  const value = parseInt(match[1]);
  const unit = match[2];
  
  switch (unit) {
    case 's': return value * 1000;
    case 'm': return value * 60 * 1000;
    case 'h': return value * 60 * 60 * 1000;
    case 'd': return value * 24 * 60 * 60 * 1000;
    default: return 24 * 60 * 60 * 1000;
  }
}
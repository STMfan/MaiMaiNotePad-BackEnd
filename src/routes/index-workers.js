import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import { serveStatic } from 'hono/cloudflare-workers';

// Import route modules
import authRoutes from './auth-workers.js';
import knowledgeRoutes from './knowledge-workers.js';
import uploadRoutes from './upload-workers.js';
import adminRoutes from './admin-workers.js';
import analyticsRoutes from './analytics-workers.js';
import backupRoutes from './backup-workers.js';

// Import middleware
import { authMiddleware } from '../middleware/auth-workers.js';
import { requestLogger } from '../middleware/logger-workers.js';
import { errorHandler } from '../middleware/error-handler-workers.js';
import { rateLimiter } from '../middleware/rate-limiter-workers.js';
import { securityHeaders } from '../middleware/security-headers-workers.js';

// Create main router
const router = new Hono();

// Global middleware
router.use('*', cors({
  origin: ['https://maimnp.tech', 'https://www.maimnp.tech', 'http://localhost:3000'],
  credentials: true,
  allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowHeaders: ['Content-Type', 'Authorization', 'X-Requested-With', 'X-API-Key'],
  exposeHeaders: ['X-Total-Count', 'X-Page-Size', 'X-Current-Page']
}));

router.use('*', logger());
router.use('*', requestLogger);
router.use('*', securityHeaders);
router.use('*', rateLimiter({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 1000 // limit each IP to 1000 requests per windowMs
}));

// Health check endpoint
router.get('/health', (c) => {
  return c.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    environment: c.env.ENVIRONMENT || 'development',
    version: c.env.APP_VERSION || '1.0.0'
  });
});

// API documentation endpoint
router.get('/api/docs', (c) => {
  return c.json({
    name: 'MaiMaiNotePad API',
    version: '2.0.0',
    description: 'Cloudflare Workers compatible API for MaiMaiNotePad',
    endpoints: {
      auth: '/api/auth/*',
      knowledge: '/api/knowledge/*',
      upload: '/api/upload/*',
      admin: '/api/admin/*',
      analytics: '/api/analytics/*',
      backup: '/api/backup/*'
    },
    documentation: 'https://docs.maimnp.tech'
  });
});

// Mount route modules
router.route('/api/auth', authRoutes);
router.route('/api/knowledge', knowledgeRoutes);
router.route('/api/upload', uploadRoutes);
router.route('/api/admin', adminRoutes);
router.route('/api/analytics', analyticsRoutes);
router.route('/api/backup', backupRoutes);

// Protected user profile endpoint
router.get('/api/profile', authMiddleware, (c) => {
  return c.json({
    user: c.get('user'),
    message: 'User profile retrieved successfully'
  });
});

// System status endpoint (admin only)
router.get('/api/system/status', authMiddleware, async (c) => {
  const user = c.get('user');
  
  if (user.role !== 'admin') {
    return c.json({ error: 'Access denied' }, 403);
  }

  try {
    const db = c.env.DB;
    const storage = c.env.MAIMAI_STORAGE;
    const kv = c.env.MAIMAI_KV;

    // Get database statistics
    const userCount = await db.prepare('SELECT COUNT(*) as count FROM users').first();
    const knowledgeCount = await db.prepare('SELECT COUNT(*) as count FROM knowledge').first();
    const sessionCount = await db.prepare('SELECT COUNT(*) as count FROM sessions WHERE expires_at > ?')
      .bind(new Date().toISOString()).first();

    // Get storage statistics
    const storageStats = await storage.list({ limit: 1000 });
    const totalStorageObjects = storageStats.objects?.length || 0;
    const totalStorageSize = storageStats.objects?.reduce((sum, obj) => sum + (obj.size || 0), 0) || 0;

    // Get KV statistics
    const kvKeys = await kv.list({ limit: 1000 });
    const totalKVKeys = kvKeys.keys?.length || 0;

    return c.json({
      database: {
        users: userCount?.count || 0,
        knowledge: knowledgeCount?.count || 0,
        activeSessions: sessionCount?.count || 0
      },
      storage: {
        objects: totalStorageObjects,
        totalSize: totalStorageSize,
        humanReadableSize: formatBytes(totalStorageSize)
      },
      kvStore: {
        keys: totalKVKeys
      },
      environment: c.env.ENVIRONMENT || 'development',
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('System status error:', error);
    return c.json({ error: 'Failed to retrieve system status' }, 500);
  }
});

// Error handling middleware (must be last)
router.use('*', errorHandler);

// 404 handler
router.notFound((c) => {
  return c.json({ error: 'Endpoint not found', path: c.req.path }, 404);
});

// Utility function to format bytes
function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

export default router;
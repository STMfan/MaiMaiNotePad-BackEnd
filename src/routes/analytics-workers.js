import { Hono } from 'hono';
import { authMiddleware, requireRole } from '../middleware/auth-workers.js';

const analytics = new Hono();

// Apply authentication to all analytics routes
analytics.use('*', authMiddleware);

// Get user analytics
analytics.get('/user/overview', async (c) => {
  try {
    const user = c.get('user');
    const days = parseInt(c.req.query('days')) || 30;
    
    // Get user activity data from KV store
    const userKey = `analytics:user:${user.userId}`;
    const userAnalytics = await c.env.MAIMAI_KV.get(userKey, 'json') || {
      totalLogins: 0,
      lastLogin: null,
      knowledgeCreated: 0,
      knowledgeUpdated: 0,
      filesUploaded: 0,
      totalStorageUsed: 0
    };
    
    // Get recent activity (last N days)
    const recentActivity = await getRecentUserActivity(c.env.DB, user.userId, days);
    
    return c.json({
      overview: userAnalytics,
      recentActivity,
      period: days
    });
    
  } catch (error) {
    console.error('Get user analytics error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

analytics.get('/user/activity', async (c) => {
  try {
    const user = c.get('user');
    const days = parseInt(c.req.query('days')) || 7;
    const granularity = c.req.query('granularity') || 'daily'; // daily, hourly
    
    if (days > 90) {
      return c.json({ error: 'Maximum period is 90 days' }, 400);
    }
    
    const activityData = await getUserActivityTimeline(c.env.DB, user.userId, days, granularity);
    
    return c.json({
      activity: activityData,
      period: days,
      granularity
    });
    
  } catch (error) {
    console.error('Get user activity analytics error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Get knowledge analytics
analytics.get('/knowledge/overview', async (c) => {
  try {
    const user = c.get('user');
    const days = parseInt(c.req.query('days')) || 30;
    
    const knowledgeKey = `analytics:knowledge:${user.userId}`;
    const knowledgeAnalytics = await c.env.MAIMAI_KV.get(knowledgeKey, 'json') || {
      totalItems: 0,
      publicItems: 0,
      privateItems: 0,
      categories: {},
      tags: {},
      totalViews: 0,
      averageRating: 0
    };
    
    // Get detailed knowledge statistics
    const detailedStats = await getKnowledgeStats(c.env.DB, user.userId);
    
    return c.json({
      overview: knowledgeAnalytics,
      detailedStats,
      period: days
    });
    
  } catch (error) {
    console.error('Get knowledge analytics error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

analytics.get('/knowledge/popular', async (c) => {
  try {
    const user = c.get('user');
    const limit = parseInt(c.req.query('limit')) || 10;
    const period = c.req.query('period') || '30d'; // 7d, 30d, 90d, 1y
    
    if (limit > 100) {
      return c.json({ error: 'Maximum limit is 100' }, 400);
    }
    
    const popularItems = await getPopularKnowledgeItems(c.env.DB, user.userId, period, limit);
    
    return c.json({
      items: popularItems,
      period,
      limit
    });
    
  } catch (error) {
    console.error('Get popular knowledge analytics error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Get storage analytics
analytics.get('/storage/overview', async (c) => {
  try {
    const user = c.get('user');
    
    const storageKey = `analytics:storage:${user.userId}`;
    const storageAnalytics = await c.env.MAIMAI_KV.get(storageKey, 'json') || {
      totalFiles: 0,
      totalSize: 0,
      byType: {},
      byDate: {},
      averageFileSize: 0
    };
    
    // Get current storage usage from R2
    const r2Stats = await getUserStorageStats(c.env.MAIMAI_STORAGE, user.userId);
    
    return c.json({
      overview: storageAnalytics,
      currentUsage: r2Stats,
      userId: user.userId
    });
    
  } catch (error) {
    console.error('Get storage analytics error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Get search analytics
analytics.get('/search/overview', async (c) => {
  try {
    const user = c.get('user');
    const days = parseInt(c.req.query('days')) || 30;
    
    const searchKey = `analytics:search:${user.userId}`;
    const searchAnalytics = await c.env.MAIMAI_KV.get(searchKey, 'json') || {
      totalSearches: 0,
      successfulSearches: 0,
      averageResults: 0,
      topQueries: [],
      searchHistory: []
    };
    
    return c.json({
      overview: searchAnalytics,
      period: days
    });
    
  } catch (error) {
    console.error('Get search analytics error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Admin analytics (require admin role)
analytics.get('/admin/overview', requireRole('admin'), async (c) => {
  try {
    const days = parseInt(c.req.query('days')) || 30;
    
    // Get system-wide analytics
    const systemKey = 'analytics:system';
    const systemAnalytics = await c.env.MAIMAI_KV.get(systemKey, 'json') || {
      totalUsers: 0,
      totalKnowledge: 0,
      totalStorage: 0,
      totalBandwidth: 0,
      activeUsers: 0,
      newUsers: 0
    };
    
    // Get detailed admin statistics
    const adminStats = await getAdminStats(c.env.DB, days);
    
    return c.json({
      system: systemAnalytics,
      detailedStats: adminStats,
      period: days
    });
    
  } catch (error) {
    console.error('Get admin analytics error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

analytics.get('/admin/users', requireRole('admin'), async (c) => {
  try {
    const days = parseInt(c.req.query('days')) || 30;
    const metric = c.req.query('metric') || 'growth'; // growth, activity, retention
    
    const userAnalytics = await getUserAnalytics(c.env.DB, days, metric);
    
    return c.json({
      users: userAnalytics,
      period: days,
      metric
    });
    
  } catch (error) {
    console.error('Get admin user analytics error:', error);
    return c.json({ error: 'Internal server error' }, 500;
  }
});

analytics.get('/admin/content', requireRole('admin'), async (c) => {
  try {
    const days = parseInt(c.req.query('days')) || 30;
    
    const contentAnalytics = await getContentAnalytics(c.env.DB, days);
    
    return c.json({
      content: contentAnalytics,
      period: days
    });
    
  } catch (error) {
    console.error('Get admin content analytics error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

analytics.get('/admin/performance', requireRole('admin'), async (c) => {
  try {
    const hours = parseInt(c.req.query('hours')) || 24;
    
    if (hours > 168) { // 7 days max
      return c.json({ error: 'Maximum period is 7 days' }, 400);
    }
    
    const performanceData = await getPerformanceAnalytics(c.env.MAIMAI_KV, hours);
    
    return c.json({
      performance: performanceData,
      period: hours
    });
    
  } catch (error) {
    console.error('Get admin performance analytics error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Helper functions
async function getRecentUserActivity(db, userId, days) {
  try {
    const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
    
    // Get knowledge activity
    const knowledgeStmt = db.prepare(`
      SELECT 
        COUNT(*) as knowledge_created,
        MAX(created_at) as last_created
      FROM knowledge 
      WHERE user_id = ? AND created_at > ?
    `);
    const knowledgeResult = await knowledgeStmt.bind(userId, since).first();
    
    // Get file upload activity (from KV store)
    const uploadsKey = `analytics:uploads:${userId}:${new Date().toISOString().slice(0, 7)}`;
    const uploadsData = await c.env.MAIMAI_KV.get(uploadsKey, 'json') || { count: 0, totalSize: 0 };
    
    return {
      knowledgeCreated: knowledgeResult?.knowledge_created || 0,
      lastKnowledgeCreated: knowledgeResult?.last_created,
      filesUploaded: uploadsData.count,
      totalUploadSize: uploadsData.totalSize
    };
    
  } catch (error) {
    console.error('Get recent user activity error:', error);
    return {
      knowledgeCreated: 0,
      lastKnowledgeCreated: null,
      filesUploaded: 0,
      totalUploadSize: 0
    };
  }
}

async function getUserActivityTimeline(db, userId, days, granularity) {
  try {
    const timeline = [];
    const now = new Date();
    
    for (let i = 0; i < days; i++) {
      const date = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
      const dateStr = date.toISOString().slice(0, 10);
      
      // Get activity for this day
      const dayKey = `analytics:activity:${userId}:${dateStr}`;
      const dayData = await c.env.MAIMAI_KV.get(dayKey, 'json') || {
        logins: 0,
        knowledgeCreated: 0,
        knowledgeUpdated: 0,
        filesUploaded: 0
      };
      
      timeline.push({
        date: dateStr,
        ...dayData
      });
    }
    
    return timeline.reverse();
    
  } catch (error) {
    console.error('Get user activity timeline error:', error);
    return [];
  }
}

async function getKnowledgeStats(db, userId) {
  try {
    // Get knowledge statistics
    const statsStmt = db.prepare(`
      SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN is_public = 1 THEN 1 ELSE 0 END) as public,
        SUM(CASE WHEN is_public = 0 THEN 1 ELSE 0 END) as private,
        COUNT(DISTINCT category) as categories,
        AVG(LENGTH(content)) as avg_content_length,
        SUM(views) as total_views
      FROM knowledge 
      WHERE user_id = ?
    `);
    const stats = await statsStmt.bind(userId).first();
    
    // Get category breakdown
    const categoryStmt = db.prepare(`
      SELECT category, COUNT(*) as count
      FROM knowledge 
      WHERE user_id = ? AND category IS NOT NULL
      GROUP BY category
      ORDER BY count DESC
    `);
    const categories = await categoryStmt.bind(userId).all();
    
    return {
      total: stats?.total || 0,
      public: stats?.public || 0,
      private: stats?.private || 0,
      categories: categories?.results || [],
      averageContentLength: stats?.avg_content_length || 0,
      totalViews: stats?.total_views || 0
    };
    
  } catch (error) {
    console.error('Get knowledge stats error:', error);
    return {
      total: 0,
      public: 0,
      private: 0,
      categories: [],
      averageContentLength: 0,
      totalViews: 0
    };
  }
}

async function getPopularKnowledgeItems(db, userId, period, limit) {
  try {
    let dateFilter = '';
    const now = new Date();
    
    switch (period) {
      case '7d':
        dateFilter = `AND created_at > '${new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString()}'`;
        break;
      case '30d':
        dateFilter = `AND created_at > '${new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString()}'`;
        break;
      case '90d':
        dateFilter = `AND created_at > '${new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000).toISOString()}'`;
        break;
      case '1y':
        dateFilter = `AND created_at > '${new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000).toISOString()}'`;
        break;
    }
    
    const stmt = db.prepare(`
      SELECT id, title, category, views, created_at
      FROM knowledge 
      WHERE user_id = ? ${dateFilter}
      ORDER BY views DESC
      LIMIT ?
    `);
    const items = await stmt.bind(userId, limit).all();
    
    return items?.results || [];
    
  } catch (error) {
    console.error('Get popular knowledge items error:', error);
    return [];
  }
}

async function getUserStorageStats(storage, userId) {
  try {
    // List objects for this user (assuming user ID prefix)
    const listResult = await storage.list({ prefix: `user_${userId}/` });
    
    let totalObjects = 0;
    let totalSize = 0;
    const byType = {};
    
    if (listResult.objects) {
      totalObjects = listResult.objects.length;
      
      listResult.objects.forEach(obj => {
        totalSize += obj.size || 0;
        
        // Count by file type
        const extension = obj.key.split('.').pop().toLowerCase();
        byType[extension] = (byType[extension] || 0) + 1;
      });
    }
    
    return {
      totalObjects,
      totalSize,
      byType,
      averageSize: totalObjects > 0 ? Math.round(totalSize / totalObjects) : 0
    };
    
  } catch (error) {
    console.error('Get user storage stats error:', error);
    return {
      totalObjects: 0,
      totalSize: 0,
      byType: {},
      averageSize: 0
    };
  }
}

async function getAdminStats(db, days) {
  try {
    const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
    
    // Get new users
    const newUsersStmt = db.prepare(`
      SELECT COUNT(*) as count
      FROM users 
      WHERE created_at > ?
    `);
    const newUsers = await newUsersStmt.bind(since).first();
    
    // Get new knowledge items
    const newKnowledgeStmt = db.prepare(`
      SELECT COUNT(*) as count
      FROM knowledge 
      WHERE created_at > ?
    `);
    const newKnowledge = await newKnowledgeStmt.bind(since).first();
    
    // Get active users (users who logged in recently)
    const activeUsersStmt = db.prepare(`
      SELECT COUNT(*) as count
      FROM users 
      WHERE last_login_at > ?
    `);
    const activeUsers = await activeUsersStmt.bind(since).first();
    
    return {
      newUsers: newUsers?.count || 0,
      newKnowledge: newKnowledge?.count || 0,
      activeUsers: activeUsers?.count || 0
    };
    
  } catch (error) {
    console.error('Get admin stats error:', error);
    return {
      newUsers: 0,
      newKnowledge: 0,
      activeUsers: 0
    };
  }
}

async function getUserAnalytics(db, days, metric) {
  try {
    const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
    
    let result = {};
    
    switch (metric) {
      case 'growth':
        const growthStmt = db.prepare(`
          SELECT 
            DATE(created_at) as date,
            COUNT(*) as count
          FROM users 
          WHERE created_at > ?
          GROUP BY DATE(created_at)
          ORDER BY date
        `);
        result = await growthStmt.bind(since).all();
        break;
        
      case 'activity':
        const activityStmt = db.prepare(`
          SELECT 
            DATE(last_login_at) as date,
            COUNT(*) as count
          FROM users 
          WHERE last_login_at > ?
          GROUP BY DATE(last_login_at)
          ORDER BY date
        `);
        result = await activityStmt.bind(since).all();
        break;
        
      case 'retention':
        // Simplified retention calculation
        const retentionStmt = db.prepare(`
          SELECT 
            COUNT(*) as total_users,
            SUM(CASE WHEN last_login_at > ? THEN 1 ELSE 0 END) as active_users
          FROM users
        `);
        result = await retentionStmt.bind(since).first();
        break;
    }
    
    return result || {};
    
  } catch (error) {
    console.error('Get user analytics error:', error);
    return {};
  }
}

async function getContentAnalytics(db, days) {
  try {
    const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
    
    // Get content creation trends
    const contentTrendsStmt = db.prepare(`
      SELECT 
        DATE(created_at) as date,
        COUNT(*) as total,
        SUM(CASE WHEN is_public = 1 THEN 1 ELSE 0 END) as public
      FROM knowledge 
      WHERE created_at > ?
      GROUP BY DATE(created_at)
      ORDER BY date
    `);
    const contentTrends = await contentTrendsStmt.bind(since).all();
    
    // Get category distribution
    const categoryStmt = db.prepare(`
      SELECT category, COUNT(*) as count
      FROM knowledge 
      WHERE created_at > ? AND category IS NOT NULL
      GROUP BY category
      ORDER BY count DESC
    `);
    const categories = await categoryStmt.bind(since).all();
    
    return {
      trends: contentTrends?.results || [],
      categories: categories?.results || []
    };
    
  } catch (error) {
    console.error('Get content analytics error:', error);
    return {
      trends: [],
      categories: []
    };
  }
}

async function getPerformanceAnalytics(kv, hours) {
  try {
    const performanceData = [];
    const now = new Date();
    
    for (let i = 0; i < hours; i++) {
      const hour = new Date(now.getTime() - i * 60 * 60 * 1000);
      const hourKey = `analytics:performance:${hour.toISOString().slice(0, 13)}`;
      
      const hourData = await kv.get(hourKey, 'json') || {
        requests: 0,
        errors: 0,
        averageResponseTime: 0,
        peakResponseTime: 0
      };
      
      performanceData.push({
        hour: hour.toISOString().slice(0, 13),
        ...hourData
      });
    }
    
    return performanceData.reverse();
    
  } catch (error) {
    console.error('Get performance analytics error:', error);
    return [];
  }
}

export default analytics;
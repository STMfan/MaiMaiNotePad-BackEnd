import { Hono } from 'hono';
import { KnowledgeModel } from '../database/models/knowledge-model.js';
import { authMiddleware } from '../middleware/auth-workers.js';
import { validateKnowledgeItem } from '../utils/validators.js';

const knowledge = new Hono();

// Get all knowledge items with pagination and filtering
knowledge.get('/', optionalAuthMiddleware, async (c) => {
  try {
    const page = parseInt(c.req.query('page')) || 1;
    const limit = parseInt(c.req.query('limit')) || 20;
    const search = c.req.query('search');
    const category = c.req.query('category');
    const tags = c.req.query('tags');
    const isPublic = c.req.query('public') === 'true';
    const sortBy = c.req.query('sortBy') || 'created_at';
    const sortOrder = c.req.query('sortOrder') || 'desc';
    
    const knowledgeModel = new KnowledgeModel(c.env.DB);
    
    const filters = {
      search,
      category,
      tags: tags ? tags.split(',').map(tag => tag.trim()) : undefined,
      isPublic: isPublic || !c.get('user'), // If no auth, only show public items
      userId: c.get('user')?.userId
    };
    
    const result = await knowledgeModel.findAll({
      page,
      limit,
      filters,
      sortBy,
      sortOrder
    });
    
    // Add pagination headers
    c.header('X-Total-Count', result.total.toString());
    c.header('X-Page-Size', limit.toString());
    c.header('X-Current-Page', page.toString());
    c.header('X-Total-Pages', Math.ceil(result.total / limit).toString());
    
    return c.json({
      items: result.items,
      total: result.total,
      page,
      limit,
      totalPages: Math.ceil(result.total / limit)
    });
    
  } catch (error) {
    console.error('Get knowledge items error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Get single knowledge item
knowledge.get('/:id', optionalAuthMiddleware, async (c) => {
  try {
    const { id } = c.req.param();
    const knowledgeModel = new KnowledgeModel(c.env.DB);
    
    const item = await knowledgeModel.findById(id);
    if (!item) {
      return c.json({ error: 'Knowledge item not found' }, 404);
    }
    
    // Check permissions
    const user = c.get('user');
    if (!item.is_public && (!user || (item.user_id !== user.userId && user.role !== 'admin'))) {
      return c.json({ error: 'Access denied' }, 403);
    }
    
    // Increment view count
    await knowledgeModel.incrementViews(id);
    
    return c.json({ item });
    
  } catch (error) {
    console.error('Get knowledge item error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Create new knowledge item
knowledge.post('/', authMiddleware, async (c) => {
  try {
    const user = c.get('user');
    const data = await c.req.json();
    
    // Validate input
    const validation = validateKnowledgeItem(data);
    if (!validation.isValid) {
      return c.json({ error: validation.errors }, 400);
    }
    
    const knowledgeModel = new KnowledgeModel(c.env.DB);
    
    const item = await knowledgeModel.create({
      ...data,
      user_id: user.userId,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });
    
    return c.json({
      message: 'Knowledge item created successfully',
      item
    }, 201);
    
  } catch (error) {
    console.error('Create knowledge item error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Update knowledge item
knowledge.put('/:id', authMiddleware, async (c) => {
  try {
    const { id } = c.req.param();
    const user = c.get('user');
    const updates = await c.req.json();
    
    const knowledgeModel = new KnowledgeModel(c.env.DB);
    const existingItem = await knowledgeModel.findById(id);
    
    if (!existingItem) {
      return c.json({ error: 'Knowledge item not found' }, 404);
    }
    
    // Check permissions
    if (existingItem.user_id !== user.userId && user.role !== 'admin') {
      return c.json({ error: 'Access denied' }, 403);
    }
    
    // Validate updates
    const validation = validateKnowledgeItem(updates, true); // true for update validation
    if (!validation.isValid) {
      return c.json({ error: validation.errors }, 400);
    }
    
    const updatedItem = await knowledgeModel.update(id, {
      ...updates,
      updated_at: new Date().toISOString()
    });
    
    return c.json({
      message: 'Knowledge item updated successfully',
      item: updatedItem
    });
    
  } catch (error) {
    console.error('Update knowledge item error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Delete knowledge item
knowledge.delete('/:id', authMiddleware, async (c) => {
  try {
    const { id } = c.req.param();
    const user = c.get('user');
    
    const knowledgeModel = new KnowledgeModel(c.env.DB);
    const existingItem = await knowledgeModel.findById(id);
    
    if (!existingItem) {
      return c.json({ error: 'Knowledge item not found' }, 404);
    }
    
    // Check permissions
    if (existingItem.user_id !== user.userId && user.role !== 'admin') {
      return c.json({ error: 'Access denied' }, 403);
    }
    
    await knowledgeModel.delete(id);
    
    return c.json({ message: 'Knowledge item deleted successfully' });
    
  } catch (error) {
    console.error('Delete knowledge item error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Get user's knowledge items
knowledge.get('/user/my-items', authMiddleware, async (c) => {
  try {
    const user = c.get('user');
    const page = parseInt(c.req.query('page')) || 1;
    const limit = parseInt(c.req.query('limit')) || 20;
    const search = c.req.query('search');
    const category = c.req.query('category');
    const isPublic = c.req.query('public');
    
    const knowledgeModel = new KnowledgeModel(c.env.DB);
    
    const filters = {
      userId: user.userId,
      search,
      category,
      isPublic: isPublic === 'true' ? true : isPublic === 'false' ? false : undefined
    };
    
    const result = await knowledgeModel.findAll({
      page,
      limit,
      filters
    });
    
    return c.json({
      items: result.items,
      total: result.total,
      page,
      limit,
      totalPages: Math.ceil(result.total / limit)
    });
    
  } catch (error) {
    console.error('Get user knowledge items error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Get knowledge categories
knowledge.get('/categories/list', async (c) => {
  try {
    const knowledgeModel = new KnowledgeModel(c.env.DB);
    const categories = await knowledgeModel.getCategories();
    
    return c.json({ categories });
    
  } catch (error) {
    console.error('Get categories error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Get knowledge tags
knowledge.get('/tags/list', async (c) => {
  try {
    const knowledgeModel = new KnowledgeModel(c.env.DB);
    const tags = await knowledgeModel.getTags();
    
    return c.json({ tags });
    
  } catch (error) {
    console.error('Get tags error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Search knowledge items
knowledge.get('/search/advanced', optionalAuthMiddleware, async (c) => {
  try {
    const query = c.req.query('q');
    const category = c.req.query('category');
    const tags = c.req.query('tags');
    const dateFrom = c.req.query('dateFrom');
    const dateTo = c.req.query('dateTo');
    const isPublic = c.req.query('public') === 'true';
    const page = parseInt(c.req.query('page')) || 1;
    const limit = parseInt(c.req.query('limit')) || 20;
    
    if (!query || query.trim().length < 2) {
      return c.json({ error: 'Search query must be at least 2 characters' }, 400);
    }
    
    const knowledgeModel = new KnowledgeModel(c.env.DB);
    
    const filters = {
      search: query.trim(),
      category,
      tags: tags ? tags.split(',').map(tag => tag.trim()) : undefined,
      dateFrom: dateFrom ? new Date(dateFrom).toISOString() : undefined,
      dateTo: dateTo ? new Date(dateTo).toISOString() : undefined,
      isPublic: isPublic || !c.get('user'), // If no auth, only show public items
      userId: c.get('user')?.userId
    };
    
    const result = await knowledgeModel.searchAdvanced({
      page,
      limit,
      filters
    });
    
    return c.json({
      items: result.items,
      total: result.total,
      page,
      limit,
      totalPages: Math.ceil(result.total / limit),
      searchQuery: query
    });
    
  } catch (error) {
    console.error('Advanced search error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Get knowledge statistics
knowledge.get('/stats/overview', optionalAuthMiddleware, async (c) => {
  try {
    const knowledgeModel = new KnowledgeModel(c.env.DB);
    
    const user = c.get('user');
    const userId = user?.userId;
    const isAdmin = user?.role === 'admin';
    
    const stats = await knowledgeModel.getStats({
      userId: !isAdmin ? userId : undefined,
      includeSystemStats: isAdmin
    });
    
    return c.json({ stats });
    
  } catch (error) {
    console.error('Get knowledge stats error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Export knowledge items
knowledge.get('/export/data', authMiddleware, async (c) => {
  try {
    const format = c.req.query('format') || 'json';
    const user = c.get('user');
    const userId = user.role === 'admin' ? undefined : user.userId;
    
    const knowledgeModel = new KnowledgeModel(c.env.DB);
    const items = await knowledgeModel.exportData({ userId });
    
    if (format === 'csv') {
      // Convert to CSV format
      const csv = convertToCSV(items);
      c.header('Content-Type', 'text/csv');
      c.header('Content-Disposition', 'attachment; filename="knowledge_export.csv"');
      return c.text(csv);
    } else {
      // Default JSON format
      c.header('Content-Type', 'application/json');
      c.header('Content-Disposition', 'attachment; filename="knowledge_export.json"');
      return c.json({ items, exportedAt: new Date().toISOString() });
    }
    
  } catch (error) {
    console.error('Export knowledge data error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Import knowledge items
knowledge.post('/import/data', authMiddleware, async (c) => {
  try {
    const user = c.get('user');
    const data = await c.req.json();
    
    if (!data.items || !Array.isArray(data.items)) {
      return c.json({ error: 'Invalid import data format' }, 400);
    }
    
    const knowledgeModel = new KnowledgeModel(c.env.DB);
    const result = await knowledgeModel.importData({
      items: data.items,
      userId: user.userId
    });
    
    return c.json({
      message: 'Knowledge items imported successfully',
      imported: result.imported,
      skipped: result.skipped,
      errors: result.errors
    });
    
  } catch (error) {
    console.error('Import knowledge data error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Helper function to convert data to CSV
function convertToCSV(items) {
  if (!items || items.length === 0) return '';
  
  const headers = ['id', 'title', 'content', 'category', 'tags', 'is_public', 'created_at', 'updated_at'];
  const csvRows = [headers.join(',')];
  
  items.forEach(item => {
    const row = [
      item.id,
      `"${(item.title || '').replace(/"/g, '""')}"`,
      `"${(item.content || '').replace(/"/g, '""')}"`,
      item.category || '',
      item.tags ? `"${item.tags.join(';')}"` : '',
      item.is_public ? 'true' : 'false',
      item.created_at || '',
      item.updated_at || ''
    ];
    csvRows.push(row.join(','));
  });
  
  return csvRows.join('\n');
}

// Helper middleware for optional authentication
async function optionalAuthMiddleware(c, next) {
  try {
    const token = c.req.header('Authorization')?.replace('Bearer ', '');
    
    if (token) {
      const { verify } = await import('hono/jwt');
      const payload = await verify(token, c.env.JWT_SECRET);
      c.set('user', payload);
    }
  } catch (error) {
    // Invalid token, continue without user
  }
  
  await next();
}

export default knowledge;
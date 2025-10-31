import { Hono } from 'hono';
import { UserModel } from '../database/models/user-model.js';
import { KnowledgeModel } from '../database/models/knowledge-model.js';
import { authMiddleware } from '../middleware/auth-workers.js';
import { requireRole } from '../middleware/auth-workers.js';

const admin = new Hono();

// Apply authentication and admin role requirement to all admin routes
admin.use('*', authMiddleware);
admin.use('*', requireRole('admin'));

// User management endpoints
admin.get('/users', async (c) => {
  try {
    const page = parseInt(c.req.query('page')) || 1;
    const limit = parseInt(c.req.query('limit')) || 20;
    const search = c.req.query('search');
    const role = c.req.query('role');
    const isActive = c.req.query('isActive');
    const sortBy = c.req.query('sortBy') || 'created_at';
    const sortOrder = c.req.query('sortOrder') || 'desc';

    const userModel = new UserModel(c.env.DB);

    const filters = {
      search,
      role,
      isActive: isActive === 'true' ? true : isActive === 'false' ? false : undefined
    };

    const result = await userModel.findAll({
      page,
      limit,
      filters,
      sortBy,
      sortOrder
    });

    // Remove passwords from response
    const users = result.items.map(user => {
      const { password, ...userWithoutPassword } = user;
      return userWithoutPassword;
    });

    return c.json({
      users,
      total: result.total,
      page,
      limit,
      totalPages: Math.ceil(result.total / limit)
    });

  } catch (error) {
    console.error('Get users error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

admin.get('/users/:id', async (c) => {
  try {
    const { id } = c.req.param();
    const userModel = new UserModel(c.env.DB);

    const user = await userModel.findById(id);
    if (!user) {
      return c.json({ error: 'User not found' }, 404);
    }

    // Remove password from response
    const { password, ...userWithoutPassword } = user;

    return c.json({ user: userWithoutPassword });

  } catch (error) {
    console.error('Get user error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

admin.put('/users/:id', async (c) => {
  try {
    const { id } = c.req.param();
    const updates = await c.req.json();

    // Remove protected fields that shouldn't be updated directly
    delete updates.id;
    delete updates.password;
    delete updates.created_at;

    const userModel = new UserModel(c.env.DB);

    const updatedUser = await userModel.update(id, {
      ...updates,
      updated_at: new Date().toISOString()
    });

    if (!updatedUser) {
      return c.json({ error: 'User not found' }, 404);
    }

    // Remove password from response
    const { password, ...userWithoutPassword } = updatedUser;

    return c.json({
      message: 'User updated successfully',
      user: userWithoutPassword
    });

  } catch (error) {
    console.error('Update user error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

admin.put('/users/:id/status', async (c) => {
  try {
    const { id } = c.req.param();
    const { isActive } = await c.req.json();

    if (typeof isActive !== 'boolean') {
      return c.json({ error: 'isActive must be a boolean' }, 400);
    }

    const userModel = new UserModel(c.env.DB);

    const updatedUser = await userModel.update(id, {
      is_active: isActive,
      updated_at: new Date().toISOString()
    });

    if (!updatedUser) {
      return c.json({ error: 'User not found' }, 404);
    }

    return c.json({
      message: `User ${isActive ? 'activated' : 'deactivated'} successfully`,
      user: { id: updatedUser.id, is_active: updatedUser.is_active }
    });

  } catch (error) {
    console.error('Update user status error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

admin.put('/users/:id/role', async (c) => {
  try {
    const { id } = c.req.param();
    const { role } = await c.req.json();

    const validRoles = ['user', 'admin', 'moderator'];
    if (!validRoles.includes(role)) {
      return c.json({ error: 'Invalid role' }, 400);
    }

    // Prevent changing your own role
    const currentUser = c.get('user');
    if (id === currentUser.userId) {
      return c.json({ error: 'Cannot change your own role' }, 400);
    }

    const userModel = new UserModel(c.env.DB);

    const updatedUser = await userModel.update(id, {
      role,
      updated_at: new Date().toISOString()
    });

    if (!updatedUser) {
      return c.json({ error: 'User not found' }, 404);
    }

    return c.json({
      message: 'User role updated successfully',
      user: { id: updatedUser.id, role: updatedUser.role }
    });

  } catch (error) {
    console.error('Update user role error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Knowledge management endpoints
admin.get('/knowledge', async (c) => {
  try {
    const page = parseInt(c.req.query('page')) || 1;
    const limit = parseInt(c.req.query('limit')) || 20;
    const search = c.req.query('search');
    const category = c.req.query('category');
    const userId = c.req.query('userId');
    const isPublic = c.req.query('isPublic');
    const flagged = c.req.query('flagged') === 'true';

    const knowledgeModel = new KnowledgeModel(c.env.DB);

    const filters = {
      search,
      category,
      userId: userId || undefined,
      isPublic: isPublic === 'true' ? true : isPublic === 'false' ? false : undefined,
      flagged
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
    console.error('Get admin knowledge items error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

admin.put('/knowledge/:id/flag', async (c) => {
  try {
    const { id } = c.req.param();
    const { flagged, reason } = await c.req.json();

    if (typeof flagged !== 'boolean') {
      return c.json({ error: 'flagged must be a boolean' }, 400);
    }

    const knowledgeModel = new KnowledgeModel(c.env.DB);

    const updatedItem = await knowledgeModel.update(id, {
      flagged,
      flag_reason: reason || null,
      flagged_at: flagged ? new Date().toISOString() : null,
      flagged_by: flagged ? c.get('user').userId : null,
      updated_at: new Date().toISOString()
    });

    if (!updatedItem) {
      return c.json({ error: 'Knowledge item not found' }, 404);
    }

    return c.json({
      message: `Knowledge item ${flagged ? 'flagged' : 'unflagged'} successfully`,
      item: updatedItem
    });

  } catch (error) {
    console.error('Flag knowledge item error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

admin.delete('/knowledge/:id', async (c) => {
  try {
    const { id } = c.req.param();

    const knowledgeModel = new KnowledgeModel(c.env.DB);
    const existingItem = await knowledgeModel.findById(id);

    if (!existingItem) {
      return c.json({ error: 'Knowledge item not found' }, 404);
    }

    await knowledgeModel.delete(id);

    return c.json({ message: 'Knowledge item deleted successfully' });

  } catch (error) {
    console.error('Admin delete knowledge item error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// System statistics endpoints
admin.get('/stats/overview', async (c) => {
  try {
    const userModel = new UserModel(c.env.DB);
    const knowledgeModel = new KnowledgeModel(c.env.DB);

    // Get user statistics
    const totalUsers = await userModel.count();
    const activeUsers = await userModel.count({ isActive: true });
    const usersByRole = await userModel.countByRole();
    const usersByMonth = await userModel.countByMonth();

    // Get knowledge statistics
    const totalKnowledge = await knowledgeModel.count();
    const publicKnowledge = await knowledgeModel.count({ isPublic: true });
    const flaggedKnowledge = await knowledgeModel.count({ flagged: true });
    const knowledgeByCategory = await knowledgeModel.countByCategory();
    const knowledgeByMonth = await knowledgeModel.countByMonth();

    return c.json({
      users: {
        total: totalUsers,
        active: activeUsers,
        byRole: usersByRole,
        byMonth: usersByMonth
      },
      knowledge: {
        total: totalKnowledge,
        public: publicKnowledge,
        flagged: flaggedKnowledge,
        byCategory: knowledgeByCategory,
        byMonth: knowledgeByMonth
      },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Get admin stats error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

admin.get('/stats/activity', async (c) => {
  try {
    const days = parseInt(c.req.query('days')) || 30;
    const userModel = new UserModel(c.env.DB);
    const knowledgeModel = new KnowledgeModel(c.env.DB);

    const userActivity = await userModel.getActivityStats(days);
    const knowledgeActivity = await knowledgeModel.getActivityStats(days);

    return c.json({
      userActivity,
      knowledgeActivity,
      period: days
    });

  } catch (error) {
    console.error('Get activity stats error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// System configuration endpoints
admin.get('/config', async (c) => {
  try {
    // Get system configuration from KV store or environment
    const config = await c.env.MAIMAI_KV.get('system_config', 'json') || {
      siteName: 'MaiMaiNotePad',
      siteDescription: 'A knowledge management platform',
      allowRegistration: true,
      requireEmailVerification: false,
      maxKnowledgePerUser: 1000,
      maxFileSize: 10 * 1024 * 1024, // 10MB
      allowedFileTypes: ['txt', 'md', 'pdf', 'jpg', 'png', 'gif'],
      enableAnalytics: true,
      enableBackups: true,
      backupInterval: 24, // hours
      maintenanceMode: false
    };

    return c.json({ config });

  } catch (error) {
    console.error('Get system config error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

admin.put('/config', async (c) => {
  try {
    const updates = await c.req.json();

    // Get current config
    const currentConfig = await c.env.MAIMAI_KV.get('system_config', 'json') || {};

    // Merge updates
    const updatedConfig = {
      ...currentConfig,
      ...updates,
      updatedAt: new Date().toISOString(),
      updatedBy: c.get('user').userId
    };

    // Store updated config
    await c.env.MAIMAI_KV.put('system_config', JSON.stringify(updatedConfig));

    return c.json({
      message: 'System configuration updated successfully',
      config: updatedConfig
    });

  } catch (error) {
    console.error('Update system config error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

// Backup management endpoints
admin.post('/backup/create', async (c) => {
  try {
    const { type = 'full' } = await c.req.json();

    // Create backup task
    const backupTask = {
      id: crypto.randomUUID(),
      type,
      status: 'pending',
      createdAt: new Date().toISOString(),
      createdBy: c.get('user').userId
    };

    // Store backup task
    await c.env.MAIMAI_KV.put(`backup_task:${backupTask.id}`, JSON.stringify(backupTask));

    // Trigger backup process (in a real implementation, this would queue a background job)
    // For now, we'll just return the task ID

    return c.json({
      message: 'Backup task created successfully',
      taskId: backupTask.id,
      status: backupTask.status
    });

  } catch (error) {
    console.error('Create backup error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

admin.get('/backup/tasks', async (c) => {
  try {
    const limit = parseInt(c.req.query('limit')) || 50;

    // List backup tasks from KV store
    const backupList = await c.env.MAIMAI_KV.list({ prefix: 'backup_task:' });
    const tasks = [];

    for (const key of backupList.keys) {
      const taskData = await c.env.MAIMAI_KV.get(key.name, 'json');
      if (taskData) {
        tasks.push(taskData);
      }
    }

    // Sort by created date (newest first)
    tasks.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

    return c.json({
      tasks: tasks.slice(0, limit),
      total: tasks.length
    });

  } catch (error) {
    console.error('Get backup tasks error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

export default admin;

// Character card management endpoints
admin.get('/characters', async (c) => {
  try {
    const { page = 1, limit = 20, status = 'all', search } = c.req.query();

    // Import CharacterModel dynamically to avoid circular dependencies
    const CharacterModel = require('../database/models/character-model');

    const options = {
      page: parseInt(page),
      limit: Math.min(parseInt(limit), 100),
      sortBy: 'created_at',
      sortOrder: 'DESC'
    };

    // Add status filter if specified
    if (status !== 'all') {
      options.status = status;
    }

    // Add search filter if specified
    if (search) {
      options.search = search;
    }

    const result = await CharacterModel.getList(options);

    return c.json({
      success: true,
      data: result.items,
      pagination: {
        page: result.page,
        limit: options.limit,
        total: result.total,
        totalPages: result.totalPages
      }
    });

  } catch (error) {
    console.error('Get admin characters list error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

admin.get('/characters/pending', async (c) => {
  try {
    const { page = 1, limit = 20 } = c.req.query();

    const CharacterModel = require('../database/models/character-model');

    const result = await CharacterModel.getPendingList({
      page: parseInt(page),
      limit: Math.min(parseInt(limit), 100)
    });

    return c.json({
      success: true,
      data: result.items,
      pagination: {
        page: result.page,
        limit: parseInt(limit),
        total: result.total,
        totalPages: result.totalPages
      }
    });

  } catch (error) {
    console.error('Get pending characters error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

admin.get('/characters/:id', async (c) => {
  try {
    const { id } = c.req.param();

    const CharacterModel = require('../database/models/character-model');

    const character = await CharacterModel.getById(id, true); // Include private data

    if (!character) {
      return c.json({ error: 'Character not found' }, 404);
    }

    return c.json({
      success: true,
      data: character
    });

  } catch (error) {
    console.error('Get admin character detail error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

admin.put('/characters/:id/review', async (c) => {
  try {
    const { id } = c.req.param();
    const { status, review_note = '' } = await c.req.json();

    // Validate status
    if (!['approved', 'rejected'].includes(status)) {
      return c.json({ error: 'Invalid status. Must be "approved" or "rejected"' }, 400);
    }

    const CharacterModel = require('../database/models/character-model');
    const UserModel = require('../database/models/user-model');

    // Get character details
    const character = await CharacterModel.getById(id, true);
    if (!character) {
      return c.json({ error: 'Character not found' }, 404);
    }

    // Get admin user info
    const adminUser = await UserModel.findById(c.get('user').userId);

    // Update character status
    const updatedCharacter = await CharacterModel.updateStatus(
      id,
      status,
      adminUser.id,
      review_note
    );

    // Get character author info for email notification
    const author = await UserModel.findById(character.author_id);

    // Send email notification
    try {
      if (status === 'approved') {
        await emailService.sendCharacterApprovedEmail(
          author.email,
          character.name
        );
      } else if (status === 'rejected') {
        await emailService.sendCharacterRejectedEmail(
          author.email,
          character.name,
          review_note
        );
      }
    } catch (emailError) {
      console.error('Failed to send character review email:', emailError);
      // Don't fail the request if email sending fails
    }

    logger.info(`管理员 ${adminUser.username} 审核了人设卡 ${character.name}: ${status}`);

    return c.json({
      success: true,
      message: `Character ${status} successfully`,
      data: updatedCharacter
    });

  } catch (error) {
    console.error('Review character error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

admin.delete('/characters/:id', async (c) => {
  try {
    const { id } = c.req.param();

    const CharacterModel = require('../database/models/character-model');

    const character = await CharacterModel.getById(id, true);
    if (!character) {
      return c.json({ error: 'Character not found' }, 404);
    }

    // Delete character
    const deleted = await CharacterModel.delete(id);

    if (!deleted) {
      return c.json({ error: 'Failed to delete character' }, 500);
    }

    logger.info(`管理员删除了人设卡: ${character.name}`);

    return c.json({
      success: true,
      message: 'Character deleted successfully'
    });

  } catch (error) {
    console.error('Delete character error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});

admin.get('/characters/stats/overview', async (c) => {
  try {
    const CharacterModel = require('../database/models/character-model');

    // Get character statistics
    const totalCharacters = await CharacterModel.getList({ page: 1, limit: 1 });
    const pendingCharacters = await CharacterModel.getPendingList({ page: 1, limit: 1 });

    // Get categories and tag cloud
    const categories = await CharacterModel.getCategories();
    const tagCloud = await CharacterModel.getTagCloud(20);

    return c.json({
      success: true,
      stats: {
        total: totalCharacters.total,
        pending: pendingCharacters.total,
        categories: categories.length,
        tags: tagCloud.length
      },
      categories,
      tagCloud
    });

  } catch (error) {
    console.error('Get character stats error:', error);
    return c.json({ error: 'Internal server error' }, 500);
  }
});
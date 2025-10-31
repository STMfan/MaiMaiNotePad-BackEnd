/**
 * 人设卡路由处理
 * Character Card Routes
 * 
 * 处理人设卡的上传、管理、审核等业务逻辑
 */

const { Hono } = require('hono');
const { logger } = require('../../utils/logger');
const CharacterModel = require('../database/models/character-model');
const { authenticateToken } = require('../middleware/auth');
const { uploadToR2 } = require('../services/r2-storage');
const { validateCharacterData } = require('../middleware/validation');
const { emailService } = require('../services/email/email-service');

const router = new Hono();

/**
 * 获取人设卡列表
 * GET /api/characters
 * 公开接口，只返回已审核通过的人设卡
 */
router.get('/', async (c) => {
  try {
    const {
      page = 1,
      limit = 20,
      category,
      search,
      sortBy = 'created_at',
      sortOrder = 'DESC'
    } = c.req.query();

    const options = {
      page: parseInt(page),
      limit: Math.min(parseInt(limit), 100), // 最大100条
      category,
      search,
      sortBy,
      sortOrder,
      status: 'approved' // 只显示已审核通过的
    };

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
    logger.error('获取人设卡列表失败:', error);
    return c.json({
      success: false,
      error: '获取人设卡列表失败'
    }, 500);
  }
});

/**
 * 获取单个人设卡详情
 * GET /api/characters/:id
 * 公开接口，只返回已审核通过的人设卡
 */
router.get('/:id', async (c) => {
  try {
    const { id } = c.req.param();
    
    const character = await CharacterModel.getById(id, false);
    
    if (!character) {
      return c.json({
        success: false,
        error: '人设卡不存在或未通过审核'
      }, 404);
    }

    // 增加浏览次数
    await CharacterModel.incrementViewCount(id);
    
    return c.json({
      success: true,
      data: character
    });
  } catch (error) {
    logger.error('获取人设卡详情失败:', error);
    return c.json({
      success: false,
      error: '获取人设卡详情失败'
    }, 500);
  }
});

/**
 * 上传人设卡
 * POST /api/characters
 * 需要认证，用户上传新的人设卡
 */
router.post('/', authenticateToken, async (c) => {
  try {
    const userId = c.get('userId');
    const body = await c.req.json();
    
    // 验证必填字段
    const { name, description, content, category, tags, fileContent } = body;
    
    if (!name || !description || (!content && !fileContent) || !category) {
      return c.json({
        success: false,
        error: '缺少必填字段'
      }, 400);
    }

    // 如果有文件内容，优先使用文件内容
    let finalContent = content;
    if (fileContent) {
      try {
        finalContent = typeof fileContent === 'string' ? JSON.parse(fileContent) : fileContent;
      } catch (jsonError) {
        finalContent = fileContent;
      }
    }

    // 验证内容长度
    if (JSON.stringify(finalContent).length > 50000) {
      return c.json({
        success: false,
        error: '内容长度不能超过50000个字符'
      }, 400);
    }

    // 验证内容格式
    let parsedContent;
    try {
      parsedContent = typeof finalContent === 'string' ? JSON.parse(finalContent) : finalContent;
    } catch (error) {
      return c.json({
        success: false,
        error: '人设卡内容格式错误，必须是有效的JSON格式'
      }, 400);
    }

    // 创建人设卡数据
    const characterData = {
      name: name.trim(),
      description: description.trim(),
      content: JSON.stringify(parsedContent),
      author_id: userId,
      file_url: body.file_url || '',
      file_type: body.file_type || 'json',
      category: category.trim(),
      tags: Array.isArray(tags) ? tags.map(tag => tag.trim()).filter(Boolean) : []
    };

    // 保存到数据库
    const character = await CharacterModel.create(characterData);
    
    logger.info(`用户 ${userId} 上传了新的人设卡: ${character.id}`);
    
    return c.json({
      success: true,
      data: character,
      message: '人设卡上传成功，请等待审核'
    }, 201);
  } catch (error) {
    logger.error('上传人设卡失败:', error);
    return c.json({
      success: false,
      error: '上传人设卡失败'
    }, 500);
  }
});

/**
 * 更新人设卡
 * PUT /api/characters/:id
 * 需要认证，用户只能更新自己的人设卡
 */
router.put('/:id', authenticateToken, async (c) => {
  try {
    const userId = c.get('userId');
    const { id } = c.req.param();
    const body = await c.req.json();
    
    // 获取原人设卡
    const originalCharacter = await CharacterModel.getById(id, true);
    
    if (!originalCharacter) {
      return c.json({
        success: false,
        error: '人设卡不存在'
      }, 404);
    }

    // 检查权限
    if (originalCharacter.author_id !== userId) {
      return c.json({
        success: false,
        error: '没有权限更新此人设卡'
      }, 403);
    }

    // 只能更新特定字段
    const allowedUpdates = {};
    const allowedFields = ['name', 'description', 'content', 'category', 'tags'];
    
    for (const field of allowedFields) {
      if (body[field] !== undefined) {
        if (field === 'content') {
          // 验证JSON格式
          try {
            const parsedContent = typeof body[field] === 'string' 
              ? JSON.parse(body[field]) 
              : body[field];
            allowedUpdates[field] = JSON.stringify(parsedContent);
          } catch (error) {
            return c.json({
              success: false,
              error: '人设卡内容格式错误，必须是有效的JSON格式'
            }, 400);
          }
        } else if (field === 'tags') {
          allowedUpdates[field] = Array.isArray(body[field]) 
            ? body[field].map(tag => tag.trim()).filter(Boolean)
            : [];
        } else {
          allowedUpdates[field] = body[field].trim();
        }
      }
    }

    // 如果状态是已审核通过，更新后需要重新审核
    if (originalCharacter.status === 'approved') {
      allowedUpdates.status = 'pending';
    }

    const updatedCharacter = await CharacterModel.update(id, allowedUpdates);
    
    logger.info(`用户 ${userId} 更新了人设卡: ${id}`);
    
    return c.json({
      success: true,
      data: updatedCharacter,
      message: '人设卡更新成功，请等待重新审核'
    });
  } catch (error) {
    logger.error('更新人设卡失败:', error);
    return c.json({
      success: false,
      error: '更新人设卡失败'
    }, 500);
  }
});

/**
   * 删除人设卡
 * DELETE /api/characters/:id
 * 需要认证，用户只能删除自己的人设卡
 */
router.delete('/:id', authenticateToken, async (c) => {
  try {
    const userId = c.get('userId');
    const { id } = c.req.param();
    
    // 获取原人设卡
    const character = await CharacterModel.getById(id, true);
    
    if (!character) {
      return c.json({
        success: false,
        error: '人设卡不存在'
      }, 404);
    }

    // 检查权限
    if (character.author_id !== userId) {
      return c.json({
        success: false,
        error: '没有权限删除此人设卡'
      }, 403);
    }

    // 删除人设卡
    const deleted = await CharacterModel.delete(id);
    
    if (!deleted) {
      return c.json({
        success: false,
        error: '删除人设卡失败'
      }, 500);
    }

    logger.info(`用户 ${userId} 删除了人设卡: ${id}`);
    
    return c.json({
      success: true,
      message: '人设卡删除成功'
    });
  } catch (error) {
    logger.error('删除人设卡失败:', error);
    return c.json({
      success: false,
      error: '删除人设卡失败'
    }, 500);
  }
});

/**
 * 获取用户自己的人设卡列表
 * GET /api/characters/user/my
 * 需要认证
 */
router.get('/user/my', authenticateToken, async (c) => {
  try {
    const userId = c.get('userId');
    const { page = 1, limit = 20 } = c.req.query();

    const options = {
      page: parseInt(page),
      limit: Math.min(parseInt(limit), 100),
      author_id: userId,
      sortBy: 'created_at',
      sortOrder: 'DESC'
    };

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
    logger.error('获取用户人设卡列表失败:', error);
    return c.json({
      success: false,
      error: '获取用户人设卡列表失败'
    }, 500);
  }
});

/**
 * 获取用户人设卡统计
 * GET /api/characters/user/stats
 * 需要认证
 */
router.get('/user/stats', authenticateToken, async (c) => {
  try {
    const userId = c.get('userId');
    
    const stats = await CharacterModel.getUserStats(userId);
    
    return c.json({
      success: true,
      data: stats
    });
  } catch (error) {
    logger.error('获取用户人设卡统计失败:', error);
    return c.json({
      success: false,
      error: '获取用户人设卡统计失败'
    }, 500);
  }
});

/**
 * 获取分类列表
 * GET /api/characters/categories
 * 公开接口
 */
router.get('/categories', async (c) => {
  try {
    const categories = await CharacterModel.getCategories();
    
    return c.json({
      success: true,
      data: categories
    });
  } catch (error) {
    logger.error('获取人设卡分类列表失败:', error);
    return c.json({
      success: false,
      error: '获取人设卡分类列表失败'
    }, 500);
  }
});

/**
 * 获取标签云
 * GET /api/characters/tags/cloud
 * 公开接口
 */
router.get('/tags/cloud', async (c) => {
  try {
    const { limit = 50 } = c.req.query();
    const tagCloud = await CharacterModel.getTagCloud(parseInt(limit));
    
    return c.json({
      success: true,
      data: tagCloud
    });
  } catch (error) {
    logger.error('获取人设卡标签云失败:', error);
    return c.json({
      success: false,
      error: '获取人设卡标签云失败'
    }, 500);
  }
});

module.exports = router;
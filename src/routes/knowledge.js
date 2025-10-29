const express = require('express');
const router = express.Router();
const { Knowledge } = require('../models');
const { logger } = require('../middleware/logger');
const { authMiddleware } = require('../middleware/auth');
const { validateKnowledge } = require('../middleware/validation');

// 获取知识库列表
router.get('/', async (req, res) => {
  try {
    const { 
      page = 1, 
      limit = 10, 
      category, 
      tag, 
      search,
      sortBy = 'createdAt',
      order = 'desc'
    } = req.query;

    const query = {};
    
    // 分类筛选
    if (category) {
      query.category = category;
    }
    
    // 标签筛选
    if (tag) {
      query.tags = { $in: [tag] };
    }
    
    // 搜索功能
    if (search) {
      query.$or = [
        { title: { $regex: search, $options: 'i' } },
        { content: { $regex: search, $options: 'i' } },
        { description: { $regex: search, $options: 'i' } }
      ];
    }

    const skip = (page - 1) * limit;
    const sortOrder = order === 'desc' ? -1 : 1;
    
    const [knowledge, total] = await Promise.all([
      Knowledge.find(query)
        .sort({ [sortBy]: sortOrder })
        .skip(skip)
        .limit(parseInt(limit))
        .lean(),
      Knowledge.countDocuments(query)
    ]);

    res.json({
      success: true,
      data: knowledge,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total,
        pages: Math.ceil(total / limit)
      }
    });
  } catch (error) {
    logger.error('获取知识库列表失败:', error);
    res.status(500).json({
      success: false,
      message: '获取知识库列表失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 获取单个知识条目
router.get('/:id', async (req, res) => {
  try {
    const knowledge = await Knowledge.findById(req.params.id).lean();
    
    if (!knowledge) {
      return res.status(404).json({
        success: false,
        message: '知识条目不存在'
      });
    }

    res.json({
      success: true,
      data: knowledge
    });
  } catch (error) {
    logger.error('获取知识条目失败:', error);
    res.status(500).json({
      success: false,
      message: '获取知识条目失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 创建知识条目（需要认证）
router.post('/', authMiddleware, validateKnowledge, async (req, res) => {
  try {
    const { title, content, category, tags, description } = req.body;
    
    const knowledge = new Knowledge({
      title,
      content,
      category,
      tags: tags || [],
      description,
      createdBy: req.user.userId,
      lastModifiedBy: req.user.userId
    });

    await knowledge.save();

    logger.info(`用户 ${req.user.userId} 创建了知识条目: ${title}`);

    res.status(201).json({
      success: true,
      message: '知识条目创建成功',
      data: knowledge
    });
  } catch (error) {
    logger.error('创建知识条目失败:', error);
    res.status(500).json({
      success: false,
      message: '创建知识条目失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 更新知识条目（需要认证）
router.put('/:id', authMiddleware, validateKnowledge, async (req, res) => {
  try {
    const { title, content, category, tags, description } = req.body;
    
    const knowledge = await Knowledge.findById(req.params.id);
    
    if (!knowledge) {
      return res.status(404).json({
        success: false,
        message: '知识条目不存在'
      });
    }

    // 更新字段
    if (title) knowledge.title = title;
    if (content) knowledge.content = content;
    if (category) knowledge.category = category;
    if (tags) knowledge.tags = tags;
    if (description) knowledge.description = description;
    
    knowledge.lastModifiedBy = req.user.userId;
    knowledge.updatedAt = Date.now();

    await knowledge.save();

    logger.info(`用户 ${req.user.userId} 更新了知识条目: ${knowledge.title}`);

    res.json({
      success: true,
      message: '知识条目更新成功',
      data: knowledge
    });
  } catch (error) {
    logger.error('更新知识条目失败:', error);
    res.status(500).json({
      success: false,
      message: '更新知识条目失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 删除知识条目（需要认证）
router.delete('/:id', authMiddleware, async (req, res) => {
  try {
    const knowledge = await Knowledge.findById(req.params.id);
    
    if (!knowledge) {
      return res.status(404).json({
        success: false,
        message: '知识条目不存在'
      });
    }

    await Knowledge.findByIdAndDelete(req.params.id);

    logger.info(`用户 ${req.user.userId} 删除了知识条目: ${knowledge.title}`);

    res.json({
      success: true,
      message: '知识条目删除成功'
    });
  } catch (error) {
    logger.error('删除知识条目失败:', error);
    res.status(500).json({
      success: false,
      message: '删除知识条目失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 获取分类列表
router.get('/categories/list', async (req, res) => {
  try {
    const categories = await Knowledge.distinct('category');
    res.json({
      success: true,
      data: categories
    });
  } catch (error) {
    logger.error('获取分类列表失败:', error);
    res.status(500).json({
      success: false,
      message: '获取分类列表失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 获取标签列表
router.get('/tags/list', async (req, res) => {
  try {
    const tags = await Knowledge.distinct('tags');
    res.json({
      success: true,
      data: tags
    });
  } catch (error) {
    logger.error('获取标签列表失败:', error);
    res.status(500).json({
      success: false,
      message: '获取标签列表失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

module.exports = router;
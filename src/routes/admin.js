const express = require('express');
const router = express.Router();
const { User, Knowledge } = require('../models');
const { logger } = require('../middleware/logger');
const { adminMiddleware } = require('../middleware/auth');
const { validateObjectId, validatePagination } = require('../middleware/validation');

// 应用管理员中间件
router.use(adminMiddleware);

// 获取系统统计信息
router.get('/stats', async (req, res) => {
  try {
    const [
      totalUsers,
      totalKnowledge,
      recentUsers,
      recentKnowledge
    ] = await Promise.all([
      User.countDocuments(),
      Knowledge.countDocuments(),
      User.countDocuments({ 
        createdAt: { $gte: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) }
      }),
      Knowledge.countDocuments({ 
        createdAt: { $gte: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) }
      })
    ]);

    res.json({
      success: true,
      data: {
        users: {
          total: totalUsers,
          recent: recentUsers
        },
        knowledge: {
          total: totalKnowledge,
          recent: recentKnowledge
        }
      }
    });
  } catch (error) {
    logger.error('获取统计信息失败:', error);
    res.status(500).json({
      success: false,
      message: '获取统计信息失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 获取用户列表
router.get('/users', validatePagination, async (req, res) => {
  try {
    const { page = 1, limit = 10, search, role } = req.query;
    const skip = (page - 1) * limit;

    // 构建查询条件
    const query = {};
    if (search) {
      query.$or = [
        { username: { $regex: search, $options: 'i' } },
        { email: { $regex: search, $options: 'i' } }
      ];
    }
    if (role) {
      query.role = role;
    }

    const [users, total] = await Promise.all([
      User.find(query)
        .select('-password')
        .sort({ createdAt: -1 })
        .skip(skip)
        .limit(parseInt(limit)),
      User.countDocuments(query)
    ]);

    res.json({
      success: true,
      data: {
        users,
        pagination: {
          total,
          page: parseInt(page),
          limit: parseInt(limit),
          pages: Math.ceil(total / limit)
        }
      }
    });
  } catch (error) {
    logger.error('获取用户列表失败:', error);
    res.status(500).json({
      success: false,
      message: '获取用户列表失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 获取单个用户信息
router.get('/users/:id', validateObjectId, async (req, res) => {
  try {
    const user = await User.findById(req.params.id).select('-password');
    
    if (!user) {
      return res.status(404).json({
        success: false,
        message: '用户不存在'
      });
    }

    res.json({
      success: true,
      data: { user }
    });
  } catch (error) {
    logger.error('获取用户信息失败:', error);
    res.status(500).json({
      success: false,
      message: '获取用户信息失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 更新用户角色
router.patch('/users/:id/role', validateObjectId, async (req, res) => {
  try {
    const { role } = req.body;
    
    if (!['user', 'admin'].includes(role)) {
      return res.status(400).json({
        success: false,
        message: '无效的角色'
      });
    }

    const user = await User.findById(req.params.id);
    
    if (!user) {
      return res.status(404).json({
        success: false,
        message: '用户不存在'
      });
    }

    // 防止管理员修改自己的角色
    if (user._id.toString() === req.user.userId) {
      return res.status(400).json({
        success: false,
        message: '不能修改自己的角色'
      });
    }

    user.role = role;
    await user.save();

    logger.info(`管理员修改用户角色: ${user.username} -> ${role}`);

    res.json({
      success: true,
      message: '用户角色更新成功',
      data: {
        user: {
          id: user._id,
          username: user.username,
          role: user.role
        }
      }
    });
  } catch (error) {
    logger.error('更新用户角色失败:', error);
    res.status(500).json({
      success: false,
      message: '更新用户角色失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 删除用户
router.delete('/users/:id', validateObjectId, async (req, res) => {
  try {
    const user = await User.findById(req.params.id);
    
    if (!user) {
      return res.status(404).json({
        success: false,
        message: '用户不存在'
      });
    }

    // 防止管理员删除自己
    if (user._id.toString() === req.user.userId) {
      return res.status(400).json({
        success: false,
        message: '不能删除自己的账户'
      });
    }

    await User.findByIdAndDelete(req.params.id);

    logger.info(`管理员删除用户: ${user.username}`);

    res.json({
      success: true,
      message: '用户删除成功'
    });
  } catch (error) {
    logger.error('删除用户失败:', error);
    res.status(500).json({
      success: false,
      message: '删除用户失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 获取知识库列表（管理员视图）
router.get('/knowledge', validatePagination, async (req, res) => {
  try {
    const { page = 1, limit = 10, status, author } = req.query;
    const skip = (page - 1) * limit;

    // 构建查询条件
    const query = {};
    if (status) {
      query.status = status;
    }
    if (author) {
      query.author = author;
    }

    const [knowledge, total] = await Promise.all([
      Knowledge.find(query)
        .populate('author', 'username email')
        .sort({ createdAt: -1 })
        .skip(skip)
        .limit(parseInt(limit)),
      Knowledge.countDocuments(query)
    ]);

    res.json({
      success: true,
      data: {
        knowledge,
        pagination: {
          total,
          page: parseInt(page),
          limit: parseInt(limit),
          pages: Math.ceil(total / limit)
        }
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

// 审核知识条目
router.patch('/knowledge/:id/status', validateObjectId, async (req, res) => {
  try {
    const { status } = req.body;
    
    if (!['draft', 'published', 'archived'].includes(status)) {
      return res.status(400).json({
        success: false,
        message: '无效的状态'
      });
    }

    const knowledge = await Knowledge.findById(req.params.id);
    
    if (!knowledge) {
      return res.status(404).json({
        success: false,
        message: '知识条目不存在'
      });
    }

    knowledge.status = status;
    await knowledge.save();

    logger.info(`管理员修改知识条目状态: ${knowledge.title} -> ${status}`);

    res.json({
      success: true,
      message: '知识条目状态更新成功',
      data: {
        knowledge: {
          id: knowledge._id,
          title: knowledge.title,
          status: knowledge.status
        }
      }
    });
  } catch (error) {
    logger.error('更新知识条目状态失败:', error);
    res.status(500).json({
      success: false,
      message: '更新知识条目状态失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 系统配置管理
router.get('/config', async (req, res) => {
  try {
    // 这里可以添加系统配置逻辑
    const config = {
      siteName: 'MaiMaiNotePad',
      version: '1.0.0',
      maintenance: false,
      allowRegistration: true,
      maxFileSize: '10MB',
      supportedFormats: ['pdf', 'doc', 'docx', 'txt', 'md']
    };

    res.json({
      success: true,
      data: { config }
    });
  } catch (error) {
    logger.error('获取系统配置失败:', error);
    res.status(500).json({
      success: false,
      message: '获取系统配置失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 更新系统配置
router.patch('/config', async (req, res) => {
  try {
    const { config } = req.body;
    
    // 这里可以添加配置验证逻辑
    if (!config || typeof config !== 'object') {
      return res.status(400).json({
        success: false,
        message: '无效的配置数据'
      });
    }

    logger.info(`管理员更新系统配置: ${JSON.stringify(config)}`);

    res.json({
      success: true,
      message: '系统配置更新成功',
      data: { config }
    });
  } catch (error) {
    logger.error('更新系统配置失败:', error);
    res.status(500).json({
      success: false,
      message: '更新系统配置失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

module.exports = router;
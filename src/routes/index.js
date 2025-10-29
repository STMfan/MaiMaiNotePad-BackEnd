const express = require('express');
const router = express.Router();

// 导入各个模块的路由
const authRoutes = require('./auth');
const knowledgeRoutes = require('./knowledge');
const adminRoutes = require('./admin');
const uploadRoutes = require('./upload');
const backupRoutes = require('./backup');
const systemRoutes = require('./system');

// 路由中间件
const { authMiddleware, adminMiddleware } = require('../middleware/auth');

// 公开路由
router.use('/auth', authRoutes);
router.use('/knowledge', knowledgeRoutes);
router.use('/upload', uploadRoutes);
router.use('/system', systemRoutes);

// 需要认证的路由
router.use('/admin', authMiddleware, adminMiddleware, adminRoutes);
router.use('/backup', authMiddleware, adminMiddleware, backupRoutes);

// 根路径
router.get('/', (req, res) => {
  res.json({
    success: true,
    message: 'MaiMai NotePad API 服务正在运行',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
    endpoints: {
      auth: '/api/auth',
      knowledge: '/api/knowledge',
      upload: '/api/upload',
      system: '/api/system',
      admin: '/api/admin',
      backup: '/api/backup'
    }
  });
});

module.exports = router;
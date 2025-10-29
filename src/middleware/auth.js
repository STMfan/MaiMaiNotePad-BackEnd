const jwt = require('jsonwebtoken');
const { logger } = require('./logger');

// 认证中间件
const authMiddleware = (req, res, next) => {
  try {
    const token = req.header('Authorization')?.replace('Bearer ', '');
    
    if (!token) {
      return res.status(401).json({
        success: false,
        message: '未提供认证令牌'
      });
    }

    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'your-secret-key');
    req.user = decoded;
    
    next();
  } catch (error) {
    logger.error('认证失败:', error);
    return res.status(401).json({
      success: false,
      message: '认证失败'
    });
  }
};

// 管理员权限中间件
const adminMiddleware = (req, res, next) => {
  if (req.user && req.user.role === 'admin') {
    next();
  } else {
    return res.status(403).json({
      success: false,
      message: '需要管理员权限'
    });
  }
};

// 生成JWT令牌
const generateToken = (userId, role = 'user') => {
  return jwt.sign(
    { userId, role },
    process.env.JWT_SECRET || 'your-secret-key',
    { expiresIn: '7d' }
  );
};

module.exports = {
  authMiddleware,
  adminMiddleware,
  generateToken
};
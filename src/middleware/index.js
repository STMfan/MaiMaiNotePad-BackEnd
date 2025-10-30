const { logger, requestLogger, errorHandler } = require('./logger');
const { authMiddleware, adminMiddleware, generateToken } = require('./auth');
const {
  validateRegister,
  validateLogin,
  validateKnowledge,
  validateFileUpload,
  validatePagination,
  validateObjectId,
  validateCategory,
  validateBackupConfig,
  handleValidationErrors
} = require('./validation');

module.exports = {
  // 日志相关
  logger,
  requestLogger,
  errorHandler,
  
  // 认证相关
  authMiddleware,
  adminMiddleware,
  generateToken,
  
  // 验证相关
  validateRegister,
  validateLogin,
  validateKnowledge,
  validateFileUpload,
  validatePagination,
  validateObjectId,
  validateCategory,
  validateBackupConfig,
  handleValidationErrors
};
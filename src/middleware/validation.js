const { body, validationResult } = require('express-validator');
const { logger } = require('./logger');

// 验证错误处理中间件
const handleValidationErrors = (req, res, next) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    logger.warn('验证失败:', errors.array());
    return res.status(400).json({
      success: false,
      message: '输入验证失败',
      errors: errors.array()
    });
  }
  next();
};

// 用户注册验证
const validateRegister = [
  body('username')
    .trim()
    .isLength({ min: 3, max: 20 })
    .withMessage('用户名长度必须在3-20个字符之间')
    .matches(/^[a-zA-Z0-9_]+$/)
    .withMessage('用户名只能包含字母、数字和下划线'),
  body('email')
    .isEmail()
    .withMessage('请输入有效的邮箱地址')
    .normalizeEmail(),
  body('password')
    .isLength({ min: 6 })
    .withMessage('密码长度至少为6个字符')
    .matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/)
    .withMessage('密码必须包含大小写字母和数字'),
  handleValidationErrors
];

// 用户登录验证
const validateLogin = [
  body('email')
    .isEmail()
    .withMessage('请输入有效的邮箱地址')
    .normalizeEmail(),
  body('password')
    .notEmpty()
    .withMessage('密码不能为空'),
  handleValidationErrors
];

// 知识条目验证
const validateKnowledge = [
  body('title')
    .trim()
    .isLength({ min: 1, max: 200 })
    .withMessage('标题长度必须在1-200个字符之间'),
  body('content')
    .trim()
    .isLength({ min: 1, max: 50000 })
    .withMessage('内容长度必须在1-50000个字符之间'),
  body('category')
    .trim()
    .isLength({ min: 1, max: 50 })
    .withMessage('分类不能为空且不能超过50个字符'),
  body('tags')
    .optional()
    .isArray()
    .withMessage('标签必须是数组')
    .custom((tags) => tags.every(tag => typeof tag === 'string' && tag.length <= 20))
    .withMessage('每个标签必须是字符串且不超过20个字符'),
  body('description')
    .optional()
    .trim()
    .isLength({ max: 500 })
    .withMessage('描述不能超过500个字符'),
  handleValidationErrors
];

// 文件上传验证
const validateFileUpload = [
  body('title')
    .optional()
    .trim()
    .isLength({ max: 100 })
    .withMessage('标题不能超过100个字符'),
  body('description')
    .optional()
    .trim()
    .isLength({ max: 500 })
    .withMessage('描述不能超过500个字符'),
  handleValidationErrors
];

// 分页验证
const validatePagination = [
  body('page')
    .optional()
    .isInt({ min: 1 })
    .withMessage('页码必须是正整数')
    .toInt(),
  body('limit')
    .optional()
    .isInt({ min: 1, max: 100 })
    .withMessage('每页数量必须是1-100之间的整数')
    .toInt(),
  handleValidationErrors
];

// ID参数验证
const validateObjectId = [
  body('id')
    .isMongoId()
    .withMessage('无效的ID格式'),
  handleValidationErrors
];

// 分类验证
const validateCategory = [
  body('name')
    .trim()
    .isLength({ min: 1, max: 50 })
    .withMessage('分类名称长度必须在1-50个字符之间'),
  body('description')
    .optional()
    .trim()
    .isLength({ max: 200 })
    .withMessage('分类描述不能超过200个字符'),
  handleValidationErrors
];

// 备份配置验证
const validateBackupConfig = [
  body('frequency')
    .optional()
    .isIn(['daily', 'weekly', 'monthly'])
    .withMessage('备份频率必须是 daily, weekly 或 monthly'),
  body('retentionDays')
    .optional()
    .isInt({ min: 1, max: 365 })
    .withMessage('保留天数必须是1-365之间的整数')
    .toInt(),
  handleValidationErrors
];

module.exports = {
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
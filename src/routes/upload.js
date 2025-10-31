const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs').promises;
const { logger } = require('../middleware/logger');
const { authMiddleware } = require('../middleware/auth');
const { validateFileUpload } = require('../middleware/validation');

// 配置文件上传
const storage = multer.diskStorage({
  destination: async (req, file, cb) => {
    try {
      const uploadDir = path.join(process.cwd(), 'uploads');
      await fs.mkdir(uploadDir, { recursive: true });
      cb(null, uploadDir);
    } catch (error) {
      cb(error);
    }
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    const ext = path.extname(file.originalname);
    const name = path.basename(file.originalname, ext);
    cb(null, `${name}-${uniqueSuffix}${ext}`);
  }
});

// 文件过滤器
const fileFilter = (req, file, cb) => {
  const allowedTypes = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'text/markdown',
    'application/json',
    'application/toml',
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp'
  ];

  // 检查文件扩展名
  const allowedExtensions = ['.json', '.md', '.txt', '.toml'];
  const fileExt = path.extname(file.originalname).toLowerCase();
  
  if (allowedTypes.includes(file.mimetype) || allowedExtensions.includes(fileExt)) {
    cb(null, true);
  } else {
    cb(new Error('不支持的文件类型。支持的格式：PDF、Word、文本文件、Markdown、JSON、TOML、图片文件'), false);
  }
};

// 创建multer实例
const upload = multer({
  storage,
  fileFilter,
  limits: {
    fileSize: 10 * 1024 * 1024 // 10MB
  }
});

// 应用认证中间件
router.use(authMiddleware);

// 文件信息存储（可以扩展为数据库存储）
const fileMetadata = new Map();

// 上传文件
router.post('/upload', validateFileUpload, upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        success: false,
        message: '未选择文件或文件上传失败'
      });
    }

    const fileInfo = {
      id: Date.now().toString(),
      originalName: req.file.originalname,
      filename: req.file.filename,
      mimetype: req.file.mimetype,
      size: req.file.size,
      path: req.file.path,
      uploadedBy: req.user.userId,
      uploadedAt: new Date(),
      description: req.body.description || ''
    };

    // 存储文件元数据
    fileMetadata.set(fileInfo.id, fileInfo);

    logger.info(`文件上传成功: ${req.file.originalname} (${req.file.size} bytes)`);

    res.json({
      success: true,
      message: '文件上传成功',
      data: {
        file: {
          id: fileInfo.id,
          originalName: fileInfo.originalName,
          filename: fileInfo.filename,
          mimetype: fileInfo.mimetype,
          size: fileInfo.size,
          uploadedAt: fileInfo.uploadedAt,
          description: fileInfo.description,
          url: `/api/upload/files/${fileInfo.id}`
        }
      }
    });
  } catch (error) {
    logger.error('文件上传失败:', error);
    
    // 清理上传失败的文件
    if (req.file && req.file.path) {
      try {
        await fs.unlink(req.file.path);
      } catch (unlinkError) {
        logger.error('清理失败文件错误:', unlinkError);
      }
    }

    res.status(500).json({
      success: false,
      message: '文件上传失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 上传多个文件
router.post('/upload-multiple', validateFileUpload, upload.array('files', 10), async (req, res) => {
  try {
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({
        success: false,
        message: '未选择文件或文件上传失败'
      });
    }

    const uploadedFiles = [];

    for (const file of req.files) {
      const fileInfo = {
        id: Date.now().toString() + '-' + Math.random().toString(36).substr(2, 9),
        originalName: file.originalname,
        filename: file.filename,
        mimetype: file.mimetype,
        size: file.size,
        path: file.path,
        uploadedBy: req.user.userId,
        uploadedAt: new Date(),
        description: req.body.description || ''
      };

      fileMetadata.set(fileInfo.id, fileInfo);
      uploadedFiles.push(fileInfo);
    }

    logger.info(`批量文件上传成功: ${req.files.length} 个文件`);

    res.json({
      success: true,
      message: '批量文件上传成功',
      data: {
        files: uploadedFiles.map(file => ({
          id: file.id,
          originalName: file.originalName,
          filename: file.filename,
          mimetype: file.mimetype,
          size: file.size,
          uploadedAt: file.uploadedAt,
          description: file.description,
          url: `/api/upload/files/${file.id}`
        }))
      }
    });
  } catch (error) {
    logger.error('批量文件上传失败:', error);
    
    // 清理上传失败的文件
    if (req.files) {
      for (const file of req.files) {
        try {
          await fs.unlink(file.path);
        } catch (unlinkError) {
          logger.error('清理失败文件错误:', unlinkError);
        }
      }
    }

    res.status(500).json({
      success: false,
      message: '批量文件上传失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 获取文件列表
router.get('/files', async (req, res) => {
  try {
    const { page = 1, limit = 20 } = req.query;
    const skip = (page - 1) * limit;

    // 获取当前用户的文件
    const userFiles = Array.from(fileMetadata.values())
      .filter(file => file.uploadedBy === req.user.userId)
      .sort((a, b) => b.uploadedAt - a.uploadedAt);

    const total = userFiles.length;
    const files = userFiles.slice(skip, skip + parseInt(limit));

    res.json({
      success: true,
      data: {
        files: files.map(file => ({
          id: file.id,
          originalName: file.originalName,
          filename: file.filename,
          mimetype: file.mimetype,
          size: file.size,
          uploadedAt: file.uploadedAt,
          description: file.description,
          url: `/api/upload/files/${file.id}`
        })),
        pagination: {
          total,
          page: parseInt(page),
          limit: parseInt(limit),
          pages: Math.ceil(total / limit)
        }
      }
    });
  } catch (error) {
    logger.error('获取文件列表失败:', error);
    res.status(500).json({
      success: false,
      message: '获取文件列表失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 下载文件
router.get('/files/:id', async (req, res) => {
  try {
    const fileId = req.params.id;
    const fileInfo = fileMetadata.get(fileId);

    if (!fileInfo) {
      return res.status(404).json({
        success: false,
        message: '文件不存在'
      });
    }

    // 检查权限（只允许上传者下载）
    if (fileInfo.uploadedBy !== req.user.userId) {
      return res.status(403).json({
        success: false,
        message: '没有权限访问此文件'
      });
    }

    // 检查文件是否存在
    try {
      await fs.access(fileInfo.path);
    } catch (error) {
      fileMetadata.delete(fileId);
      return res.status(404).json({
        success: false,
        message: '文件不存在或已被删除'
      });
    }

    // 设置响应头
    res.setHeader('Content-Disposition', `attachment; filename="${encodeURIComponent(fileInfo.originalName)}"`);
    res.setHeader('Content-Type', fileInfo.mimetype);

    // 发送文件
    res.sendFile(path.resolve(fileInfo.path));
  } catch (error) {
    logger.error('文件下载失败:', error);
    res.status(500).json({
      success: false,
      message: '文件下载失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 删除文件
router.delete('/files/:id', async (req, res) => {
  try {
    const fileId = req.params.id;
    const fileInfo = fileMetadata.get(fileId);

    if (!fileInfo) {
      return res.status(404).json({
        success: false,
        message: '文件不存在'
      });
    }

    // 检查权限（只允许上传者删除）
    if (fileInfo.uploadedBy !== req.user.userId) {
      return res.status(403).json({
        success: false,
        message: '没有权限删除此文件'
      });
    }

    // 删除文件
    try {
      await fs.unlink(fileInfo.path);
    } catch (error) {
      logger.error('删除物理文件失败:', error);
    }

    // 删除元数据
    fileMetadata.delete(fileId);

    logger.info(`文件删除成功: ${fileInfo.originalName}`);

    res.json({
      success: true,
      message: '文件删除成功'
    });
  } catch (error) {
    logger.error('文件删除失败:', error);
    res.status(500).json({
      success: false,
      message: '文件删除失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 更新文件信息
router.patch('/files/:id', async (req, res) => {
  try {
    const fileId = req.params.id;
    const { description } = req.body;
    const fileInfo = fileMetadata.get(fileId);

    if (!fileInfo) {
      return res.status(404).json({
        success: false,
        message: '文件不存在'
      });
    }

    // 检查权限（只允许上传者修改）
    if (fileInfo.uploadedBy !== req.user.userId) {
      return res.status(403).json({
        success: false,
        message: '没有权限修改此文件'
      });
    }

    // 更新文件信息
    if (description !== undefined) {
      fileInfo.description = description;
    }

    fileInfo.updatedAt = new Date();

    res.json({
      success: true,
      message: '文件信息更新成功',
      data: {
        file: {
          id: fileInfo.id,
          originalName: fileInfo.originalName,
          filename: fileInfo.filename,
          mimetype: fileInfo.mimetype,
          size: fileInfo.size,
          uploadedAt: fileInfo.uploadedAt,
          updatedAt: fileInfo.updatedAt,
          description: fileInfo.description,
          url: `/api/upload/files/${fileInfo.id}`
        }
      }
    });
  } catch (error) {
    logger.error('更新文件信息失败:', error);
    res.status(500).json({
      success: false,
      message: '更新文件信息失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

module.exports = router;
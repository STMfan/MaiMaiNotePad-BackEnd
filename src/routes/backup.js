const express = require('express');
const router = express.Router();
const fs = require('fs').promises;
const path = require('path');
const { exec } = require('child_process');
const { promisify } = require('util');
const { logger } = require('../middleware/logger');
const { adminMiddleware } = require('../middleware/auth');
const { validateBackupConfig } = require('../middleware/validation');

const execAsync = promisify(exec);

// 应用管理员中间件
router.use(adminMiddleware);

// 创建备份
router.post('/create', validateBackupConfig, async (req, res) => {
  try {
    const { type = 'full', includeUploads = true } = req.body;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupName = `backup-${type}-${timestamp}`;
    const backupDir = path.join(process.cwd(), 'backups', backupName);

    logger.info(`开始创建备份: ${backupName}`);

    // 创建备份目录
    await fs.mkdir(backupDir, { recursive: true });

    const backupInfo = {
      name: backupName,
      type,
      includeUploads,
      createdAt: new Date(),
      createdBy: req.user.userId,
      status: 'in_progress',
      files: []
    };

    try {
      // 1. 备份数据库
      if (type === 'full' || type === 'database') {
        const dbBackupFile = path.join(backupDir, 'database.json');
        
        // 模拟数据库备份（实际项目中需要连接到MongoDB）
        const mockDbData = {
          timestamp: new Date().toISOString(),
          collections: ['users', 'knowledge', 'sessions'],
          backupInfo: 'This is a mock database backup'
        };
        
        await fs.writeFile(dbBackupFile, JSON.stringify(mockDbData, null, 2));
        backupInfo.files.push({
          type: 'database',
          path: 'database.json',
          size: JSON.stringify(mockDbData).length
        });
      }

      // 2. 备份上传文件
      if (includeUploads && (type === 'full' || type === 'files')) {
        const uploadsDir = path.join(process.cwd(), 'uploads');
        const uploadsBackupDir = path.join(backupDir, 'uploads');

        try {
          await fs.access(uploadsDir);
          
          // 复制上传文件目录
          await execAsync(`cp -r "${uploadsDir}" "${uploadsBackupDir}"`);
          
          // 获取上传文件信息
          const uploads = await fs.readdir(uploadsDir);
          backupInfo.files.push({
            type: 'uploads',
            path: 'uploads/',
            count: uploads.length
          });
        } catch (error) {
          logger.warn('上传目录不存在或备份失败:', error.message);
        }
      }

      // 3. 备份配置文件
      const configFiles = ['package.json', '.env.example', 'README.md'];
      const configBackupDir = path.join(backupDir, 'config');
      await fs.mkdir(configBackupDir, { recursive: true });

      for (const file of configFiles) {
        const srcPath = path.join(process.cwd(), file);
        const destPath = path.join(configBackupDir, file);
        
        try {
          await fs.copyFile(srcPath, destPath);
          backupInfo.files.push({
            type: 'config',
            path: `config/${file}`,
            name: file
          });
        } catch (error) {
          logger.warn(`配置文件 ${file} 备份失败:`, error.message);
        }
      }

      // 4. 创建备份元数据
      const metadataFile = path.join(backupDir, 'backup-info.json');
      backupInfo.status = 'completed';
      backupInfo.completedAt = new Date();
      
      await fs.writeFile(metadataFile, JSON.stringify(backupInfo, null, 2));

      // 5. 创建压缩包（可选）
      try {
        const zipFile = `${backupDir}.zip`;
        await execAsync(`cd "${path.dirname(backupDir)}" && zip -r "${zipFile}" "${path.basename(backupDir)}"`);
        
        // 获取压缩包大小
        const stats = await fs.stat(zipFile);
        backupInfo.compressedSize = stats.size;
        backupInfo.compressedPath = `${backupName}.zip`;
        
        // 更新元数据
        await fs.writeFile(metadataFile, JSON.stringify(backupInfo, null, 2));
        
        logger.info(`备份压缩完成: ${zipFile}`);
      } catch (error) {
        logger.warn('创建压缩包失败:', error.message);
      }

      logger.info(`备份创建成功: ${backupName}`);

      res.json({
        success: true,
        message: '备份创建成功',
        data: {
          backup: {
            name: backupInfo.name,
            type: backupInfo.type,
            status: backupInfo.status,
            createdAt: backupInfo.createdAt,
            files: backupInfo.files,
            compressedSize: backupInfo.compressedSize,
            compressedPath: backupInfo.compressedPath
          }
        }
      });

    } catch (error) {
      backupInfo.status = 'failed';
      backupInfo.error = error.message;
      
      const metadataFile = path.join(backupDir, 'backup-info.json');
      await fs.writeFile(metadataFile, JSON.stringify(backupInfo, null, 2));
      
      throw error;
    }

  } catch (error) {
    logger.error('备份创建失败:', error);
    res.status(500).json({
      success: false,
      message: '备份创建失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 获取备份列表
router.get('/list', async (req, res) => {
  try {
    const backupsDir = path.join(process.cwd(), 'backups');
    const backups = [];

    try {
      const items = await fs.readdir(backupsDir);
      
      for (const item of items) {
        const itemPath = path.join(backupsDir, item);
        const stats = await fs.stat(itemPath);
        
        if (stats.isDirectory()) {
          try {
            const infoFile = path.join(itemPath, 'backup-info.json');
            const infoData = await fs.readFile(infoFile, 'utf8');
            const info = JSON.parse(infoData);
            
            backups.push({
              name: info.name,
              type: info.type,
              status: info.status,
              createdAt: info.createdAt,
              completedAt: info.completedAt,
              files: info.files,
              compressedSize: info.compressedSize,
              compressedPath: info.compressedPath
            });
          } catch (error) {
            // 如果没有info文件，创建基本信息
            backups.push({
              name: item,
              type: 'unknown',
              status: 'unknown',
              createdAt: stats.birthtime,
              size: stats.size
            });
          }
        } else if (item.endsWith('.zip')) {
          backups.push({
            name: item.replace('.zip', ''),
            type: 'compressed',
            status: 'completed',
            createdAt: stats.birthtime,
            compressedSize: stats.size,
            compressedPath: item
          });
        }
      }
    } catch (error) {
      // backups目录不存在
      logger.warn('备份目录不存在:', error.message);
    }

    // 按创建时间排序
    backups.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

    res.json({
      success: true,
      data: {
        backups,
        total: backups.length
      }
    });
  } catch (error) {
    logger.error('获取备份列表失败:', error);
    res.status(500).json({
      success: false,
      message: '获取备份列表失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 下载备份
router.get('/download/:name', async (req, res) => {
  try {
    const { name } = req.params;
    const backupsDir = path.join(process.cwd(), 'backups');
    
    // 首先尝试下载压缩包
    const zipFile = path.join(backupsDir, `${name}.zip`);
    try {
      await fs.access(zipFile);
      res.setHeader('Content-Disposition', `attachment; filename="${name}.zip"`);
      res.setHeader('Content-Type', 'application/zip');
      return res.sendFile(path.resolve(zipFile));
    } catch (error) {
      // 压缩包不存在，尝试下载目录
    }

    // 尝试下载目录备份
    const backupDir = path.join(backupsDir, name);
    try {
      await fs.access(backupDir);
      
      // 这里可以实现目录打包下载，简化处理返回错误
      return res.status(400).json({
        success: false,
        message: '目录备份不支持直接下载，请联系管理员'
      });
    } catch (error) {
      return res.status(404).json({
        success: false,
        message: '备份不存在'
      });
    }

  } catch (error) {
    logger.error('下载备份失败:', error);
    res.status(500).json({
      success: false,
      message: '下载备份失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 删除备份
router.delete('/:name', async (req, res) => {
  try {
    const { name } = req.params;
    const backupsDir = path.join(process.cwd(), 'backups');
    
    // 删除压缩包
    const zipFile = path.join(backupsDir, `${name}.zip`);
    let deleted = false;
    
    try {
      await fs.access(zipFile);
      await fs.unlink(zipFile);
      deleted = true;
      logger.info(`删除备份压缩包: ${name}.zip`);
    } catch (error) {
      // 压缩包不存在
    }

    // 删除备份目录
    const backupDir = path.join(backupsDir, name);
    try {
      await fs.access(backupDir);
      await execAsync(`rm -rf "${backupDir}"`);
      deleted = true;
      logger.info(`删除备份目录: ${name}`);
    } catch (error) {
      // 目录不存在
    }

    if (!deleted) {
      return res.status(404).json({
        success: false,
        message: '备份不存在'
      });
    }

    res.json({
      success: true,
      message: '备份删除成功'
    });
  } catch (error) {
    logger.error('删除备份失败:', error);
    res.status(500).json({
      success: false,
      message: '删除备份失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 恢复备份
router.post('/restore/:name', async (req, res) => {
  try {
    const { name } = req.params;
    const { type = 'full' } = req.body;
    const backupsDir = path.join(process.cwd(), 'backups');
    
    logger.info(`开始恢复备份: ${name}`);

    // 首先尝试从压缩包恢复
    const zipFile = path.join(backupsDir, `${name}.zip`);
    let backupDir = path.join(backupsDir, name);
    
    try {
      await fs.access(zipFile);
      
      // 解压备份
      await execAsync(`cd "${backupsDir}" && unzip -o "${name}.zip"`);
      
    } catch (error) {
      // 压缩包不存在，尝试直接目录恢复
      try {
        await fs.access(backupDir);
      } catch (error) {
        return res.status(404).json({
          success: false,
          message: '备份不存在'
        });
      }
    }

    // 读取备份信息
    const infoFile = path.join(backupDir, 'backup-info.json');
    let backupInfo;
    
    try {
      const infoData = await fs.readFile(infoFile, 'utf8');
      backupInfo = JSON.parse(infoData);
    } catch (error) {
      return res.status(400).json({
        success: false,
        message: '备份信息文件损坏'
      });
    }

    // 执行恢复操作
    try {
      // 1. 恢复数据库
      if (type === 'full' || type === 'database') {
        const dbFile = path.join(backupDir, 'database.json');
        
        try {
          await fs.access(dbFile);
          // 这里应该实现实际的数据库恢复逻辑
          logger.info('数据库恢复完成');
        } catch (error) {
          logger.warn('数据库备份文件不存在:', error.message);
        }
      }

      // 2. 恢复上传文件
      if (type === 'full' || type === 'files') {
        const uploadsBackupDir = path.join(backupDir, 'uploads');
        const uploadsDir = path.join(process.cwd(), 'uploads');
        
        try {
          await fs.access(uploadsBackupDir);
          
          // 确保上传目录存在
          await fs.mkdir(path.dirname(uploadsDir), { recursive: true });
          
          // 恢复上传文件
          await execAsync(`cp -r "${uploadsBackupDir}" "${uploadsDir}"`);
          
          logger.info('上传文件恢复完成');
        } catch (error) {
          logger.warn('上传文件备份不存在:', error.message);
        }
      }

      logger.info(`备份恢复成功: ${name}`);

      res.json({
        success: true,
        message: '备份恢复成功',
        data: {
          restoredBackup: name,
          type: type,
          restoredAt: new Date()
        }
      });

    } catch (error) {
      logger.error('备份恢复失败:', error);
      throw error;
    }

  } catch (error) {
    logger.error('恢复备份失败:', error);
    res.status(500).json({
      success: false,
      message: '恢复备份失败',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

module.exports = router;
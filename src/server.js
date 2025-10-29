const app = require('./app');
const { logger } = require('./middleware/logger');

const PORT = process.env.PORT || 3001;

const server = app.listen(PORT, '0.0.0.0', () => {
  logger.info(`服务器运行在端口 ${PORT}`);
  logger.info(`环境: ${process.env.NODE_ENV}`);
  logger.info(`本地访问地址: http://localhost:${PORT}`);
  logger.info(`局域网访问地址: http://0.0.0.0:${PORT} (请替换为你的实际IP地址)`);
});

// 优雅关闭处理
const gracefulShutdown = (signal) => {
  logger.info(`收到 ${signal} 信号，开始优雅关闭...`);
  
  server.close(() => {
    logger.info('HTTP服务器已关闭');
    
    // 关闭数据库连接
    const mongoose = require('mongoose');
    mongoose.connection.close(() => {
      logger.info('数据库连接已关闭');
      process.exit(0);
    });
  });
  
  // 强制关闭超时
  setTimeout(() => {
    logger.error('优雅关闭超时，强制退出');
    process.exit(1);
  }, 10000);
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// 未捕获异常处理
process.on('uncaughtException', (error) => {
  logger.error('未捕获的异常:', error);
  gracefulShutdown('uncaughtException');
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error('未处理的Promise拒绝:', reason);
  gracefulShutdown('unhandledRejection');
});

module.exports = server;
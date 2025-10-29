const mongoose = require('mongoose');
const { logger } = require('../middleware/logger');

const connectDB = async () => {
  try {
    const mongoURI = process.env.MONGODB_URI || 'mongodb://localhost:27017/maimai-notepad';
    
    const conn = await mongoose.connect(mongoURI, {
      useNewUrlParser: true,
      useUnifiedTopology: true,
      maxPoolSize: 10,
      serverSelectionTimeoutMS: 5000,
      socketTimeoutMS: 45000,
      family: 4
    });

    logger.info(`MongoDB 连接成功: ${conn.connection.host}`);
    
    // 监听连接事件
    mongoose.connection.on('connected', () => {
      logger.info('MongoDB 连接已建立');
    });

    mongoose.connection.on('error', (err) => {
      logger.error('MongoDB 连接错误:', err);
    });

    mongoose.connection.on('disconnected', () => {
      logger.warn('MongoDB 连接已断开');
    });

    // 进程退出时关闭连接
    process.on('SIGINT', async () => {
      await mongoose.connection.close();
      logger.info('MongoDB 连接已通过应用关闭');
      process.exit(0);
    });

  } catch (error) {
    logger.error('MongoDB 连接失败:', error);
    process.exit(1);
  }
};

module.exports = { connectDB };
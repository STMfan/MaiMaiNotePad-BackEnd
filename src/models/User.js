const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

const userSchema = new mongoose.Schema({
  username: {
    type: String,
    required: [true, '用户名不能为空'],
    unique: true,
    trim: true,
    minlength: [3, '用户名长度不能少于3个字符'],
    maxlength: [20, '用户名长度不能超过20个字符'],
    match: [/^[a-zA-Z0-9_]+$/, '用户名只能包含字母、数字和下划线']
  },
  email: {
    type: String,
    required: [true, '邮箱不能为空'],
    unique: true,
    lowercase: true,
    trim: true,
    match: [/^\S+@\S+\.\S+$/, '请输入有效的邮箱地址']
  },
  password: {
    type: String,
    required: [true, '密码不能为空'],
    minlength: [6, '密码长度不能少于6个字符'],
    select: false // 默认查询不包含密码
  },
  role: {
    type: String,
    enum: ['user', 'admin'],
    default: 'user'
  },
  profile: {
    firstName: {
      type: String,
      trim: true,
      maxlength: [50, '名字长度不能超过50个字符']
    },
    lastName: {
      type: String,
      trim: true,
      maxlength: [50, '姓氏长度不能超过50个字符']
    },
    avatar: {
      type: String,
      default: ''
    },
    bio: {
      type: String,
      trim: true,
      maxlength: [500, '个人简介长度不能超过500个字符']
    }
  },
  preferences: {
    theme: {
      type: String,
      enum: ['light', 'dark', 'auto'],
      default: 'auto'
    },
    language: {
      type: String,
      enum: ['zh-CN', 'en-US'],
      default: 'zh-CN'
    },
    notifications: {
      email: {
        type: Boolean,
        default: true
      },
      push: {
        type: Boolean,
        default: true
      }
    }
  },
  statistics: {
    knowledgeCount: {
      type: Number,
      default: 0
    },
    loginCount: {
      type: Number,
      default: 0
    },
    lastLoginAt: {
      type: Date
    }
  },
  isActive: {
    type: Boolean,
    default: true
  },
  isVerified: {
    type: Boolean,
    default: false
  },
  verificationToken: {
    type: String
  },
  passwordResetToken: {
    type: String
  },
  passwordResetExpires: {
    type: Date
  }
}, {
  timestamps: true,
  toJSON: { 
    virtuals: true,
    transform: function(doc, ret) {
      delete ret.password;
      delete ret.verificationToken;
      delete ret.passwordResetToken;
      delete ret.passwordResetExpires;
      return ret;
    }
  },
  toObject: { virtuals: true }
});

// 虚拟字段：全名
userSchema.virtual('fullName').get(function() {
  if (this.profile.firstName && this.profile.lastName) {
    return `${this.profile.firstName} ${this.profile.lastName}`;
  }
  return this.username;
});

// 索引
userSchema.index({ email: 1 });
userSchema.index({ username: 1 });
userSchema.index({ role: 1 });
userSchema.index({ isActive: 1 });

// 密码加密中间件
userSchema.pre('save', async function(next) {
  if (!this.isModified('password')) return next();
  
  try {
    const salt = await bcrypt.genSalt(12);
    this.password = await bcrypt.hash(this.password, salt);
    next();
  } catch (error) {
    next(error);
  }
});

// 密码验证方法
userSchema.methods.comparePassword = async function(candidatePassword) {
  try {
    return await bcrypt.compare(candidatePassword, this.password);
  } catch (error) {
    throw new Error('密码比较失败');
  }
};

// 更新最后登录时间
userSchema.methods.updateLastLogin = async function() {
  this.statistics.lastLoginAt = new Date();
  this.statistics.loginCount += 1;
  return this.save();
};

// 增加知识条目数量
userSchema.methods.incrementKnowledgeCount = async function() {
  this.statistics.knowledgeCount += 1;
  return this.save();
};

// 减少知识条目数量
userSchema.methods.decrementKnowledgeCount = async function() {
  this.statistics.knowledgeCount = Math.max(0, this.statistics.knowledgeCount - 1);
  return this.save();
};

// 生成密码重置令牌
userSchema.methods.generatePasswordResetToken = function() {
  const crypto = require('crypto');
  const resetToken = crypto.randomBytes(32).toString('hex');
  
  this.passwordResetToken = crypto
    .createHash('sha256')
    .update(resetToken)
    .digest('hex');
  
  this.passwordResetExpires = Date.now() + 3600000; // 1小时
  
  return resetToken;
};

// 生成邮箱验证令牌
userSchema.methods.generateVerificationToken = function() {
  const crypto = require('crypto');
  const verificationToken = crypto.randomBytes(32).toString('hex');
  
  this.verificationToken = crypto
    .createHash('sha256')
    .update(verificationToken)
    .digest('hex');
  
  return verificationToken;
};

// 静态方法：按角色查找用户
userSchema.statics.findByRole = function(role) {
  return this.find({ role, isActive: true }).select('-password');
};

// 静态方法：查找活跃用户
userSchema.statics.findActive = function() {
  return this.find({ isActive: true }).select('-password');
};

// 静态方法：按邮箱查找用户（包含密码）
userSchema.statics.findByEmailWithPassword = function(email) {
  return this.findOne({ email }).select('+password');
};

// 静态方法：验证用户凭据
userSchema.statics.validateCredentials = async function(email, password) {
  const user = await this.findByEmailWithPassword(email);
  
  if (!user || !user.isActive) {
    return null;
  }
  
  const isPasswordValid = await user.comparePassword(password);
  if (!isPasswordValid) {
    return null;
  }
  
  return user;
};

module.exports = mongoose.model('User', userSchema);
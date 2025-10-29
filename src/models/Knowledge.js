const mongoose = require('mongoose');

const knowledgeSchema = new mongoose.Schema({
  title: {
    type: String,
    required: [true, '标题不能为空'],
    trim: true,
    maxlength: [200, '标题不能超过200个字符']
  },
  content: {
    type: String,
    required: [true, '内容不能为空'],
    maxlength: [50000, '内容不能超过50000个字符']
  },
  description: {
    type: String,
    trim: true,
    maxlength: [500, '描述不能超过500个字符']
  },
  category: {
    type: String,
    required: [true, '分类不能为空'],
    trim: true
  },
  tags: [{
    type: String,
    trim: true
  }],
  attachments: [{
    filename: String,
    originalName: String,
    path: String,
    size: Number,
    mimetype: String,
    uploadedAt: { type: Date, default: Date.now }
  }],
  viewCount: {
    type: Number,
    default: 0
  },
  likeCount: {
    type: Number,
    default: 0
  },
  isPublic: {
    type: Boolean,
    default: true
  },
  isDeleted: {
    type: Boolean,
    default: false
  },
  createdBy: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  lastModifiedBy: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User'
  },
  relatedKnowledge: [{
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Knowledge'
  }]
}, {
  timestamps: true,
  toJSON: { virtuals: true },
  toObject: { virtuals: true }
});

// 索引
knowledgeSchema.index({ title: 'text', content: 'text', description: 'text' });
knowledgeSchema.index({ category: 1 });
knowledgeSchema.index({ tags: 1 });
knowledgeSchema.index({ createdAt: -1 });
knowledgeSchema.index({ updatedAt: -1 });
knowledgeSchema.index({ createdBy: 1 });

// 虚拟字段：创建者信息
knowledgeSchema.virtual('creator', {
  ref: 'User',
  localField: 'createdBy',
  foreignField: '_id',
  justOne: true
});

// 虚拟字段：最后修改者信息
knowledgeSchema.virtual('modifier', {
  ref: 'User',
  localField: 'lastModifiedBy',
  foreignField: '_id',
  justOne: true
});

// 增加浏览次数的方法
knowledgeSchema.methods.incrementViewCount = async function() {
  this.viewCount += 1;
  return this.save();
};

// 增加点赞次数的方法
knowledgeSchema.methods.incrementLikeCount = async function() {
  this.likeCount += 1;
  return this.save();
};

// 减少点赞次数的方法
knowledgeSchema.methods.decrementLikeCount = async function() {
  this.likeCount = Math.max(0, this.likeCount - 1);
  return this.save();
};

// 静态方法：按分类获取知识条目
knowledgeSchema.statics.findByCategory = function(category, options = {}) {
  const query = { category, isDeleted: false };
  if (options.isPublic !== undefined) {
    query.isPublic = options.isPublic;
  }
  
  return this.find(query)
    .populate('creator', 'username email')
    .populate('modifier', 'username email')
    .sort(options.sort || { createdAt: -1 })
    .limit(options.limit || 0)
    .skip(options.skip || 0);
};

// 静态方法：按标签获取知识条目
knowledgeSchema.statics.findByTag = function(tag, options = {}) {
  const query = { tags: tag, isDeleted: false };
  if (options.isPublic !== undefined) {
    query.isPublic = options.isPublic;
  }
  
  return this.find(query)
    .populate('creator', 'username email')
    .populate('modifier', 'username email')
    .sort(options.sort || { createdAt: -1 })
    .limit(options.limit || 0)
    .skip(options.skip || 0);
};

// 静态方法：搜索知识条目
knowledgeSchema.statics.search = function(keyword, options = {}) {
  const query = {
    $and: [
      { isDeleted: false },
      {
        $or: [
          { title: { $regex: keyword, $options: 'i' } },
          { content: { $regex: keyword, $options: 'i' } },
          { description: { $regex: keyword, $options: 'i' } },
          { tags: { $in: [new RegExp(keyword, 'i')] } }
        ]
      }
    ]
  };
  
  if (options.isPublic !== undefined) {
    query.$and[0].isPublic = options.isPublic;
  }
  
  if (options.category) {
    query.$and[0].category = options.category;
  }
  
  return this.find(query)
    .populate('creator', 'username email')
    .populate('modifier', 'username email')
    .sort(options.sort || { relevance: -1, createdAt: -1 })
    .limit(options.limit || 0)
    .skip(options.skip || 0);
};

// 静态方法：获取热门知识条目
knowledgeSchema.statics.getPopular = function(options = {}) {
  const query = { isDeleted: false, isPublic: true };
  
  return this.find(query)
    .populate('creator', 'username email')
    .populate('modifier', 'username email')
    .sort({ viewCount: -1, createdAt: -1 })
    .limit(options.limit || 10)
    .skip(options.skip || 0);
};

module.exports = mongoose.model('Knowledge', knowledgeSchema);
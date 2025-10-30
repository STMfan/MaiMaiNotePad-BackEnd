/**
 * Knowledge Model for Cloudflare D1
 * 适配Workers运行时的知识库数据模型
 */

export class KnowledgeModel {
  constructor(database) {
    this.db = database;
  }

  /**
   * 创建知识条目
   */
  async create(knowledgeData) {
    const {
      title,
      content,
      category = 'general',
      tags = [],
      authorId,
      isPublic = true,
      metadata = {}
    } = knowledgeData;

    const sql = `
      INSERT INTO knowledge (title, content, category, tags, author_id, is_public, metadata)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `;

    const result = await this.db.run(sql, [
      title,
      content,
      category,
      JSON.stringify(tags),
      authorId,
      isPublic ? 1 : 0,
      JSON.stringify(metadata)
    ]);

    return this.findById(result.meta.last_row_id);
  }

  /**
   * 根据ID查找知识条目
   */
  async findById(id) {
    const sql = `
      SELECT k.*, u.username as author_name 
      FROM knowledge k 
      LEFT JOIN users u ON k.author_id = u.id 
      WHERE k.id = ?
    `;
    const result = await this.db.query(sql, [id]);
    
    if (result.results.length === 0) {
      return null;
    }

    return this.formatKnowledge(result.results[0]);
  }

  /**
   * 更新知识条目
   */
  async update(id, updateData) {
    // 首先创建版本历史
    const current = await this.findById(id);
    if (!current) {
      throw new Error('Knowledge item not found');
    }

    // 创建版本记录
    await this.createVersion(current);

    const fields = [];
    const values = [];

    Object.entries(updateData).forEach(([key, value]) => {
      if (key === 'tags') {
        fields.push('tags = ?');
        values.push(JSON.stringify(value));
      } else if (key === 'isPublic') {
        fields.push('is_public = ?');
        values.push(value ? 1 : 0);
      } else if (key === 'metadata') {
        fields.push('metadata = ?');
        values.push(JSON.stringify(value));
      } else {
        fields.push(`${key} = ?');
        values.push(value);
      }
    });

    if (fields.length === 0) {
      return current;
    }

    fields.push('version = version + 1');
    fields.push('updated_at = CURRENT_TIMESTAMP');
    values.push(id);

    const sql = `UPDATE knowledge SET ${fields.join(', ')} WHERE id = ?`;
    await this.db.run(sql, values);

    return this.findById(id);
  }

  /**
   * 删除知识条目
   */
  async delete(id) {
    const sql = 'DELETE FROM knowledge WHERE id = ?';
    await this.db.run(sql, [id]);
    return true;
  }

  /**
   * 获取知识条目列表
   */
  async findAll(options = {}) {
    const {
      page = 1,
      limit = 10,
      category,
      authorId,
      isPublic,
      search,
      tags
    } = options;

    let whereClause = 'WHERE 1=1';
    const params = [];

    if (category) {
      whereClause += ' AND k.category = ?';
      params.push(category);
    }

    if (authorId) {
      whereClause += ' AND k.author_id = ?';
      params.push(authorId);
    }

    if (isPublic !== undefined) {
      whereClause += ' AND k.is_public = ?';
      params.push(isPublic ? 1 : 0);
    }

    if (search) {
      whereClause += ' AND (k.title LIKE ? OR k.content LIKE ?)';
      params.push(`%${search}%`, `%${search}%`);
    }

    if (tags && tags.length > 0) {
      const tagConditions = tags.map(() => 'k.tags LIKE ?').join(' OR ');
      whereClause += ` AND (${tagConditions})`;
      tags.forEach(tag => params.push(`%"${tag}"%`));
    }

    const countSql = `
      SELECT COUNT(*) as total 
      FROM knowledge k 
      ${whereClause}
    `;
    const countResult = await this.db.query(countSql, params);
    const total = countResult.results[0].total;

    const offset = (page - 1) * limit;
    const selectSql = `
      SELECT k.*, u.username as author_name 
      FROM knowledge k 
      LEFT JOIN users u ON k.author_id = u.id 
      ${whereClause} 
      ORDER BY k.created_at DESC 
      LIMIT ? OFFSET ?
    `;
    
    const result = await this.db.query(selectSql, [...params, limit, offset]);
    
    return {
      knowledge: result.results.map(item => this.formatKnowledge(item)),
      pagination: {
        page,
        limit,
        total,
        pages: Math.ceil(total / limit)
      }
    };
  }

  /**
   * 增加浏览次数
   */
  async incrementViewCount(id) {
    const sql = 'UPDATE knowledge SET view_count = view_count + 1 WHERE id = ?';
    await this.db.run(sql, [id]);
    return true;
  }

  /**
   * 增加点赞次数
   */
  async incrementLikeCount(id) {
    const sql = 'UPDATE knowledge SET like_count = like_count + 1 WHERE id = ?';
    await this.db.run(sql, [id]);
    return true;
  }

  /**
   * 获取分类列表
   */
  async getCategories() {
    const sql = `
      SELECT category, COUNT(*) as count 
      FROM knowledge 
      WHERE category IS NOT NULL 
      GROUP BY category 
      ORDER BY count DESC
    `;
    
    const result = await this.db.query(sql);
    return result.results;
  }

  /**
   * 获取标签云
   */
  async getTags() {
    const sql = 'SELECT tags FROM knowledge WHERE tags IS NOT NULL';
    const result = await this.db.query(sql);
    
    const tagCounts = {};
    result.results.forEach(row => {
      const tags = this.safeJsonParse(row.tags, []);
      tags.forEach(tag => {
        tagCounts[tag] = (tagCounts[tag] || 0) + 1;
      });
    });

    return Object.entries(tagCounts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);
  }

  /**
   * 创建版本历史
   */
  async createVersion(knowledge) {
    const sql = `
      INSERT INTO knowledge_versions 
      (knowledge_id, title, content, category, tags, version_number, created_by)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `;

    await this.db.run(sql, [
      knowledge.id,
      knowledge.title,
      knowledge.content,
      knowledge.category,
      JSON.stringify(knowledge.tags),
      knowledge.version,
      knowledge.authorId
    ]);
  }

  /**
   * 获取版本历史
   */
  async getVersions(knowledgeId) {
    const sql = `
      SELECT kv.*, u.username as creator_name 
      FROM knowledge_versions kv 
      LEFT JOIN users u ON kv.created_by = u.id 
      WHERE kv.knowledge_id = ? 
      ORDER BY kv.version_number DESC
    `;
    
    const result = await this.db.query(sql, [knowledgeId]);
    return result.results.map(version => ({
      id: version.id,
      knowledgeId: version.knowledge_id,
      title: version.title,
      content: version.content,
      category: version.category,
      tags: this.safeJsonParse(version.tags, []),
      versionNumber: version.version_number,
      createdBy: version.created_by,
      creatorName: version.creator_name,
      createdAt: version.created_at
    }));
  }

  /**
   * 获取统计信息
   */
  async getStatistics() {
    const sql = `
      SELECT 
        COUNT(*) as total_knowledge,
        COUNT(CASE WHEN is_public = 1 THEN 1 END) as public_knowledge,
        COUNT(CASE WHEN is_public = 0 THEN 1 END) as private_knowledge,
        COUNT(CASE WHEN DATE(created_at) = DATE('now') THEN 1 END) as today_knowledge,
        SUM(view_count) as total_views,
        SUM(like_count) as total_likes,
        COUNT(DISTINCT category) as category_count,
        COUNT(DISTINCT author_id) as author_count
      FROM knowledge
    `;

    const result = await this.db.query(sql);
    return result.results[0];
  }

  /**
   * 格式化知识条目数据
   */
  formatKnowledge(knowledge) {
    if (!knowledge) return null;

    return {
      id: knowledge.id,
      title: knowledge.title,
      content: knowledge.content,
      category: knowledge.category,
      tags: this.safeJsonParse(knowledge.tags, []),
      authorId: knowledge.author_id,
      authorName: knowledge.author_name,
      isPublic: Boolean(knowledge.is_public),
      viewCount: knowledge.view_count,
      likeCount: knowledge.like_count,
      version: knowledge.version,
      parentId: knowledge.parent_id,
      metadata: this.safeJsonParse(knowledge.metadata, {}),
      createdAt: knowledge.created_at,
      updatedAt: knowledge.updated_at
    };
  }

  /**
   * 安全解析JSON
   */
  safeJsonParse(str, defaultValue = {}) {
    try {
      return str ? JSON.parse(str) : defaultValue;
    } catch (error) {
      console.error('JSON parse error:', error);
      return defaultValue;
    }
  }
}
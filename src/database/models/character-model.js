/**
 * 人设卡数据模型
 * Character Card Model
 * 
 * 管理人设卡的CRUD操作、审核状态管理、文件存储等
 */

const { db } = require('../connection');
const { logger } = require('../../utils/logger');

class CharacterModel {
  /**
   * 创建人设卡
   * @param {Object} characterData - 人设卡数据
   * @param {string} characterData.name - 人设卡名称
   * @param {string} characterData.description - 人设描述
   * @param {string} characterData.content - 人设卡内容（JSON格式）
   * @param {string} characterData.author_id - 作者用户ID
   * @param {string} characterData.file_url - 文件存储URL
   * @param {string} characterData.file_type - 文件类型
   * @param {Array} characterData.tags - 标签数组
   * @param {string} characterData.category - 分类
   * @returns {Promise<Object>} 创建的人设卡对象
   */
  static async create(characterData) {
    try {
      const query = `
        INSERT INTO characters (
          name, description, content, author_id, file_url, file_type,
          tags, category, status, created_at, updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
        RETURNING *
      `;
      
      const values = [
        characterData.name,
        characterData.description,
        characterData.content,
        characterData.author_id,
        characterData.file_url,
        characterData.file_type,
        JSON.stringify(characterData.tags || []),
        characterData.category,
        'pending' // 默认状态为待审核
      ];

      const result = await db.query(query, values);
      return result.rows[0];
    } catch (error) {
      logger.error('创建人设卡失败:', error);
      throw error;
    }
  }

  /**
   * 根据ID获取人设卡
   * @param {string} id - 人设卡ID
   * @param {boolean} includePrivate - 是否包含私有内容
   * @returns {Promise<Object|null>} 人设卡对象或null
   */
  static async getById(id, includePrivate = false) {
    try {
      let query = `
        SELECT 
          c.*,
          u.username as author_name,
          u.avatar_url as author_avatar
        FROM characters c
        JOIN users u ON c.author_id = u.id
        WHERE c.id = $1
      `;
      
      if (!includePrivate) {
        query += ' AND c.status = \'approved\'';
      }

      const result = await db.query(query, [id]);
      return result.rows[0] || null;
    } catch (error) {
      logger.error('获取人设卡失败:', error);
      throw error;
    }
  }

  /**
   * 获取人设卡列表（支持分页和筛选）
   * @param {Object} options - 查询选项
   * @param {number} options.page - 页码
   * @param {number} options.limit - 每页数量
   * @param {string} options.status - 状态筛选
   * @param {string} options.category - 分类筛选
   * @param {string} options.author_id - 作者ID筛选
   * @param {string} options.search - 搜索关键词
   * @param {string} options.sortBy - 排序字段
   * @param {string} options.sortOrder - 排序顺序
   * @returns {Promise<Object>} 人设卡列表和总数
   */
  static async getList(options = {}) {
    try {
      const {
        page = 1,
        limit = 20,
        status = 'approved',
        category,
        author_id,
        search,
        sortBy = 'created_at',
        sortOrder = 'DESC'
      } = options;

      const offset = (page - 1) * limit;
      let whereConditions = ['c.status = $1'];
      let queryParams = [status];
      let paramIndex = 1;

      // 添加筛选条件
      if (category) {
        paramIndex++;
        whereConditions.push(`c.category = $${paramIndex}`);
        queryParams.push(category);
      }

      if (author_id) {
        paramIndex++;
        whereConditions.push(`c.author_id = $${paramIndex}`);
        queryParams.push(author_id);
      }

      if (search) {
        paramIndex++;
        whereConditions.push(`(c.name ILIKE $${paramIndex} OR c.description ILIKE $${paramIndex})`);
        queryParams.push(`%${search}%`);
      }

      const whereClause = whereConditions.join(' AND ');

      // 获取总数
      const countQuery = `
        SELECT COUNT(DISTINCT c.id)
        FROM characters c
        WHERE ${whereClause}
      `;
      
      const countResult = await db.query(countQuery, queryParams);
      const total = parseInt(countResult.rows[0].count);

      // 获取列表
      const listQuery = `
        SELECT 
          c.id, c.name, c.description, c.category, c.tags,
          c.status, c.created_at, c.updated_at,
          u.username as author_name, u.avatar_url as author_avatar
        FROM characters c
        JOIN users u ON c.author_id = u.id
        WHERE ${whereClause}
        ORDER BY c.${sortBy} ${sortOrder}
        LIMIT $${paramIndex + 1} OFFSET $${paramIndex + 2}
      `;

      queryParams.push(limit, offset);
      const listResult = await db.query(listQuery, queryParams);

      return {
        items: listResult.rows,
        total,
        page,
        totalPages: Math.ceil(total / limit)
      };
    } catch (error) {
      logger.error('获取人设卡列表失败:', error);
      throw error;
    }
  }

  /**
   * 更新人设卡
   * @param {string} id - 人设卡ID
   * @param {Object} updateData - 更新数据
   * @returns {Promise<Object|null>} 更新后的人设卡对象
   */
  static async update(id, updateData) {
    try {
      const allowedFields = ['name', 'description', 'content', 'category', 'tags', 'status'];
      const fields = [];
      const values = [];
      let paramIndex = 0;

      // 构建更新字段
      for (const [key, value] of Object.entries(updateData)) {
        if (allowedFields.includes(key)) {
          if (key === 'tags') {
            paramIndex++;
            fields.push(`${key} = $${paramIndex}`);
            values.push(JSON.stringify(value));
          } else {
            paramIndex++;
            fields.push(`${key} = $${paramIndex}`);
            values.push(value);
          }
        }
      }

      if (fields.length === 0) {
        throw new Error('没有有效的更新字段');
      }

      paramIndex++;
      fields.push(`updated_at = $${paramIndex}`);
      values.push(new Date());

      paramIndex++;
      const query = `
        UPDATE characters 
        SET ${fields.join(', ')}
        WHERE id = $${paramIndex}
        RETURNING *
      `;
      values.push(id);

      const result = await db.query(query, values);
      return result.rows[0] || null;
    } catch (error) {
      logger.error('更新人设卡失败:', error);
      throw error;
    }
  }

  /**
   * 删除人设卡
   * @param {string} id - 人设卡ID
   * @returns {Promise<boolean>} 是否删除成功
   */
  static async delete(id) {
    try {
      const query = 'DELETE FROM characters WHERE id = $1 RETURNING id';
      const result = await db.query(query, [id]);
      return result.rows.length > 0;
    } catch (error) {
      logger.error('删除人设卡失败:', error);
      throw error;
    }
  }

  /**
   * 更新审核状态
   * @param {string} id - 人设卡ID
   * @param {string} status - 新状态 (pending, approved, rejected)
   * @param {string} reviewed_by - 审核员ID
   * @param {string} review_note - 审核备注
   * @returns {Promise<Object|null>} 更新后的人设卡对象
   */
  static async updateStatus(id, status, reviewed_by, review_note = '') {
    try {
      const query = `
        UPDATE characters 
        SET 
          status = $1,
          reviewed_by = $2,
          review_note = $3,
          reviewed_at = NOW(),
          updated_at = NOW()
        WHERE id = $4
        RETURNING *
      `;
      
      const result = await db.query(query, [status, reviewed_by, review_note, id]);
      return result.rows[0] || null;
    } catch (error) {
      logger.error('更新人设卡审核状态失败:', error);
      throw error;
    }
  }

  /**
   * 获取待审核的人设卡列表
   * @param {Object} options - 查询选项
   * @returns {Promise<Object>} 待审核人设卡列表
   */
  static async getPendingList(options = {}) {
    try {
      const { page = 1, limit = 20 } = options;
      const offset = (page - 1) * limit;

      const query = `
        SELECT 
          c.id, c.name, c.description, c.category, c.tags,
          c.created_at, c.status,
          u.username as author_name, u.email as author_email
        FROM characters c
        JOIN users u ON c.author_id = u.id
        WHERE c.status = 'pending'
        ORDER BY c.created_at ASC
        LIMIT $1 OFFSET $2
      `;

      const countQuery = `
        SELECT COUNT(*) 
        FROM characters 
        WHERE status = 'pending'
      `;

      const [listResult, countResult] = await Promise.all([
        db.query(query, [limit, offset]),
        db.query(countQuery)
      ]);

      return {
        items: listResult.rows,
        total: parseInt(countResult.rows[0].count),
        page,
        totalPages: Math.ceil(parseInt(countResult.rows[0].count) / limit)
      };
    } catch (error) {
      logger.error('获取待审核人设卡列表失败:', error);
      throw error;
    }
  }

  /**
   * 获取用户的人设卡统计
   * @param {string} userId - 用户ID
   * @returns {Promise<Object>} 统计信息
   */
  static async getUserStats(userId) {
    try {
      const query = `
        SELECT 
          COUNT(*) as total,
          COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved,
          COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
          COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected
        FROM characters
        WHERE author_id = $1
      `;

      const result = await db.query(query, [userId]);
      return result.rows[0];
    } catch (error) {
      logger.error('获取用户人设卡统计失败:', error);
      throw error;
    }
  }

  /**
   * 获取分类列表
   * @returns {Promise<Array>} 分类列表
   */
  static async getCategories() {
    try {
      const query = `
        SELECT DISTINCT category, COUNT(*) as count
        FROM characters
        WHERE status = 'approved'
        GROUP BY category
        ORDER BY count DESC
      `;

      const result = await db.query(query);
      return result.rows;
    } catch (error) {
      logger.error('获取人设卡分类列表失败:', error);
      throw error;
    }
  }

  /**
   * 获取标签云
   * @param {number} limit - 限制数量
   * @returns {Promise<Array>} 标签云数据
   */
  static async getTagCloud(limit = 50) {
    try {
      const query = `
        SELECT tag, COUNT(*) as count
        FROM (
          SELECT jsonb_array_elements_text(tags) as tag
          FROM characters
          WHERE status = 'approved'
        ) as tags
        GROUP BY tag
        ORDER BY count DESC
        LIMIT $1
      `;

      const result = await db.query(query, [limit]);
      return result.rows;
    } catch (error) {
      logger.error('获取人设卡标签云失败:', error);
      throw error;
    }
  }

  /**
   * 增加浏览次数
   * @param {string} id - 人设卡ID
   * @returns {Promise<void>}
   */
  static async incrementViewCount(id) {
    try {
      const query = `
        UPDATE characters 
        SET view_count = view_count + 1 
        WHERE id = $1
      `;
      await db.query(query, [id]);
    } catch (error) {
      logger.error('增加浏览次数失败:', error);
      // 不抛出错误，避免影响主流程
    }
  }
}

module.exports = CharacterModel;
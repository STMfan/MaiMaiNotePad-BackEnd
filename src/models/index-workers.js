/**
 * Models Index for Cloudflare Workers
 * Exports all D1-compatible models
 */

import { User, UserModel, createUserModel } from './User-workers.js';
import { Note, NoteVersion, NoteShare, NoteModel, createNoteModel } from './Note-workers.js';
import { File, FileShare, FileModel, createFileModel } from './File-workers.js';
import { Tag, NoteTag, FileTag, TagModel, createTagModel } from './Tag-workers.js';

/**
 * Models Collection
 */
const Models = {
  User,
  UserModel,
  Note,
  NoteVersion,
  NoteShare,
  NoteModel,
  File,
  FileShare,
  FileModel,
  Tag,
  NoteTag,
  FileTag,
  TagModel
};

/**
 * Model Factory Functions
 */
const ModelFactories = {
  createUserModel,
  createNoteModel,
  createFileModel,
  createTagModel
};

/**
 * Initialize all model tables
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Initialization results
 */
export async function initializeAllModels(env) {
  const results = {
    success: true,
    errors: [],
    models: []
  };

  try {
    // Initialize each model
    const models = [
      { name: 'User', factory: createUserModel },
      { name: 'Note', factory: createNoteModel },
      { name: 'File', factory: createFileModel },
      { name: 'Tag', factory: createTagModel }
    ];

    for (const model of models) {
      try {
        const modelInstance = model.factory(env);
        await modelInstance.initializeTables();
        results.models.push({
          name: model.name,
          status: 'initialized'
        });
      } catch (error) {
        results.models.push({
          name: model.name,
          status: 'failed',
          error: error.message
        });
        results.errors.push({
          model: model.name,
          error: error.message
        });
      }
    }

    // If any model failed, set overall success to false
    if (results.errors.length > 0) {
      results.success = false;
    }

    return results;
  } catch (error) {
    console.error('Initialize all models error:', error);
    return {
      success: false,
      errors: [{
        model: 'initialization',
        error: error.message
      }],
      models: []
    };
  }
}

/**
 * Get all model instances
 * @param {Object} env - Environment variables
 * @returns {Object} Model instances
 */
export function getModelInstances(env) {
  return {
    userModel: createUserModel(env),
    noteModel: createNoteModel(env),
    fileModel: createFileModel(env),
    tagModel: createTagModel(env)
  };
}

/**
 * Get models (alias for getModelInstances)
 * @param {Object} env - Environment variables
 * @returns {Object} Model instances
 */
export function getModels(env) {
  return getModelInstances(env);
}

/**
 * Model validation utilities
 */
export const ModelUtils = {
  /**
   * Validate model data
   * @param {string} modelType - Type of model (user, note, file, tag)
   * @param {Object} data - Data to validate
   * @returns {Object} Validation result
   */
  validateModelData(modelType, data) {
    const validators = {
      user: (data) => {
        const errors = [];
        if (!data.username || data.username.length < 3) {
          errors.push('Username must be at least 3 characters');
        }
        if (!data.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) {
          errors.push('Valid email is required');
        }
        if (data.password && data.password.length < 6) {
          errors.push('Password must be at least 6 characters');
        }
        return { isValid: errors.length === 0, errors };
      },
      
      note: (data) => {
        const errors = [];
        if (!data.title || data.title.trim().length === 0) {
          errors.push('Title is required');
        }
        if (data.content && typeof data.content !== 'string') {
          errors.push('Content must be a string');
        }
        return { isValid: errors.length === 0, errors };
      },
      
      file: (data) => {
        const errors = [];
        if (!data.filename || data.filename.trim().length === 0) {
          errors.push('Filename is required');
        }
        if (!data.file_size || data.file_size <= 0) {
          errors.push('Valid file size is required');
        }
        return { isValid: errors.length === 0, errors };
      },
      
      tag: (data) => {
        const errors = [];
        if (!data.name || !Tag.isValidName(data.name)) {
          errors.push('Valid tag name is required (1-50 characters, alphanumeric, spaces, hyphens, underscores)');
        }
        return { isValid: errors.length === 0, errors };
      }
    };

    const validator = validators[modelType];
    if (!validator) {
      return { isValid: false, errors: ['Unknown model type'] };
    }

    return validator(data);
  },

  /**
   * Sanitize model data
   * @param {string} modelType - Type of model
   * @param {Object} data - Data to sanitize
   * @returns {Object} Sanitized data
   */
  sanitizeModelData(modelType, data) {
    const sanitizers = {
      user: (data) => ({
        username: data.username?.trim().toLowerCase(),
        email: data.email?.trim().toLowerCase(),
        full_name: data.full_name?.trim(),
        bio: data.bio?.trim(),
        avatar_url: data.avatar_url?.trim(),
        is_active: data.is_active,
        role: data.role
      }),
      
      note: (data) => ({
        title: data.title?.trim(),
        content: data.content?.trim(),
        is_public: data.is_public,
        is_pinned: data.is_pinned,
        folder: data.folder?.trim()
      }),
      
      file: (data) => ({
        filename: data.filename?.trim(),
        original_filename: data.original_filename?.trim(),
        mime_type: data.mime_type?.trim(),
        file_size: data.file_size,
        folder: data.folder?.trim(),
        is_public: data.is_public
      }),
      
      tag: (data) => ({
        name: Tag.normalizeName(data.name),
        color: data.color?.trim(),
        description: data.description?.trim()
      })
    };

    const sanitizer = sanitizers[modelType];
    if (!sanitizer) {
      return data;
    }

    return sanitizer(data);
  }
};

export {
  User,
  UserModel,
  createUserModel,
  Note,
  NoteVersion,
  NoteShare,
  NoteModel,
  createNoteModel,
  File,
  FileShare,
  FileModel,
  createFileModel,
  Tag,
  NoteTag,
  FileTag,
  TagModel,
  createTagModel
};

export default {
  Models,
  ModelFactories,
  initializeAllModels,
  getModelInstances,
  ModelUtils,
  User,
  UserModel,
  Note,
  NoteModel,
  File,
  FileModel,
  Tag,
  TagModel
};
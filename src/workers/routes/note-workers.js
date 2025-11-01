/**
 * Note management routes for Cloudflare Workers
 */

export async function handleNoteRoutes(context, ...params) {
  const { request, env, config, log } = context;
  const url = new URL(request.url);
  const path = url.pathname;
  const method = request.method;
  
  try {
    // Route to specific note handlers
    if (path === '/api/notes' && method === 'GET') {
      return await handleGetNotes(context);
    } else if (path === '/api/notes' && method === 'POST') {
      return await handleCreateNote(context);
    } else if (path.includes('/share') && method === 'POST') {
      const noteId = params[0];
      return await handleShareNote(context, noteId);
    } else if (path.includes('/tags') && method === 'PUT') {
      const noteId = params[0];
      return await handleUpdateNoteTags(context, noteId);
    } else if (path.includes('/shared/') && method === 'GET') {
      const shareId = params[0];
      return await handleGetSharedNote(context, shareId);
    } else if (path.match(/^\/api\/notes\/([^\/]+)$/) && method === 'GET') {
      const noteId = params[0];
      return await handleGetNote(context, noteId);
    } else if (path.match(/^\/api\/notes\/([^\/]+)$/) && method === 'PUT') {
      const noteId = params[0];
      return await handleUpdateNote(context, noteId);
    } else if (path.match(/^\/api\/notes\/([^\/]+)$/) && method === 'DELETE') {
      const noteId = params[0];
      return await handleDeleteNote(context, noteId);
    }
    
    return new Response(JSON.stringify({ 
      error: 'Not Found',
      message: 'Note endpoint not found'
    }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Note route error', { error: error.message, path, method });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Note service error'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleGetNotes(context) {
  const { request, env, config, log } = context;
  
  try {
    // Verify authentication
    const userId = await getUserIdFromToken(request, config);
    if (!userId) {
      return new Response(JSON.stringify({ 
        error: 'Unauthorized',
        message: 'Invalid or expired token'
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const limit = parseInt(url.searchParams.get('limit') || '10');
    const search = url.searchParams.get('search') || '';
    const tag = url.searchParams.get('tag') || '';
    
    // Get notes from KV
    if (env.KV) {
      const userNotesKey = `user:${userId}:notes`;
      const notesData = await env.KV.get(userNotesKey);
      
      let notes = [];
      if (notesData) {
        notes = JSON.parse(notesData);
      }
      
      // Apply filters
      if (search) {
        notes = notes.filter(note => 
          note.title.toLowerCase().includes(search.toLowerCase()) ||
          note.content.toLowerCase().includes(search.toLowerCase())
        );
      }
      
      if (tag) {
        notes = notes.filter(note => 
          note.tags && note.tags.includes(tag)
        );
      }
      
      // Pagination
      const startIndex = (page - 1) * limit;
      const endIndex = startIndex + limit;
      const paginatedNotes = notes.slice(startIndex, endIndex);
      
      return new Response(JSON.stringify({
        notes: paginatedNotes,
        pagination: {
          page,
          limit,
          total: notes.length,
          pages: Math.ceil(notes.length / limit)
        }
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Fallback response with demo data
    const demoNotes = [
      {
        id: 'note-1',
        title: 'Welcome to MaiMai NotePad',
        content: 'This is your first note! Start creating amazing content.',
        tags: ['welcome', 'tutorial'],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        user_id: userId
      },
      {
        id: 'note-2',
        title: 'Getting Started',
        content: 'Learn how to use all the features of MaiMai NotePad.',
        tags: ['tutorial'],
        created_at: new Date(Date.now() - 86400000).toISOString(),
        updated_at: new Date(Date.now() - 86400000).toISOString(),
        user_id: userId
      }
    ];
    
    return new Response(JSON.stringify({
      notes: demoNotes,
      pagination: {
        page: 1,
        limit: 10,
        total: 2,
        pages: 1
      }
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Get notes error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to get notes'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleCreateNote(context) {
  const { request, env, config, log } = context;
  
  try {
    // Verify authentication
    const userId = await getUserIdFromToken(request, config);
    if (!userId) {
      return new Response(JSON.stringify({ 
        error: 'Unauthorized',
        message: 'Invalid or expired token'
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const body = await request.json();
    const { title, content, tags = [] } = body;
    
    if (!title || !content) {
      return new Response(JSON.stringify({ 
        error: 'Bad Request',
        message: 'Title and content are required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const noteId = crypto.randomUUID();
    const now = new Date().toISOString();
    
    const newNote = {
      id: noteId,
      title,
      content,
      tags: Array.isArray(tags) ? tags : [],
      created_at: now,
      updated_at: now,
      user_id: userId
    };
    
    // Store note in KV
    if (env.KV) {
      const userNotesKey = `user:${userId}:notes`;
      let notes = [];
      
      const existingNotes = await env.KV.get(userNotesKey);
      if (existingNotes) {
        notes = JSON.parse(existingNotes);
      }
      
      notes.unshift(newNote); // Add to beginning
      await env.KV.put(userNotesKey, JSON.stringify(notes));
      
      // Also store individual note
      await env.KV.put(`note:${noteId}`, JSON.stringify(newNote));
    }
    
    return new Response(JSON.stringify({
      message: 'Note created successfully',
      note: newNote
    }), {
      status: 201,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Create note error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to create note'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleGetNote(context, noteId) {
  const { request, env, config, log } = context;
  
  try {
    // Verify authentication
    const userId = await getUserIdFromToken(request, config);
    if (!userId) {
      return new Response(JSON.stringify({ 
        error: 'Unauthorized',
        message: 'Invalid or expired token'
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Get note from KV
    if (env.KV) {
      const noteData = await env.KV.get(`note:${noteId}`);
      if (noteData) {
        const note = JSON.parse(noteData);
        
        // Verify note belongs to user
        if (note.user_id !== userId) {
          return new Response(JSON.stringify({ 
            error: 'Forbidden',
            message: 'Access denied to this note'
          }), {
            status: 403,
            headers: { 'Content-Type': 'application/json' }
          });
        }
        
        return new Response(JSON.stringify({ note }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }
    
    return new Response(JSON.stringify({ 
      error: 'Not Found',
      message: 'Note not found'
    }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Get note error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to get note'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleUpdateNote(context, noteId) {
  const { request, env, config, log } = context;
  
  try {
    // Verify authentication
    const userId = await getUserIdFromToken(request, config);
    if (!userId) {
      return new Response(JSON.stringify({ 
        error: 'Unauthorized',
        message: 'Invalid or expired token'
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const body = await request.json();
    const { title, content, tags } = body;
    
    if (!title && !content && !tags) {
      return new Response(JSON.stringify({ 
        error: 'Bad Request',
        message: 'Title, content, or tags must be provided for update'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Get existing note
    if (env.KV) {
      const noteData = await env.KV.get(`note:${noteId}`);
      if (noteData) {
        const note = JSON.parse(noteData);
        
        // Verify note belongs to user
        if (note.user_id !== userId) {
          return new Response(JSON.stringify({ 
            error: 'Forbidden',
            message: 'Access denied to this note'
          }), {
            status: 403,
            headers: { 'Content-Type': 'application/json' }
          });
        }
        
        // Update note
        if (title) note.title = title;
        if (content) note.content = content;
        if (tags !== undefined) note.tags = Array.isArray(tags) ? tags : [];
        note.updated_at = new Date().toISOString();
        
        // Save updated note
        await env.KV.put(`note:${noteId}`, JSON.stringify(note));
        
        // Update in user's notes list
        const userNotesKey = `user:${userId}:notes`;
        const existingNotes = await env.KV.get(userNotesKey);
        if (existingNotes) {
          const notes = JSON.parse(existingNotes);
          const noteIndex = notes.findIndex(n => n.id === noteId);
          if (noteIndex !== -1) {
            notes[noteIndex] = note;
            await env.KV.put(userNotesKey, JSON.stringify(notes));
          }
        }
        
        return new Response(JSON.stringify({
          message: 'Note updated successfully',
          note
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }
    
    return new Response(JSON.stringify({ 
      error: 'Not Found',
      message: 'Note not found'
    }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Update note error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to update note'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleDeleteNote(context, noteId) {
  const { request, env, config, log } = context;
  
  try {
    // Verify authentication
    const userId = await getUserIdFromToken(request, config);
    if (!userId) {
      return new Response(JSON.stringify({ 
        error: 'Unauthorized',
        message: 'Invalid or expired token'
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Get existing note
    if (env.KV) {
      const noteData = await env.KV.get(`note:${noteId}`);
      if (noteData) {
        const note = JSON.parse(noteData);
        
        // Verify note belongs to user
        if (note.user_id !== userId) {
          return new Response(JSON.stringify({ 
            error: 'Forbidden',
            message: 'Access denied to this note'
          }), {
            status: 403,
            headers: { 'Content-Type': 'application/json' }
          });
        }
        
        // Delete note
        await env.KV.delete(`note:${noteId}`);
        
        // Remove from user's notes list
        const userNotesKey = `user:${userId}:notes`;
        const existingNotes = await env.KV.get(userNotesKey);
        if (existingNotes) {
          const notes = JSON.parse(existingNotes);
          const filteredNotes = notes.filter(n => n.id !== noteId);
          await env.KV.put(userNotesKey, JSON.stringify(filteredNotes));
        }
        
        return new Response(JSON.stringify({
          message: 'Note deleted successfully'
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }
    
    return new Response(JSON.stringify({ 
      error: 'Not Found',
      message: 'Note not found'
    }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Delete note error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to delete note'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleShareNote(context, noteId) {
  const { request, env, config, log } = context;
  
  try {
    // Verify authentication
    const userId = await getUserIdFromToken(request, config);
    if (!userId) {
      return new Response(JSON.stringify({ 
        error: 'Unauthorized',
        message: 'Invalid or expired token'
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Get existing note
    if (env.KV) {
      const noteData = await env.KV.get(`note:${noteId}`);
      if (noteData) {
        const note = JSON.parse(noteData);
        
        // Verify note belongs to user
        if (note.user_id !== userId) {
          return new Response(JSON.stringify({ 
            error: 'Forbidden',
            message: 'Access denied to this note'
          }), {
            status: 403,
            headers: { 'Content-Type': 'application/json' }
          });
        }
        
        // Generate share ID
        const shareId = crypto.randomUUID();
        const shareData = {
          note_id: noteId,
          user_id: userId,
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString() // 7 days
        };
        
        // Store share link
        await env.KV.put(`share:${shareId}`, JSON.stringify(shareData));
        
        return new Response(JSON.stringify({
          message: 'Note shared successfully',
          share_link: `/api/notes/shared/${shareId}`
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }
    
    return new Response(JSON.stringify({ 
      error: 'Not Found',
      message: 'Note not found'
    }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Share note error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to share note'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleUpdateNoteTags(context, noteId) {
  const { request, env, config, log } = context;
  
  try {
    // Verify authentication
    const userId = await getUserIdFromToken(request, config);
    if (!userId) {
      return new Response(JSON.stringify({ 
        error: 'Unauthorized',
        message: 'Invalid or expired token'
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const body = await request.json();
    const { tags } = body;
    
    if (!Array.isArray(tags)) {
      return new Response(JSON.stringify({ 
        error: 'Bad Request',
        message: 'Tags must be an array'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Get existing note
    if (env.KV) {
      const noteData = await env.KV.get(`note:${noteId}`);
      if (noteData) {
        const note = JSON.parse(noteData);
        
        // Verify note belongs to user
        if (note.user_id !== userId) {
          return new Response(JSON.stringify({ 
            error: 'Forbidden',
            message: 'Access denied to this note'
          }), {
            status: 403,
            headers: { 'Content-Type': 'application/json' }
          });
        }
        
        // Update tags
        note.tags = tags;
        note.updated_at = new Date().toISOString();
        
        // Save updated note
        await env.KV.put(`note:${noteId}`, JSON.stringify(note));
        
        return new Response(JSON.stringify({
          message: 'Note tags updated successfully',
          note
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }
    
    return new Response(JSON.stringify({ 
      error: 'Not Found',
      message: 'Note not found'
    }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Update note tags error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to update note tags'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleGetSharedNote(context, shareId) {
  const { request, env, config, log } = context;
  
  try {
    // Get share link data
    if (env.KV) {
      const shareData = await env.KV.get(`share:${shareId}`);
      if (shareData) {
        const share = JSON.parse(shareData);
        
        // Check if share link has expired
        if (new Date(share.expires_at) < new Date()) {
          return new Response(JSON.stringify({ 
            error: 'Gone',
            message: 'Share link has expired'
          }), {
            status: 410,
            headers: { 'Content-Type': 'application/json' }
          });
        }
        
        // Get the note
        const noteData = await env.KV.get(`note:${share.note_id}`);
        if (noteData) {
          const note = JSON.parse(noteData);
          
          return new Response(JSON.stringify({ 
            note: {
              id: note.id,
              title: note.title,
              content: note.content,
              tags: note.tags,
              created_at: note.created_at,
              updated_at: note.updated_at
            }
          }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
          });
        }
      }
    }
    
    return new Response(JSON.stringify({ 
      error: 'Not Found',
      message: 'Shared note not found'
    }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    log.error('Get shared note error', { error: error.message });
    return new Response(JSON.stringify({ 
      error: 'Internal Server Error',
      message: 'Failed to get shared note'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// Helper functions
async function getUserIdFromToken(request, config) {
  const authHeader = request.headers.get('Authorization');
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return null;
  }
  
  const token = authHeader.substring(7);
  // In a real app, validate the JWT token and extract user ID
  // For now, return a demo user ID
  return 'demo-user-id';
}
/**
 * Simple KV-based API routes for basic functionality
 * This provides a fallback when D1/R2 are not configured
 */

export async function handleKVApiRoutes(request, env, config) {
  const url = new URL(request.url);
  const path = url.pathname;
  const method = request.method;
  
  try {
    // Simple notes API using KV storage
    if (path.startsWith('/api/notes')) {
      return await handleNotesAPI(request, env, config);
    }
    
    // Simple user profile API using KV storage
    if (path.startsWith('/api/users/profile')) {
      return await handleUserProfileAPI(request, env, config);
    }
    
    // System status endpoint
    if (path === '/api/system/status') {
      return await handleSystemStatus(request, env, config);
    }
    
    // API root
    if (path === '/api') {
      return new Response(JSON.stringify({
        name: 'MaiMaiNotePad API',
        version: config.get('API_VERSION'),
        environment: config.get('ENVIRONMENT'),
        features: ['kv_storage', 'basic_notes', 'user_profiles'],
        endpoints: [
          'GET /api/notes',
          'POST /api/notes',
          'GET /api/users/profile',
          'PUT /api/users/profile',
          'GET /api/system/status'
        ]
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    return null; // Route not handled
  } catch (error) {
    console.error('KV API error:', error);
    return new Response(JSON.stringify({
      error: 'Internal server error',
      message: error.message
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleNotesAPI(request, env, config) {
  const url = new URL(request.url);
  const method = request.method;
  const userId = 'demo_user'; // Simple demo user for now
  
  try {
    if (method === 'GET') {
      // Get all notes for user
      const notesKey = `notes:${userId}`;
      const notesData = await env.KV.get(notesKey);
      const notes = notesData ? JSON.parse(notesData) : [];
      
      return new Response(JSON.stringify({
        notes: notes,
        total: notes.length
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'POST') {
      // Create new note
      const body = await request.json();
      const { title, content } = body;
      
      if (!title || !content) {
        return new Response(JSON.stringify({
          error: 'Title and content are required'
        }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      
      const notesKey = `notes:${userId}`;
      const notesData = await env.KV.get(notesKey);
      const notes = notesData ? JSON.parse(notesData) : [];
      
      const newNote = {
        id: Date.now().toString(),
        title,
        content,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      
      notes.push(newNote);
      await env.KV.put(notesKey, JSON.stringify(notes));
      
      return new Response(JSON.stringify(newNote), {
        status: 201,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    return new Response(JSON.stringify({
      error: 'Method not allowed'
    }), {
      status: 405,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    console.error('Notes API error:', error);
    return new Response(JSON.stringify({
      error: 'Failed to process notes'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleUserProfileAPI(request, env, config) {
  const method = request.method;
  const userId = 'demo_user'; // Simple demo user for now
  
  try {
    const profileKey = `profile:${userId}`;
    
    if (method === 'GET') {
      // Get user profile
      const profileData = await env.KV.get(profileKey);
      const profile = profileData ? JSON.parse(profileData) : {
        id: userId,
        username: 'demo_user',
        email: 'demo@example.com',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      
      return new Response(JSON.stringify(profile), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'PUT') {
      // Update user profile
      const body = await request.json();
      const profileData = await env.KV.get(profileKey);
      const currentProfile = profileData ? JSON.parse(profileData) : {
        id: userId,
        username: 'demo_user',
        email: 'demo@example.com',
        created_at: new Date().toISOString()
      };
      
      const updatedProfile = {
        ...currentProfile,
        ...body,
        id: userId,
        updated_at: new Date().toISOString()
      };
      
      await env.KV.put(profileKey, JSON.stringify(updatedProfile));
      
      return new Response(JSON.stringify(updatedProfile), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    return new Response(JSON.stringify({
      error: 'Method not allowed'
    }), {
      status: 405,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    console.error('User profile API error:', error);
    return new Response(JSON.stringify({
      error: 'Failed to process user profile'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function handleSystemStatus(request, env, config) {
  try {
    // Check KV connection
    const kvCheck = await env.KV.get('health:check', 'text');
    
    const status = {
      status: 'operational',
      timestamp: new Date().toISOString(),
      version: config.get('API_VERSION'),
      environment: config.get('ENVIRONMENT'),
      services: {
        kv: kvCheck !== null ? 'healthy' : 'unhealthy',
        database: 'not_configured',
        storage: 'not_configured'
      },
      features: ['kv_storage', 'basic_notes', 'user_profiles']
    };
    
    return new Response(JSON.stringify(status), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    console.error('System status error:', error);
    return new Response(JSON.stringify({
      status: 'error',
      timestamp: new Date().toISOString(),
      error: error.message
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
#!/usr/bin/env node

/**
 * MaiMaiNotePad Database Migration Script Runner
 * 
 * This script automates the execution of database migration scripts
 * for Cloudflare Workers D1 database.
 */

import { execSync } from 'child_process';
import { readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Configuration
const MIGRATION_DIR = join(__dirname, '../migrations');
const WRANGLER_CONFIG = 'wrangler.toml';
const DATABASE_NAME = 'maimai-notepad-db';

// Migration files in execution order
const MIGRATION_FILES = [
    '001_create_tables.sql',
    '002_data_migration.sql',
    '003_migration_utils.sql'
];

// Colors for console output
const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    cyan: '\x1b[36m'
};

/**
 * Log messages with colors
 */
function log(message, color = 'reset') {
    console.log(`${colors[color]}${message}${colors.reset}`);
}

/**
 * Check if wrangler is installed and configured
 */
function checkWrangler() {
    try {
        execSync('wrangler --version', { stdio: 'pipe' });
        return true;
    } catch (error) {
        return false;
    }
}

/**
 * Check if wrangler.toml exists
 */
function checkWranglerConfig() {
    return existsSync(WRANGLER_CONFIG);
}

/**
 * Execute a single migration file
 */
async function executeMigrationFile(filename) {
    const filePath = join(MIGRATION_DIR, filename);
    
    if (!existsSync(filePath)) {
        throw new Error(`Migration file not found: ${filename}`);
    }

    log(`Executing migration: ${filename}`, 'cyan');
    
    try {
        // Read the SQL file
        const sqlContent = readFileSync(filePath, 'utf8');
        
        // Split SQL content into individual statements
        const statements = sqlContent
            .split(';')
            .map(stmt => stmt.trim())
            .filter(stmt => stmt.length > 0)
            .filter(stmt => !stmt.startsWith('--'));

        log(`  Found ${statements.length} SQL statements`, 'blue');

        // Execute each statement
        for (let i = 0; i < statements.length; i++) {
            const statement = statements[i];
            const statementNumber = i + 1;
            
            try {
                // Use wrangler to execute the SQL statement
                const command = `wrangler d1 execute ${DATABASE_NAME} --command "${statement.replace(/"/g, '\\"')}"`;
                execSync(command, { stdio: 'pipe' });
                log(`  ✓ Statement ${statementNumber}/${statements.length} executed`, 'green');
            } catch (error) {
                log(`  ✗ Statement ${statementNumber}/${statements.length} failed: ${error.message}`, 'red');
                throw new Error(`Migration failed at statement ${statementNumber}: ${statement}`);
            }
        }

        log(`  ✓ Migration ${filename} completed successfully`, 'green');
        return true;
    } catch (error) {
        log(`  ✗ Migration ${filename} failed: ${error.message}`, 'red');
        throw error;
    }
}

/**
 * Execute all migration files
 */
async function runMigrations() {
    log('Starting database migration process...', 'bright');
    log('=====================================', 'bright');

    let successCount = 0;
    let failureCount = 0;

    for (const filename of MIGRATION_FILES) {
        try {
            await executeMigrationFile(filename);
            successCount++;
        } catch (error) {
            log(`Migration process stopped due to error in ${filename}`, 'red');
            log(`Error: ${error.message}`, 'red');
            failureCount++;
            break;
        }
    }

    log('', 'reset');
    log('Migration Summary', 'bright');
    log('=================', 'bright');
    log(`Total migrations: ${MIGRATION_FILES.length}`, 'blue');
    log(`Successful: ${successCount}`, 'green');
    log(`Failed: ${failureCount}`, failureCount > 0 ? 'red' : 'green');

    return failureCount === 0;
}

/**
 * Generate migration report
 */
async function generateMigrationReport() {
    log('Generating migration report...', 'cyan');
    
    const reportQueries = [
        {
            name: 'User Statistics',
            query: 'SELECT COUNT(*) as total_users, COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_users, COUNT(CASE WHEN email_verified = 1 THEN 1 END) as verified_users FROM users;'
        },
        {
            name: 'Note Statistics',
            query: 'SELECT COUNT(*) as total_notes, COUNT(CASE WHEN is_public = 1 THEN 1 END) as public_notes, AVG(word_count) as avg_word_count FROM notes;'
        },
        {
            name: 'File Statistics',
            query: 'SELECT COUNT(*) as total_files, SUM(file_size) as total_size, AVG(file_size) as avg_size FROM files;'
        },
        {
            name: 'System Settings',
            query: 'SELECT COUNT(*) as total_settings FROM system_settings;'
        },
        {
            name: 'Database Size',
            query: "SELECT name, sql FROM sqlite_master WHERE type='table';"
        }
    ];

    log('\nMigration Report', 'bright');
    log('================', 'bright');

    for (const query of reportQueries) {
        try {
            const command = `wrangler d1 execute ${DATABASE_NAME} --command "${query.query}"`;
            const result = execSync(command, { encoding: 'utf8' });
            
            log(`\n${query.name}:`, 'cyan');
            log(result, 'reset');
        } catch (error) {
            log(`Failed to execute query for ${query.name}: ${error.message}`, 'yellow');
        }
    }
}

/**
 * Rollback migration (drop all tables)
 */
async function rollbackMigrations() {
    log('WARNING: This will drop all tables and data!', 'red');
    log('Are you sure you want to continue? (yes/no)', 'yellow');

    // In a real implementation, you would read user input here
    // For now, we'll just log the rollback SQL
    
    const rollbackSQL = `
        -- Drop all tables in reverse order (respect foreign key constraints)
        DROP TABLE IF EXISTS webhook_deliveries;
        DROP TABLE IF EXISTS file_upload_sessions;
        DROP TABLE IF EXISTS api_rate_limits;
        DROP TABLE IF EXISTS statistics;
        DROP TABLE IF EXISTS backup_metadata;
        DROP TABLE IF EXISTS file_tags;
        DROP TABLE IF EXISTS note_tags;
        DROP TABLE IF EXISTS file_shares;
        DROP TABLE IF EXISTS user_sessions;
        DROP TABLE IF EXISTS user_preferences;
        DROP TABLE IF EXISTS audit_logs;
        DROP TABLE IF EXISTS system_settings;
        DROP TABLE IF EXISTS files;
        DROP TABLE IF EXISTS notes;
        DROP TABLE IF EXISTS tags;
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS files_staging;
        DROP TABLE IF EXISTS notes_staging;
        DROP TABLE IF EXISTS users_staging;
        DROP TABLE IF EXISTS migration_validation_logs;
    `;

    log('Rollback SQL generated (not executed):', 'cyan');
    log(rollbackSQL, 'reset');
}

/**
 * Main function
 */
async function main() {
    try {
        // Check prerequisites
        if (!checkWrangler()) {
            log('Error: wrangler CLI is not installed or not in PATH', 'red');
            log('Please install wrangler: npm install -g wrangler', 'yellow');
            process.exit(1);
        }

        if (!checkWranglerConfig()) {
            log('Error: wrangler.toml not found in current directory', 'red');
            log('Please run this script from the project root directory', 'yellow');
            process.exit(1);
        }

        // Parse command line arguments
        const args = process.argv.slice(2);
        const command = args[0];

        switch (command) {
            case 'migrate':
                const success = await runMigrations();
                if (success) {
                    await generateMigrationReport();
                    log('\n✓ All migrations completed successfully!', 'green');
                } else {
                    log('\n✗ Migration process failed!', 'red');
                    process.exit(1);
                }
                break;

            case 'rollback':
                await rollbackMigrations();
                break;

            case 'report':
                await generateMigrationReport();
                break;

            case 'help':
            default:
                log('MaiMaiNotePad Database Migration Tool', 'bright');
                log('=====================================', 'bright');
                log('Usage: node migrate.js [command]', 'cyan');
                log('', 'reset');
                log('Commands:', 'bright');
                log('  migrate  - Run all migration files', 'green');
                log('  rollback - Generate rollback SQL (manual execution required)', 'yellow');
                log('  report   - Generate migration report', 'blue');
                log('  help     - Show this help message', 'cyan');
                log('', 'reset');
                log('Prerequisites:', 'bright');
                log('  - wrangler CLI must be installed and configured', 'reset');
                log('  - wrangler.toml must exist in current directory', 'reset');
                log('  - D1 database must be configured in wrangler.toml', 'reset');
                break;
        }

    } catch (error) {
        log(`Error: ${error.message}`, 'red');
        process.exit(1);
    }
}

// Run the main function
main().catch(error => {
    log(`Unhandled error: ${error.message}`, 'red');
    process.exit(1);
});
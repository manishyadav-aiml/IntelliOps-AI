import { spawn, spawnSync } from 'node:child_process'
import { mkdirSync, rmSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const frontendDir = path.resolve(scriptDir, '..')
const backendDir = path.resolve(frontendDir, '..', 'backend')

const python = path.join(
  backendDir,
  '.venv',
  'Scripts',
  'python.exe',
)

const env = {
  ...process.env,

  APP_ENV: 'development',
  DEBUG: 'true',

  DATABASE_URL: 'sqlite:///./e2e.db',
  JWT_SECRET: 'e2e-only-secret-e2e-only-secret-123456',

  RATE_LIMIT_ENABLED: 'false',

  EMBEDDING_MODEL: 'hashing',
  LOG_TEMPLATE_MINER: 'regex',

  GEMINI_API_KEY: '',

  UPLOAD_DIR: '../data/e2e_uploads',
  MODELS_DIR: '../data/e2e_models',
  INDEX_DIR: '../data/e2e_models/indexes',
  REPORTS_DIR: '../data/e2e_reports',
}

// Create isolated E2E directories.
for (const directory of [
  '../data/e2e_uploads',
  '../data/e2e_models/indexes',
  '../data/e2e_reports',
]) {
  mkdirSync(path.resolve(backendDir, directory), {
    recursive: true,
  })
}

// Remove only the previous E2E database.
rmSync(path.join(backendDir, 'e2e.db'), {
  force: true,
})

// Initialize the E2E database.
const databaseSetup = spawnSync(
  python,
  [
    '-c',
    'from app.database.base import Base; import app.models; from app.database.session import get_engine; Base.metadata.create_all(get_engine())',
  ],
  {
    cwd: backendDir,
    env,
    stdio: 'inherit',
  },
)

if (databaseSetup.error) {
  console.error('Database initialization failed:', databaseSetup.error)
  process.exit(1)
}

if (databaseSetup.status !== 0) {
  console.error('E2E database initialization failed.')
  process.exit(databaseSetup.status ?? 1)
}

console.log('E2E database initialized successfully.')

// Start Uvicorn through Python instead of uvicorn.exe.
const server = spawn(
  python,
  [
    '-m',
    'uvicorn',
    'app.main:app',
    '--host',
    '127.0.0.1',
    '--port',
    '8000',
  ],
  {
    cwd: backendDir,
    env,
    stdio: 'inherit',
  },
)

server.on('error', (error) => {
  console.error('Failed to start backend:', error)
  process.exitCode = 1
})

server.on('exit', (code, signal) => {
  process.exitCode = code ?? (signal ? 0 : 1)
})

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    server.kill(signal)
  })
}
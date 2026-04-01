module.exports = {
  apps: [
    {
      name: 'vectorbrain-api',
      script: './dag_api_server.py',
      interpreter: 'python3',
      cwd: '/home/user/.vectorbrain/dag',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      error_file: '/home/user/.vectorbrain/dag/logs/pm2-api-error.log',
      out_file: '/home/user/.vectorbrain/dag/logs/pm2-api-out.log',
      log_file: '/home/user/.vectorbrain/dag/logs/pm2-api-combined.log',
      time: true,
      env: {
        PYTHONUNBUFFERED: '1'
      }
    },
    {
      name: 'vectorbrain-scheduler',
      script: './dag_scheduler.py',
      interpreter: 'python3',
      cwd: '/home/user/.vectorbrain/dag',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      error_file: '/home/user/.vectorbrain/dag/logs/pm2-scheduler-error.log',
      out_file: '/home/user/.vectorbrain/dag/logs/pm2-scheduler-out.log',
      log_file: '/home/user/.vectorbrain/dag/logs/pm2-scheduler-combined.log',
      time: true,
      env: {
        PYTHONUNBUFFERED: '1'
      }
    }
  ]
};

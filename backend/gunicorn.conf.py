# Gunicorn configuration for App Runner deployment
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = 1  # App Runner works better with single worker per container
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100

# Timeouts
timeout = 120
keepalive = 2
graceful_timeout = 30

# Process naming
proc_name = "eloquent-ai-backend"

# Preload app for better performance
preload_app = True

# Restart workers after this many requests
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Environment variables
raw_env = [
    "ENVIRONMENT=" + os.getenv("ENVIRONMENT", "production"),
]

# Worker temp directory (use tmpfs for better performance)
worker_tmp_dir = "/dev/shm"


def when_ready(server):
    server.log.info("Server is ready. Spawning workers")


def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")


def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)


def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)


def post_worker_init(worker):
    worker.log.info("Worker initialized (pid: %s)", worker.pid)


def worker_abort(worker):
    worker.log.info("Worker aborted (pid: %s)", worker.pid)

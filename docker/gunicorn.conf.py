"""Gunicorn configuration for the production image.

Every tunable is read from a ``GUNICORN_*`` environment variable so a
deployment can be sized without rebuilding the image.
"""

import os

bind = "0.0.0.0:8000"

worker_class = "gthread"
# Not derived from os.cpu_count(): inside a container it reports the host's
# cores, not the container's CPU limit.
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))

# Recycle workers to bound memory growth; jitter stops them all restarting at once.
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", "100"))

preload_app = os.environ.get("GUNICORN_PRELOAD", "true").lower() == "true"

timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
# compose.prod.yaml's stop_grace_period must stay above this.
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))

# The control socket defaults to a path under the working directory, which is
# read-only in production.
control_socket_disable = True
# A heartbeat file on disk can stall under I/O load and get a healthy worker killed.
worker_tmp_dir = "/dev/shm"  # ruff: ignore[hardcoded-temp-file]

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

# The proxy reaches the container through Docker's bridge, not 127.0.0.1.
# Trusting any peer is safe only because compose.prod.yaml publishes the port
# on the loopback interface alone; change one and the other must change too.
forwarded_allow_ips = os.environ.get("GUNICORN_FORWARDED_ALLOW_IPS", "*")

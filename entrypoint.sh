#!/bin/bash
set -e

# Add /app to safe.directory to allow git operations regardless of owner
git config --system --add safe.directory /app

# entrypoint.sh - Handle user permissions and execute command

# If HOST_UID and HOST_GID are passed, we might need to adjust permissions
# or run as that user. However, for simplicity in this MVP, we run as root
# but ensure files created in /app have correct permissions if possible,
# OR rely on Docker's user mapping (-u $(id -u):$(id -g)).
# If the user runs `docker run -u ...`, we are already that user.
# But if we need to write to /root or /opt, we might fail if we are not root.

# The prompt requirement: "entrypoint.sh を用意し、ホスト側のUID/GIDと権限問題を解決できる仕組みを入れること。"
# Standard way: create a user 'appuser' with HOST_UID/GID if provided.

if [ -n "$HOST_UID" ] && [ -n "$HOST_GID" ]; then
    # Create group if not exists
    if ! getent group "$HOST_GID" >/dev/null; then
        groupadd -g "$HOST_GID" appgroup
    fi

    # Create user if not exists
    if ! getent passwd "$HOST_UID" >/dev/null; then
        useradd -m -u "$HOST_UID" -g "$HOST_GID" -s /bin/bash appuser
    fi

    # Ensure /app is writable (if mounted as root owned initially)
    # Usually mounted volumes retain host perms.

    # Execute as the user
    # We use gosu if installed, or su-exec, or simple su.
    # But python-slim doesn't have gosu by default.
    # Let's assume the user might not have installed gosu.
    # We can just run the command.

    # Since we didn't install gosu in Dockerfile, let's try to run via sudo or su if we are root.
    if [ "$(id -u)" = "0" ]; then
        # We are root, switch to user
        # export HOME=/home/appuser # Optional
        exec runuser -u appuser -- "$@"
    fi
fi

# Fallback: run as is (root or specified user)
exec "$@"

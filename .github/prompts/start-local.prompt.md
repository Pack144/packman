---
agent: 'agent'
description: 'Start and verify the Packman local development server'
---

Start the Packman local development server using `./util/start_local.sh`.

1. Run `./util/start_local.sh --detach`. Do not duplicate the setup or port
   detection performed by the script.
2. If the script reports that another Packman server from this checkout is
   using port 8000, ask whether to stop it with `--kill-existing` or use a
   different available port with `--port <port>`. Do not use `--kill-existing`
   without approval. If an unrelated process owns the port, ask whether to
   terminate the exact PID outside the script or use a different port. Never
   terminate a process without approval.
3. After the script reports that Django is ready, verify the site responds over
   HTTP and report the local URL.

If startup fails, diagnose the script output and fix repository-related
problems when possible. Surface environment or credential problems clearly
instead of bypassing them.

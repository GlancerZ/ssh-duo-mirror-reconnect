# Compact application verification

Use existing context or a helper-returned `app_ref` before discovering remote IDs. Do not invent IDs or use references from a different SSH destination. If a cached read fails, discover once and replace the cache only after a successful matching read.

In a tool orchestration cell, consume the response before printing it. Adapt the method to the tools actually available. For the desktop `read_thread` response, the compact pattern is:

```javascript
const result = await tools.mcp__codex_app__read_thread({
  hostId, threadId, turnLimit: 1, includeOutputs: false,
  maxOutputCharsPerItem: 200
});
let verified = false;
let status = "unavailable";
try {
  const block = result.content.find(item => item.type === "text");
  const data = JSON.parse(block.text);
  verified = !result.isError && data.thread?.id === threadId
    && data.thread?.hostId === hostId && Array.isArray(data.turns);
  if (verified) status = data.thread.status?.type ?? "available";
} catch {}
text({remote_read: verified, status});
```

Do not call `text(result)` first. Per-item truncation still permits many historical items to be returned; filtering the full response prevents that expansion into model context. `isError: false` alone is not proof of a matching read.

For ID discovery, filter the returned entries to the intended host inside the cell. Emit one suitable existing ID/status, not an entire project/thread list. Never send a message or create a task for a connectivity test.

For App Server logs, start at the current attempt time, select the intended host, and emit only the latest timestamp/state. A historical `connected` line is not current evidence. A successful current remote app read may provide equivalent readiness evidence when no separate status tool is available.

Cache the verified routing metadata with:

```sh
python3 scripts/check_connection.py hpc-dev --remember-app OBSERVED_HOST_ID OBSERVED_THREAD_ID
```

The helper stores a mode-600 file outside the repository, keyed by alias and invalidated when effective SSH configuration changes. This cache is private routing metadata, not credentials or authorization. If the environment does not permit cache writes, keep IDs in the current conversation and continue without persistence.

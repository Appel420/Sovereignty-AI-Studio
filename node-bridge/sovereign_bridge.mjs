// Sovereignty AI Studio — Sovereign Node Bridge
// WebSocket + HTTP bridge between frontend and Python AI core.
// Routes ALL AI requests through sovereign providers only.
// No external SaaS. No data leaves the infrastructure.

import http from "node:http";
import { WebSocketServer } from "ws";
import { URL } from "node:url";

// ──────────────────────────────────────────────────────────────────────────
// Configuration
// ──────────────────────────────────────────────────────────────────────────
const PORT = parseInt(process.env.NODE_BRIDGE_PORT || "9898", 10);
const BACKEND_URL = (
  process.env.BACKEND_URL || "http://localhost:8002"
).replace(/\/$/, "");
const SOVEREIGN_API_URL = (
  process.env.SOVEREIGN_API_URL || "http://localhost:8002/api/ai"
).replace(/\/$/, "");
const CORS_ORIGIN = process.env.CORS_ORIGIN || "*";

// Rate limiting: max requests per user per minute
const RATE_LIMIT_RPM = parseInt(process.env.RATE_LIMIT_RPM || "30", 10);
const _rateBuckets = new Map(); // userId -> { count, resetAt }

// ──────────────────────────────────────────────────────────────────────────
// Rate limiter
// ──────────────────────────────────────────────────────────────────────────
function checkRateLimit(identifier) {
  const now = Date.now();
  let bucket = _rateBuckets.get(identifier);
  if (!bucket || now > bucket.resetAt) {
    bucket = { count: 0, resetAt: now + 60_000 };
    _rateBuckets.set(identifier, bucket);
  }
  bucket.count += 1;
  return bucket.count <= RATE_LIMIT_RPM;
}

// ──────────────────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────────────────
function corsHeaders(origin) {
  const allowed =
    CORS_ORIGIN === "*" ? origin || "*" : CORS_ORIGIN;
  return {
    "Access-Control-Allow-Origin": allowed,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "86400",
  };
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

async function proxyToBackend(path, method, body, headers) {
  const url = new URL(BACKEND_URL + path);
  return new Promise((resolve, reject) => {
    const options = {
      hostname: url.hostname,
      port: url.port || 80,
      path: url.pathname + url.search,
      method,
      headers: {
        "Content-Type": "application/json",
        ...(headers?.Authorization
          ? { Authorization: headers.Authorization }
          : {}),
      },
    };
    const proxyReq = http.request(options, (proxyRes) => {
      const chunks = [];
      proxyRes.on("data", (c) => chunks.push(c));
      proxyRes.on("end", () =>
        resolve({
          status: proxyRes.statusCode,
          body: Buffer.concat(chunks).toString("utf8"),
        })
      );
    });
    proxyReq.on("error", reject);
    if (body) proxyReq.write(body);
    proxyReq.end();
  });
}

async function sovereignAIRequest(payload, authHeader) {
  const url = new URL(SOVEREIGN_API_URL + "/chat");
  const body = JSON.stringify(payload);
  return new Promise((resolve, reject) => {
    const options = {
      hostname: url.hostname,
      port: url.port || 80,
      path: url.pathname + url.search,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(body),
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
    };
    const req = http.request(options, (res) => {
      const chunks = [];
      res.on("data", (c) => chunks.push(c));
      res.on("end", () => {
        if (res.statusCode >= 400) {
          reject(
            new Error(
              `Sovereign API error ${res.statusCode}: ${Buffer.concat(chunks)}`
            )
          );
          return;
        }
        try {
          resolve(JSON.parse(Buffer.concat(chunks).toString("utf8")));
        } catch (e) {
          reject(new Error(`Invalid JSON from sovereign API: ${e.message}`));
        }
      });
    });
    req.on("error", reject);
    req.write(body);
    req.end();
  });
}

// ──────────────────────────────────────────────────────────────────────────
// HTTP request handler
// ──────────────────────────────────────────────────────────────────────────
async function handleRequest(req, res) {
  const origin = req.headers.origin;
  const ch = corsHeaders(origin);

  if (req.method === "OPTIONS") {
    res.writeHead(204, ch);
    res.end();
    return;
  }

  const parsed = new URL(req.url, `http://localhost:${PORT}`);
  const path = parsed.pathname;

  // Health check
  if (path === "/health" || path === "/api/health") {
    res.writeHead(200, { "Content-Type": "application/json", ...ch });
    res.end(
      JSON.stringify({
        status: "sovereign",
        bridge: "node-bridge/sovereign_bridge.mjs",
        backend: BACKEND_URL,
        sovereign_api: SOVEREIGN_API_URL,
        timestamp: new Date().toISOString(),
      })
    );
    return;
  }

  // AI chat endpoint
  if (path === "/api/ai/chat" && req.method === "POST") {
    let body;
    try {
      body = JSON.parse(await readBody(req));
    } catch {
      res.writeHead(400, { "Content-Type": "application/json", ...ch });
      res.end(JSON.stringify({ error: "Invalid JSON body" }));
      return;
    }

    const userId = body?.context?.userId || req.headers["x-user-id"] || "anonymous";
    if (!checkRateLimit(userId)) {
      res.writeHead(429, { "Content-Type": "application/json", ...ch });
      res.end(JSON.stringify({ error: "Rate limit exceeded. Max 30 req/min." }));
      return;
    }

    try {
      const result = await sovereignAIRequest(body, req.headers.authorization);
      res.writeHead(200, { "Content-Type": "application/json", ...ch });
      res.end(JSON.stringify(result));
    } catch (err) {
      res.writeHead(502, { "Content-Type": "application/json", ...ch });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // Proxy all other /api/* requests to the backend
  if (path.startsWith("/api/")) {
    let bodyStr = null;
    if (req.method !== "GET" && req.method !== "HEAD") {
      bodyStr = await readBody(req);
    }
    try {
      const upstream = await proxyToBackend(
        path + (parsed.search || ""),
        req.method,
        bodyStr,
        req.headers
      );
      res.writeHead(upstream.status, {
        "Content-Type": "application/json",
        ...ch,
      });
      res.end(upstream.body);
    } catch (err) {
      res.writeHead(502, { "Content-Type": "application/json", ...ch });
      res.end(JSON.stringify({ error: `Backend proxy error: ${err.message}` }));
    }
    return;
  }

  res.writeHead(404, { "Content-Type": "application/json", ...ch });
  res.end(JSON.stringify({ error: "Not found" }));
}

// ──────────────────────────────────────────────────────────────────────────
// WebSocket handler
// ──────────────────────────────────────────────────────────────────────────
function handleWebSocket(wss) {
  wss.on("connection", (ws, req) => {
    const userId =
      new URL(req.url, `http://localhost`).searchParams.get("userId") ||
      "anonymous";

    ws.on("message", async (raw) => {
      let msg;
      try {
        msg = JSON.parse(raw.toString());
      } catch {
        ws.send(JSON.stringify({ type: "error", error: "Invalid JSON" }));
        return;
      }

      if (msg.type === "agent_request" || msg.type === "ai_chat") {
        if (!checkRateLimit(userId)) {
          ws.send(
            JSON.stringify({
              type: "error",
              error: "Rate limit exceeded. Max 30 req/min.",
            })
          );
          return;
        }

        try {
          const payload = {
            messages: msg.messages || [
              { role: "user", content: msg.payload?.prompt || msg.prompt || "" },
            ],
            max_tokens: msg.max_tokens || 1200,
            context: {
              userId,
              orgId: msg.orgId || msg.payload?.orgId,
              projectId: msg.projectId || msg.payload?.projectId,
            },
          };
          const result = await sovereignAIRequest(payload, msg.token ? `Bearer ${msg.token}` : null);
          ws.send(
            JSON.stringify({
              type: "agent_response",
              id: msg.id,
              payload: { text: result.text || result.response || result.choices?.[0]?.message?.content || "" },
            })
          );
        } catch (err) {
          ws.send(
            JSON.stringify({
              type: "agent_response",
              id: msg.id,
              payload: { error: err.message },
            })
          );
        }
        return;
      }

      // Unknown message type — echo back for debugging
      ws.send(JSON.stringify({ type: "ack", received: msg.type }));
    });

    ws.on("error", (err) => {
      console.error("[sovereign_bridge] WebSocket error:", err.message);
    });
  });
}

// ──────────────────────────────────────────────────────────────────────────
// Server startup
// ──────────────────────────────────────────────────────────────────────────
const server = http.createServer(handleRequest);
const wss = new WebSocketServer({ server });
handleWebSocket(wss);

server.listen(PORT, () => {
  console.log(`[sovereign_bridge] Listening on port ${PORT}`);
  console.log(`[sovereign_bridge] Backend: ${BACKEND_URL}`);
  console.log(`[sovereign_bridge] Sovereign AI: ${SOVEREIGN_API_URL}`);
  console.log(`[sovereign_bridge] Rate limit: ${RATE_LIMIT_RPM} req/min`);
});

server.on("error", (err) => {
  console.error("[sovereign_bridge] Server error:", err.message);
  process.exit(1);
});

export { server, wss };

import { verifyJWT } from "../middleware/auth.js";
import { route } from "./router/index.js";
import { trackUsage } from "../analytics/usage.js";
import { logAudit } from "../analytics/audit.js";

export default async function handler(req, res) {
  const user = verifyJWT(req);
  const { prompt, orgId, projectId, provider } = req.body;

  const contextPrompt = orgId ? `[ORG:${orgId}] ${prompt}` : prompt;
  const { provider: usedProvider, result } = await route(contextPrompt, provider);

  await trackUsage(user.id, orgId, result.length, usedProvider);
  await logAudit(user.id, orgId, 'ai_call', 'ai', null, {
    provider: usedProvider,
    promptLength: prompt.length,
    projectId
  });

  res.json({ result, provider: usedProvider });
}

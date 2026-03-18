import { db } from "../db/index.js";

export async function trackUsage(userId, orgId, tokens, provider) {
  await db.query(
    "INSERT INTO usage (user_id, org_id, tokens, provider) VALUES ($1,$2,$3,$4)",
    [userId, orgId, tokens, provider]
  );
}

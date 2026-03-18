import { db } from "../db/index.js";

export async function logAudit(userId, orgId, action, resourceType, resourceId, details, ipAddress) {
  await db.query(
    "INSERT INTO audit_logs (user_id, org_id, action, resource_type, resource_id, details, ip_address) VALUES ($1,$2,$3,$4,$5,$6,$7)",
    [userId, orgId, action, resourceType, resourceId, JSON.stringify(details || {}), ipAddress]
  );
}

export async function getAuditLogs(orgId, filters = {}) {
  let query = "SELECT * FROM audit_logs WHERE org_id=$1";
  const params = [orgId];
  let idx = 2;
  if (filters.action) { query += ` AND action=$${idx++}`; params.push(filters.action); }
  if (filters.userId) { query += ` AND user_id=$${idx++}`; params.push(filters.userId); }
  query += " ORDER BY created_at DESC LIMIT 100";
  const result = await db.query(query, params);
  return result.rows;
}

import { db } from "../db/index.js";

export async function checkPermission(userId, projectId, requiredRole) {
  const roleHierarchy = { owner: 4, admin: 3, contributor: 2, viewer: 1 };
  const result = await db.query(
    "SELECT role FROM project_permissions WHERE user_id=$1 AND project_id=$2",
    [userId, projectId]
  );
  if (!result.rows.length) return false;
  return roleHierarchy[result.rows[0].role] >= roleHierarchy[requiredRole];
}

import { verifyJWT } from "../middleware/auth.js";
import { db } from "../db/index.js";

export default async function handler(req, res) {
  const user = verifyJWT(req);
  if (req.method === "GET") {
    const { orgId } = req.query;
    const projects = await db.query(
      "SELECT p.* FROM projects p JOIN project_permissions pp ON pp.project_id=p.id WHERE pp.user_id=$1 AND p.org_id=$2",
      [user.id, orgId]
    );
    return res.json(projects.rows);
  }
  if (req.method === "POST") {
    const { name, orgId, visibility } = req.body;
    const project = await db.query(
      "INSERT INTO projects (name, org_id, visibility) VALUES ($1,$2,$3) RETURNING *",
      [name, orgId, visibility || 'private']
    );
    await db.query(
      "INSERT INTO project_permissions (user_id, project_id, role) VALUES ($1,$2,'owner')",
      [user.id, project.rows[0].id]
    );
    res.json(project.rows[0]);
  }
}

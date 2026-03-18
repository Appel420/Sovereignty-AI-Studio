import { verifyJWT } from "../middleware/auth.js";
import { db } from "../db/index.js";

export default async function handler(req, res) {
  const user = verifyJWT(req);
  if (req.method === "GET") {
    const orgs = await db.query(
      "SELECT o.* FROM organizations o JOIN memberships m ON m.org_id=o.id WHERE m.user_id=$1",
      [user.id]
    );
    return res.json(orgs.rows);
  }
  if (req.method === "POST") {
    const { name } = req.body;
    const org = await db.query(
      "INSERT INTO organizations (name) VALUES ($1) RETURNING *",
      [name]
    );
    await db.query(
      "INSERT INTO memberships (user_id, org_id, role) VALUES ($1,$2,'owner')",
      [user.id, org.rows[0].id]
    );
    res.json(org.rows[0]);
  }
}

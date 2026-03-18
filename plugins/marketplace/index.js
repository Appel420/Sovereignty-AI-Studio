import { db } from "../../backend/db/index.js";

export async function listAgents() {
  const result = await db.query("SELECT * FROM marketplace_agents WHERE enabled=true ORDER BY downloads DESC");
  return result.rows;
}

export async function registerAgent(agent) {
  const result = await db.query(
    "INSERT INTO marketplace_agents (name, description, author_id, version, config) VALUES ($1,$2,$3,$4,$5) RETURNING *",
    [agent.name, agent.description, agent.authorId, agent.version, JSON.stringify(agent.config)]
  );
  return result.rows[0];
}

export async function getAgent(id) {
  const result = await db.query("SELECT * FROM marketplace_agents WHERE id=$1", [id]);
  return result.rows[0];
}

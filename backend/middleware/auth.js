import jwt from "jsonwebtoken";

export function verifyJWT(req) {
  const token = req.headers.authorization?.replace("Bearer ", "");
  if (!token) throw new Error("No token provided");
  try {
    return jwt.verify(token, process.env.JWT_SECRET || "sovereignty-one-secret");
  } catch (err) {
    throw new Error("Invalid token");
  }
}

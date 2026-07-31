import { callProvider } from "../providers/index.js";

const providers = ["gpt", "anthropic", "local"];
const branchByProvider = { gpt: "gpt", anthropic: "claude", local: "devassist420" };

export async function route(prompt, preferredProvider, options = {}) {
  const requestedBranch = options.branch || branchByProvider[preferredProvider] || "devassist420";
  if (requestedBranch === "main") throw new Error("Direct agent writes to main are forbidden");
  const order = preferredProvider
    ? [preferredProvider, ...providers.filter(p => p !== preferredProvider)]
    : providers;

  for (const p of order) {
    try {
      return {
        provider: p,
        branch: requestedBranch,
        coordination: { writePolicy: "branch-only", ownerApprovalRequired: true },
        result: await callProvider(p, prompt)
      };
    } catch (err) {
      console.error(`Provider ${p} failed:`, err.message);
    }
  }
  throw new Error("All providers failed");
}

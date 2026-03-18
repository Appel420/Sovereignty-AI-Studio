import { callProvider } from "../providers/index.js";

const providers = ["gpt", "anthropic", "local"];

export async function route(prompt, preferredProvider) {
  const order = preferredProvider
    ? [preferredProvider, ...providers.filter(p => p !== preferredProvider)]
    : providers;

  for (const p of order) {
    try {
      return { provider: p, result: await callProvider(p, prompt) };
    } catch (err) {
      console.error(`Provider ${p} failed:`, err.message);
      continue;
    }
  }
  throw new Error("All providers failed");
}

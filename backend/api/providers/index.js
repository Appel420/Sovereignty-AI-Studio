import { gptModel } from "./gpt.js";
import { anthropicModel } from "./anthropic.js";

const providerMap = {
  gpt: gptModel,
  anthropic: anthropicModel
};

export async function callProvider(name, prompt) {
  const fn = providerMap[name];
  if (!fn) throw new Error(`Unknown or disabled provider: ${name}`);
  return fn(prompt);
}

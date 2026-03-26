import { gptModel } from "./gpt.js";
import { anthropicModel } from "./anthropic.js";
import { localModel } from "./local.js";

const providerMap = {
  gpt: gptModel,
  anthropic: anthropicModel,
  local: localModel
};

export async function callProvider(name, prompt) {
  const fn = providerMap[name];
  if (!fn) throw new Error(`Unknown provider: ${name}`);
  return fn(prompt);
}

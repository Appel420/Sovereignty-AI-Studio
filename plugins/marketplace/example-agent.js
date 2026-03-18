import { SovereigntyPlugin } from "../sdk/plugin-sdk.js";

const weatherAgent = new SovereigntyPlugin({
  name: "weather-agent",
  version: "1.0.0",
  description: "Fetches weather data and provides climate analysis"
});

weatherAgent.on("query", async (context) => {
  return { type: "weather", message: `Weather analysis for: ${context.prompt}` };
});

weatherAgent.on("schedule", async (context) => {
  return { type: "scheduled", interval: "hourly" };
});

export default weatherAgent;

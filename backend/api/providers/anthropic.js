export async function anthropicModel(prompt) {
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": process.env.ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01"
    },
    body: JSON.stringify({
      model: process.env.ANTHROPIC_MODEL || "claude-3-sonnet-20240229",
      max_tokens: 4096,
      messages: [{ role: "user", content: prompt }]
    })
  });
  const data = await res.json();
  return data.content[0].text;
}

export async function gptModel(prompt) {
  const res = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`
    },
    body: JSON.stringify({
      model: process.env.GPT_MODEL || "gpt-4",
      messages: [{ role: "user", content: prompt }]
    })
  });
  const data = await res.json();
  return data.choices[0].message.content;
}

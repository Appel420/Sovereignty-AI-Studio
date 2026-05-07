export async function localModel(prompt) {
  const res = await fetch("http://localhost:9899/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: process.env.LOCAL_MODEL || "llama3", prompt })
  });
  const data = await res.json();
  return data.response;
}

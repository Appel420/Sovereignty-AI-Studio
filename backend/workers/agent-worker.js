import { route } from "../api/router/index.js";

const taskQueue = [];

export function enqueueTask(task) {
  taskQueue.push({ ...task, status: "pending", createdAt: new Date() });
}

export async function processQueue() {
  while (true) {
    const task = taskQueue.find(t => t.status === "pending");
    if (task) {
      task.status = "processing";
      try {
        const result = await route(task.prompt, task.provider);
        task.result = result;
        task.status = "completed";
      } catch (err) {
        task.error = err.message;
        task.status = "failed";
      }
    }
    await new Promise(r => setTimeout(r, 1000));
  }
}

if (process.argv[1] === import.meta.url) processQueue();

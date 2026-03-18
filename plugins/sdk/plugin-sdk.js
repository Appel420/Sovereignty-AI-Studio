export class SovereigntyPlugin {
  constructor(config) {
    this.name = config.name;
    this.version = config.version || "1.0.0";
    this.description = config.description || "";
    this.hooks = {};
  }
  on(event, handler) { this.hooks[event] = handler; }
  async execute(event, context) {
    if (this.hooks[event]) return this.hooks[event](context);
    return null;
  }
  manifest() {
    return {
      name: this.name,
      version: this.version,
      description: this.description,
      events: Object.keys(this.hooks)
    };
  }
}

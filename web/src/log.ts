const MAX_LINES = 300;
const lines: string[] = [];

function render(value: unknown): string {
  if (typeof value === "string") return value;
  if (value instanceof Error) return value.stack ?? String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function log(level: "info" | "warn" | "error", ...parts: unknown[]) {
  lines.push(`${new Date().toISOString()} ${level.toUpperCase()} ${parts.map(render).join(" ")}`);
  if (lines.length > MAX_LINES) lines.shift();
}

export function recentLogs(): string[] {
  return [...lines];
}

export function captureErrors() {
  addEventListener("error", (e) => log("error", `uncaught: ${e.message} (${e.filename}:${e.lineno})`));
  addEventListener("unhandledrejection", (e) => log("error", "unhandled rejection:", e.reason));
  for (const level of ["warn", "error"] as const) {
    const original = console[level].bind(console);
    console[level] = (...args: unknown[]) => {
      log(level, ...args);
      original(...args);
    };
  }
}

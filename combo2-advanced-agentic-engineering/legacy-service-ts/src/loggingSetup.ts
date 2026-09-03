// loggingSetup.ts -- shared logging config for OrderBase.
//
// Log lines go to stdout AND logs/app-YYYY-MM-DD.log (when a logs/ dir
// exists in the working directory -- prod boxes have one, CI doesn't).
// The format is FROZEN: the metrics pusher (see DOCS/INSTRUCTIONS.md) greps
// these lines every minute. Change it and the dashboards go dark.
//
// Hand-rolled on purpose -- no pino, no winston. getLogger(name) mirrors the
// stdlib logging.getLogger(name) call in the Python original.

import { appendFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const LOG_DIR = "logs";
let configured = false;
let logPath: string | null = null;

export function setupLogging(): void {
  if (configured) {
    return;
  }
  if (existsSync(LOG_DIR)) {
    const today = new Date();
    const stamp = today.toISOString().slice(0, 10);
    logPath = join(LOG_DIR, `app-${stamp}.log`);
  }
  configured = true;
}

function pad2(n: number): string {
  return n < 10 ? `0${n}` : `${n}`;
}

function pad3(n: number): string {
  return n.toString().padStart(3, "0");
}

function timestamp(): string {
  const d = new Date();
  const date = `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
  const time = `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
  return `${date} ${time},${pad3(d.getMilliseconds())}`;
}

function emit(level: string, name: string, line: string): void {
  const full = `${timestamp()} ${level} ${name} ${line}`;
  console.log(full);
  if (logPath) {
    appendFileSync(logPath, full + "\n");
  }
}

export interface Logger {
  info(message: string, ...args: unknown[]): void;
  warning(message: string, ...args: unknown[]): void;
}

function format(message: string, args: unknown[]): string {
  if (args.length === 0) {
    return message;
  }
  let i = 0;
  return message.replace(/\{\}/g, () => String(args[i++]));
}

export function getLogger(name: string): Logger {
  return {
    info: (message, ...args) => emit("INFO", name, format(message, args)),
    warning: (message, ...args) => emit("WARNING", name, format(message, args)),
  };
}

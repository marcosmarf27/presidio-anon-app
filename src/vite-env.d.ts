/// <reference types="vite/client" />

interface CliStatusResult {
  backendDir: string;
  windows: { installed: boolean; onPath: boolean };
  wsl: { available: boolean; installed: boolean; shimPath: string };
}

interface CliActionResult {
  ok: boolean;
  note?: string;
  error?: string;
  shimPath?: string;
  onPath?: boolean;
  alreadyInstalled?: boolean;
}

interface CliAPI {
  status: () => Promise<CliStatusResult>;
  installWindows: () => Promise<CliActionResult>;
  uninstallWindows: () => Promise<CliActionResult>;
  installWsl: () => Promise<CliActionResult>;
  uninstallWsl: () => Promise<CliActionResult>;
}

interface ElectronAPI {
  readFile: (path: string) => Promise<string>;
  saveFile: (path: string, content: string) => Promise<void>;
  selectFiles: () => Promise<{ name: string; path: string }[]>;
  cli: CliAPI;
}

interface Window {
  electronAPI: ElectronAPI;
}

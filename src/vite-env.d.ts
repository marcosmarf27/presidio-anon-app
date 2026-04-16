/// <reference types="vite/client" />

interface ElectronAPI {
  readFile: (path: string) => Promise<string>;
  saveFile: (path: string, content: string) => Promise<void>;
  selectFiles: () => Promise<{ name: string; path: string }[]>;
}

interface Window {
  electronAPI: ElectronAPI;
}

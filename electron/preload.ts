import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("electronAPI", {
  readFile: (path: string) => ipcRenderer.invoke("read-file", path),
  saveFile: (path: string, content: string) =>
    ipcRenderer.invoke("save-file", path, content),
  selectFiles: () => ipcRenderer.invoke("select-files"),
  cli: {
    status: () => ipcRenderer.invoke("cli-status"),
    installWindows: () => ipcRenderer.invoke("cli-install-windows"),
    uninstallWindows: () => ipcRenderer.invoke("cli-uninstall-windows"),
    installWsl: () => ipcRenderer.invoke("cli-install-wsl"),
    uninstallWsl: () => ipcRenderer.invoke("cli-uninstall-wsl"),
  },
});

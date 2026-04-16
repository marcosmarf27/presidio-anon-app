import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("electronAPI", {
  readFile: (path: string) => ipcRenderer.invoke("read-file", path),
  saveFile: (path: string, content: string) =>
    ipcRenderer.invoke("save-file", path, content),
  selectFiles: () => ipcRenderer.invoke("select-files"),
});

import { app, BrowserWindow, ipcMain, dialog } from "electron";
import { spawn, ChildProcess } from "child_process";
import * as path from "path";
import * as fs from "fs";
import * as net from "net";

let mainWindow: BrowserWindow | null = null;
let pythonProcess: ChildProcess | null = null;
const PYTHON_PORT = 8123;

function getResourcePath(...segments: string[]): string {
  const isProd = app.isPackaged;
  if (isProd) {
    return path.join(process.resourcesPath, ...segments);
  }
  return path.join(__dirname, "..", ...segments);
}

function findAvailablePort(startPort: number): Promise<number> {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.listen(startPort, "127.0.0.1", () => {
      server.close(() => resolve(startPort));
    });
    server.on("error", () => {
      resolve(findAvailablePort(startPort + 1));
    });
  });
}

async function startPythonBackend(port: number): Promise<void> {
  const isDev = !app.isPackaged;

  let pythonPath: string;
  let serverPath: string;

  if (isDev) {
    // Em dev, usa o Python do venv local
    pythonPath = path.join(__dirname, "..", ".venv", "bin", "python");
    if (!fs.existsSync(pythonPath)) {
      pythonPath = "python3"; // fallback para python do sistema
    }
    serverPath = path.join(__dirname, "..", "python-backend", "server.py");
  } else {
    // Em produção, usa o Python embutido (dentro de python-embed/)
    pythonPath = getResourcePath(
      "python-backend",
      "python-embed",
      "python.exe"
    );
    serverPath = getResourcePath("python-backend", "server.py");
  }

  console.log(`Iniciando Python: ${pythonPath} ${serverPath} --port ${port}`);

  pythonProcess = spawn(pythonPath, [serverPath, "--port", String(port)], {
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
    stdio: ["ignore", "pipe", "pipe"],
  });

  pythonProcess.stdout?.on("data", (data: Buffer) => {
    console.log(`[Python] ${data.toString().trim()}`);
  });

  pythonProcess.stderr?.on("data", (data: Buffer) => {
    console.error(`[Python ERR] ${data.toString().trim()}`);
  });

  pythonProcess.on("exit", (code) => {
    console.log(`Python process exited with code ${code}`);
    pythonProcess = null;
  });
}

function stopPythonBackend(): void {
  if (pythonProcess) {
    console.log("Parando servidor Python...");
    pythonProcess.kill("SIGTERM");
    setTimeout(() => {
      if (pythonProcess) {
        pythonProcess.kill("SIGKILL");
        pythonProcess = null;
      }
    }, 5000);
  }
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 750,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
    titleBarStyle: "default",
    backgroundColor: "#0f172a",
  });

  const isDev = !app.isPackaged;

  if (isDev) {
    mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.openDevTools({ mode: "bottom" });
  } else {
    mainWindow.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// IPC Handlers
ipcMain.handle("read-file", async (_event, filePath: string) => {
  // Tenta UTF-8 estrito; se o arquivo contiver bytes inválidos, cai para cp1252
  const buffer = fs.readFileSync(filePath);
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(buffer);
  } catch {
    return buffer.toString("latin1");
  }
});

ipcMain.handle(
  "save-file",
  async (_event, filePath: string, content: string) => {
    fs.writeFileSync(filePath, content, "utf-8");
  }
);

ipcMain.handle("select-files", async () => {
  if (!mainWindow) return [];

  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openFile", "multiSelections"],
    filters: [
      { name: "Documentos de texto", extensions: ["txt", "md", "rtf"] },
    ],
  });

  if (result.canceled) return [];

  return result.filePaths.slice(0, 10).map((filePath) => ({
    name: path.basename(filePath),
    path: filePath,
  }));
});

// App lifecycle
app.whenReady().then(async () => {
  const port = await findAvailablePort(PYTHON_PORT);
  await startPythonBackend(port);
  createWindow();
});

app.on("window-all-closed", () => {
  stopPythonBackend();
  app.quit();
});

app.on("before-quit", () => {
  stopPythonBackend();
});

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('spark', {
  status: () => ipcRenderer.invoke('status'),
  saveConfig: (settings) => ipcRenderer.invoke('save-config', settings),
  login: () => ipcRenderer.invoke('login'),
  dryRun: () => ipcRenderer.invoke('dry-run'),
  startWatch: (confirmation) => ipcRenderer.invoke('watch', confirmation),
  pause: () => ipcRenderer.invoke('pause'),
  logs: () => ipcRenderer.invoke('logs'),
  onLog: (callback) => {
    const listener = (_event, message) => callback(message);
    ipcRenderer.on('log', listener);
    return () => ipcRenderer.removeListener('log', listener);
  },
});

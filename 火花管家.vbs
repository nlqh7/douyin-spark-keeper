Option Explicit
Dim shell, fso, root, electron
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
electron = root & "\desktop\node_modules\electron\dist\electron.exe"
If Not fso.FileExists(electron) Then
    MsgBox "Electron 尚未安装，请先完成应用安装。", 16, "火花管家"
    WScript.Quit 2
End If
shell.CurrentDirectory = root
shell.Run """" & electron & """ """ & root & "\desktop""", 0, False

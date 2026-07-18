Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
root = fso.GetParentFolderName(dir)
exe = root & "\venv\Scripts\ReadAloud.exe"
script = dir & "\read-aloud-gui-win.py"
If Not fso.FileExists(exe) Then
  MsgBox "ReadAloud.exe is missing." & vbCrLf & _
    "Run windows\install-windows.ps1 first." & vbCrLf & exe, vbCritical, "Read Aloud"
  WScript.Quit 1
End If
sh.CurrentDirectory = root
sh.Run """" & exe & """ """ & script & """", 1, False

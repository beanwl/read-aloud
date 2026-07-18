Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
exe = dir & "\ReadAloud.exe"
If Not fso.FileExists(exe) Then
  MsgBox "ReadAloud.exe is missing." & vbCrLf & _
    "Run windows\install-windows.ps1 first.", vbCritical, "Read Aloud"
  WScript.Quit 1
End If
sh.CurrentDirectory = fso.GetParentFolderName(dir)
sh.Run """" & exe & """", 1, False

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

projectFolder = FSO.GetParentFolderName(WScript.ScriptFullName)
serverCommand = "cmd /c cd /d """ & projectFolder & """ && python server.py"
url = "http://192.168.50.57:5000"

' Start server hidden
WshShell.Run serverCommand, 0, False

' Wait until port 5000 is listening (up to ~15 seconds)
portReady = False
For i = 1 To 30
    WScript.Sleep 500
    cmd = "powershell -NoProfile -ExecutionPolicy Bypass -Command ""$c = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue; if ($c) { exit 0 } else { exit 1 }"""
    rc = WshShell.Run(cmd, 0, True)
    If rc = 0 Then
        portReady = True
        Exit For
    End If
Next

If portReady Then
    ' Open app in default browser
    WshShell.Run url, 1, False
Else
    MsgBox "Server did not start on port 5000.", vbCritical, "Start Prompt Library"
End If
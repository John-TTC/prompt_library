' launches the prompt library
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

projectFolder = FSO.GetParentFolderName(WScript.ScriptFullName)
serverCommand = "cmd /c cd /d """ & projectFolder & """ && python server.py"
configPath = projectFolder & "\launch-config.ini"
listenPort = "5000"
openScheme = "http"
openHost = "127.0.0.1"

If FSO.FileExists(configPath) Then
    Set cfg = FSO.OpenTextFile(configPath, 1)
    Do Until cfg.AtEndOfStream
        line = Trim(cfg.ReadLine)
        If line <> "" And Left(line, 1) <> "#" And Left(line, 1) <> ";" Then
            eqPos = InStr(line, "=")
            If eqPos > 1 Then
                key = LCase(Trim(Left(line, eqPos - 1)))
                value = Trim(Mid(line, eqPos + 1))
                If key = "listen_port" And value <> "" Then
                    listenPort = value
                ElseIf key = "open_scheme" And value <> "" Then
                    openScheme = value
                ElseIf key = "open_host" And value <> "" Then
                    openHost = value
                End If
            End If
        End If
    Loop
    cfg.Close
End If

url = openScheme & "://" & openHost & ":" & listenPort

' Start server hidden
WshShell.Run serverCommand, 0, False

' Wait until port 5000 is listening (up to ~15 seconds)
portReady = False
For i = 1 To 30
    WScript.Sleep 500
    cmd = "powershell -NoProfile -ExecutionPolicy Bypass -Command ""$c = Get-NetTCPConnection -LocalPort " & listenPort & " -State Listen -ErrorAction SilentlyContinue; if ($c) { exit 0 } else { exit 1 }"""
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
    MsgBox "Server did not start on port " & listenPort & ".", vbCritical, "Start Prompt Library"
End If
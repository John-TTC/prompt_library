Option Explicit

Dim shell, i, stillListening
Set shell = CreateObject("WScript.Shell")

shell.Run "cmd /c for /f ""tokens=5"" %a in ('netstat -ano -p tcp ^| findstr LISTENING ^| findstr "":5000""') do taskkill /F /PID %a >nul 2>&1", 0, True

stillListening = True
For i = 1 To 20
    WScript.Sleep 500
    If Not PortListening(5000) Then
        stillListening = False
        Exit For
    End If
Next

If Not stillListening Then
    MsgBox "SUCCESS!" & vbCrLf & _
           "No process is listening on port 5000.", vbInformation, "Stop Local Web Server"
Else
    MsgBox "ERROR:" & vbCrLf & _
           "Port 5000 is still in use." & vbCrLf & _
           "Another process may still be running.", vbCritical, "Stop Local Web Server"
    WScript.Quit 1
End If


Function PortListening(port)
    Dim exec, output
    PortListening = False
    Set exec = shell.Exec("cmd /c netstat -ano -p tcp | findstr LISTENING")
    output = UCase(exec.StdOut.ReadAll)

    If InStr(output, ":" & CStr(port)) > 0 Then
        PortListening = True
    End If
End Function
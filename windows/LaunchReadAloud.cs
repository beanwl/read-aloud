// Tiny Windows launcher for Read Aloud. Built by install-windows.ps1 into ReadAloud.exe.
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Forms;

internal static class Program
{
    private const string AppUserModelId = "Beanwl.ReadAloud";

    [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
    private static extern int SetCurrentProcessExplicitAppUserModelID(string appID);

    [STAThread]
    private static int Main()
    {
        try
        {
            SetCurrentProcessExplicitAppUserModelID(AppUserModelId);
        }
        catch
        {
            // Older Windows — ignore.
        }

        string winDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\', '/');
        string root = Path.GetFullPath(Path.Combine(winDir, ".."));
        string pythonw = Path.Combine(root, "venv", "Scripts", "pythonw.exe");
        string script = Path.Combine(winDir, "read-aloud-gui-win.py");

        if (!File.Exists(pythonw) || !File.Exists(script))
        {
            MessageBox.Show(
                "Read Aloud is not set up yet.\n\nRun windows\\install-windows.ps1 first.",
                "Read Aloud",
                MessageBoxButtons.OK,
                MessageBoxIcon.Information
            );
            return 1;
        }

        Process.Start(
            new ProcessStartInfo
            {
                FileName = pythonw,
                Arguments = "\"" + script + "\"",
                WorkingDirectory = root,
                UseShellExecute = false,
            }
        );
        return 0;
    }
}

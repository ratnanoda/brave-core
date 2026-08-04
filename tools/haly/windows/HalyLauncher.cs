// Copyright (c) 2026 The Haly Authors. All rights reserved.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

internal static class HalyLauncher
{
    private const string AppUserModelId = "Haly.Browser";

    [DllImport("shell32.dll", SetLastError = true)]
    private static extern int SetCurrentProcessExplicitAppUserModelID(
        [MarshalAs(UnmanagedType.LPWStr)] string appId);

    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            SetCurrentProcessExplicitAppUserModelID(AppUserModelId);

            string installDirectory = AppDomain.CurrentDomain.BaseDirectory;
            string applicationDirectory = Path.Combine(installDirectory, "Application");
            string browserExecutable = FindBrowserExecutable(applicationDirectory);
            if (browserExecutable == null)
            {
                throw new FileNotFoundException(
                    "Haly browser files are missing. Reinstall Haly to repair the installation.");
            }

            string localAppData = Environment.GetFolderPath(
                Environment.SpecialFolder.LocalApplicationData);
            string userDataDirectory = Path.Combine(localAppData, "Haly", "User Data");
            Directory.CreateDirectory(userDataDirectory);

            var launchArguments = new List<string>
            {
                "--user-data-dir=" + QuoteArgument(userDataDirectory),
                "--no-default-browser-check",
                "--disable-background-mode",
                "--disable-crash-reporter",
                "--disable-breakpad"
            };

            // The profile path is deliberately enforced so command-line arguments cannot
            // make Haly share Brave's normal profile by accident.
            foreach (string argument in args)
            {
                if (argument.StartsWith("--user-data-dir", StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }
                launchArguments.Add(QuoteArgument(argument));
            }

            var startInfo = new ProcessStartInfo
            {
                FileName = browserExecutable,
                Arguments = string.Join(" ", launchArguments.ToArray()),
                WorkingDirectory = Path.GetDirectoryName(browserExecutable),
                UseShellExecute = false
            };

            Process.Start(startInfo);
            return 0;
        }
        catch (Exception error)
        {
            MessageBox.Show(
                error.Message,
                "Haly",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            return 1;
        }
    }

    private static string FindBrowserExecutable(string applicationDirectory)
    {
        if (!Directory.Exists(applicationDirectory))
        {
            return null;
        }

        string directPath = Path.Combine(applicationDirectory, "haly-browser.exe");
        if (File.Exists(directPath))
        {
            return directPath;
        }

        return Directory
            .EnumerateFiles(applicationDirectory, "haly-browser.exe", SearchOption.AllDirectories)
            .OrderBy(path => path.Count(character => character == Path.DirectorySeparatorChar))
            .FirstOrDefault();
    }

    private static string QuoteArgument(string argument)
    {
        if (argument == null)
        {
            return "\"\"";
        }
        if (argument.Length > 0 && !argument.Any(character =>
            char.IsWhiteSpace(character) || character == '\"' || character == '\\'))
        {
            return argument;
        }

        var output = new StringBuilder();
        output.Append('\"');
        int backslashes = 0;
        foreach (char character in argument)
        {
            if (character == '\\')
            {
                backslashes++;
                continue;
            }
            if (character == '\"')
            {
                output.Append('\\', backslashes * 2 + 1);
                output.Append('\"');
                backslashes = 0;
                continue;
            }
            output.Append('\\', backslashes);
            backslashes = 0;
            output.Append(character);
        }
        output.Append('\\', backslashes * 2);
        output.Append('\"');
        return output.ToString();
    }
}

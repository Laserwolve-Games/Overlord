﻿using System.Windows;
using System.Windows.Controls;
using System.Diagnostics;
using System.Reflection;
using System.Windows.Media.Imaging;
using System.Windows.Media;

namespace Overlord;

public partial class MainWindow : Window
{

    private string scriptDirectory = System.IO.Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
        "OneDrive",
        "repositories",
        "DAZScripts"
    );
    private bool noPrompt = true;
    string logSize = "500000000";
    Dictionary<string, string> argumentData = new() { };

    public MainWindow()
    {
        InitializeComponent();
        SetWindowTitle();
        AddFormElements();
    }

    private void SetWindowTitle()
    {
        string appName = "Overlord";
        string version = Assembly.GetExecutingAssembly().GetName().Version?.ToString() ?? "0.0.0.0";
        this.Title = $"{appName} v{version}";
    }

    private void AddFormElements()
    {
        Canvas canvas = new();

        Image logo = new()
        {
            Source = new BitmapImage(new Uri("pack://application:,,,/Overlord;component/logo.png")),
            Width = 300,
            Height = 117
        };
        Canvas.SetLeft(logo, 10);
        Canvas.SetTop(logo, 10);
        canvas.Children.Add(logo);

        // Checkbox for noPrompt
        CheckBox noPromptCheckBox = new()
        {
            Content = "No Prompt",
            IsChecked = noPrompt
        };
        noPromptCheckBox.Checked += (s, e) => noPrompt = true;
        noPromptCheckBox.Unchecked += (s, e) => noPrompt = false;
        Canvas.SetLeft(noPromptCheckBox, 10);
        Canvas.SetTop(noPromptCheckBox, 140);

        // Label for log size
        TextBlock logSizeLabel = new()
        {
            Text = "Log file size (megabytes):"
        };
        Canvas.SetLeft(logSizeLabel, 10);
        Canvas.SetTop(logSizeLabel, 160);
        // Textbox for log size
        TextBox logSizeTextBox = new()
        {
            Text = "500", // Default value
            Width = 100
        };
        logSizeTextBox.TextChanged += (s, e) =>
        {
            if (int.TryParse(logSizeTextBox.Text, out int sizeInMb))
            {
                logSize = (sizeInMb * 1000000).ToString(); // Convert MB to bytes
            }
        };
        Canvas.SetLeft(logSizeTextBox, 200);
        Canvas.SetTop(logSizeTextBox, 160);

        // Execute button
        Button executeButton = new()
        {
            Content = "Start Rendering"
        };
        executeButton.Click += ExecuteButton_Click;
        Canvas.SetLeft(executeButton, 10);
        Canvas.SetTop(executeButton, 210);

        // Add elements to canvas
        canvas.Children.Add(noPromptCheckBox);
        canvas.Children.Add(logSizeLabel);
        canvas.Children.Add(logSizeTextBox);
        canvas.Children.Add(executeButton);

        // Fixed "The name 'MainContainer' does exist in the current context" error with this:
        // https://github.com/dotnet/vscode-csharp/issues/5958#issuecomment-2283458200
        MainContainer.Children.Add(canvas);
    }

    private void ExecuteButton_Click(object sender, RoutedEventArgs e)
    {
        Process process = new();
        process.StartInfo.FileName = "\"C:\\Program Files\\DAZ 3D\\DAZStudio4\\DAZStudio.exe\"";

        string masterRendererPath = System.IO.Path.Combine(scriptDirectory, "masterRenderer.dsa");

        process.StartInfo.Arguments = 
            $"-scriptArg {argumentData} " + // JSON of all the custom arguments
            "-instanceName # " + // Incrementally name each instance
            $"-logSize {logSize} " + // The size of the log file, in bytes
            (noPrompt ? "-noPrompt " : "") + // Whether or not prompts should be supressed
            $"\"{masterRendererPath}\""; // The path to the script

        process.StartInfo.UseShellExecute = false;
        process.StartInfo.RedirectStandardOutput = true;
        process.StartInfo.RedirectStandardError = true;
        process.StartInfo.CreateNoWindow = false;

        process.Start();
    }
}
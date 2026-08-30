namespace TinyAgent.Shared;

/// <summary>
/// A 20-line <c>.env</c> reader, so the C# path needs no extra NuGet package
/// where Python uses <c>python-dotenv</c>. GIVEN.
/// </summary>
public static class DotEnv
{
    /// <summary>
    /// Load <c>.env</c> from <paramref name="startDirectory"/> or the nearest
    /// ancestor that has one. Existing environment variables always win.
    /// </summary>
    public static void Load(string? startDirectory = null)
    {
        var dir = new DirectoryInfo(startDirectory ?? Directory.GetCurrentDirectory());

        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, ".env");
            if (File.Exists(candidate))
            {
                Apply(candidate);
                return;
            }
            dir = dir.Parent;
        }
    }

    private static void Apply(string path)
    {
        foreach (var raw in File.ReadAllLines(path))
        {
            var line = raw.Trim();
            if (line.Length == 0 || line.StartsWith('#')) continue;

            var eq = line.IndexOf('=');
            if (eq <= 0) continue;

            var key = line[..eq].Trim();
            var value = line[(eq + 1)..].Trim().Trim('"', '\'');

            // Don't clobber a real environment variable with a file value.
            if (Environment.GetEnvironmentVariable(key) is null)
            {
                Environment.SetEnvironmentVariable(key, value);
            }
        }
    }

    /// <summary>The API key, or null. Callers produce their own error message.</summary>
    public static string? ApiKey() => Environment.GetEnvironmentVariable("GOOGLE_API_KEY");

    /// <summary>The model id, defaulting to the workshop model.</summary>
    public static string Model() =>
        Environment.GetEnvironmentVariable("GEMINI_MODEL") is { Length: > 0 } m
            ? m
            : GeminiClient.DefaultModel;
}

using TinyAgent.Shared;

namespace TinyAgent.Reference;

/// <summary>
/// Three file-system tools the agent can call — complete worked solution.
/// </summary>
/// <remarks>
/// Mirrors Thorsten Ball's ampcode walkthrough: https://ampcode.com/how-to-build-an-agent
///
/// Safety model: every path is resolved against the sandbox root and rejected if
/// it escapes. No ".." traversal, no absolute paths outside the sandbox.
///
/// Errors are RETURNED as strings, never thrown. The model reads the message and
/// self-corrects; a stack trace just confuses it and kills the loop.
/// </remarks>
public sealed class ReferenceTools : ITools
{
    private readonly PathSandbox _sandbox;

    public ReferenceTools(string sandboxRoot) => _sandbox = new PathSandbox(sandboxRoot);

    public string ReadFile(string path)
    {
        if (!_sandbox.TryResolve(path, out var resolved, out var error)) return error;

        if (Directory.Exists(resolved)) return $"ERROR: '{path}' is not a file";
        if (!File.Exists(resolved)) return $"ERROR: '{path}' does not exist";

        try
        {
            return File.ReadAllText(resolved);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            return $"ERROR: could not read '{path}': {ex.Message}";
        }
    }

    public ToolListResult ListFiles(string path = ".")
    {
        if (!_sandbox.TryResolve(path, out var resolved, out var error))
            return ToolListResult.Fail(error);

        if (File.Exists(resolved)) return ToolListResult.Fail($"ERROR: '{path}' is not a directory");
        if (!Directory.Exists(resolved)) return ToolListResult.Fail($"ERROR: '{path}' does not exist");

        try
        {
            var entries = new List<string>();
            foreach (var child in Directory.EnumerateFileSystemEntries(resolved))
            {
                var name = Path.GetFileName(child);
                entries.Add(Directory.Exists(child) ? name + "/" : name);
            }
            entries.Sort(StringComparer.Ordinal);
            return ToolListResult.Ok(entries);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            return ToolListResult.Fail($"ERROR: could not list '{path}': {ex.Message}");
        }
    }

    public string EditFile(string path, string oldStr, string newStr)
    {
        if (!_sandbox.TryResolve(path, out var resolved, out var error)) return error;

        if (Directory.Exists(resolved)) return $"ERROR: '{path}' is not a file";
        if (!File.Exists(resolved)) return $"ERROR: '{path}' does not exist";

        string content;
        try
        {
            content = File.ReadAllText(resolved);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            return $"ERROR: could not read '{path}': {ex.Message}";
        }

        var count = CountOccurrences(content, oldStr);
        if (count == 0) return $"ERROR: old_str not found in '{path}'";
        if (count > 1)
        {
            return $"ERROR: old_str appears {count} times in '{path}'; must be unique. "
                 + "Add more surrounding context to old_str so it matches exactly once.";
        }

        var index = content.IndexOf(oldStr, StringComparison.Ordinal);
        var updated = content[..index] + newStr + content[(index + oldStr.Length)..];

        try
        {
            File.WriteAllText(resolved, updated);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            return $"ERROR: could not write '{path}': {ex.Message}";
        }

        return $"OK: edited {path}";
    }

    /// <summary>Count non-overlapping occurrences. An empty needle counts as zero.</summary>
    private static int CountOccurrences(string haystack, string needle)
    {
        if (string.IsNullOrEmpty(needle)) return 0;

        var count = 0;
        var index = 0;
        while ((index = haystack.IndexOf(needle, index, StringComparison.Ordinal)) >= 0)
        {
            count++;
            index += needle.Length;
        }
        return count;
    }
}

namespace TinyAgent.Shared;

/// <summary>
/// Resolves a caller-supplied path against a fixed root, refusing anything that
/// escapes it. This helper is GIVEN to you — it does the path-safety check so
/// you can focus on the tool logic.
/// </summary>
/// <remarks>
/// The Python original captures the sandbox root at import time in a module
/// global. Here the root is injected through the constructor instead: it is the
/// same idea, and it makes the tests straightforward (they hand in a temp
/// directory rather than monkey-patching a global).
/// </remarks>
public sealed class PathSandbox
{
    private readonly string _root;

    public PathSandbox(string root) => _root = Path.TrimEndingDirectorySeparator(Path.GetFullPath(root));

    public string Root => _root;

    /// <summary>
    /// Resolve <paramref name="path"/> inside the sandbox.
    /// </summary>
    /// <returns>
    /// <c>true</c> and sets <paramref name="resolved"/>; or <c>false</c> and sets
    /// <paramref name="error"/> to a string starting with "ERROR:".
    /// </returns>
    public bool TryResolve(string path, out string resolved, out string error)
    {
        resolved = string.Empty;
        error = string.Empty;

        string candidate;
        try
        {
            candidate = Path.GetFullPath(Path.Combine(_root, path));
        }
        catch (Exception ex) when (ex is ArgumentException or NotSupportedException or PathTooLongException)
        {
            error = $"ERROR: could not resolve path '{path}': {ex.Message}";
            return false;
        }

        if (!IsInsideRoot(candidate))
        {
            error = $"ERROR: path '{path}' is outside the sandbox ({_root})";
            return false;
        }

        resolved = candidate;
        return true;
    }

    private bool IsInsideRoot(string candidate)
    {
        var trimmed = Path.TrimEndingDirectorySeparator(candidate);

        // Windows and macOS default to case-insensitive file systems; Linux does
        // not. Matching the platform keeps "../SANDBOX/x" from sneaking through
        // on Windows while staying strict on Linux.
        var comparison = OperatingSystem.IsLinux()
            ? StringComparison.Ordinal
            : StringComparison.OrdinalIgnoreCase;

        if (string.Equals(trimmed, _root, comparison)) return true;

        // Compare against root + separator, never a bare prefix: a plain
        // StartsWith would let "/tmp/sandbox-evil" pass as inside "/tmp/sandbox".
        return trimmed.StartsWith(_root + Path.DirectorySeparatorChar, comparison);
    }
}

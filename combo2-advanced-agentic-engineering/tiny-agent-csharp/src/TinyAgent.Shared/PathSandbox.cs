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

    /// <summary>
    /// The root with symlinks resolved. Containment is decided against this
    /// rather than <see cref="_root"/>, because a real path can only be compared
    /// against another real path: on macOS <c>Path.GetTempPath()</c> is itself
    /// behind a symlink, so checking a resolved path against a textual root
    /// would reject the sandbox's own files.
    /// </summary>
    private readonly string _realRoot;

    public PathSandbox(string root)
    {
        _root = Path.TrimEndingDirectorySeparator(Path.GetFullPath(root));
        _realRoot = RealPath(_root);
    }

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

        // First pass, purely textual: catches ".." traversal and absolute paths
        // pointing elsewhere, which is most of what a confused model sends.
        if (!IsInside(_root, candidate))
        {
            error = $"ERROR: path '{path}' is outside the sandbox ({_root})";
            return false;
        }

        // Second pass, following symlinks. Path.GetFullPath is textual, so a
        // symlink *inside* the sandbox may point anywhere on disk and still sail
        // through the check above — and File.ReadAllText will happily follow it.
        // Decide on the real path.
        if (!IsInside(_realRoot, RealPath(candidate)))
        {
            error = $"ERROR: path '{path}' is a symlink leading outside the sandbox ({_root})";
            return false;
        }

        resolved = candidate;
        return true;
    }

    /// <summary>True when <paramref name="candidate"/> is the root itself, or under it.</summary>
    private static bool IsInside(string root, string candidate)
    {
        var trimmed = Path.TrimEndingDirectorySeparator(candidate);

        // Windows and macOS default to case-insensitive file systems; Linux does
        // not. Matching the platform keeps "../SANDBOX/x" from sneaking through
        // on Windows while staying strict on Linux.
        var comparison = OperatingSystem.IsLinux()
            ? StringComparison.Ordinal
            : StringComparison.OrdinalIgnoreCase;

        if (string.Equals(trimmed, root, comparison)) return true;

        // Compare against root + separator, never a bare prefix: a plain
        // StartsWith would let "/tmp/sandbox-evil" pass as inside "/tmp/sandbox".
        return trimmed.StartsWith(root + Path.DirectorySeparatorChar, comparison);
    }

    /// <summary>
    /// <paramref name="target"/> with every symlink along it resolved.
    /// </summary>
    /// <remarks>
    /// .NET has no <c>realpath(3)</c>, and <c>ResolveLinkTarget</c> only reports
    /// on the entry it is handed — a link in the *middle* of a path is invisible
    /// to it. So walk the path a segment at a time and follow each link found.
    /// A path that does not exist yet still has to be checked, because its parent
    /// may be the link, so a missing segment is appended rather than rejected.
    /// </remarks>
    private static string RealPath(string target)
    {
        var full = Path.GetFullPath(target);
        var root = Path.GetPathRoot(full);
        if (string.IsNullOrEmpty(root)) return Path.TrimEndingDirectorySeparator(full);

        var segments = full[root.Length..]
            .Split(Path.DirectorySeparatorChar, StringSplitOptions.RemoveEmptyEntries);

        var current = root;
        foreach (var segment in segments)
        {
            current = Path.Combine(current, segment);

            FileSystemInfo? link;
            try
            {
                link = Directory.Exists(current)
                    ? Directory.ResolveLinkTarget(current, returnFinalTarget: true)
                    : File.ResolveLinkTarget(current, returnFinalTarget: true);
            }
            catch (IOException)
            {
                // A broken link, or a chain too long to follow. Treat it as
                // opaque — the tool's own existence check will report it.
                link = null;
            }

            if (link is not null)
            {
                // A relative link target is relative to the link's own directory,
                // not the process's working directory.
                current = Path.IsPathRooted(link.FullName)
                    ? Path.GetFullPath(link.FullName)
                    : Path.GetFullPath(Path.Combine(Path.GetDirectoryName(current) ?? root, link.FullName));
            }
        }

        return Path.TrimEndingDirectorySeparator(current);
    }
}

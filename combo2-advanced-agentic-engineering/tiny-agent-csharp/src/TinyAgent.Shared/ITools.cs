namespace TinyAgent.Shared;

/// <summary>
/// The three file-system tools the agent can call.
/// </summary>
/// <remarks>
/// Both <c>TinyAgent.Starter</c> and <c>TinyAgent.Reference</c> implement this,
/// which is how the test suite can point at either one (see
/// <c>TINY_AGENT_IMPL</c> in the README).
///
/// Note the return types: every method returns a value, and failures come back
/// as strings starting with "ERROR:". Nothing throws. That is deliberate — the
/// model reads the error text and self-corrects; an exception just kills the
/// loop. It is the single most important contract in this file.
/// </remarks>
public interface ITools
{
    /// <summary>Read a UTF-8 text file and return its contents.</summary>
    string ReadFile(string path);

    /// <summary>List entries in a directory. Directory names end with "/".</summary>
    ToolListResult ListFiles(string path = ".");

    /// <summary>Replace <paramref name="oldStr"/> with <paramref name="newStr"/>, exactly once.</summary>
    string EditFile(string path, string oldStr, string newStr);
}

/// <summary>
/// Result of <see cref="ITools.ListFiles"/> — either entries, or an error string.
/// </summary>
/// <remarks>
/// The Python original returns a single-element <c>["ERROR: ..."]</c> list on
/// failure so the return type never changes. That is a Python-typing workaround;
/// in C# a small result type says the same thing honestly. What matters — and
/// what carries over unchanged — is that the model still receives a plain string
/// describing the failure.
/// </remarks>
public readonly record struct ToolListResult(IReadOnlyList<string>? Entries, string? Error)
{
    public static ToolListResult Ok(IReadOnlyList<string> entries) => new(entries, null);
    public static ToolListResult Fail(string error) => new(null, error);

    public bool IsError => Error is not null;

    /// <summary>Flatten to what the model sees: the entries, or the error text.</summary>
    public string ToModelString() =>
        Error ?? string.Join("\n", Entries ?? Array.Empty<string>());
}

using TinyAgent.Shared;

namespace TinyAgent.Starter;

/// <summary>
/// Three file-system tools the agent can call. YOU WRITE THESE.
/// </summary>
/// <remarks>
/// <para>
/// Safety model: every path must be resolved through <see cref="PathSandbox"/>
/// and rejected if it escapes. That helper is given to you — call
/// <c>_sandbox.TryResolve(path, out var resolved, out var error)</c>.
/// </para>
/// <para>
/// <b>Return errors as strings starting with "ERROR:". Do not throw.</b> The
/// model reads the message and self-corrects; an exception kills the loop. This
/// is the contract the tests check hardest.
/// </para>
/// <para>
/// The JSON schema the model sees lives in <c>TinyAgent.Shared/ToolSchemas.cs</c>
/// and is already written for you. Read it before you start — it is the spec.
/// </para>
/// </remarks>
public sealed class StarterTools : ITools
{
    private readonly PathSandbox _sandbox;

    public StarterTools(string sandboxRoot) => _sandbox = new PathSandbox(sandboxRoot);

    // -------------------------------------------------------------------------
    // STEP 2a — implement ReadFile
    // -------------------------------------------------------------------------
    public string ReadFile(string path)
    {
        // TODO: call _sandbox.TryResolve(path, out var resolved, out var error).
        //       If it returns false, return the error string.
        // TODO: return "ERROR: '{path}' is not a file" if it's a directory.
        // TODO: return "ERROR: '{path}' does not exist" if it isn't there.
        // TODO: read the file with File.ReadAllText and return the contents.
        //       Wrap the read so an IOException comes back as an ERROR string.
        throw new NotImplementedException("Implement ReadFile for step 2a.");
    }

    // -------------------------------------------------------------------------
    // STEP 2b — implement ListFiles
    // -------------------------------------------------------------------------
    public ToolListResult ListFiles(string path = ".")
    {
        // TODO: resolve + validate (is it a file? does it exist?).
        //       Return ToolListResult.Fail("ERROR: ...") on any failure.
        // TODO: enumerate entries with Directory.EnumerateFileSystemEntries.
        // TODO: append "/" to directory names so the model can tell them apart.
        // TODO: sort with StringComparer.Ordinal, return ToolListResult.Ok(entries).
        throw new NotImplementedException("Implement ListFiles for step 2b.");
    }

    // -------------------------------------------------------------------------
    // STEP 2c — implement EditFile
    // -------------------------------------------------------------------------
    public string EditFile(string path, string oldStr, string newStr)
    {
        // TODO: resolve + validate (exists, is a file).
        // TODO: read the current content.
        // TODO: count occurrences of oldStr.
        //       0        -> "ERROR: old_str not found in '{path}'"
        //       above 1  -> "ERROR: old_str appears {count} times in '{path}'; must be unique. ..."
        //       and in BOTH error cases leave the file untouched.
        // TODO: replace the single occurrence, write it back, return "OK: edited {path}".
        //
        // Watch out: string.Replace() replaces EVERY occurrence. That is exactly
        // what the exactly-once rule exists to prevent, and there is a test for it.
        throw new NotImplementedException("Implement EditFile for step 2c.");
    }
}

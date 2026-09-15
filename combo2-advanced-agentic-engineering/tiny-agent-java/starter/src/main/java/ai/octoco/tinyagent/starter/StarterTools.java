package ai.octoco.tinyagent.starter;

import ai.octoco.tinyagent.shared.PathSandbox;
import ai.octoco.tinyagent.shared.ToolListResult;
import ai.octoco.tinyagent.shared.Tools;

/**
 * Three file-system tools the agent can call. YOU WRITE THESE.
 *
 * <p>Safety model: every path must be resolved through {@link PathSandbox}
 * and rejected if it escapes. That helper is given to you — call
 * {@code sandbox.tryResolve(path)} and check {@code result.isOk()}.
 *
 * <p><b>Return errors as strings starting with "ERROR:". Do not throw.</b> The
 * model reads the message and self-corrects; an exception kills the loop. This
 * is the contract the tests check hardest.
 *
 * <p>The JSON schema the model sees lives in {@code ai.octoco.tinyagent.shared.ToolSchemas}
 * and is already written for you. Read it before you start — it is the spec.
 */
public final class StarterTools implements Tools {

    private final PathSandbox sandbox;

    public StarterTools(String sandboxRoot) {
        this.sandbox = new PathSandbox(sandboxRoot);
    }

    // -------------------------------------------------------------------------
    // STEP 2a — implement readFile
    // -------------------------------------------------------------------------
    @Override
    public String readFile(String path) {
        // TODO: call sandbox.tryResolve(path) and check result.isOk() / result.error().
        // TODO: return "ERROR: '{path}' is not a file" if it's a directory (Files.isDirectory).
        // TODO: return "ERROR: '{path}' does not exist" if it isn't there (Files.exists).
        // TODO: read the file with Files.readString and return the contents.
        //       Wrap the read so an IOException comes back as an ERROR string.
        throw new UnsupportedOperationException("Implement readFile for step 2a.");
    }

    // -------------------------------------------------------------------------
    // STEP 2b — implement listFiles
    // -------------------------------------------------------------------------
    @Override
    public ToolListResult listFiles(String path) {
        // TODO: resolve + validate (is it a file? does it exist?).
        //       Return ToolListResult.fail("ERROR: ...") on any failure.
        // TODO: enumerate entries with Files.newDirectoryStream.
        // TODO: append "/" to directory names so the model can tell them apart.
        // TODO: sort the entries (natural String order), return ToolListResult.ok(entries).
        throw new UnsupportedOperationException("Implement listFiles for step 2b.");
    }

    // -------------------------------------------------------------------------
    // STEP 2c — implement editFile
    // -------------------------------------------------------------------------
    @Override
    public String editFile(String path, String oldStr, String newStr) {
        // TODO: resolve + validate (exists, is a file).
        // TODO: read the current content.
        // TODO: count occurrences of oldStr.
        //       0        -> "ERROR: old_str not found in '{path}'"
        //       above 1  -> "ERROR: old_str appears {count} times in '{path}'; must be unique. ..."
        //       and in BOTH error cases leave the file untouched.
        // TODO: replace the single occurrence, write it back, return "OK: edited {path}".
        //
        // Watch out: String.replace() replaces EVERY occurrence. That is exactly
        // what the exactly-once rule exists to prevent, and there is a test for it.
        throw new UnsupportedOperationException("Implement editFile for step 2c.");
    }
}

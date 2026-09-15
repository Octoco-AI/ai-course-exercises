package ai.octoco.tinyagent.shared;

/**
 * The three file-system tools the agent can call.
 *
 * <p>Both the starter and the reference implement this, which is how the test
 * suite can point at either one (see {@code TINY_AGENT_IMPL} in the README).
 *
 * <p>Note the return types: every method returns a value, and failures come back
 * as strings starting with {@code "ERROR:"}. Nothing throws. That is deliberate —
 * the model reads the error text and self-corrects; an exception just kills the
 * loop. It is the single most important contract in this file.
 */
public interface Tools {

    /** Read a UTF-8 text file and return its contents. */
    String readFile(String path);

    /** List entries in a directory. Directory names end with {@code "/"}. */
    ToolListResult listFiles(String path);

    /** Replace {@code oldStr} with {@code newStr}, exactly once. */
    String editFile(String path, String oldStr, String newStr);
}

package ai.octoco.tinyagent.reference;

import ai.octoco.tinyagent.shared.PathSandbox;
import ai.octoco.tinyagent.shared.PathSandbox.ResolveResult;
import ai.octoco.tinyagent.shared.ToolListResult;
import ai.octoco.tinyagent.shared.Tools;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Three file-system tools the agent can call — complete worked solution.
 *
 * <p>Mirrors Thorsten Ball's ampcode walkthrough: https://ampcode.com/how-to-build-an-agent
 *
 * <p>Safety model: every path is resolved against the sandbox root and rejected if
 * it escapes. No ".." traversal, no absolute paths outside the sandbox.
 *
 * <p>Errors are RETURNED as strings, never thrown. The model reads the message and
 * self-corrects; a stack trace just confuses it and kills the loop.
 */
public final class ReferenceTools implements Tools {

    private final PathSandbox sandbox;

    public ReferenceTools(String sandboxRoot) {
        this.sandbox = new PathSandbox(sandboxRoot);
    }

    @Override
    public String readFile(String path) {
        ResolveResult resolved = sandbox.tryResolve(path);
        if (!resolved.isOk()) return resolved.error();

        Path p = resolved.path();
        if (Files.isDirectory(p)) return "ERROR: '" + path + "' is not a file";
        if (!Files.exists(p)) return "ERROR: '" + path + "' does not exist";

        try {
            return Files.readString(p, StandardCharsets.UTF_8);
        } catch (IOException e) {
            return "ERROR: could not read '" + path + "': " + e.getMessage();
        }
    }

    @Override
    public ToolListResult listFiles(String path) {
        ResolveResult resolved = sandbox.tryResolve(path);
        if (!resolved.isOk()) return ToolListResult.fail(resolved.error());

        Path p = resolved.path();
        if (Files.isRegularFile(p)) return ToolListResult.fail("ERROR: '" + path + "' is not a directory");
        if (!Files.exists(p)) return ToolListResult.fail("ERROR: '" + path + "' does not exist");

        try (DirectoryStream<Path> stream = Files.newDirectoryStream(p)) {
            List<String> entries = new ArrayList<>();
            for (Path child : stream) {
                String name = child.getFileName().toString();
                entries.add(Files.isDirectory(child) ? name + "/" : name);
            }
            Collections.sort(entries);
            return ToolListResult.ok(entries);
        } catch (IOException e) {
            return ToolListResult.fail("ERROR: could not list '" + path + "': " + e.getMessage());
        }
    }

    @Override
    public String editFile(String path, String oldStr, String newStr) {
        ResolveResult resolved = sandbox.tryResolve(path);
        if (!resolved.isOk()) return resolved.error();

        Path p = resolved.path();
        if (Files.isDirectory(p)) return "ERROR: '" + path + "' is not a file";
        if (!Files.exists(p)) return "ERROR: '" + path + "' does not exist";

        String content;
        try {
            content = Files.readString(p, StandardCharsets.UTF_8);
        } catch (IOException e) {
            return "ERROR: could not read '" + path + "': " + e.getMessage();
        }

        int count = countOccurrences(content, oldStr);
        if (count == 0) return "ERROR: old_str not found in '" + path + "'";
        if (count > 1) {
            return "ERROR: old_str appears " + count + " times in '" + path + "'; must be unique. "
                    + "Add more surrounding context to old_str so it matches exactly once.";
        }

        int index = content.indexOf(oldStr);
        String updated = content.substring(0, index) + newStr + content.substring(index + oldStr.length());

        try {
            Files.writeString(p, updated, StandardCharsets.UTF_8);
        } catch (IOException e) {
            return "ERROR: could not write '" + path + "': " + e.getMessage();
        }

        return "OK: edited " + path;
    }

    /** Count non-overlapping occurrences. An empty needle counts as zero. */
    private static int countOccurrences(String haystack, String needle) {
        if (needle == null || needle.isEmpty()) return 0;

        int count = 0;
        int index = 0;
        while ((index = haystack.indexOf(needle, index)) >= 0) {
            count++;
            index += needle.length();
        }
        return count;
    }
}

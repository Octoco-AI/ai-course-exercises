package ai.octoco.tinyagent.tests;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.octoco.tinyagent.shared.ToolListResult;
import ai.octoco.tinyagent.shared.Tools;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * The contract your tool implementations must satisfy.
 *
 * <p>These 15 tests ARE the spec — read them before you write anything. They
 * are also a preview of M11: notice that each one names a behaviour and
 * asserts on it, rather than checking the implementation.
 *
 * <p>Run from the tiny-agent-java/ directory: {@code ./mvnw test}
 */
final class ToolsTests {

    private Path sandbox;
    private Tools tools;
    private final List<Path> outsideFiles = new ArrayList<>();

    @BeforeEach
    void setUp() throws IOException {
        // A fresh temp directory per test, seeded the same way as the Python
        // fixture: one file, one nested directory with a file in it.
        sandbox = Files.createTempDirectory("tiny-agent-tests-");
        Files.writeString(sandbox.resolve("hello.txt"), "hello world\n");
        Files.createDirectory(sandbox.resolve("nested"));
        Files.writeString(sandbox.resolve("nested").resolve("deep.txt"), "deep content\n");

        tools = ToolsFactory.create(sandbox.toString());
    }

    @AfterEach
    void tearDown() throws IOException {
        deleteRecursively(sandbox);
        for (Path p : outsideFiles) Files.deleteIfExists(p);
    }

    private String read(String relative) throws IOException {
        return Files.readString(sandbox.resolve(relative));
    }

    /**
     * Create a symlink, or report that the OS wouldn't allow it — Windows
     * needs developer mode or admin rights. The escape tests below skip there
     * rather than fail for a reason that has nothing to do with your code.
     */
    private boolean trySymlink(Path target, Path linkPath) {
        try {
            Files.createSymbolicLink(linkPath, target);
            return true;
        } catch (IOException | UnsupportedOperationException e) {
            return false;
        }
    }

    /** A file outside the sandbox, cleaned up with the fixture. */
    private Path makeOutsideFile(String tag) throws IOException {
        Path target = Files.createTempFile("tiny-agent-outside-" + tag + "-", ".txt");
        Files.writeString(target, "secret\n");
        outsideFiles.add(target);
        return target;
    }

    // ---- readFile -------------------------------------------------------

    @Test
    void readFile_success() {
        assertEquals("hello world\n", tools.readFile("hello.txt"));
    }

    @Test
    void readFile_nested() {
        assertEquals("deep content\n", tools.readFile("nested/deep.txt"));
    }

    @Test
    void readFile_missing() {
        var result = tools.readFile("does-not-exist.txt");
        assertTrue(result.startsWith("ERROR:"));
        assertTrue(result.contains("does not exist"));
    }

    @Test
    void readFile_directoryNotFile() {
        var result = tools.readFile("nested");
        assertTrue(result.startsWith("ERROR:"));
        assertTrue(result.contains("not a file"));
    }

    @Test
    void readFile_escapeAttempt() {
        // The guard. If this ever goes green by accident, the sandbox is broken.
        var result = tools.readFile("../outside.txt");
        assertTrue(result.startsWith("ERROR:"));
        assertTrue(result.contains("outside"));
    }

    @Test
    void readFile_symlinkEscapeAttempt() throws IOException {
        // The second guard, and the subtler one. Path.normalize is textual, so
        // a symlink *inside* the sandbox pointing anywhere on disk passes a
        // textual containment check — and then Files.readString follows it.
        // PathSandbox resolves the real path before deciding, which is why
        // calling it is not optional.
        Path outside = makeOutsideFile("read");
        if (!trySymlink(outside, sandbox.resolve("link.txt"))) return;

        var result = tools.readFile("link.txt");
        assertTrue(result.startsWith("ERROR:"));
        assertTrue(result.contains("outside"));
    }

    // ---- listFiles --------------------------------------------------------

    @Test
    void listFiles_root() {
        ToolListResult result = tools.listFiles(".");
        assertFalse(result.isError());
        assertTrue(result.entries().contains("hello.txt"));
        assertTrue(result.entries().contains("nested/"));
    }

    @Test
    void listFiles_nested() {
        ToolListResult result = tools.listFiles("nested");
        assertFalse(result.isError());
        assertEquals(List.of("deep.txt"), result.entries());
    }

    @Test
    void listFiles_missing() {
        ToolListResult result = tools.listFiles("no-such-dir");
        assertTrue(result.isError());
        assertTrue(result.error().startsWith("ERROR:"));
    }

    @Test
    void listFiles_onFile() {
        ToolListResult result = tools.listFiles("hello.txt");
        assertTrue(result.isError());
        assertTrue(result.error().startsWith("ERROR:"));
    }

    // ---- editFile -----------------------------------------------------------

    @Test
    void editFile_success() throws IOException {
        var result = tools.editFile("hello.txt", "hello", "hi");
        assertTrue(result.startsWith("OK:"));
        assertEquals("hi world\n", read("hello.txt"));
    }

    @Test
    void editFile_missingOldStr() {
        var result = tools.editFile("hello.txt", "goodbye", "hi");
        assertTrue(result.startsWith("ERROR:"));
        assertTrue(result.contains("not found"));
    }

    @Test
    void editFile_nonUniqueOldStr() throws IOException {
        Files.writeString(sandbox.resolve("repeated.txt"), "foo bar foo baz\n");

        var result = tools.editFile("repeated.txt", "foo", "qux");
        assertTrue(result.startsWith("ERROR:"));
        assertTrue(result.contains("2 times"));

        // The file must NOT have been modified on a non-unique match. This is the
        // test that catches a naive String.replace().
        assertEquals("foo bar foo baz\n", read("repeated.txt"));
    }

    @Test
    void editFile_preservesFileOnError() throws IOException {
        String original = read("hello.txt");
        tools.editFile("hello.txt", "nope", "yep");
        assertEquals(original, read("hello.txt"));
    }

    @Test
    void editFile_willNotWriteThroughSymlinkOutOfSandbox() throws IOException {
        Path outside = makeOutsideFile("edit");
        if (!trySymlink(outside, sandbox.resolve("link.txt"))) return;

        var result = tools.editFile("link.txt", "secret", "pwned");
        assertTrue(result.startsWith("ERROR:"));
        assertEquals("secret\n", Files.readString(outside));
    }

    private static void deleteRecursively(Path path) throws IOException {
        if (!Files.exists(path)) return;
        try (var walk = Files.walk(path)) {
            walk.sorted(Comparator.reverseOrder()).forEach(p -> {
                try {
                    Files.delete(p);
                } catch (IOException ignored) {
                    // best-effort cleanup
                }
            });
        }
    }
}

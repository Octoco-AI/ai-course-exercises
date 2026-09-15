package ai.octoco.tinyagent.shared;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

/**
 * Resolves a caller-supplied path against a fixed root, refusing anything that
 * escapes it. This helper is GIVEN to you — it does the path-safety check so
 * you can focus on the tool logic.
 *
 * <p>The Python original captures the sandbox root at import time in a module
 * global. Here the root is injected through the constructor instead: it is the
 * same idea, and it makes the tests straightforward (they hand in a temp
 * directory rather than monkey-patching a global).
 */
public final class PathSandbox {

    private final Path root;
    /** The root with symlinks resolved. Containment is decided against this. */
    private final Path realRoot;
    private final boolean caseSensitive;

    public PathSandbox(String root) {
        this.root = Path.of(root).toAbsolutePath().normalize();
        this.realRoot = realPath(this.root);
        // Windows and macOS default to case-insensitive file systems; Linux does not.
        String os = System.getProperty("os.name", "").toLowerCase(Locale.ROOT);
        this.caseSensitive = os.contains("linux");
    }

    public Path root() {
        return root;
    }

    /**
     * Resolve {@code path} inside the sandbox.
     *
     * @return a successful resolution, or a failure whose {@link ResolveResult#error()}
     *         starts with {@code "ERROR:"}.
     */
    public ResolveResult tryResolve(String path) {
        Path candidate;
        try {
            candidate = root.resolve(path).toAbsolutePath().normalize();
        } catch (Exception ex) {
            return ResolveResult.fail("ERROR: could not resolve path '" + path + "': " + ex.getMessage());
        }

        // First pass, purely textual: catches ".." traversal and absolute paths
        // pointing elsewhere, which is most of what a confused model sends.
        if (!isInside(root, candidate)) {
            return ResolveResult.fail("ERROR: path '" + path + "' is outside the sandbox (" + root + ")");
        }

        // Second pass, following symlinks. Path.normalize is textual, so a
        // symlink *inside* the sandbox may point anywhere on disk and still sail
        // through the check above — and Files.readString will happily follow it.
        if (!isInside(realRoot, realPath(candidate))) {
            return ResolveResult.fail(
                    "ERROR: path '" + path + "' is a symlink leading outside the sandbox (" + root + ")");
        }

        return ResolveResult.ok(candidate);
    }

    private boolean isInside(Path base, Path candidate) {
        Path trimmed = candidate.normalize();
        if (pathsEqual(trimmed, base)) {
            return true;
        }
        return trimmed.startsWith(base);
    }

    private boolean pathsEqual(Path a, Path b) {
        if (caseSensitive) {
            return a.equals(b);
        }
        return a.toString().equalsIgnoreCase(b.toString());
    }

    /**
     * {@code target} with every symlink along it resolved. Missing segments are
     * appended rather than rejected, because a path that does not exist yet still
     * has to be checked — its parent may be the link.
     */
    private static Path realPath(Path target) {
        Path absolute = target.toAbsolutePath().normalize();
        Path root = absolute.getRoot();
        if (root == null) {
            return absolute;
        }

        Path current = root;
        for (Path segment : absolute) {
            Path next = current.resolve(segment);
            try {
                if (Files.exists(next, java.nio.file.LinkOption.NOFOLLOW_LINKS)
                        && Files.isSymbolicLink(next)) {
                    Path linkTarget = Files.readSymbolicLink(next);
                    if (!linkTarget.isAbsolute()) {
                        linkTarget = next.getParent().resolve(linkTarget);
                    }
                    current = linkTarget.toAbsolutePath().normalize();
                    // Follow final target if the link points at another link chain.
                    if (Files.exists(current)) {
                        try {
                            current = current.toRealPath();
                        } catch (IOException ignored) {
                            // broken chain — keep what we have
                        }
                    }
                } else if (Files.exists(next)) {
                    try {
                        // Resolve intermediate real directories when possible.
                        if (Files.isDirectory(next)) {
                            current = next.toRealPath();
                        } else {
                            current = next;
                        }
                    } catch (IOException e) {
                        current = next.toAbsolutePath().normalize();
                    }
                } else {
                    current = next.toAbsolutePath().normalize();
                }
            } catch (IOException e) {
                current = next.toAbsolutePath().normalize();
            }
        }
        return current.normalize();
    }

    /** Result of {@link #tryResolve(String)}. */
    public record ResolveResult(Path path, String error) {
        public static ResolveResult ok(Path path) {
            return new ResolveResult(path, null);
        }

        public static ResolveResult fail(String error) {
            return new ResolveResult(null, error);
        }

        public boolean isOk() {
            return error == null;
        }
    }
}

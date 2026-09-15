package ai.octoco.expensecategoriser;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/**
 * A small {@code .env} reader, so the Java path needs no extra dependency
 * where Python uses {@code python-dotenv}.
 */
public final class DotEnv {

    private DotEnv() {}

    /**
     * Load {@code .env} from {@code startDirectory} or the nearest ancestor
     * that has one. Existing environment variables always win.
     */
    public static void load() {
        load(Path.of("").toAbsolutePath());
    }

    public static void load(Path startDirectory) {
        Path dir = startDirectory.toAbsolutePath().normalize();
        while (dir != null) {
            Path candidate = dir.resolve(".env");
            if (Files.isRegularFile(candidate)) {
                apply(candidate);
                return;
            }
            dir = dir.getParent();
        }
    }

    private static void apply(Path path) {
        List<String> lines;
        try {
            lines = Files.readAllLines(path);
        } catch (IOException ex) {
            return;
        }

        for (String raw : lines) {
            String line = raw.trim();
            if (line.isEmpty() || line.startsWith("#")) {
                continue;
            }

            int eq = line.indexOf('=');
            if (eq <= 0) {
                continue;
            }

            String key = line.substring(0, eq).trim();
            String value = line.substring(eq + 1).trim();
            if ((value.startsWith("\"") && value.endsWith("\""))
                    || (value.startsWith("'") && value.endsWith("'"))) {
                value = value.substring(1, value.length() - 1);
            }

            if (System.getenv(key) == null && System.getProperty(key) == null) {
                // Process environment is immutable on the JVM; expose via
                // system properties so GeminiClient can still read overrides
                // set only in .env files. Prefer getenv first.
                System.setProperty(key, value);
            }
        }
    }

    /**
     * Resolve a config value: real environment first, then system property
     * (which is how {@link #load} injects .env values).
     */
    public static String get(String key) {
        String fromEnv = System.getenv(key);
        if (fromEnv != null) {
            return fromEnv;
        }
        return System.getProperty(key);
    }
}

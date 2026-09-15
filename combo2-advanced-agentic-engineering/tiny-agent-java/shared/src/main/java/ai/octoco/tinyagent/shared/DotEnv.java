package ai.octoco.tinyagent.shared;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * A small {@code .env} reader, so the Java path needs no extra dependency
 * where Python uses {@code python-dotenv}. GIVEN.
 *
 * <p>Unlike the C# port, this does not call the equivalent of
 * {@code Environment.SetEnvironmentVariable} — the JVM has no public API to
 * mutate the current process's environment block once it has started. Values
 * read from {@code .env} are kept in a private map instead, and {@link #get}
 * checks the real environment first so a real environment variable always
 * wins, then falls back to what {@code .env} provided.
 */
public final class DotEnv {

    private static final Map<String, String> LOADED = new ConcurrentHashMap<>();

    private DotEnv() {}

    /**
     * Load {@code .env} from {@code startDirectory} or the nearest ancestor
     * that has one.
     */
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
        } catch (IOException e) {
            return;
        }

        for (String raw : lines) {
            String line = raw.trim();
            if (line.isEmpty() || line.startsWith("#")) continue;

            int eq = line.indexOf('=');
            if (eq <= 0) continue;

            String key = line.substring(0, eq).trim();
            String value = stripQuotes(line.substring(eq + 1).trim());
            LOADED.put(key, value);
        }
    }

    private static String stripQuotes(String value) {
        if (value.length() >= 2) {
            char first = value.charAt(0);
            char last = value.charAt(value.length() - 1);
            if ((first == '"' && last == '"') || (first == '\'' && last == '\'')) {
                return value.substring(1, value.length() - 1);
            }
        }
        return value;
    }

    /** A value from the real environment, or from {@code .env} — real environment wins. */
    public static String get(String key) {
        String fromEnv = System.getenv(key);
        return fromEnv != null ? fromEnv : LOADED.get(key);
    }

    /** The API key, or null. Callers produce their own error message. */
    public static String apiKey() {
        return get("GOOGLE_API_KEY");
    }

    /** The model id, defaulting to the workshop model. */
    public static String model() {
        String m = get("GEMINI_MODEL");
        return (m != null && !m.isBlank()) ? m : GeminiClient.DEFAULT_MODEL;
    }
}

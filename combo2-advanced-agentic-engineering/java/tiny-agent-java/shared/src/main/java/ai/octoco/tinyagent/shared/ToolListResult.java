package ai.octoco.tinyagent.shared;

import java.util.List;

/**
 * Result of {@link Tools#listFiles(String)} — either entries, or an error string.
 *
 * <p>The Python original returns a single-element {@code ["ERROR: ..."]} list on
 * failure so the return type never changes. That is a Python-typing workaround;
 * in Java a small result type says the same thing honestly. What matters — and
 * what carries over unchanged — is that the model still receives a plain string
 * describing the failure.
 */
public record ToolListResult(List<String> entries, String error) {

    public static ToolListResult ok(List<String> entries) {
        return new ToolListResult(List.copyOf(entries), null);
    }

    public static ToolListResult fail(String error) {
        return new ToolListResult(null, error);
    }

    public boolean isError() {
        return error != null;
    }

    /** Flatten to what the model sees: the entries, or the error text. */
    public String toModelString() {
        if (error != null) {
            return error;
        }
        return String.join("\n", entries == null ? List.of() : entries);
    }
}

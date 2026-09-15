package ai.octoco.tinyagent.tests;

/**
 * Which implementation the tests exercise.
 *
 * <p><b>Defaults to your code</b> — both the tools and the loop. Set
 * {@code TINY_AGENT_IMPL=reference} to run the same suite against the worked
 * solution, useful to confirm the tests themselves are sane, or to see green
 * before you start.
 *
 * <pre>{@code
 * ./mvnw test                                    # tests YOUR code
 * TINY_AGENT_IMPL=reference ./mvnw test          # tests the worked solution
 * }</pre>
 *
 * <p>The Python version of this exercise imports the reference implementation
 * when it is present and falls back to the starter, which means the suite
 * goes green against code the attendee never wrote until they hand-edit the
 * import. This is that bug fixed: here the default is always your own code.
 */
final class Impl {

    private Impl() {}

    static String selected() {
        String impl = System.getenv("TINY_AGENT_IMPL");
        String normalized = impl == null ? "" : impl.trim().toLowerCase(java.util.Locale.ROOT);

        return switch (normalized) {
            case "reference" -> "reference";
            case "starter", "" -> "starter";
            default -> throw new IllegalStateException(
                    "TINY_AGENT_IMPL must be 'starter' or 'reference', got '" + impl + "'.");
        };
    }
}

package ai.octoco.tinyagent.shared;

import java.nio.file.Path;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.function.Consumer;
import java.util.function.Function;

/**
 * Shared console entrypoint. GIVEN — no changes needed.
 */
public final class Cli {

    private Cli() {}

    /** Runs the agent loop for one prompt and returns its final answer. */
    @FunctionalInterface
    public interface AgentRunner {
        CompletableFuture<String> run(String prompt, Tools tools, GeminiClient client, Consumer<AgentEvent> onEvent);
    }

    /** Print one line per meaningful action, so the loop is visible as it runs. */
    public static void printEvent(AgentEvent event) {
        if (event instanceof AgentEvent.ToolCall call) {
            System.out.println("  -> " + call.name() + "(" + call.argsPreview() + ")");
        } else if (event instanceof AgentEvent.ToolResult result) {
            String text = result.result();
            if (text.length() > 200) text = text.substring(0, 197) + "...";
            System.out.println("     " + text.replace("\r\n", " | ").replace("\n", " | "));
        }
    }

    /** Wire up env, client and tools, then run one prompt. Returns a process exit code. */
    public static int run(String[] args, String usage, Function<String, Tools> makeTools, AgentRunner runner) {
        if (args.length == 0) {
            System.err.println(usage);
            return 1;
        }

        DotEnv.load(Path.of("").toAbsolutePath());

        String apiKey = DotEnv.apiKey();
        if (apiKey == null || apiKey.isBlank() || apiKey.equals("your_gemini_api_key_here")) {
            System.err.println("ERROR: GOOGLE_API_KEY is not set. Copy .env.example to .env and paste your key.");
            return 2;
        }

        // The sandbox root is wherever you started the agent — same rule as the
        // Python version, where it is Path.cwd().
        Tools tools = makeTools.apply(Path.of("").toAbsolutePath().toString());
        GeminiClient client = new GeminiClient(apiKey);

        try {
            String prompt = String.join(" ", List.of(args));
            String finalText = runner.run(prompt, tools, client, Cli::printEvent).join();
            System.out.println();
            System.out.println(finalText);
            return 0;
        } catch (CompletionException wrapped) {
            Throwable cause = wrapped.getCause() != null ? wrapped.getCause() : wrapped;
            if (cause instanceof UnsupportedOperationException ex) {
                System.err.println("Not implemented yet: " + ex.getMessage());
                return 3;
            }
            if (cause instanceof GeminiRequestException ex) {
                System.err.println("ERROR: " + ex.getMessage());
                return 4;
            }
            throw wrapped;
        }
    }
}

package ai.octoco.tinyagent.starter;

import ai.octoco.tinyagent.shared.AgentEvent;
import ai.octoco.tinyagent.shared.DotEnv;
import ai.octoco.tinyagent.shared.FunctionCall;
import ai.octoco.tinyagent.shared.GeminiClient;
import ai.octoco.tinyagent.shared.ToolSchemas;
import ai.octoco.tinyagent.shared.Tools;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

/**
 * The agent loop. YOU WRITE THIS (step 1).
 *
 * <p>Thesis (Thorsten Ball, ampcode.com): <i>It's an LLM, a loop, and enough
 * tokens.</i> The shape of the loop you're going to write:
 *
 * <pre>{@code
 * contents = [userPrompt]
 * for turn in 1..maxTurns:
 *     response = client.generateContentAsync(model, request).join()
 *     contents.add(candidate.content())        // don't forget this line
 *     calls = parts where functionCall() is not null
 *     if no calls: return the joined text      // done
 *     foreach call: dispatch it, append a functionResponse part
 *     contents.add(new Content("user", responseParts))
 * }</pre>
 *
 * <p>{@link GeminiClient#generateContentAsync} returns a {@link CompletableFuture}
 * because {@code java.net.http.HttpClient.sendAsync} does. Calling {@code .join()}
 * on it is the Java equivalent of {@code await} — plumbing, not the lesson.
 */
public final class Agent {

    public static final String SYSTEM_INSTRUCTION = """
            You are a careful coding assistant working inside a small
            code repository. You have three tools: read_file, list_files, and edit_file.

            Workflow:
            1. Explore first. Use list_files and read_file to build an understanding before editing.
            2. Edit sparingly. One edit per logical change. Use enough surrounding context in
               old_str so it matches exactly once.
            3. Report what you did in plain prose when you are finished. Do not call any tool on
               the final turn — that's how you signal you're done.
            4. If a tool returns a string starting with "ERROR:", read the error carefully and
               adjust your approach. Don't retry the same call blindly.
            """;

    private Agent() {}

    // -------------------------------------------------------------------------
    // STEP 1 — implement runAsync
    // -------------------------------------------------------------------------
    /**
     * Run the agent loop until the model returns a final answer.
     *
     * <p>Hints — everything you need is in {@code ai.octoco.tinyagent.shared}:
     * <ul>
     *   <li>Build a turn: {@code new Content("user", List.of(Part.text(userPrompt)))}</li>
     *   <li>Build the request: {@code new GeminiRequest(contents, List.of(ToolSchemas.all()), systemInstruction)}</li>
     *   <li>Call the model: {@code client.generateContentAsync(model, request).join()}</li>
     *   <li>The model's turn: {@code response.firstCandidate().content()}</li>
     *   <li>Function calls live in {@code content.parts()} where {@code part.functionCall() != null}</li>
     *   <li>Send a result back: {@code Part.functionResponse(new FunctionResponse(name, resultNode))}</li>
     *   <li>Tool results go back with role <b>"user"</b>, not "tool" and not "function"</li>
     *   <li>Termination: a turn with no function-call parts</li>
     *   <li>{@link #dispatch} below is written for you — call it, don't rewrite it</li>
     * </ul>
     * Start with the simplest version that handles the exploration prompts
     * (TODO.md items 1 and 2), then try the bug-fix prompt (item 3).
     */
    public static CompletableFuture<String> runAsync(
            String userPrompt,
            Tools tools,
            GeminiClient client,
            String model,
            int maxTurns,
            Consumer<AgentEvent> onEvent) {
        String resolvedModel = model != null ? model : DotEnv.model();

        // TODO: Step 1 — write the loop.
        return CompletableFuture.failedFuture(new UnsupportedOperationException("Implement runAsync for step 1."));
    }

    // ---- given below this line — no changes needed -------------------------

    /**
     * Route one function call to a tool. Every failure path returns a string.
     */
    public static String dispatch(Tools tools, FunctionCall call) {
        try {
            return switch (call.name()) {
                case ToolSchemas.READ_FILE -> tools.readFile(requiredArg(call, "path"));
                case ToolSchemas.LIST_FILES -> {
                    String path = optionalArg(call, "path");
                    yield tools.listFiles(path != null ? path : ".").toModelString();
                }
                case ToolSchemas.EDIT_FILE -> tools.editFile(
                        requiredArg(call, "path"),
                        requiredArg(call, "old_str"),
                        requiredArg(call, "new_str"));
                default -> "ERROR: unknown tool '" + call.name() + "'";
            };
        } catch (IllegalArgumentException ex) {
            return "ERROR: bad arguments to " + call.name() + ": " + ex.getMessage();
        } catch (Exception ex) {
            return "ERROR: " + ex.getClass().getSimpleName() + ": " + ex.getMessage();
        }
    }

    public static String requiredArg(FunctionCall call, String name) {
        String value = optionalArg(call, name);
        if (value == null) throw new IllegalArgumentException("missing required argument '" + name + "'");
        return value;
    }

    public static String optionalArg(FunctionCall call, String name) {
        JsonNode args = call.args();
        if (args == null) return null;
        JsonNode node = args.get(name);
        return (node == null || node.isNull()) ? null : node.asText();
    }

    public static String previewArgs(JsonNode args) {
        if (args == null || args.isEmpty()) return "";

        StringBuilder sb = new StringBuilder();
        var fields = args.fields();
        while (fields.hasNext()) {
            var entry = fields.next();
            if (sb.length() > 0) sb.append(", ");
            sb.append(entry.getKey()).append('=').append(entry.getValue().toString());
        }

        String preview = sb.toString();
        return preview.length() > 120 ? preview.substring(0, 117) + "..." : preview;
    }
}

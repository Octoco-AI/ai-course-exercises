package ai.octoco.tinyagent.reference;

import ai.octoco.tinyagent.shared.AgentEvent;
import ai.octoco.tinyagent.shared.Content;
import ai.octoco.tinyagent.shared.DotEnv;
import ai.octoco.tinyagent.shared.FunctionCall;
import ai.octoco.tinyagent.shared.FunctionResponse;
import ai.octoco.tinyagent.shared.GeminiClient;
import ai.octoco.tinyagent.shared.GeminiRequest;
import ai.octoco.tinyagent.shared.Part;
import ai.octoco.tinyagent.shared.ToolSchemas;
import ai.octoco.tinyagent.shared.Tools;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

/**
 * The agent loop — complete worked solution.
 *
 * <p>Thesis (Thorsten Ball, ampcode.com): <i>It's an LLM, a loop, and enough
 * tokens.</i> What the loop does, in one glance:
 *
 * <pre>{@code
 * contents = [user_prompt]
 * while turn < maxTurns:
 *     response = gemini.generate(contents, tools)
 *     contents.add(response.content)          // the most-forgotten line
 *     calls = function calls in the response
 *     if no calls: return the text            // done
 *     foreach call: contents.add(functionResponse)
 * }</pre>
 *
 * <p>Note {@link #runAsync} returns a {@link CompletableFuture}. The Python
 * original is deliberately synchronous — its facilitator notes say "not a
 * chance to teach asyncio". In Java, {@code HttpClient.sendAsync} returns a
 * {@code CompletableFuture}, so each turn calls {@code .join()} on it —
 * the Java equivalent of {@code await}. It is plumbing, not the lesson: read
 * past it and look at the loop.
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

    public static CompletableFuture<String> runAsync(String userPrompt, Tools tools, GeminiClient client) {
        return runAsync(userPrompt, tools, client, null, 20, evt -> { });
    }

    public static CompletableFuture<String> runAsync(
            String userPrompt, Tools tools, GeminiClient client, String model, int maxTurns) {
        return runAsync(userPrompt, tools, client, model, maxTurns, evt -> { });
    }

    public static CompletableFuture<String> runAsync(
            String userPrompt,
            Tools tools,
            GeminiClient client,
            String model,
            int maxTurns,
            Consumer<AgentEvent> onEvent) {
        String resolvedModel = model != null ? model : DotEnv.model();

        // Conversation state. Gemini's "contents" is an ordered list of turns
        // alternating between role "user" and role "model". Tool results go back
        // as a *user* turn whose parts are functionResponse parts.
        List<Content> contents = new ArrayList<>();
        contents.add(new Content("user", List.of(Part.text(userPrompt))));

        List<JsonNode> declarations = List.of(ToolSchemas.all());
        Content systemInstruction = new Content("user", List.of(Part.text(SYSTEM_INSTRUCTION)));

        return CompletableFuture.supplyAsync(() -> {
            for (int turn = 1; turn <= maxTurns; turn++) {
                onEvent.accept(new AgentEvent.TurnStart(turn));

                GeminiRequest request = new GeminiRequest(contents, declarations, systemInstruction);
                var response = client.generateContentAsync(resolvedModel, request).join();

                var candidate = response.firstCandidate();
                if (candidate == null || candidate.content() == null) {
                    String finishReason = candidate != null ? candidate.finishReason() : "none";
                    return "ERROR: model returned no content (finishReason: "
                            + (finishReason != null ? finishReason : "none") + ")";
                }

                // Append the model's turn BEFORE doing anything else. Forget this and
                // the model re-reads a context that never contains its own tool calls,
                // so it asks for the same thing forever. It is the #1 failure here.
                contents.add(candidate.content());

                List<FunctionCall> calls = new ArrayList<>();
                List<Part> parts = candidate.content().parts();
                if (parts != null) {
                    for (Part part : parts) {
                        if (part.functionCall() != null) {
                            calls.add(part.functionCall());
                        }
                    }
                }

                if (calls.isEmpty()) {
                    // No tool calls -> the model signalled it is done.
                    StringBuilder finalText = new StringBuilder();
                    if (parts != null) {
                        for (Part part : parts) {
                            if (part.text() != null) finalText.append(part.text());
                        }
                    }
                    onEvent.accept(new AgentEvent.Final(finalText.toString(), turn));
                    return finalText.toString();
                }

                // Execute every call and collect the responses.
                List<Part> responseParts = new ArrayList<>();
                for (FunctionCall call : calls) {
                    onEvent.accept(new AgentEvent.ToolCall(call.name(), previewArgs(call.args())));

                    String result = dispatch(tools, call);

                    onEvent.accept(new AgentEvent.ToolResult(call.name(), result));
                    ObjectNode resultNode = JsonNodeFactory.instance.objectNode().put("result", result);
                    responseParts.add(Part.functionResponse(new FunctionResponse(call.name(), resultNode)));
                }

                // Send all tool responses back in a single user turn.
                contents.add(new Content("user", responseParts));
            }

            return "ERROR: agent did not finish within " + maxTurns + " turns";
        });
    }

    /**
     * Route one function call to a tool. Every failure path returns a string —
     * nothing thrown here reaches the loop.
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
            // Surface any tool failure to the model rather than killing the loop.
            return "ERROR: " + ex.getClass().getSimpleName() + ": " + ex.getMessage();
        }
    }

    private static String requiredArg(FunctionCall call, String name) {
        String value = optionalArg(call, name);
        if (value == null) throw new IllegalArgumentException("missing required argument '" + name + "'");
        return value;
    }

    private static String optionalArg(FunctionCall call, String name) {
        JsonNode args = call.args();
        if (args == null) return null;
        JsonNode node = args.get(name);
        return (node == null || node.isNull()) ? null : node.asText();
    }

    private static String previewArgs(JsonNode args) {
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

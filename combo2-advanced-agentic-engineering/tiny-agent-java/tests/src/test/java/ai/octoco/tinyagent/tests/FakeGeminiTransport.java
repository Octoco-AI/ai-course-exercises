package ai.octoco.tinyagent.tests;

import ai.octoco.tinyagent.shared.GeminiTransport;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import java.util.concurrent.CompletableFuture;

/**
 * A canned Gemini transport that replays scripted turns, so the loop can be
 * tested without an API key or a cent of spend.
 *
 * <p>Also records every request body, which is how the tests below assert on
 * what the loop actually sent back — the part you cannot see from the outside.
 */
final class FakeGeminiTransport implements GeminiTransport {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final Deque<String> responses;
    private final List<String> requests = new ArrayList<>();

    FakeGeminiTransport(String... responseBodies) {
        this.responses = new ArrayDeque<>(List.of(responseBodies));
    }

    List<String> requests() {
        return requests;
    }

    @Override
    public CompletableFuture<String> post(String url, String apiKey, String requestBody) {
        requests.add(requestBody);

        if (responses.isEmpty()) {
            return CompletableFuture.failedFuture(new IllegalStateException(
                    "FakeGeminiTransport ran out of scripted responses — the loop asked for more turns than expected."));
        }

        return CompletableFuture.completedFuture(responses.poll());
    }

    // ---- helpers for building scripted turns --------------------------------

    static String textTurn(String text) {
        return candidate("{\"text\": " + json(text) + "}");
    }

    static String toolCallTurn(String name, Object args) {
        return candidate("{\"functionCall\": {\"name\": " + json(name) + ", \"args\": " + toJson(args) + "}}");
    }

    private static String candidate(String part) {
        return "{\"candidates\": [{\"content\": {\"role\": \"model\", \"parts\": [" + part + "]}}]}";
    }

    private static String json(String value) {
        return toJson(value);
    }

    private static String toJson(Object value) {
        try {
            return MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}

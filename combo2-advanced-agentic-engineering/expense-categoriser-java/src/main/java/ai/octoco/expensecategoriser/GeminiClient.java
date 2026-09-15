package ai.octoco.expensecategoriser;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

/**
 * Thin Gemini client over {@link HttpClient}. No SDK.
 *
 * <p>There is no first-party Google GenAI SDK we want attendees to learn here,
 * so this talks to the REST API directly — about 80 lines. The same choice as
 * the tiny-agent exercise, for the same reason: you can see the whole protocol.
 *
 * <p>Two settings matter for a classifier and are easy to miss:
 * <ul>
 *   <li>{@code responseMimeType: "application/json"} — ask for JSON rather than
 *       hoping for it. Halves the contract violations on its own.</li>
 *   <li>{@code temperature: 0.1} — this is classification; we want
 *       near-determinism, not creativity.</li>
 * </ul>
 */
public final class GeminiClient implements LlmClient {

    public static final String DEFAULT_MODEL = "gemini-3.1-flash-lite";
    private static final String BASE_URL =
            "https://generativelanguage.googleapis.com/v1beta/models";

    private final HttpClient http;
    private final ObjectMapper mapper;
    private final String apiKey;
    private final String model;

    public GeminiClient() {
        this(null, null, null);
    }

    public GeminiClient(String apiKey, String model, HttpClient http) {
        this.apiKey = firstNonBlank(
                apiKey,
                DotEnv.get("GOOGLE_API_KEY"),
                System.getenv("GOOGLE_API_KEY"));
        this.model = firstNonBlank(
                model,
                DotEnv.get("GEMINI_MODEL"),
                System.getenv("GEMINI_MODEL"),
                DEFAULT_MODEL);
        this.http = http != null
                ? http
                : HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(30)).build();
        this.mapper = new ObjectMapper();
    }

    @Override
    public String generate(String systemPrompt, String userPrompt) {
        if (apiKey == null || apiKey.isBlank()) {
            // A configuration problem, not a model problem — the API maps this
            // to 500, where a contract violation maps to 502.
            throw new IllegalStateException(
                    "GOOGLE_API_KEY is not set. Either add it to .env or pass apiKey explicitly.");
        }

        ObjectNode payload = mapper.createObjectNode();

        ArrayNode contents = payload.putArray("contents");
        ObjectNode userTurn = contents.addObject();
        userTurn.put("role", "user");
        ArrayNode userParts = userTurn.putArray("parts");
        userParts.addObject().put("text", userPrompt);

        ObjectNode systemInstruction = payload.putObject("systemInstruction");
        ArrayNode systemParts = systemInstruction.putArray("parts");
        systemParts.addObject().put("text", systemPrompt);

        ObjectNode generationConfig = payload.putObject("generationConfig");
        generationConfig.put("responseMimeType", "application/json");
        generationConfig.put("temperature", 0.1);

        String body;
        try {
            body = mapper.writeValueAsString(payload);
        } catch (IOException ex) {
            throw new IllegalStateException("failed to serialise Gemini payload", ex);
        }

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(BASE_URL + "/" + model + ":generateContent"))
                .timeout(Duration.ofSeconds(60))
                .header("Content-Type", "application/json")
                .header("x-goog-api-key", apiKey)
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .build();

        HttpResponse<String> response;
        try {
            response = http.send(request, HttpResponse.BodyHandlers.ofString());
        } catch (IOException | InterruptedException ex) {
            if (ex instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            throw new IllegalStateException("Gemini request failed: " + ex.getMessage(), ex);
        }

        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            String hint = response.statusCode() == 429
                    ? " (free-tier rate limit — wait a few seconds and retry)"
                    : "";
            throw new IllegalStateException(
                    "Gemini returned " + response.statusCode() + hint + ": " + response.body());
        }

        return extractText(response.body());
    }

    /** Pull the text out of the first candidate. Returns "" if there isn't one. */
    private String extractText(String body) {
        try {
            JsonNode root = mapper.readTree(body);
            JsonNode candidates = root.get("candidates");
            if (candidates == null || !candidates.isArray() || candidates.isEmpty()) {
                return "";
            }
            JsonNode parts = candidates.get(0).path("content").path("parts");
            if (!parts.isArray()) {
                return "";
            }
            StringBuilder text = new StringBuilder();
            for (JsonNode part : parts) {
                JsonNode t = part.get("text");
                if (t != null && t.isTextual()) {
                    text.append(t.asText());
                }
            }
            return text.toString();
        } catch (IOException ex) {
            throw new IllegalStateException(
                    "failed to parse Gemini response: " + ex.getMessage(), ex);
        }
    }

    private static String firstNonBlank(String... values) {
        if (values == null) {
            return null;
        }
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return null;
    }
}

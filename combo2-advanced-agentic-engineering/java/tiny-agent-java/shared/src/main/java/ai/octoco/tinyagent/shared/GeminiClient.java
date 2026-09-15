package ai.octoco.tinyagent.shared;

import com.fasterxml.jackson.core.JsonProcessingException;
import java.io.UncheckedIOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;

/**
 * A small async Gemini client built on {@code java.net.http.HttpClient}. No SDK.
 *
 * <p>The Python version of this exercise uses the {@code google-genai} SDK and
 * has to pass {@code automatic_function_calling=AutomaticFunctionCallingConfig(disable=True)}
 * to stop the SDK running the tools for you and handing back only the final
 * text. At the REST layer there is nothing to disable: <b>the loop is always
 * yours</b>. That is the same lesson, arrived at from the other direction.
 *
 * <p>There is no first-party Google GenAI SDK for Java. That turns out to be a
 * gift for this exercise — you can see the entire protocol.
 */
public final class GeminiClient {

    public static final String DEFAULT_MODEL = "gemini-3.1-flash-lite";
    private static final String BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models";

    private final String apiKey;
    private final GeminiTransport transport;

    public GeminiClient(String apiKey) {
        this(apiKey, defaultTransport(Duration.ofSeconds(120)));
    }

    public GeminiClient(String apiKey, GeminiTransport transport) {
        if (apiKey == null || apiKey.isBlank()) {
            throw new IllegalStateException(
                    "GOOGLE_API_KEY is not set. Copy .env.example to .env and paste your key.");
        }
        this.apiKey = apiKey;
        this.transport = transport;
    }

    /** One round-trip to the model. */
    public CompletableFuture<GeminiResponse> generateContentAsync(String model, GeminiRequest request) {
        String url = BASE_URL + "/" + model + ":generateContent";

        String body;
        try {
            body = GeminiJson.MAPPER.writeValueAsString(request);
        } catch (JsonProcessingException e) {
            return CompletableFuture.failedFuture(new UncheckedIOException(e));
        }

        return transport.post(url, apiKey, body).thenApply(responseBody -> {
            try {
                return GeminiJson.MAPPER.readValue(responseBody, GeminiResponse.class);
            } catch (JsonProcessingException e) {
                throw new UncheckedIOException(e);
            }
        });
    }

    /** The real transport: a plain {@link HttpClient}, called asynchronously. */
    private static GeminiTransport defaultTransport(Duration timeout) {
        HttpClient http = HttpClient.newBuilder()
                .connectTimeout(timeout)
                .build();

        return (url, apiKey, requestBody) -> {
            HttpRequest httpRequest = HttpRequest.newBuilder(URI.create(url))
                    .timeout(timeout)
                    .header("Content-Type", "application/json")
                    // The key travels in a header, not the query string, so it stays out of logs.
                    .header("x-goog-api-key", apiKey)
                    .POST(HttpRequest.BodyPublishers.ofString(requestBody, StandardCharsets.UTF_8))
                    .build();

            return http.sendAsync(httpRequest, HttpResponse.BodyHandlers.ofString())
                    .thenApply(response -> {
                        if (response.statusCode() != 200) {
                            // 429 on the free tier is common and worth naming explicitly —
                            // it is the single most likely thing to go wrong in the room.
                            String hint = response.statusCode() == 429
                                    ? " (free-tier rate limit — wait a few seconds and retry)"
                                    : "";
                            throw new GeminiRequestException(
                                    "Gemini returned " + response.statusCode() + hint + ": " + response.body());
                        }
                        return response.body();
                    });
        };
    }
}

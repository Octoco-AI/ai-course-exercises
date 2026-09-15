package ai.octoco.tinyagent.shared;

import java.util.concurrent.CompletableFuture;

/**
 * Sends one raw JSON request body to a Gemini URL and returns the raw JSON
 * response body. This is the seam {@link GeminiClient} uses for offline tests.
 *
 * <p>{@code java.net.http.HttpClient} is an abstract class with over a dozen
 * abstract methods, so a full fake implementation is disproportionate
 * boilerplate for a workshop exercise. This interface captures exactly the
 * three inputs a test needs to assert on — url, key, and body — the same
 * three things the C# port's {@code FakeGeminiHandler} records from an
 * {@code HttpRequestMessage}.
 */
@FunctionalInterface
public interface GeminiTransport {

    CompletableFuture<String> post(String url, String apiKey, String requestBody);
}

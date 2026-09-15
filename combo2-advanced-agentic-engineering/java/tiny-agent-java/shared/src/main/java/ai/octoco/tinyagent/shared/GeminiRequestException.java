package ai.octoco.tinyagent.shared;

/** Thrown when the Gemini API returns a non-2xx response. */
public final class GeminiRequestException extends RuntimeException {

    public GeminiRequestException(String message) {
        super(message);
    }
}

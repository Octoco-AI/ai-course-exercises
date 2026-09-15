package ai.octoco.expensecategoriser;

/** An LLM client that always throws — for testing the configuration-error path. */
public final class ThrowingLlmClient implements LlmClient {

    private final RuntimeException exception;

    public ThrowingLlmClient(RuntimeException exception) {
        this.exception = exception;
    }

    @Override
    public String generate(String systemPrompt, String userPrompt) {
        throw exception;
    }
}

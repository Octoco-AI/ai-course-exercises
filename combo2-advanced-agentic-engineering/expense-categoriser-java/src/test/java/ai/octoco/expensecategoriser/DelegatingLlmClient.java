package ai.octoco.expensecategoriser;

/**
 * The {@link LlmClient} bean registered in the API tests' Spring context.
 *
 * <p>Spring Boot has no direct equivalent of ASP.NET's per-test
 * {@code WebApplicationFactory} (which rebuilds the whole app for each test).
 * Reusing one Spring context across a test class is the idiomatic — and much
 * faster — Spring approach, so this class holds a swappable delegate: each
 * test points it at the {@link FakeLlmClient} or {@link ThrowingLlmClient} it
 * needs before making its HTTP call.
 */
public final class DelegatingLlmClient implements LlmClient {

    private volatile LlmClient delegate = FakeLlmClient.returning("Other", 0.9);

    public void setDelegate(LlmClient delegate) {
        this.delegate = delegate;
    }

    @Override
    public String generate(String systemPrompt, String userPrompt) {
        return delegate.generate(systemPrompt, userPrompt);
    }
}

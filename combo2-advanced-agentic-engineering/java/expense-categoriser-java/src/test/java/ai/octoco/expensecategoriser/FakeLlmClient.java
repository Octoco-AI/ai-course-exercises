package ai.octoco.expensecategoriser;

/**
 * A canned LLM. The seam that makes the unit and API layers free and instant.
 *
 * <p>Layer 1 (unit) and layer 2 (API contract) never call a real model — they
 * test OUR code. Layer 3 (evals) never uses this — it measures the model.
 * Mixing the two up is the single most common mistake when teams first add
 * evals.
 */
public final class FakeLlmClient implements LlmClient {

    private final String response;
    private String lastSystemPrompt;
    private String lastUserPrompt;
    private int callCount;

    public FakeLlmClient(String response) {
        this.response = response;
    }

    public static FakeLlmClient returning(String category, double confidence) {
        return new FakeLlmClient(
                "{\"category\": \"" + category + "\", \"confidence\": " + confidence + "}");
    }

    @Override
    public String generate(String systemPrompt, String userPrompt) {
        lastSystemPrompt = systemPrompt;
        lastUserPrompt = userPrompt;
        callCount += 1;
        return response;
    }

    public String lastSystemPrompt() {
        return lastSystemPrompt;
    }

    public String lastUserPrompt() {
        return lastUserPrompt;
    }

    public int callCount() {
        return callCount;
    }
}

package ai.octoco.expensecategoriser;

/**
 * Narrow interface so tests can substitute a fake without touching Gemini.
 *
 * <p>This seam is the whole reason the unit tests need no API key and cost
 * nothing. M11 leans on it heavily — notice that the eval suite deliberately
 * does NOT use it, because evals measure the real model.
 */
public interface LlmClient {

    /** Return the raw JSON string the model produced. */
    String generate(String systemPrompt, String userPrompt);
}

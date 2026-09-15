package ai.octoco.expensecategoriser;

import java.util.List;
import java.util.Locale;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import ai.octoco.expensecategoriser.Models.CategorisationOut;
import ai.octoco.expensecategoriser.Models.ContractViolationException;
import ai.octoco.expensecategoriser.Models.ModelResponse;

/**
 * The categorisation logic.
 *
 * <p>Deliberately pulls apart the pieces that matter for three-layer testing:
 * <ul>
 *   <li>{@link #buildPrompt} — pure function, unit-test with exact assertions.</li>
 *   <li>{@link #parseResponse} — pure function, unit-test.</li>
 *   <li>{@link #applyConfidenceThreshold} — pure function, unit-test.</li>
 *   <li>{@link #categorise} — calls Gemini; mock at the LLM boundary for unit tests.</li>
 * </ul>
 *
 * <p>Herman's blog "Testing the Untestable" says: test the deterministic parts
 * traditionally, test the AI boundary for contract conformance, and measure the
 * AI itself via evals at scale. This class is the code under test for all three.
 */
public final class Core {

    public static final double DEFAULT_CONFIDENCE_THRESHOLD = 0.6;

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private static final String SYSTEM_PROMPT_TEMPLATE = """
            You are an expense-categorisation assistant for a personal finance app.

            Given a transaction description and amount, pick the single best category from this list:

            %s

            Respond with a JSON object of exactly this shape:

              {"category": "<one of the categories above>", "confidence": <0.0-1.0>}

            Rules:
            - Use only categories from the list above. No new categories.
            - "confidence" is your self-reported certainty. Use 0.9+ for obvious matches
              (grocery store -> Food & Dining), 0.5-0.7 for ambiguous cases, below 0.5
              for genuinely unclear items.
            - Do not explain. Do not add extra keys. Respond with JSON only.
            """;

    private Core() {}

    /** Build the user-turn prompt. Unit-tested for construction correctness. */
    public static String buildPrompt(String description, double amount) {
        return "Transaction: \"" + description + "\"\nAmount: "
                + String.format(Locale.ROOT, "%.2f", amount);
    }

    /** Render the system prompt with the canonical category list. */
    public static String buildSystemPrompt() {
        return buildSystemPrompt(Models.CANONICAL_CATEGORIES);
    }

    public static String buildSystemPrompt(List<String> categories) {
        StringBuilder joined = new StringBuilder();
        for (String category : categories) {
            if (!joined.isEmpty()) {
                joined.append('\n');
            }
            joined.append("  - ").append(category);
        }
        return SYSTEM_PROMPT_TEMPLATE.formatted(joined);
    }

    /**
     * Parse and validate the model's JSON output.
     *
     * @throws ContractViolationException malformed JSON, unknown category, or
     *     out-of-range confidence. The caller decides how to handle that
     *     (HTTP 502? Fall back to "Other"? Product policy).
     */
    public static ModelResponse parseResponse(String raw) {
        return parseResponse(raw, Models.CANONICAL_CATEGORIES);
    }

    public static ModelResponse parseResponse(String raw, List<String> validCategories) {
        JsonNode root;
        try {
            root = MAPPER.readTree(raw);
        } catch (Exception ex) {
            throw new ContractViolationException(
                    "model response is not valid JSON: " + ex.getMessage());
        }

        if (root == null || !root.isObject()) {
            throw new ContractViolationException(
                    "model response must be a JSON object, got "
                            + (root == null ? "null" : root.getNodeType()));
        }

        JsonNode categoryNode = root.get("category");
        if (categoryNode == null || !categoryNode.isTextual()) {
            throw new ContractViolationException(
                    "model response is missing required field: category");
        }

        JsonNode confidenceNode = root.get("confidence");
        if (confidenceNode == null || !confidenceNode.isNumber()) {
            throw new ContractViolationException(
                    "model response is missing required field: confidence");
        }

        String category = categoryNode.asText();
        if (!validCategories.contains(category)) {
            throw new ContractViolationException(
                    "model returned unknown category '" + category
                            + "'; expected one of [" + String.join(", ", validCategories) + "]");
        }

        double confidence = confidenceNode.asDouble();
        if (confidence < 0.0 || confidence > 1.0) {
            throw new ContractViolationException(
                    "confidence must be in [0, 1], got " + confidence);
        }

        return new ModelResponse(category, confidence);
    }

    /**
     * Graceful degradation: if confidence is below the threshold, return the
     * fallback category instead of the model's (uncertain) answer.
     *
     * <p>From Herman's blog: {@code if confidence < threshold: show 'popular in
     * similar situations'}. For expense categorisation the analogue is
     * "Other", which the user can manually re-classify.
     */
    public static CategorisationOut applyConfidenceThreshold(
            ModelResponse response, double threshold) {
        return applyConfidenceThreshold(response, threshold, Models.FALLBACK_CATEGORY);
    }

    public static CategorisationOut applyConfidenceThreshold(
            ModelResponse response, double threshold, String fallbackCategory) {
        if (response.confidence() < threshold) {
            return new CategorisationOut(fallbackCategory, response.confidence(), true);
        }
        return new CategorisationOut(response.category(), response.confidence(), false);
    }

    /** Categorise a single expense. The function three-layer-tested above. */
    public static CategorisationOut categorise(
            String description, double amount, LlmClient client) {
        return categorise(description, amount, client, null);
    }

    public static CategorisationOut categorise(
            String description,
            double amount,
            LlmClient client,
            Double confidenceThreshold) {
        double threshold = confidenceThreshold != null
                ? confidenceThreshold
                : resolveThreshold();

        String systemPrompt = buildSystemPrompt();
        String userPrompt = buildPrompt(description, amount);

        String raw = client.generate(systemPrompt, userPrompt);
        ModelResponse parsed = parseResponse(raw);
        return applyConfidenceThreshold(parsed, threshold);
    }

    private static double resolveThreshold() {
        String raw = System.getenv("CONFIDENCE_THRESHOLD");
        if (raw == null || raw.isBlank()) {
            return DEFAULT_CONFIDENCE_THRESHOLD;
        }
        try {
            return Double.parseDouble(raw.trim());
        } catch (NumberFormatException ex) {
            return DEFAULT_CONFIDENCE_THRESHOLD;
        }
    }
}

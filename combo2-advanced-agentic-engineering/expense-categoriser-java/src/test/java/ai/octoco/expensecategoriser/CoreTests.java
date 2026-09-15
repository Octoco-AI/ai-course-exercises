package ai.octoco.expensecategoriser;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.octoco.expensecategoriser.Models.CategorisationOut;
import ai.octoco.expensecategoriser.Models.ContractViolationException;
import ai.octoco.expensecategoriser.Models.ModelResponse;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.junit.jupiter.api.Test;

/**
 * Layer 1 — unit tests over the deterministic parts. No LLM, no key, no cost.
 *
 * <p>This is the layer most teams skip when they build an AI feature, on the
 * grounds that "it's all AI, you can't test it". Look how much of this file
 * tests ordinary code with exact assertions. That is the point of pulling
 * {@code buildPrompt}, {@code parseResponse} and {@code applyConfidenceThreshold}
 * apart in the first place.
 */
class CoreTests {

    // ---- buildPrompt ----------------------------------------------------

    @Test
    void buildPrompt_formatsDescriptionAndAmount() {
        String prompt = Core.buildPrompt("Whole Foods Market", 78.23);

        assertEquals("Transaction: \"Whole Foods Market\"\nAmount: 78.23", prompt);
    }

    @Test
    void buildPrompt_alwaysUsesTwoDecimalPlaces() {
        assertTrue(Core.buildPrompt("Coffee", 5).contains("Amount: 5.00"));
        assertTrue(Core.buildPrompt("Refund", -20).contains("Amount: -20.00"));
    }

    @Test
    void buildSystemPrompt_listsEveryCanonicalCategory() {
        String prompt = Core.buildSystemPrompt();

        for (String category : Models.CANONICAL_CATEGORIES) {
            assertTrue(prompt.contains("  - " + category));
        }
    }

    // ---- parseResponse ----------------------------------------------------

    @Test
    void parseResponse_validJson() {
        ModelResponse parsed = Core.parseResponse("{\"category\": \"Food & Dining\", \"confidence\": 0.95}");

        assertEquals("Food & Dining", parsed.category());
        assertEquals(0.95, parsed.confidence(), 0.00001);
    }

    @Test
    void parseResponse_rejectsMalformedJson() {
        var ex = assertThrows(ContractViolationException.class,
                () -> Core.parseResponse("not json at all"));

        assertTrue(ex.getMessage().contains("not valid JSON"));
    }

    @Test
    void parseResponse_rejectsNonObject() {
        var ex = assertThrows(ContractViolationException.class, () -> Core.parseResponse("[1, 2, 3]"));

        assertTrue(ex.getMessage().contains("must be a JSON object"));
    }

    @Test
    void parseResponse_rejectsMissingFields() {
        assertThrows(ContractViolationException.class,
                () -> Core.parseResponse("{\"category\": \"Food & Dining\"}"));

        assertThrows(ContractViolationException.class,
                () -> Core.parseResponse("{\"confidence\": 0.9}"));
    }

    @Test
    void parseResponse_rejectsUnknownCategory() {
        // The model inventing a category is the most common contract violation
        // in practice, and the easiest to miss without this assertion.
        var ex = assertThrows(ContractViolationException.class,
                () -> Core.parseResponse("{\"category\": \"Snacks\", \"confidence\": 0.9}"));

        assertTrue(ex.getMessage().contains("unknown category"));
        assertTrue(ex.getMessage().contains("Snacks"));
    }

    @ParameterizedTest
    @ValueSource(doubles = {-0.1, 1.5})
    void parseResponse_rejectsOutOfRangeConfidence(double confidence) {
        var ex = assertThrows(ContractViolationException.class,
                () -> Core.parseResponse("{\"category\": \"Other\", \"confidence\": " + confidence + "}"));

        assertTrue(ex.getMessage().contains("confidence must be in [0, 1]"));
    }

    // ---- applyConfidenceThreshold ------------------------------------------

    @Test
    void applyConfidenceThreshold_keepsConfidentAnswer() {
        CategorisationOut result =
                Core.applyConfidenceThreshold(new ModelResponse("Travel", 0.85), 0.6);

        assertEquals("Travel", result.category());
        assertFalse(result.usedFallback());
    }

    @Test
    void applyConfidenceThreshold_fallsBackBelowThreshold() {
        CategorisationOut result =
                Core.applyConfidenceThreshold(new ModelResponse("Travel", 0.4), 0.6);

        assertEquals("Other", result.category());
        assertTrue(result.usedFallback());
        // The original confidence is preserved — the caller may want to show it.
        assertEquals(0.4, result.confidence(), 0.00001);
    }

    @Test
    void applyConfidenceThreshold_boundaryIsInclusive() {
        // Exactly at the threshold counts as confident. Worth pinning: an
        // off-by-one here silently changes behaviour for a whole band of inputs.
        CategorisationOut result =
                Core.applyConfidenceThreshold(new ModelResponse("Housing", 0.6), 0.6);

        assertEquals("Housing", result.category());
        assertFalse(result.usedFallback());
    }

    // ---- categorise (mocked at the LLM boundary) ---------------------------

    @Test
    void categorise_happyPath() {
        FakeLlmClient client = FakeLlmClient.returning("Food & Dining", 0.95);

        CategorisationOut result = Core.categorise("Starbucks", 5.45, client, 0.6);

        assertEquals("Food & Dining", result.category());
        assertFalse(result.usedFallback());
        assertEquals(1, client.callCount());
    }

    @Test
    void categorise_passesThePromptsThrough() {
        FakeLlmClient client = FakeLlmClient.returning("Other", 0.9);

        Core.categorise("Starbucks", 5.45, client, 0.6);

        assertTrue(client.lastUserPrompt().contains("Starbucks"));
        assertTrue(client.lastSystemPrompt().contains("Food & Dining"));
    }

    @Test
    void categorise_surfacesContractViolations() {
        FakeLlmClient client = new FakeLlmClient("{ nonsense");

        assertThrows(ContractViolationException.class,
                () -> Core.categorise("Starbucks", 5.45, client));
    }
}

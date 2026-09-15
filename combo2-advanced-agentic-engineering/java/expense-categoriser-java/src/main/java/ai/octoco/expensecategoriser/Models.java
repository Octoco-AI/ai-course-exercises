package ai.octoco.expensecategoriser;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Request/response contracts + the canonical category list.
 */
public final class Models {

    private Models() {}

    /**
     * Keep this list short and stable — the prompt enumerates it. Don't
     * reshuffle without re-running the eval baseline; label order can subtly
     * affect the LLM.
     */
    public static final List<String> CANONICAL_CATEGORIES = List.of(
            "Food & Dining",
            "Transportation",
            "Shopping",
            "Entertainment",
            "Healthcare",
            "Utilities",
            "Housing",
            "Travel",
            "Personal Care",
            "Subscriptions",
            "Education",
            "Gifts & Donations",
            "Income",
            "Other");

    public static final String FALLBACK_CATEGORY = "Other";

    /** What the API caller sends. */
    public record ExpenseIn(
            @NotBlank
            @Size(min = 1, max = 500)
            @JsonProperty("description")
            String description,

            /** Transaction amount in the user's currency. Negative = credit. */
            @JsonProperty("amount")
            double amount) {}

    /** What the API returns. */
    public record CategorisationOut(
            @JsonProperty("category") String category,
            @JsonProperty("confidence") double confidence,
            /**
             * True when the model's confidence fell below the threshold and we
             * returned "Other" as a fallback. Note this is a SUCCESSFUL
             * response, not an error.
             */
            @JsonProperty("used_fallback") boolean usedFallback) {}

    /**
     * The schema we ask Gemini to produce. Kept separate from
     * {@link CategorisationOut} so we can wrap the raw model output with our
     * fallback logic before returning it.
     */
    public record ModelResponse(
            @JsonProperty("category") String category,
            @JsonProperty("confidence") double confidence) {}

    /**
     * Raised when the model's output violates the contract we asked for.
     *
     * <p>This is the "the model started misbehaving" signal that the CE
     * pipeline in M12 watches for. It maps to HTTP 502, not 500 — the service
     * is fine, the model isn't.
     */
    public static final class ContractViolationException extends RuntimeException {
        public ContractViolationException(String message) {
            super(message);
        }
    }
}

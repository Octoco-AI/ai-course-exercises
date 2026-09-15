package ai.octoco.expensecategoriser.evals;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import ai.octoco.expensecategoriser.Core;
import ai.octoco.expensecategoriser.DotEnv;
import ai.octoco.expensecategoriser.GeminiClient;
import ai.octoco.expensecategoriser.Models.CategorisationOut;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;

/**
 * Layer 3 — the eval suite. This is the "third layer" from Herman's blog.
 *
 * <p>Run locally: {@code ./mvnw test -Dgroups=evals}
 *
 * <p>In CI: {@code .github/workflows/evals.yml} runs this on every PR with the
 * {@code GOOGLE_API_KEY} secret. A failing eval blocks the merge.
 *
 * <p>What's being tested:
 * <ol>
 *   <li><b>Acceptance accuracy</b> — across the golden dataset, the rate of
 *       "chose an acceptable category" must be at least {@link #ACCURACY_THRESHOLD}.</li>
 *   <li><b>Zero catastrophics</b> — no case may be categorised as one of its
 *       explicitly unacceptable categories. This is a hard gate.</li>
 *   <li><b>Latency</b> — p95 per-request latency below a ceiling.</li>
 *   <li><b>Confidence distribution</b> — most high-confidence predictions should
 *       actually be correct (rough calibration check).</li>
 * </ol>
 *
 * <p>Costs real money: every case is a Gemini call. Keep the dataset small
 * (~20 cases) for the fast-feedback CI loop; expand to 100+ for nightly runs.
 *
 * <p>The thresholds and the dataset are identical to the Python, C# and
 * TypeScript versions of this exercise, on purpose — a cross-language
 * debrief is only interesting if everyone is measuring the same thing.
 *
 * <p>All 22 cases run once, in {@link #runDataset()}, and every gate below
 * reads from the cached results — that is the only expensive step.
 */
@Tag("evals")
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class CategorisationQualityTests {

    // ---- thresholds (the spec's acceptance criteria turned into CE gates) ----

    private static final double ACCURACY_THRESHOLD = 0.85;        // >= 85% of cases must be acceptable
    private static final int CATASTROPHIC_THRESHOLD = 0;          // ZERO cases may hit an unacceptable category
    private static final double P95_LATENCY_SECONDS = 3.0;        // generous; tighten once we have a baseline
    private static final double MIN_HIGH_CONF_ACCEPTABLE = 0.90;  // of high-conf (>=0.8), at least 90% acceptable

    private final List<EvalResult> results = new ArrayList<>();
    private boolean skipped;

    /**
     * Run every case through the real categoriser, once, and cache the
     * results. This is the only expensive step — all four gates below read
     * from it, so they share a single full pass of the dataset.
     */
    @BeforeAll
    void runDataset() throws IOException {
        DotEnv.load();

        if (DotEnv.get("GOOGLE_API_KEY") == null || DotEnv.get("GOOGLE_API_KEY").isBlank()) {
            // Explicit opt-in required. A missing key is a skip, not a
            // failure — otherwise every developer without a key sees a red suite.
            skipped = true;
            return;
        }

        List<EvalCase> cases = loadDataset();
        GeminiClient client = new GeminiClient();

        for (EvalCase evalCase : cases) {
            long start = System.nanoTime();
            try {
                CategorisationOut output =
                        Core.categorise(evalCase.description(), evalCase.amount(), client);
                double elapsed = (System.nanoTime() - start) / 1_000_000_000.0;
                results.add(new EvalResult(evalCase, output, elapsed, null));
            } catch (Exception ex) {
                double elapsed = (System.nanoTime() - start) / 1_000_000_000.0;
                // Record and keep going — one failure shouldn't hide the rest.
                results.add(new EvalResult(evalCase, null, elapsed, ex.getMessage()));
            }
        }
    }

    private void skipIfNoKey() {
        assumeTrue(!skipped, "GOOGLE_API_KEY not set — eval suite skipped (explicit opt-in required)");
    }

    // ---- the gates ------------------------------------------------------

    @Test
    void accuracyAboveThreshold() {
        skipIfNoKey();

        int total = results.size();
        long acceptable = results.stream().filter(EvalResult::isAcceptable).count();
        double accuracy = (double) acceptable / total;

        String failures = results.stream()
                .filter(r -> !r.isAcceptable())
                .map(r -> "  - '" + r.evalCase().description() + "' -> "
                        + (r.output() != null ? r.output().category() : "ERROR")
                        + " (acceptable: " + String.join(", ", r.evalCase().acceptable()) + ")")
                .reduce("", (a, b) -> a + "\n" + b);

        assertTrue(accuracy >= ACCURACY_THRESHOLD,
                String.format("Accuracy %.1f%% below threshold %.1f%%.%nFailing cases:%s",
                        accuracy * 100, ACCURACY_THRESHOLD * 100, failures));
    }

    @Test
    void zeroCatastrophicFailures() {
        skipIfNoKey();

        List<EvalResult> catastrophics = results.stream().filter(EvalResult::isCatastrophic).toList();

        String details = catastrophics.stream()
                .map(r -> "  - '" + r.evalCase().description() + "' -> " + r.output().category()
                        + " (explicitly unacceptable: " + String.join(", ", r.evalCase().unacceptable()) + ")")
                .reduce("", (a, b) -> a + "\n" + b);

        assertTrue(catastrophics.size() <= CATASTROPHIC_THRESHOLD,
                catastrophics.size() + " catastrophic failure(s):" + details);
    }

    @Test
    void p95LatencyBelowCeiling() {
        skipIfNoKey();

        List<Double> latencies = results.stream()
                .map(EvalResult::elapsed)
                .sorted()
                .toList();
        double p95 = latencies.get((int) (latencies.size() * 0.95));
        double mean = latencies.stream().mapToDouble(Double::doubleValue).average().orElse(0);
        double median = latencies.get(latencies.size() / 2);
        double max = latencies.get(latencies.size() - 1);

        assertTrue(p95 <= P95_LATENCY_SECONDS,
                String.format("p95 latency %.2fs exceeds ceiling %.1fs. mean=%.2fs median=%.2fs max=%.2fs",
                        p95, P95_LATENCY_SECONDS, mean, median, max));
    }

    @Test
    void highConfidencePredictionsAreReliable() {
        skipIfNoKey();

        List<EvalResult> highConf = results.stream()
                .filter(r -> r.output() != null && r.output().confidence() >= 0.8)
                .toList();
        assumeTrue(!highConf.isEmpty(), "No high-confidence predictions in this run");

        long acceptable = highConf.stream().filter(EvalResult::isAcceptable).count();
        double rate = (double) acceptable / highConf.size();

        assertTrue(rate >= MIN_HIGH_CONF_ACCEPTABLE,
                String.format("High-confidence acceptance rate %.1f%% below threshold %.1f%%. "
                        + "The model is overconfident.", rate * 100, MIN_HIGH_CONF_ACCEPTABLE * 100));
    }

    /**
     * Not a gate — prints a summary so facilitators can eyeball what the
     * model actually did. Always passes.
     */
    @Test
    void printEvalSummary() {
        skipIfNoKey();

        int total = results.size();
        List<Double> latencies = results.stream().map(EvalResult::elapsed).sorted().toList();
        long acceptable = results.stream().filter(EvalResult::isAcceptable).count();
        long catastrophic = results.stream().filter(EvalResult::isCatastrophic).count();
        long errors = results.stream().filter(r -> r.output() == null).count();

        System.out.println("\n=== Eval summary ===");
        System.out.printf("  total cases:       %d%n", total);
        System.out.printf("  acceptable:        %d (%.1f%%)%n", acceptable, 100.0 * acceptable / total);
        System.out.printf("  catastrophic:      %d%n", catastrophic);
        System.out.printf("  errors:            %d%n", errors);
        System.out.printf("  latency p50/p95:   %.2fs / %.2fs%n",
                latencies.get(latencies.size() / 2), latencies.get((int) (latencies.size() * 0.95)));
        System.out.println();
    }

    // ---- dataset ------------------------------------------------------

    private static List<EvalCase> loadDataset() throws IOException {
        try (InputStream in = CategorisationQualityTests.class
                .getResourceAsStream("/evals/eval_dataset.json")) {
            if (in == null) {
                throw new IllegalStateException("eval dataset not found on the classpath at evals/eval_dataset.json");
            }
            ObjectMapper mapper = new ObjectMapper();
            EvalCase[] cases = mapper.readValue(in, EvalCase[].class);
            return Arrays.asList(cases);
        }
    }

    private record EvalCase(
            @JsonProperty("description") String description,
            @JsonProperty("amount") double amount,
            @JsonProperty("acceptable") List<String> acceptable,
            @JsonProperty("unacceptable") List<String> unacceptable) {
    }

    private record EvalResult(EvalCase evalCase, CategorisationOut output, double elapsed, String error) {

        boolean isAcceptable() {
            return output != null && evalCase.acceptable().contains(output.category());
        }

        boolean isCatastrophic() {
            return output != null && evalCase.unacceptable().contains(output.category());
        }
    }
}

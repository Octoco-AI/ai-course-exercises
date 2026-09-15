package ai.octoco.expensecategoriser;

import java.util.LinkedHashMap;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import ai.octoco.expensecategoriser.Models.CategorisationOut;
import ai.octoco.expensecategoriser.Models.ContractViolationException;
import ai.octoco.expensecategoriser.Models.ExpenseIn;
import jakarta.validation.Valid;

/**
 * Spring Boot app exposing the categoriser.
 *
 * <p>Run locally:
 * <pre>
 *   ./mvnw spring-boot:run
 * </pre>
 *
 * <p>Test:
 * <pre>
 *   curl -X POST http://localhost:5080/categorise \
 *        -H "Content-Type: application/json" \
 *        -d '{"description": "Whole Foods", "amount": 45.23}'
 * </pre>
 */
@SpringBootApplication
public class ExpenseCategoriserApplication {

    public static void main(String[] args) {
        DotEnv.load();
        SpringApplication.run(ExpenseCategoriserApplication.class, args);
    }

    /**
     * One client for the process, so repeated requests reuse the HTTP
     * connection. Registered through the interface so the tests can swap in a
     * fake.
     */
    @Bean
    LlmClient llmClient() {
        return new GeminiClient();
    }

    @RestController
    static class ApiController {

        private static final Logger log = LoggerFactory.getLogger(ApiController.class);

        private final LlmClient client;

        ApiController(LlmClient client) {
            this.client = client;
        }

        /** Liveness probe. */
        @GetMapping("/health")
        Map<String, String> health() {
            return Map.of("status", "ok");
        }

        /** The canonical category list. Useful for API consumers and tests. */
        @GetMapping("/categories")
        Map<String, Object> categories() {
            return Map.of("categories", Models.CANONICAL_CATEGORIES);
        }

        /**
         * Categorise a single expense.
         *
         * <p>Returns 502 if the LLM returns malformed output (contract
         * violation). The confidence-threshold fallback (returning "Other"
         * with used_fallback=true) is a SUCCESSFUL response, not an error —
         * the client needs to know the model wasn't confident, not that
         * everything failed.
         */
        @PostMapping("/categorise")
        ResponseEntity<?> categorise(@Valid @RequestBody ExpenseIn expense) {
            long start = System.nanoTime();
            try {
                CategorisationOut result =
                        Core.categorise(expense.description(), expense.amount(), client);
                long elapsedMs = (System.nanoTime() - start) / 1_000_000L;
                log.info(
                        "categorised {} -> {} (conf={}, fallback={}, {}ms)",
                        expense.description(),
                        result.category(),
                        String.format(java.util.Locale.ROOT, "%.2f", result.confidence()),
                        result.usedFallback(),
                        elapsedMs);
                return ResponseEntity.ok(result);
            } catch (ContractViolationException ex) {
                // Worth logging loudly — this is the "model started misbehaving"
                // signal the CE pipeline watches for.
                log.warn("Contract violation from LLM: {}", ex.getMessage());
                return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                        .body(problem(
                                HttpStatus.BAD_GATEWAY,
                                "LLM returned unparseable output: " + ex.getMessage()));
            } catch (IllegalStateException ex) {
                // Missing API key, etc. — configuration problem.
                return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                        .body(problem(HttpStatus.INTERNAL_SERVER_ERROR, ex.getMessage()));
            }
        }

        @ExceptionHandler(MethodArgumentNotValidException.class)
        ResponseEntity<Map<String, Object>> handleValidation(MethodArgumentNotValidException ex) {
            Map<String, String[]> errors = new LinkedHashMap<>();
            ex.getBindingResult().getFieldErrors().forEach(error ->
                    errors.put(
                            error.getField(),
                            new String[] {
                                error.getDefaultMessage() != null
                                        ? error.getDefaultMessage()
                                        : "invalid value"
                            }));
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("title", "One or more validation errors occurred.");
            body.put("status", HttpStatus.BAD_REQUEST.value());
            body.put("errors", errors);
            return ResponseEntity.badRequest().body(body);
        }

        private static Map<String, Object> problem(HttpStatus status, String detail) {
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("title", status.getReasonPhrase());
            body.put("status", status.value());
            body.put("detail", detail);
            return body;
        }
    }
}

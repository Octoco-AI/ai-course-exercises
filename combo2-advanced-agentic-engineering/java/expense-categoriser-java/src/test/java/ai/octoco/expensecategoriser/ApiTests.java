package ai.octoco.expensecategoriser;

import static org.assertj.core.api.Assertions.assertThat;

import ai.octoco.expensecategoriser.Models.CategorisationOut;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

/**
 * Layer 2 — API contract tests. Boots the real app with a fake LLM.
 *
 * <p>These check the shape of the HTTP contract, not the quality of the
 * answer: status codes, response fields, and — most importantly — that a
 * contract violation from the model becomes a 502 rather than a 500 or a
 * crash. Still no key, still free.
 *
 * <p>One Spring context is shared across every test in this class — see
 * {@link DelegatingLlmClient} for why, and how each test points it at the
 * fake it needs.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(ApiTests.TestConfig.class)
class ApiTests {

    @TestConfiguration
    static class TestConfig {
        @Bean
        @Primary
        DelegatingLlmClient testLlmClient() {
            return new DelegatingLlmClient();
        }
    }

    @Autowired
    private TestRestTemplate rest;

    @Autowired
    private DelegatingLlmClient llmClient;

    @Test
    void health_returnsOk() {
        ResponseEntity<Map> response = rest.getForEntity("/health", Map.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
    }

    @Test
    void categories_returnsTheCanonicalList() {
        ResponseEntity<Map> response = rest.getForEntity("/categories", Map.class);

        @SuppressWarnings("unchecked")
        List<String> categories = (List<String>) response.getBody().get("categories");
        assertThat(categories).containsExactlyElementsOf(Models.CANONICAL_CATEGORIES);
    }

    @Test
    void categorise_returnsTheModelsAnswer() {
        llmClient.setDelegate(FakeLlmClient.returning("Food & Dining", 0.95));

        ResponseEntity<CategorisationOut> response = rest.postForEntity(
                "/categorise",
                Map.of("description", "Starbucks Coffee", "amount", 5.45),
                CategorisationOut.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody().category()).isEqualTo("Food & Dining");
        assertThat(response.getBody().usedFallback()).isFalse();
    }

    @Test
    void categorise_lowConfidenceIsStillA200() {
        // The fallback is a successful response. The client needs to know the
        // model wasn't confident — not that the request failed.
        llmClient.setDelegate(FakeLlmClient.returning("Travel", 0.2));

        ResponseEntity<CategorisationOut> response = rest.postForEntity(
                "/categorise",
                Map.of("description", "Something ambiguous", "amount", 12.0),
                CategorisationOut.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody().category()).isEqualTo("Other");
        assertThat(response.getBody().usedFallback()).isTrue();
    }

    @Test
    void categorise_contractViolationBecomes502() {
        // Not a 500. The service is healthy; the model misbehaved. This
        // distinction is what lets the CE pipeline alert on model drift
        // without drowning in ordinary server errors.
        llmClient.setDelegate(new FakeLlmClient("this is not json"));

        ResponseEntity<String> response = rest.postForEntity(
                "/categorise",
                Map.of("description", "Starbucks", "amount", 5.45),
                String.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_GATEWAY);
    }

    @Test
    void categorise_missingApiKeyBecomes500() {
        llmClient.setDelegate(new ThrowingLlmClient(
                new IllegalStateException("GOOGLE_API_KEY is not set.")));

        ResponseEntity<String> response = rest.postForEntity(
                "/categorise",
                Map.of("description", "Starbucks", "amount", 5.45),
                String.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR);
    }

    @Test
    void categorise_rejectsEmptyDescription() {
        llmClient.setDelegate(FakeLlmClient.returning("Other", 0.9));

        ResponseEntity<String> response = rest.postForEntity(
                "/categorise",
                Map.of("description", "", "amount", 5.45),
                String.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
    }
}

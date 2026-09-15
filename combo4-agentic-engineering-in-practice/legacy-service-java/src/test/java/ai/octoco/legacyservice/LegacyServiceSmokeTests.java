package ai.octoco.legacyservice;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

// Smoke tests. Thin on purpose -- they check the service turns on.
// (2018-11: the full suite lived in the old repo and never made the move.
// TODO: port the rest of the tests. -- J)

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class LegacyServiceSmokeTests {

    // Point the app at a scratch database BEFORE the Spring context ever
    // boots -- Db.DB_PATH is a static final field evaluated on first touch,
    // and @SpringBootTest never calls our own main(), so this static field
    // initializer (which runs at class-load time, before Spring's context
    // bootstrap) is what stands in for the C# port's "field-initialization
    // order matters here" comment. It also runs Db.initDb() directly, since
    // that normally only happens inside main().
    private static final String DB_PATH = pointAtScratchDbAndInit();

    @Autowired
    private TestRestTemplate rest;

    private static String pointAtScratchDbAndInit() {
        String path = Path.of(System.getProperty("java.io.tmpdir"), "orderbase-test-" + UUID.randomUUID() + ".db")
                .toString();
        System.setProperty("ORDERBASE_DB", path);
        Db.initDb();
        return path;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> createOrder() {
        Map<String, Object> payload = Map.of(
                "customer", "Smoke Test Co",
                "items", List.of(Map.of("sku", "SKU-0001", "qty", 1, "unit_price", 19.99)));

        ResponseEntity<Map> response = rest.postForEntity("/orders", payload, Map.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        return response.getBody();
    }

    @Test
    void createOrder_returnsExpectedShape() {
        Map<String, Object> body = createOrder();

        assertThat(((String) body.get("id"))).hasSize(8);
        assertThat(body.get("status")).isEqualTo("NEW");
        assertThat(((Number) body.get("total")).doubleValue()).isEqualTo(19.99);
    }

    @Test
    @SuppressWarnings("unchecked")
    void getOrder_returnsCustomer() {
        Map<String, Object> created = createOrder();
        String orderId = (String) created.get("id");

        ResponseEntity<Map> response = rest.getForEntity("/orders/" + orderId, Map.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody().get("customer")).isEqualTo("Smoke Test Co");
    }

    @Test
    @SuppressWarnings("unchecked")
    void listOrders_includesCreatedOrder() {
        Map<String, Object> created = createOrder();
        String orderId = (String) created.get("id");

        ResponseEntity<Map> response = rest.getForEntity("/orders", Map.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);

        List<Map<String, Object>> orders = (List<Map<String, Object>>) response.getBody().get("orders");
        List<Object> ids = orders.stream().map(o -> o.get("id")).toList();
        assertThat(ids).contains(orderId);
    }
}

package ai.octoco.legacyservice;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

// LegacyServiceApplication.java -- OrderBase HTTP API.
//
// Four endpoints. In production since 2018. If you are reading this because
// something broke: logs are in logs/, the reconcile cron is in the ops repo,
// and DOCS/INSTRUCTIONS.md is roughly current (last real update 2019).
//
// Run locally:
//     ./mvnw spring-boot:run
//
// The old way was `./mvnw spring-boot:run -Dspring-boot.run.fork=false` with
// a file-watcher wired in, but the reloader double-binds :5057 -- do not use it.

@SpringBootApplication
public class LegacyServiceApplication {

    private static final String APP_VERSION = "1.4.2";

    // Ops images the boxes from a golden AMI; nothing below is meant to be
    // configurable. The port was picked in 2018 to dodge the office proxy.
    private static final String SERVICE_HOST = "0.0.0.0";
    private static final int PORT = 5057;
    private static final boolean DEBUG = true; // left on after the 2019 checkout incident. Do not ask.

    public static void main(String[] args) {
        LoggingSetup.setup();
        Db.initDb();
        System.out.println("OrderBase v" + APP_VERSION + " listening on " + SERVICE_HOST + ":" + PORT + " (debug=" + DEBUG + ")");
        SpringApplication.run(LegacyServiceApplication.class, args);
    }

    @RestController
    static class ApiController {

        private static final Logger LOG = LoggingSetup.getLogger("ai.octoco.legacyservice.App");

        // NOTE: monitoring hits GET /orders?limit=1 as a liveness probe because
        // we never got around to a proper health endpoint.

        @PostMapping("/orders")
        ResponseEntity<?> createOrder(@RequestBody JsonNode payload) {
            if (DEBUG) {
                System.out.println("DEBUG: POST /orders payload=" + payload);
            }

            Order order;
            try {
                order = Orders.createOrder(payload);
            } catch (IllegalArgumentException ex) {
                LOG.warning("rejected order: " + ex.getMessage());
                return ResponseEntity.badRequest().body(Map.of("error", ex.getMessage()));
            }

            LOG.info(String.format(
                    Locale.ROOT, "POST /orders 201 id=%s total=%.2f", order.id, order.total));
            return ResponseEntity.status(HttpStatus.CREATED).body(order);
        }

        @GetMapping("/orders/{orderId}")
        ResponseEntity<?> getOrder(@PathVariable String orderId) {
            // Accept bare numeric ids ("42") as a convenience and pad them.
            // (Same rule as Utils.formatOrderId -- keep the two in sync.)
            String id = orderId;
            if (id.length() < 8 && !id.isEmpty() && id.chars().allMatch(Character::isDigit)) {
                id = Utils.formatOrderId(Long.parseLong(id));
            }

            Order order = Orders.getOrder(id);
            if (order == null) {
                LOG.info("GET /orders/" + id + " 404");
                return ResponseEntity.status(HttpStatus.NOT_FOUND)
                        .body(Map.of("error", "order " + id + " not found"));
            }
            LOG.info("GET /orders/" + id + " 200 status=" + order.status);
            return ResponseEntity.ok(order);
        }

        @GetMapping("/orders")
        ResponseEntity<?> listOrders(
                @RequestParam(required = false) String status,
                @RequestParam(required = false, defaultValue = "50") String limit) {
            List<Order> result;
            try {
                result = Orders.listOrders(status, Integer.parseInt(limit));
            } catch (IllegalArgumentException ex) {
                return ResponseEntity.badRequest().body(Map.of("error", ex.getMessage()));
            }
            LOG.info("GET /orders 200 count=" + result.size());
            return ResponseEntity.ok(Map.of("orders", result, "count", result.size()));
        }

        @GetMapping("/report")
        ResponseEntity<?> report(@RequestParam(required = false) String date) {
            DailyReportResult report;
            try {
                report = Orders.dailyReport(date);
            } catch (Exception ex) {
                return ResponseEntity.badRequest().body(Map.of("error", "date must be YYYY-MM-DD"));
            }
            LOG.info(String.format(
                    Locale.ROOT, "GET /report 200 date=%s orders=%d total=%.2f",
                    report.date, report.orders, report.total));
            return ResponseEntity.ok(report);
        }

        @ExceptionHandler(HttpMessageNotReadableException.class)
        ResponseEntity<?> handleBadJson(HttpMessageNotReadableException ex) {
            return ResponseEntity.badRequest().body(Map.of("error", "body must be JSON"));
        }
    }
}

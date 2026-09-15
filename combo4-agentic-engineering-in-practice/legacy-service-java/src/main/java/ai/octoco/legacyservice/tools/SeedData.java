package ai.octoco.legacyservice.tools;

import ai.octoco.legacyservice.Db;
import ai.octoco.legacyservice.Order;
import ai.octoco.legacyservice.Orders;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * SeedData -- seed OrderBase with deterministic sample data (Java port of
 * {@code seed_data.py} / {@code scripts/SeedData}).
 *
 * <p>Creates ~30 orders spread over three days (2026-06-28 .. 2026-06-30) by
 * going through the real order-creation path ({@link Orders#createOrder}),
 * then adjusting each row's {@code created_at} and {@code status} to the
 * target values. Running it twice gives the same database every time -- and,
 * since it drives the real {@code computeTotal}, the same 30 totals as the
 * Python/C# originals.
 *
 * <p>Usage: {@code ./mvnw exec:java -Dexec.mainClass=ai.octoco.legacyservice.tools.SeedData}
 *
 * <p>Honours {@code ORDERBASE_DB} (defaults to {@code orderbase.db} in the
 * working dir).
 */
public final class SeedData {

    private static final String[] DAYS = {"2026-06-28", "2026-06-29", "2026-06-30"};

    private static final String[] CUSTOMERS = {
        "Acme Ltd", "Northwind Traders", "Globex", "Initech", "Umbrella Co",
        "Stark Supplies", "Wayne Retail", "Soylent Foods", "Hooli", "Vandelay",
    };

    // (sku, unit_price) catalogue. Prices chosen so that discounts land on a
    // mix of clean and not-so-clean cent values.
    private static final Object[][] CATALOGUE = {
        {"SKU-0001", 19.99}, {"SKU-0002", 4.95}, {"SKU-0003", 12.50},
        {"SKU-0004", 7.25}, {"SKU-0005", 3.33}, {"SKU-0006", 49.00},
        {"SKU-0007", 8.80}, {"SKU-0008", 1.10}, {"SKU-0009", 19.99},
    };

    private static final double[] DISCOUNT_CYCLE = {0, 0, 10, 5, 0, 15, 0, 7.5, 0, 10};
    private static final String[] STATUS_CYCLE = {
        "NEW", "PAID", "SHIPPED", "PAID", "CANCELLED", "SHIPPED", "NEW", "PAID", "SHIPPED", "NEW",
    };

    private static final int N_ORDERS = 30;

    // A few orders are pinned so they line up with FAKE_SENTRY.md and the log
    // fixtures (ids are assigned in creation order, starting at 00000001):
    //   #7  -> SHIPPED, referenced by the stale-cache issue (ORDERBASE-9F2)
    //   #21 -> 5 x SKU-0009 @ 19.99, 10% off -> reconcile mismatch (ORDERBASE-3A1)
    private static final Map<Integer, Pin> PINNED = Map.of(
            7, new Pin(null, null, "SHIPPED"),
            21, new Pin(new String[][] {{"SKU-0009", "5"}}, 10.0, "SHIPPED"));

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private record Pin(String[][] items, Double discountPct, String status) {}

    private SeedData() {}

    public static void main(String[] args) {
        Db.initDb();

        // Deterministic: clear existing rows so ids restart at 00000001.
        Db.execute("DELETE FROM " + Db.ORDERS_TABLE);
        Db.execute("DELETE FROM " + Db.ITEMS_TABLE);

        List<String> createdIds = new ArrayList<>();
        for (int i = 1; i <= N_ORDERS; i++) {
            Order order = Orders.createOrder(buildPayload(i));
            String[] meta = targetMeta(i);
            Db.execute(
                    "UPDATE " + Db.ORDERS_TABLE + " SET created_at = ?, status = ? WHERE id = ?",
                    meta[0], meta[1], order.id);
            createdIds.add(order.id);
        }

        validate();

        List<Map<String, Object>> rows =
                Db.query("SELECT id, status, total, created_at FROM " + Db.ORDERS_TABLE + " ORDER BY id");
        System.out.println();
        System.out.println("Seeded " + rows.size() + " orders into " + Db.DB_PATH);
        for (String day : DAYS) {
            List<Map<String, Object>> dayRows = rows.stream()
                    .filter(r -> ((String) r.get("created_at")).startsWith(day))
                    .toList();
            double total = dayRows.stream().mapToDouble(r -> ((Number) r.get("total")).doubleValue()).sum();
            System.out.printf(Locale.ROOT, "  %s: %2d orders, total %.2f%n", day, dayRows.size(), total);
        }
        System.out.println("  ids: " + createdIds.get(0) + " .. " + createdIds.get(createdIds.size() - 1));
    }

    private static com.fasterxml.jackson.databind.JsonNode buildPayload(int i) {
        String customer = CUSTOMERS[(i - 1) % CUSTOMERS.length];
        double discount = DISCOUNT_CYCLE[(i - 1) % DISCOUNT_CYCLE.length];

        // One-to-three line items, chosen deterministically from the catalogue.
        int nItems = 1 + ((i - 1) % 3);
        List<Object[]> items = new ArrayList<>();
        for (int j = 0; j < nItems; j++) {
            Object[] entry = CATALOGUE[(i + j) % CATALOGUE.length];
            int qty = 1 + ((i + j) % 4);
            items.add(new Object[] {entry[0], qty, entry[1]});
        }

        Pin pin = PINNED.get(i);
        if (pin != null) {
            if (pin.items() != null) {
                items = new ArrayList<>();
                for (String[] pinnedItem : pin.items()) {
                    String sku = pinnedItem[0];
                    int qty = Integer.parseInt(pinnedItem[1]);
                    double price = catalogueLookup(sku);
                    items.add(new Object[] {sku, qty, price});
                }
            }
            if (pin.discountPct() != null) {
                discount = pin.discountPct();
            }
        }

        ObjectNode payload = MAPPER.createObjectNode();
        payload.put("customer", customer);
        ArrayNode itemsNode = payload.putArray("items");
        for (Object[] item : items) {
            ObjectNode itemNode = itemsNode.addObject();
            itemNode.put("sku", (String) item[0]);
            itemNode.put("qty", (Integer) item[1]);
            itemNode.put("unit_price", (Double) item[2]);
        }
        payload.put("discount_pct", discount);
        return payload;
    }

    private static double catalogueLookup(String sku) {
        for (Object[] entry : CATALOGUE) {
            if (entry[0].equals(sku)) {
                return (Double) entry[1];
            }
        }
        throw new IllegalStateException("unknown sku in catalogue: " + sku);
    }

    private static String[] targetMeta(int i) {
        String day = DAYS[(i - 1) / 10];
        // Spread orders through the working day, deterministically.
        int hour = 8 + (i * 3 % 11);
        int minute = i * 7 % 60;
        int second = i * 13 % 60;
        String createdAt = String.format(Locale.ROOT, "%s %02d:%02d:%02d", day, hour, minute, second);

        Pin pin = PINNED.get(i);
        String status = (pin != null ? pin.status() : null);
        if (status == null) {
            status = STATUS_CYCLE[(i - 1) % STATUS_CYCLE.length];
        }
        return new String[] {createdAt, status};
    }

    // Validate what we produced. (Assertions the Python original lacks -- this
    // is the "regenerate fixtures WITH validation" chore.)
    private static void validate() {
        List<Map<String, Object>> rows =
                Db.query("SELECT id, status, total, created_at FROM " + Db.ORDERS_TABLE + " ORDER BY id");
        if (rows.size() != N_ORDERS) {
            throw new IllegalStateException("expected " + N_ORDERS + " orders, got " + rows.size());
        }
        for (Map<String, Object> row : rows) {
            if (((String) row.get("id")).length() != 8) {
                throw new IllegalStateException("found an id that is not 8 chars");
            }
        }
        Map<String, Object> order21 = rows.stream()
                .filter(r -> "00000021".equals(r.get("id")))
                .findFirst()
                .orElseThrow(() -> new IllegalStateException("order #21 missing"));
        double total21 = ((Number) order21.get("total")).doubleValue();
        if (total21 != 89.95) {
            throw new IllegalStateException("order #21 should total 89.95, got " + total21);
        }
        Map<String, Object> order7 = rows.stream()
                .filter(r -> "00000007".equals(r.get("id")))
                .findFirst()
                .orElseThrow(() -> new IllegalStateException("order #7 missing"));
        if (!"SHIPPED".equals(order7.get("status"))) {
            throw new IllegalStateException("order #7 should be SHIPPED, got " + order7.get("status"));
        }
    }
}

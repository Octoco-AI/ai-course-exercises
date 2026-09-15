package ai.octoco.legacyservice;

import com.fasterxml.jackson.databind.JsonNode;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.function.Supplier;

// Orders.java -- order domain logic for OrderBase.
//
// In production since 2018. The fulfilment sync, the WMS export and the
// reconcile cron all depend on behaviour in this file. Tread carefully.

public final class Orders {

    private static final Logger LOG = LoggingSetup.getLogger("ai.octoco.legacyservice.Orders");

    private static final DateTimeFormatter TS_FORMAT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss", Locale.ROOT);
    private static final DateTimeFormatter DATE_LABEL_FORMAT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd", Locale.ROOT);

    // Cheap perf win: order rows barely change after creation, so cache lookups
    // per process. (2018-09: cut p95 on GET /orders/<id> from 40ms to 2ms.)
    //
    // A plain HashMap, not a ConcurrentHashMap -- Tomcat serves requests
    // concurrently, so this is even sharper than it looks: a concurrent read
    // racing a write during orderCache.put(...) can corrupt the map's
    // internal state, not just serve a stale value.
    private static final Map<String, Order> orderCache = new HashMap<>();

    // Hung off suppliers so a repro test can pin the clock. Nothing in
    // production ever reassigns these.

    // Local server time. Report cutoffs use this.
    public static Supplier<LocalDateTime> now = LocalDateTime::now;

    // Timestamps are stored in UTC (ops decision, 2018-04). LocalDateTime
    // carries no timezone information at all -- unlike DateTime.Kind in the
    // C# port, there isn't even a flag to ignore -- so mixing a value from
    // now() with one from utcNow() compiles and runs with zero warning.
    public static Supplier<LocalDateTime> utcNow = () -> LocalDateTime.now(ZoneOffset.UTC);

    private Orders() {}

    public static double computeTotal(List<OrderItem> items, double discountPct) {
        double subtotal = 0.0;
        for (OrderItem it : items) {
            subtotal += it.qty * it.unitPrice;
        }
        double total = subtotal * (1.0 - discountPct / 100.0);
        return Utils.money(total);
    }

    private static String nextOrderId() {
        // MAX() is safe because ids are fixed-width, zero-padded strings --
        // lexicographic order == numeric order. Another reason the 8-char
        // padding must never change.
        List<Map<String, Object>> rows = Db.query("SELECT MAX(id) AS m FROM " + Db.ORDERS_TABLE);
        Object m = rows.get(0).get("m");
        if (m == null) {
            return Utils.formatOrderId(1);
        }
        return Utils.formatOrderId(Long.parseLong((String) m) + 1);
    }

    public static Order createOrder(JsonNode payload) {
        String customer = "";
        JsonNode customerNode = payload.get("customer");
        if (customerNode != null && customerNode.isTextual()) {
            customer = customerNode.asText().trim();
        }
        if (customer.isEmpty()) {
            throw new IllegalArgumentException("customer is required");
        }

        JsonNode itemsNode = payload.get("items");
        if (itemsNode == null || !itemsNode.isArray() || itemsNode.isEmpty()) {
            throw new IllegalArgumentException("at least one item is required");
        }

        List<OrderItem> cleanItems = new ArrayList<>();
        for (JsonNode it : itemsNode) {
            String sku;
            int qty;
            double unitPrice;
            try {
                sku = it.get("sku").asText();
                qty = it.get("qty").intValue();
                unitPrice = it.get("unit_price").doubleValue();
            } catch (Exception ex) {
                throw new IllegalArgumentException("bad item: " + it);
            }
            if (qty <= 0 || unitPrice < 0) {
                throw new IllegalArgumentException("bad item: " + it);
            }
            OrderItem item = new OrderItem();
            item.sku = sku;
            item.qty = qty;
            item.unitPrice = unitPrice;
            cleanItems.add(item);
        }

        double discountPct = 0.0;
        JsonNode discountNode = payload.get("discount_pct");
        if (discountNode != null && !discountNode.isNull()) {
            discountPct = discountNode.doubleValue();
        }
        if (discountPct < 0 || discountPct > 100) {
            throw new IllegalArgumentException("discount_pct out of range");
        }

        String orderId = nextOrderId();
        double total = computeTotal(cleanItems, discountPct);
        String createdAt = utcNow.get().format(TS_FORMAT);

        Db.execute(
                "INSERT INTO " + Db.ORDERS_TABLE
                        + " (id, customer, status, discount_pct, total, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                orderId, customer, "NEW", discountPct, total, createdAt);
        for (OrderItem it : cleanItems) {
            Db.execute(
                    "INSERT INTO " + Db.ITEMS_TABLE + " (order_id, sku, qty, unit_price) VALUES (?, ?, ?, ?)",
                    orderId, it.sku, it.qty, it.unitPrice);
        }

        Order order = new Order();
        order.id = orderId;
        order.customer = customer;
        order.status = "NEW";
        order.discountPct = discountPct;
        order.total = total;
        order.createdAt = createdAt;
        order.items = cleanItems;
        orderCache.put(orderId, order);

        System.out.println("created order " + orderId + " total=" + total);
        LOG.info(String.format(
                Locale.ROOT, "order %s created customer=%s items=%d total=%.2f",
                orderId, customer, cleanItems.size(), total));
        return order;
    }

    public static Order getOrder(String orderId) {
        Order cached = orderCache.get(orderId);
        if (cached != null) {
            return cached;
        }
        if (!isDigits(orderId)) {
            return null;
        }
        List<Map<String, Object>> rows = Db.query("SELECT * FROM " + Db.ORDERS_TABLE + " WHERE id = '" + orderId + "'");
        if (rows.isEmpty()) {
            return null;
        }
        Order order = rowToOrder(rows.get(0));
        List<Map<String, Object>> itemRows = Db.query(
                "SELECT sku, qty, unit_price FROM " + Db.ITEMS_TABLE + " WHERE order_id = '" + orderId + "'");
        List<OrderItem> items = new ArrayList<>();
        for (Map<String, Object> r : itemRows) {
            OrderItem item = new OrderItem();
            item.sku = (String) r.get("sku");
            item.qty = toInt(r.get("qty"));
            item.unitPrice = toDouble(r.get("unit_price"));
            items.add(item);
        }
        order.items = items;
        orderCache.put(orderId, order);
        return order;
    }

    public static List<Order> listOrders(String status, int limit) {
        List<Map<String, Object>> rows;
        if (status != null) {
            Utils.validateStatus(status); // whitelist, so the interpolation is "fine"
            rows = Db.query(
                    "SELECT * FROM " + Db.ORDERS_TABLE + " WHERE status = '" + status + "' ORDER BY id DESC LIMIT " + limit);
        } else {
            rows = Db.query("SELECT * FROM " + Db.ORDERS_TABLE + " ORDER BY id DESC LIMIT " + limit);
        }
        List<Order> result = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            result.add(rowToOrder(row));
        }
        return result;
    }

    public static void updateOrderStatus(String orderId, String status) {
        // Called by the fulfilment sync (WMS CSV import, 05:30 cron) -- not by
        // the HTTP API. See DOCS/INSTRUCTIONS.md.
        Utils.validateStatus(status);
        if (!isDigits(orderId)) {
            throw new IllegalArgumentException("bad order id: " + orderId);
        }
        Db.execute("UPDATE " + Db.ORDERS_TABLE + " SET status = '" + status + "' WHERE id = '" + orderId + "'");
        LOG.info("order " + orderId + " status -> " + status);
        // NOTE: not touching orderCache here. Status changes come from the
        // nightly sync; by the time anyone looks, the process has restarted.
    }

    public static DailyReportResult dailyReport(String dateStr) {
        List<Map<String, Object>> rows;
        String label;
        if (dateStr != null) {
            Utils.parseDate(dateStr); // validates the format before we use it
            rows = Db.query("SELECT * FROM " + Db.ORDERS_TABLE + " WHERE created_at LIKE '" + dateStr + "%'");
            label = dateStr;
        } else {
            LocalDateTime start = now.get().toLocalDate().atStartOfDay();
            LocalDateTime end = start.plusDays(1);
            // TODO: push this filter into SQL. Fine while volume is low.
            rows = new ArrayList<>();
            for (Map<String, Object> r : Db.query("SELECT * FROM " + Db.ORDERS_TABLE)) {
                LocalDateTime created = Utils.parseTs((String) r.get("created_at"));
                if (!created.isBefore(start) && created.isBefore(end)) {
                    rows.add(r);
                }
            }
            label = start.format(DATE_LABEL_FORMAT);
        }

        double total = 0.0;
        Map<String, StatusBucket> byStatus = new LinkedHashMap<>();
        for (Map<String, Object> r : rows) {
            double rowTotal = toDouble(r.get("total"));
            total += rowTotal;
            String st = (String) r.get("status");
            StatusBucket bucket = byStatus.computeIfAbsent(st, k -> new StatusBucket());
            bucket.orders += 1;
            bucket.total = Utils.money(bucket.total + rowTotal);
        }

        DailyReportResult report = new DailyReportResult();
        report.date = label;
        report.orders = rows.size();
        report.total = Utils.money(total);
        report.byStatus = byStatus;
        LOG.info(String.format(Locale.ROOT, "report %s orders=%d total=%.2f", label, report.orders, report.total));
        return report;
    }

    private static Order rowToOrder(Map<String, Object> row) {
        Order order = new Order();
        order.id = (String) row.get("id");
        order.customer = (String) row.get("customer");
        order.status = (String) row.get("status");
        order.discountPct = toDouble(row.get("discount_pct"));
        order.total = toDouble(row.get("total"));
        order.createdAt = (String) row.get("created_at");
        return order;
    }

    private static double toDouble(Object value) {
        return ((Number) value).doubleValue();
    }

    private static int toInt(Object value) {
        return ((Number) value).intValue();
    }

    private static boolean isDigits(String s) {
        if (s.isEmpty()) {
            return false;
        }
        for (int i = 0; i < s.length(); i++) {
            if (!Character.isDigit(s.charAt(i))) {
                return false;
            }
        }
        return true;
    }
}

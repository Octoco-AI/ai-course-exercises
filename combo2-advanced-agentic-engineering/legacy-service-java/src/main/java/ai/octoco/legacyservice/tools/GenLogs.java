package ai.octoco.legacyservice.tools;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Random;
import java.util.regex.Pattern;

/**
 * GenLogs -- generate OrderBase log fixtures (Java port of {@code gen_logs.py}
 * / {@code scripts/GenLogs}).
 *
 * <p>Writes {@code logs/app-2026-06-28.log} .. {@code logs/app-2026-06-30.log}:
 * a few hundred lines each of realistic, mixed-format noise (structured INFO
 * request lines in the app's real log format, stray {@code System.out.println}
 * lines with no prefix, the odd WARNING). A handful of production-bug
 * signatures are seeded into the noise on specific days.
 *
 * <p>The RNG-driven noise is deterministic WITHIN this port (fixed seeds via
 * {@code new Random(seed)}) but does not reproduce the same bytes as the
 * Python/C# fixtures -- each platform's PRNG algorithm differs, and that's
 * fine: nothing asserts on the noise. The seeded signature lines below are
 * hand-written and byte-identical in content to the Python/C#/TypeScript
 * ports modulo logger name -- those are what FAKE_SENTRY.md and the M27
 * symptom-to-code trace actually depend on.
 *
 * <p>Usage: {@code ./mvnw exec:java -Dexec.mainClass=ai.octoco.legacyservice.tools.GenLogs}
 * <p>Add {@code -Dexec.args=--stdout} to print day 1 to stdout and write nothing.
 */
public final class GenLogs {

    private static final String[] DAYS = {"2026-06-28", "2026-06-29", "2026-06-30"};

    private static final String APP = "ai.octoco.legacyservice.App";
    private static final String ORD = "ai.octoco.legacyservice.Orders";

    private static final String[] CUSTOMERS = {
        "Acme Ltd", "Northwind Traders", "Globex", "Initech",
        "Umbrella Co", "Stark Supplies", "Wayne Retail", "Soylent Foods",
        "Hooli", "Vandelay",
    };
    private static final String[] SKUS = {
        "SKU-0001", "SKU-0002", "SKU-0003", "SKU-0004", "SKU-0005", "SKU-0006", "SKU-0007", "SKU-0008", "SKU-0009",
    };
    private static final String[] STATUSES = {"NEW", "PAID", "SHIPPED", "CANCELLED"};
    private static final double[] PRICES = {19.99, 4.95, 12.50, 7.25, 8.80};

    private static final Pattern VALID_LINE =
            Pattern.compile("^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2} (INFO|WARNING) \\S+ .+$");

    private GenLogs() {}

    public static void main(String[] args) throws IOException {
        Path repoRoot = Path.of("").toAbsolutePath();
        Path logDir = repoRoot.resolve("logs");

        if (Arrays.asList(args).contains("--stdout")) {
            for (String line : genDay(DAYS[0], 42)) {
                System.out.println(line);
            }
            return;
        }

        Files.createDirectories(logDir);
        for (int i = 0; i < DAYS.length; i++) {
            String day = DAYS[i];
            List<String> lines = genDay(day, 42 + i);
            for (String line : lines) {
                if (!lineLooksValid(line)) {
                    throw new IllegalStateException("generated a line that doesn't match the frozen format: " + line);
                }
            }
            Path path = logDir.resolve("app-" + day + ".log");
            Files.writeString(path, String.join("\n", lines) + "\n", StandardCharsets.UTF_8);
            System.out.println("wrote " + path + " (" + lines.size() + " lines)");
        }
    }

    private static double money(double x) {
        return Double.parseDouble(String.format(Locale.ROOT, "%.2f", x));
    }

    private static String fmtTs(String day, int sec) {
        return String.format(Locale.ROOT, "%s %02d:%02d:%02d", day, sec / 3600, (sec % 3600) / 60, sec % 60);
    }

    private static String logLine(String day, int sec, String level, String name, String msg) {
        return fmtTs(day, sec) + " " + level + " " + name + " " + msg;
    }

    private static String orderId(int n) {
        return String.format(Locale.ROOT, "%08d", n);
    }

    private static <T> T choice(Random rng, T[] items) {
        return items[rng.nextInt(items.length)];
    }

    private record Event(int sec, List<String> lines) {}

    private static List<String> randomEvent(Random rng, String day, int sec, int[] counter) {
        double roll = rng.nextDouble();
        List<String> lines = new ArrayList<>();

        if (roll < 0.42) {
            // GET /orders/<id>
            String oid = orderId(1 + rng.nextInt(Math.max(1, counter[0])));
            if (rng.nextDouble() < 0.06) {
                lines.add(logLine(day, sec, "INFO", APP, "GET /orders/" + oid + " 404"));
            } else {
                String status = choice(rng, STATUSES);
                lines.add(logLine(day, sec, "INFO", APP, "GET /orders/" + oid + " 200 status=" + status));
            }
        } else if (roll < 0.60) {
            // GET /orders (list)
            int count = 1 + rng.nextInt(50);
            lines.add(logLine(day, sec, "INFO", APP, "GET /orders 200 count=" + count));
        } else if (roll < 0.82) {
            // POST /orders -- emits the debug print, both log lines, and the
            // stray "created order" print, exactly as the code does.
            counter[0] += 1;
            String oid = orderId(counter[0]);
            String customer = choice(rng, CUSTOMERS);
            int nItems = 1 + rng.nextInt(3);
            StringBuilder payloadItems = new StringBuilder();
            double total = 0.0;
            for (int k = 0; k < nItems; k++) {
                String sku = choice(rng, SKUS);
                int qty = 1 + rng.nextInt(4);
                double unitPrice = choice(rng, boxed(PRICES));
                total += qty * unitPrice;
                if (k > 0) {
                    payloadItems.append(", ");
                }
                payloadItems.append(String.format(
                        Locale.ROOT, "{sku=%s, qty=%d, unitPrice=%s}", sku, qty, unitPrice));
            }
            total = money(total);
            lines.add("DEBUG: POST /orders payload={customer=" + customer + ", items=[" + payloadItems + "]}"); // stray
            lines.add(logLine(day, sec, "INFO", ORD, String.format(
                    Locale.ROOT, "order %s created customer=%s items=%d total=%.2f", oid, customer, nItems, total)));
            lines.add("created order " + oid + " total=" + total); // stray
            lines.add(logLine(day, sec, "INFO", APP, String.format(
                    Locale.ROOT, "POST /orders 201 id=%s total=%.2f", oid, total)));
        } else if (roll < 0.92) {
            // GET /report
            int n = 4 + rng.nextInt(11);
            double total = money(rng.nextDouble() * (1600 - 300) + 300);
            lines.add(logLine(day, sec, "INFO", APP, String.format(
                    Locale.ROOT, "GET /report 200 date=%s orders=%d total=%.2f", day, n, total)));
        } else {
            // An occasional rejected order (WARNING).
            String[] reasons = {"customer is required", "at least one item is required", "discount_pct out of range"};
            String reason = choice(rng, reasons);
            lines.add(logLine(day, sec, "WARNING", ORD, "rejected order: " + reason));
            lines.add(logLine(day, sec, "INFO", APP, "POST /orders 400 error=\"" + reason + "\""));
        }

        return lines;
    }

    private static Double[] boxed(double[] values) {
        Double[] result = new Double[values.length];
        for (int i = 0; i < values.length; i++) {
            result[i] = values[i];
        }
        return result;
    }

    private static List<Event> seededSignatures(String day) {
        List<Event> events = new ArrayList<>();

        if (day.equals("2026-06-28")) {
            // Bug #1 flavour: reconcile finds a penny mismatch on a discounted order.
            events.add(new Event(85805, List.of(logLine(day, 85805, "INFO", "ai.octoco.legacyservice.Reconcile",
                    "reconcile_day start date=2026-06-28"))));
            events.add(new Event(85808, List.of(logLine(day, 85808, "WARNING", "ai.octoco.legacyservice.Reconcile",
                    "total mismatch order=00000009 stored=32.62 recomputed=32.63 delta=0.01"))));
        }

        if (day.equals("2026-06-29")) {
            // Bug #3: WMS sync sets SHIPPED at 05:31, but a later read serves NEW.
            events.add(new Event(19800, List.of("db ready at orderbase.db"))); // 05:30 sync boot
            events.add(new Event(19870, List.of(logLine(day, 19870, "INFO", ORD, "order 00000007 status -> SHIPPED")))); // 05:31:10
            events.add(new Event(33164, List.of(logLine(day, 33164, "INFO", APP, "GET /orders/00000007 200 status=NEW")))); // 09:12:44
            events.add(new Event(33210, List.of(logLine(day, 33210, "WARNING", "Monitor",
                    "order 00000007 shows NEW in API but SHIPPED in WMS (cache?)"))));
            // Bug #1 flavour again.
            events.add(new Event(85805, List.of(logLine(day, 85805, "INFO", "ai.octoco.legacyservice.Reconcile",
                    "reconcile_day start date=2026-06-29"))));
            events.add(new Event(85809, List.of(logLine(day, 85809, "WARNING", "ai.octoco.legacyservice.Reconcile",
                    "total mismatch order=00000015 stored=9.40 recomputed=9.41 delta=0.01"))));
        }

        if (day.equals("2026-06-30")) {
            // Bug #2: just after 00:00 UTC the no-date /report drops the day's rows.
            events.add(new Event(192, List.of(logLine(day, 192, "INFO", APP,
                    "GET /report 200 date=2026-06-30 orders=0 total=0.00")))); // 00:03:12
            events.add(new Event(192, List.of(logLine(day, 192, "WARNING", "Monitor",
                    "daily digest EMPTY for 2026-06-30 (expected>=8), retrying"))));
            events.add(new Event(1900, List.of(logLine(day, 1900, "INFO", APP,
                    "GET /report 200 date=2026-06-30 orders=0 total=0.00")))); // 00:31:40
            events.add(new Event(29525, List.of(logLine(day, 29525, "INFO", APP,
                    "GET /report?date=2026-06-30 200 orders=9 total=1043.71")))); // 08:12:05
            // Bug #1: the reconcile mismatch that maps to FAKE_SENTRY ORDERBASE-3A1.
            events.add(new Event(85805, List.of(logLine(day, 85805, "INFO", "ai.octoco.legacyservice.Reconcile",
                    "reconcile_day start date=2026-06-30"))));
            events.add(new Event(85808, List.of(logLine(day, 85808, "WARNING", "ai.octoco.legacyservice.Reconcile",
                    "total mismatch order=00000021 stored=89.95 recomputed=89.96 delta=0.01"))));
        }

        return events;
    }

    private static List<String> genDay(String day, long seed) {
        Random rng = new Random(seed);
        List<Event> events = new ArrayList<>(List.of(
                // Boot banner (stray prints, no timestamp prefix).
                new Event(4, List.of("db ready at orderbase.db")),
                new Event(5, List.of("OrderBase v1.4.2 listening on 0.0.0.0:5057 (debug=true)"))));

        int targetLines = 430 + rng.nextInt(111);
        int[] counter = {30 + rng.nextInt(16)};
        int sec = 120 + rng.nextInt(281);
        int produced = 2;
        while (produced < targetLines && sec < 86200) {
            // Gaps are shorter during business hours, longer overnight.
            int hour = sec / 3600;
            int gap = (hour >= 7 && hour <= 19) ? 15 + rng.nextInt(76) : 120 + rng.nextInt(481);
            sec += gap;
            List<String> lines = randomEvent(rng, day, sec, counter);
            events.add(new Event(sec, lines));
            produced += lines.size();
        }

        events.addAll(seededSignatures(day));
        events.sort((a, b) -> Integer.compare(a.sec(), b.sec()));

        List<String> result = new ArrayList<>();
        for (Event e : events) {
            result.addAll(e.lines());
        }
        return result;
    }

    // Every emitted line must match the frozen format (a hand-rolled test of
    // the invariant the fixtures depend on -- the Python original lacks this).
    private static boolean lineLooksValid(String line) {
        return VALID_LINE.matcher(line).matches()
                || line.startsWith("db ready")
                || line.startsWith("OrderBase v")
                || line.startsWith("created order")
                || line.startsWith("DEBUG: ");
    }
}

package ai.octoco.legacyservice;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

// Utils.java -- grab bag of helpers. (TODO: split this up some day. -- J, 2018)

public final class Utils {

    public static final String[] VALID_STATUSES = {"NEW", "PAID", "SHIPPED", "CANCELLED"};

    private static final DateTimeFormatter TS_FORMAT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss", Locale.ROOT);
    private static final DateTimeFormatter DATE_FORMAT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd", Locale.ROOT);

    private Utils() {}

    // WMS export parses fixed-width IDs -- do not change the padding.
    // (The warehouse system reads chars 0-7 of each line of the nightly
    // export file. An ID longer or shorter than 8 chars corrupts the batch.)
    public static String formatOrderId(long n) {
        return String.format(Locale.ROOT, "%08d", n);
    }

    // Round a double to 2 decimal places. Good enough for money. (Is it?)
    //
    // 2018: Math.round(x * 100) / 100.0 disagreed with the old reporting sheet
    // on half-cent totals, so we round the EXACT binary value (round-half-even,
    // same tie-break as Python's round()) instead. Nobody has touched it since.
    //
    // IMPORTANT: this must be `new BigDecimal(x)` (the double's true binary
    // value), never `BigDecimal.valueOf(x)` or `String.format("%.2f", x)` --
    // both of those round the *shortest round-trippable decimal string* for x
    // instead of the actual value, which quietly changes results right at the
    // boundary this bug depends on (e.g. 99.95 * 0.9 prints as "89.955" but is
    // truly 89.95499999999999829..., which only the exact BigDecimal conversion
    // sees -- format-and-reparse rounds the pretty string up to 89.96 and
    // silently "fixes" the bug).
    public static double money(double x) {
        return new BigDecimal(x).setScale(2, RoundingMode.HALF_EVEN).doubleValue();
    }

    // Pretty much the same as money() but returns a string. Kept because the
    // old report templates called this one. Don't consolidate blindly.
    public static String formatMoney(double x) {
        return new BigDecimal(x).setScale(2, RoundingMode.HALF_EVEN).toPlainString();
    }

    // 2019: started migrating money math to integer cents, never finished.
    // Nothing calls this.
    public static long toCents(double x) {
        return (long) (x * 100);
    }

    public static LocalDateTime parseTs(String s) {
        return LocalDateTime.parse(s, TS_FORMAT);
    }

    // Same as parseTs but date-only. (Yes, this could share code. It's fine.)
    public static LocalDateTime parseDate(String s) {
        return LocalDate.parse(s, DATE_FORMAT).atStartOfDay();
    }

    public static String validateStatus(String status) {
        for (String valid : VALID_STATUSES) {
            if (valid.equals(status)) {
                return status;
            }
        }
        throw new IllegalArgumentException("bad status: " + status);
    }

    // Was used by the old CSV exporter. The exporter is gone; this stayed.
    public static <T> List<List<T>> chunk(List<T> seq, int size) {
        List<List<T>> chunks = new ArrayList<>();
        for (int i = 0; i < seq.size(); i += size) {
            chunks.add(new ArrayList<>(seq.subList(i, Math.min(i + size, seq.size()))));
        }
        return chunks;
    }
}

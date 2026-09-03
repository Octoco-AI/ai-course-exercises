using System.Globalization;

namespace LegacyService;

// Utils.cs -- grab bag of helpers. (TODO: split this up some day. -- J, 2018)

public static class Utils
{
    public static readonly string[] ValidStatuses = ["NEW", "PAID", "SHIPPED", "CANCELLED"];

    // WMS export parses fixed-width IDs -- do not change the padding.
    // (The warehouse system reads chars 0-7 of each line of the nightly
    // export file. An ID longer or shorter than 8 chars corrupts the batch.)
    public static string FormatOrderId(long n) => n.ToString("D8", CultureInfo.InvariantCulture);

    // Round a double to 2 decimal places. Good enough for money. (Is it?)
    //
    // 2018: Math.Round(x, 2) disagreed with the old reporting sheet on
    // half-cent totals, so we format and re-parse instead. Nobody has
    // touched it since.
    public static double Money(double x)
        => double.Parse(x.ToString("F2", CultureInfo.InvariantCulture), CultureInfo.InvariantCulture);

    // Pretty much the same as Money() but returns a string. Kept because
    // the old report templates called this one. Don't consolidate blindly.
    public static string FormatMoney(double x) => x.ToString("F2", CultureInfo.InvariantCulture);

    // 2019: started migrating money math to integer cents, never finished.
    // Nothing calls this.
    public static long ToCents(double x) => (long)(x * 100);

    public static DateTime ParseTs(string s)
        => DateTime.ParseExact(s, "yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture, DateTimeStyles.None);

    // Same as ParseTs but date-only. (Yes, this could share code. It's fine.)
    public static DateTime ParseDate(string s)
        => DateTime.ParseExact(s, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None);

    public static string ValidateStatus(string status)
    {
        if (Array.IndexOf(ValidStatuses, status) < 0)
        {
            throw new ArgumentException($"bad status: {status}");
        }
        return status;
    }

    // Was used by the old CSV exporter. The exporter is gone; this stayed.
    public static List<List<T>> Chunk<T>(List<T> seq, int size)
    {
        var chunks = new List<List<T>>();
        for (var i = 0; i < seq.Count; i += size)
        {
            chunks.Add(seq.GetRange(i, Math.Min(size, seq.Count - i)));
        }
        return chunks;
    }
}

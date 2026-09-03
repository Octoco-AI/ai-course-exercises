using System.Globalization;

// Program.cs -- generate OrderBase log fixtures (C# port of gen_logs.py).
//
// Writes logs/app-2026-06-28.log .. logs/app-2026-06-30.log: a few hundred
// lines each of realistic, mixed-format noise (structured INFO request lines
// in the app's real log format, stray Console.WriteLine-style lines with no
// prefix, the odd WARNING). A handful of production-bug signatures are
// seeded into the noise on specific days.
//
// The RNG-driven noise is deterministic WITHIN this port (fixed seeds via
// `new Random(seed)`, never Random.Shared) but does not reproduce the same
// bytes as the Python fixtures -- .NET's PRNG algorithm differs from
// Python's, and that's fine: nothing asserts on the noise. The seeded
// signature lines below are hand-written and byte-identical to the Python
// and TypeScript ports modulo logger names -- those are what FAKE_SENTRY.md
// and the M27 symptom-to-code trace actually depend on.
//
// This script doubles as the "regenerate fixtures" microtooling example.
//
// Usage:
//   dotnet run --project scripts/GenLogs              # write into ./logs
//   dotnet run --project scripts/GenLogs -- --stdout   # print day 1, write nothing

var repoRoot = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
var logDir = Path.Combine(repoRoot, "logs");
string[] days = ["2026-06-28", "2026-06-29", "2026-06-30"];

const string App = "LegacyService.App";
const string Ord = "LegacyService.Orders";

string[] customers =
[
    "Acme Ltd", "Northwind Traders", "Globex", "Initech",
    "Umbrella Co", "Stark Supplies", "Wayne Retail", "Soylent Foods",
    "Hooli", "Vandelay",
];
string[] skus = ["SKU-0001", "SKU-0002", "SKU-0003", "SKU-0004", "SKU-0005", "SKU-0006", "SKU-0007", "SKU-0008", "SKU-0009"];
string[] statuses = ["NEW", "PAID", "SHIPPED", "CANCELLED"];
double[] prices = [19.99, 4.95, 12.50, 7.25, 8.80];

static double Money(double x) => double.Parse(x.ToString("F2", CultureInfo.InvariantCulture), CultureInfo.InvariantCulture);

static string FmtTs(string day, int sec) => $"{day} {sec / 3600:D2}:{sec % 3600 / 60:D2}:{sec % 60:D2}";

static string LogLine(string day, int sec, string level, string name, string msg) => $"{FmtTs(day, sec)} {level} {name} {msg}";

static string OrderId(int n) => n.ToString("D8", CultureInfo.InvariantCulture);

static T Choice<T>(Random rng, IReadOnlyList<T> items) => items[rng.Next(items.Count)];

List<string> RandomEvent(Random rng, string day, int sec, int[] counter)
{
    var roll = rng.NextDouble();
    var lines = new List<string>();

    if (roll < 0.42)
    {
        // GET /orders/<id>
        var oid = OrderId(rng.Next(1, Math.Max(1, counter[0]) + 1));
        if (rng.NextDouble() < 0.06)
        {
            lines.Add(LogLine(day, sec, "INFO", App, $"GET /orders/{oid} 404"));
        }
        else
        {
            var status = Choice(rng, statuses);
            lines.Add(LogLine(day, sec, "INFO", App, $"GET /orders/{oid} 200 status={status}"));
        }
    }
    else if (roll < 0.60)
    {
        // GET /orders (list)
        var count = rng.Next(1, 51);
        lines.Add(LogLine(day, sec, "INFO", App, $"GET /orders 200 count={count}"));
    }
    else if (roll < 0.82)
    {
        // POST /orders -- emits the debug print, both log lines, and the
        // stray "created order" print, exactly as the code does.
        counter[0] += 1;
        var oid = OrderId(counter[0]);
        var customer = Choice(rng, customers);
        var nItems = rng.Next(1, 4);
        var items = Enumerable.Range(0, nItems)
            .Select(_ => (sku: Choice(rng, skus), qty: rng.Next(1, 5), unitPrice: Choice(rng, prices)))
            .ToList();
        var total = Money(items.Sum(i => i.qty * i.unitPrice));
        var payloadItems = string.Join(", ", items.Select(i =>
            $"{{ sku: '{i.sku}', qty: {i.qty}, unitPrice: {i.unitPrice.ToString(CultureInfo.InvariantCulture)} }}"));
        lines.Add($"DEBUG: POST /orders payload={{ Customer = {customer}, Items = [ {payloadItems} ] }}"); // stray
        lines.Add(LogLine(day, sec, "INFO", Ord,
            $"order {oid} created customer={customer} items={nItems} total={total.ToString("F2", CultureInfo.InvariantCulture)}"));
        lines.Add($"created order {oid} total={total.ToString(CultureInfo.InvariantCulture)}"); // stray
        lines.Add(LogLine(day, sec, "INFO", App,
            $"POST /orders 201 id={oid} total={total.ToString("F2", CultureInfo.InvariantCulture)}"));
    }
    else if (roll < 0.92)
    {
        // GET /report
        var n = rng.Next(4, 15);
        var total = Money(rng.NextDouble() * (1600 - 300) + 300);
        lines.Add(LogLine(day, sec, "INFO", App,
            $"GET /report 200 date={day} orders={n} total={total.ToString("F2", CultureInfo.InvariantCulture)}"));
    }
    else
    {
        // An occasional rejected order (WARNING).
        string[] reasons = ["customer is required", "at least one item is required", "discount_pct out of range"];
        var reason = Choice(rng, reasons);
        lines.Add(LogLine(day, sec, "WARNING", Ord, $"rejected order: {reason}"));
        lines.Add(LogLine(day, sec, "INFO", App, $"POST /orders 400 error=\"{reason}\""));
    }

    return lines;
}

List<(int Sec, List<string> Lines)> SeededSignatures(string day)
{
    var ev = new List<(int, List<string>)>();

    if (day == "2026-06-28")
    {
        // Bug #1 flavour: reconcile finds a penny mismatch on a discounted order.
        ev.Add((85805, [LogLine(day, 85805, "INFO", "LegacyService.Reconcile", "reconcile_day start date=2026-06-28")]));
        ev.Add((85808, [LogLine(day, 85808, "WARNING", "LegacyService.Reconcile",
            "total mismatch order=00000009 stored=32.62 recomputed=32.63 delta=0.01")]));
    }

    if (day == "2026-06-29")
    {
        // Bug #3: WMS sync sets SHIPPED at 05:31, but a later read serves NEW.
        ev.Add((19800, ["db ready at orderbase.db"])); // 05:30 sync boot
        ev.Add((19870, [LogLine(day, 19870, "INFO", Ord, "order 00000007 status -> SHIPPED")])); // 05:31:10
        ev.Add((33164, [LogLine(day, 33164, "INFO", App, "GET /orders/00000007 200 status=NEW")])); // 09:12:44
        ev.Add((33210, [LogLine(day, 33210, "WARNING", "Monitor",
            "order 00000007 shows NEW in API but SHIPPED in WMS (cache?)")]));
        // Bug #1 flavour again.
        ev.Add((85805, [LogLine(day, 85805, "INFO", "LegacyService.Reconcile", "reconcile_day start date=2026-06-29")]));
        ev.Add((85809, [LogLine(day, 85809, "WARNING", "LegacyService.Reconcile",
            "total mismatch order=00000015 stored=9.40 recomputed=9.41 delta=0.01")]));
    }

    if (day == "2026-06-30")
    {
        // Bug #2: just after 00:00 UTC the no-date /report drops the day's rows.
        ev.Add((192, [LogLine(day, 192, "INFO", App, "GET /report 200 date=2026-06-30 orders=0 total=0.00")])); // 00:03:12
        ev.Add((192, [LogLine(day, 192, "WARNING", "Monitor",
            "daily digest EMPTY for 2026-06-30 (expected>=8), retrying")]));
        ev.Add((1900, [LogLine(day, 1900, "INFO", App, "GET /report 200 date=2026-06-30 orders=0 total=0.00")])); // 00:31:40
        ev.Add((29525, [LogLine(day, 29525, "INFO", App,
            "GET /report?date=2026-06-30 200 orders=9 total=1043.71")])); // 08:12:05
        // Bug #1: the reconcile mismatch that maps to FAKE_SENTRY ORDERBASE-3A1.
        ev.Add((85805, [LogLine(day, 85805, "INFO", "LegacyService.Reconcile", "reconcile_day start date=2026-06-30")]));
        ev.Add((85808, [LogLine(day, 85808, "WARNING", "LegacyService.Reconcile",
            "total mismatch order=00000021 stored=89.95 recomputed=89.96 delta=0.01")]));
    }

    return ev;
}

List<string> GenDay(string day, int seed)
{
    var rng = new Random(seed);
    var events = new List<(int Sec, List<string> Lines)>
    {
        // Boot banner (stray prints, no timestamp prefix).
        (4, ["db ready at orderbase.db"]),
        (5, ["OrderBase v1.4.2 listening on 0.0.0.0:5057 (debug=True)"]),
    };

    var targetLines = rng.Next(430, 541);
    var counter = new[] { rng.Next(30, 46) };
    var sec = rng.Next(120, 401);
    var produced = 2;
    while (produced < targetLines && sec < 86200)
    {
        // Gaps are shorter during business hours, longer overnight.
        var hour = sec / 3600;
        var gap = hour is >= 7 and <= 19 ? rng.Next(15, 91) : rng.Next(120, 601);
        sec += gap;
        var lines = RandomEvent(rng, day, sec, counter);
        events.Add((sec, lines));
        produced += lines.Count;
    }

    events.AddRange(SeededSignatures(day));
    events.Sort((a, b) => a.Sec.CompareTo(b.Sec));

    return events.SelectMany(e => e.Lines).ToList();
}

// Every emitted line must match the frozen format (a hand-rolled test of the
// invariant the fixtures depend on -- the Python original lacks this).
bool LineLooksValid(string line) =>
    System.Text.RegularExpressions.Regex.IsMatch(
        line,
        @"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} (INFO|WARNING) \S+ .+$")
    || line.StartsWith("db ready", StringComparison.Ordinal)
    || line.StartsWith("OrderBase v", StringComparison.Ordinal)
    || line.StartsWith("created order", StringComparison.Ordinal)
    || line.StartsWith("DEBUG: ", StringComparison.Ordinal);

if (args.Contains("--stdout"))
{
    foreach (var line in GenDay(days[0], 42))
    {
        Console.WriteLine(line);
    }
    return;
}

Directory.CreateDirectory(logDir);
for (var i = 0; i < days.Length; i++)
{
    var day = days[i];
    var lines = GenDay(day, 42 + i);
    var invalid = lines.Where(l => !LineLooksValid(l)).ToList();
    if (invalid.Count > 0)
    {
        throw new InvalidOperationException($"generated a line that doesn't match the frozen format: {invalid[0]}");
    }
    var path = Path.Combine(logDir, $"app-{day}.log");
    File.WriteAllText(path, string.Join("\n", lines) + "\n");
    Console.WriteLine($"wrote {path} ({lines.Count} lines)");
}

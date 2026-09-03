using System.Globalization;
using System.Text.Json;

using LegacyService;

// Program.cs -- seed OrderBase with deterministic sample data (C# port of
// seed_data.py).
//
// Creates ~30 orders spread over three days (2026-06-28 .. 2026-06-30) by
// going through the real order-creation path (Orders.CreateOrder), then
// adjusting each row's created_at and status to the target values. Running
// it twice gives the same database every time -- and, since it drives the
// real ComputeTotal, the same 30 totals as the Python original except order
// #16 (see the TypeScript port's FACILITATOR.md for why the TS money()
// diverges there; this C# port is exact on all 30).
//
// Usage:
//   dotnet run --project scripts/SeedData
//
// Honours ORDERBASE_DB (defaults to orderbase.db in the working dir).

string[] days = ["2026-06-28", "2026-06-29", "2026-06-30"];

string[] customers =
[
    "Acme Ltd", "Northwind Traders", "Globex", "Initech", "Umbrella Co",
    "Stark Supplies", "Wayne Retail", "Soylent Foods", "Hooli", "Vandelay",
];

// (sku, unit_price) catalogue. Prices chosen so that discounts land on a mix
// of clean and not-so-clean cent values.
(string Sku, double Price)[] catalogue =
[
    ("SKU-0001", 19.99), ("SKU-0002", 4.95), ("SKU-0003", 12.50),
    ("SKU-0004", 7.25), ("SKU-0005", 3.33), ("SKU-0006", 49.00),
    ("SKU-0007", 8.80), ("SKU-0008", 1.10), ("SKU-0009", 19.99),
];

double[] discountCycle = [0, 0, 10, 5, 0, 15, 0, 7.5, 0, 10];
string[] statusCycle = ["NEW", "PAID", "SHIPPED", "PAID", "CANCELLED", "SHIPPED", "NEW", "PAID", "SHIPPED", "NEW"];

// A few orders are pinned so they line up with FAKE_SENTRY.md and the log
// fixtures (ids are assigned in creation order, starting at 00000001):
//   #7  -> SHIPPED, referenced by the stale-cache issue (ORDERBASE-9F2)
//   #21 -> 5 x SKU-0009 @ 19.99, 10% off -> reconcile mismatch (ORDERBASE-3A1)
Dictionary<int, ((string Sku, int Qty)[]? Items, double? DiscountPct, string? Status)> pinned = new()
{
    [7] = (null, null, "SHIPPED"),
    [21] = ([("SKU-0009", 5)], 10, "SHIPPED"),
};

const int NOrders = 30;

JsonElement BuildPayload(int i)
{
    var customer = customers[(i - 1) % customers.Length];
    var discount = discountCycle[(i - 1) % discountCycle.Length];

    // One-to-three line items, chosen deterministically from the catalogue.
    var nItems = 1 + ((i - 1) % 3);
    var items = new List<object>();
    for (var j = 0; j < nItems; j++)
    {
        var (sku, price) = catalogue[(i + j) % catalogue.Length];
        var qty = 1 + ((i + j) % 4);
        items.Add(new { sku, qty, unit_price = price });
    }

    if (pinned.TryGetValue(i, out var pin))
    {
        if (pin.Items is not null)
        {
            items = pin.Items
                .Select(it => (object)new { sku = it.Sku, qty = it.Qty, unit_price = catalogue.First(c => c.Sku == it.Sku).Price })
                .ToList();
        }
        if (pin.DiscountPct is not null)
        {
            discount = pin.DiscountPct.Value;
        }
    }

    return JsonSerializer.SerializeToElement(new { customer, items, discount_pct = discount });
}

(string CreatedAt, string Status) TargetMeta(int i)
{
    var day = days[(i - 1) / 10];
    // Spread orders through the working day, deterministically.
    var hour = 8 + (i * 3 % 11);
    var minute = i * 7 % 60;
    var second = i * 13 % 60;
    var createdAt = $"{day} {hour:D2}:{minute:D2}:{second:D2}";

    var status = (pinned.TryGetValue(i, out var pin) ? pin.Status : null) ?? statusCycle[(i - 1) % statusCycle.Length];
    return (createdAt, status);
}

Db.InitDb();

// Deterministic: clear existing rows so ids restart at 00000001.
Db.Execute($"DELETE FROM {Db.OrdersTable}");
Db.Execute($"DELETE FROM {Db.ItemsTable}");

var createdIds = new List<string>();
for (var i = 1; i <= NOrders; i++)
{
    var order = Orders.CreateOrder(BuildPayload(i));
    var (createdAt, status) = TargetMeta(i);
    Db.Execute($"UPDATE {Db.OrdersTable} SET created_at = ?, status = ? WHERE id = ?", createdAt, status, order.Id);
    createdIds.Add(order.Id);
}

// Validate what we produced. (Assertions the Python original lacks -- this
// is the "regenerate fixtures WITH validation" chore.)
var rows = Db.Query($"SELECT id, status, total, created_at FROM {Db.OrdersTable} ORDER BY id");
if (rows.Count != NOrders)
{
    throw new InvalidOperationException($"expected {NOrders} orders, got {rows.Count}");
}
if (rows.Any(r => ((string)r["id"]!).Length != 8))
{
    throw new InvalidOperationException("found an id that is not 8 chars");
}
var order21 = rows.Single(r => (string)r["id"]! == "00000021");
if (Convert.ToDouble(order21["total"], CultureInfo.InvariantCulture) != 89.95)
{
    throw new InvalidOperationException($"order #21 should total 89.95, got {order21["total"]}");
}
var order7 = rows.Single(r => (string)r["id"]! == "00000007");
if ((string)order7["status"]! != "SHIPPED")
{
    throw new InvalidOperationException($"order #7 should be SHIPPED, got {order7["status"]}");
}

Console.WriteLine();
Console.WriteLine($"Seeded {rows.Count} orders into {Db.DbPath}");
foreach (var day in days)
{
    var dayRows = rows.Where(r => ((string)r["created_at"]!).StartsWith(day, StringComparison.Ordinal)).ToList();
    var total = dayRows.Sum(r => Convert.ToDouble(r["total"], CultureInfo.InvariantCulture));
    Console.WriteLine($"  {day}: {dayRows.Count,2} orders, total {total.ToString("F2", CultureInfo.InvariantCulture)}");
}
Console.WriteLine($"  ids: {createdIds[0]} .. {createdIds[^1]}");

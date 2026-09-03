using System.Globalization;
using System.Text.Json;

namespace LegacyService;

// The order itself. Mutable and reference-typed on purpose -- see the
// _orderCache comment on GetOrder below. Not a record: a record's
// value-equality and (with `with`) copy-on-write semantics would quietly
// fix the cache's reference-bleed bug.
public class Order
{
    public string Id { get; set; } = "";
    public string Customer { get; set; } = "";
    public string Status { get; set; } = "NEW";
    public double DiscountPct { get; set; }
    public double Total { get; set; }
    public string CreatedAt { get; set; } = "";
    public List<OrderItem> Items { get; set; } = [];
}

public class OrderItem
{
    public string Sku { get; set; } = "";
    public int Qty { get; set; }
    public double UnitPrice { get; set; }
}

public class StatusBucket
{
    public int Orders { get; set; }
    public double Total { get; set; }
}

public class DailyReportResult
{
    public string Date { get; set; } = "";
    public int Orders { get; set; }
    public double Total { get; set; }
    public Dictionary<string, StatusBucket> ByStatus { get; set; } = [];
}

// Orders.cs -- order domain logic for OrderBase.
//
// In production since 2018. The fulfilment sync, the WMS export and the
// reconcile cron all depend on behaviour in this file. Tread carefully.

public static class Orders
{
    private static readonly Logger Log = LoggingSetup.GetLogger("LegacyService.Orders");

    // Cheap perf win: order rows barely change after creation, so cache lookups
    // per process. (2018-09: cut p95 on GET /orders/<id> from 40ms to 2ms.)
    private static readonly Dictionary<string, Order> OrderCache = [];

    // Hung off delegates so the 2019 report tests could pin the clock.
    // Nothing in production ever reassigns these.

    // Local server time. Report cutoffs use this.
    public static Func<DateTime> Now = () => DateTime.Now;

    // Timestamps are stored in UTC (ops decision, 2018-04).
    public static Func<DateTime> UtcNow = () => DateTime.UtcNow;

    public static double ComputeTotal(List<OrderItem> items, double discountPct)
    {
        var subtotal = 0.0;
        foreach (var it in items)
        {
            subtotal += it.Qty * it.UnitPrice;
        }
        var total = subtotal * (1.0 - discountPct / 100.0);
        return Utils.Money(total);
    }

    private static string NextOrderId()
    {
        // MAX() is safe because ids are fixed-width, zero-padded strings --
        // lexicographic order == numeric order. Another reason the 8-char
        // padding must never change.
        var rows = Db.Query($"SELECT MAX(id) AS m FROM {Db.OrdersTable}");
        var m = rows[0]["m"] as string;
        if (m is null)
        {
            return Utils.FormatOrderId(1);
        }
        return Utils.FormatOrderId(long.Parse(m, CultureInfo.InvariantCulture) + 1);
    }

    public static Order CreateOrder(JsonElement payload)
    {
        var customer = payload.TryGetProperty("customer", out var customerEl) && customerEl.ValueKind == JsonValueKind.String
            ? customerEl.GetString()!.Trim()
            : "";
        if (customer.Length == 0)
        {
            throw new ArgumentException("customer is required");
        }

        if (!payload.TryGetProperty("items", out var itemsEl)
            || itemsEl.ValueKind != JsonValueKind.Array
            || itemsEl.GetArrayLength() == 0)
        {
            throw new ArgumentException("at least one item is required");
        }

        var cleanItems = new List<OrderItem>();
        foreach (var it in itemsEl.EnumerateArray())
        {
            string sku;
            int qty;
            double unitPrice;
            try
            {
                sku = it.GetProperty("sku").ToString();
                qty = it.GetProperty("qty").GetInt32();
                unitPrice = it.GetProperty("unit_price").GetDouble();
            }
            catch (Exception ex) when (ex is KeyNotFoundException or InvalidOperationException or FormatException or OverflowException)
            {
                throw new ArgumentException($"bad item: {it}");
            }
            if (qty <= 0 || unitPrice < 0)
            {
                throw new ArgumentException($"bad item: {it}");
            }
            cleanItems.Add(new OrderItem { Sku = sku, Qty = qty, UnitPrice = unitPrice });
        }

        var discountPct = 0.0;
        if (payload.TryGetProperty("discount_pct", out var discountEl) && discountEl.ValueKind != JsonValueKind.Null)
        {
            discountPct = discountEl.GetDouble();
        }
        if (discountPct < 0 || discountPct > 100)
        {
            throw new ArgumentException("discount_pct out of range");
        }

        var orderId = NextOrderId();
        var total = ComputeTotal(cleanItems, discountPct);
        var createdAt = UtcNow().ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture);

        Db.Execute(
            $"INSERT INTO {Db.OrdersTable} (id, customer, status, discount_pct, total, created_at)"
            + " VALUES (?, ?, ?, ?, ?, ?)",
            orderId, customer, "NEW", discountPct, total, createdAt);
        foreach (var it in cleanItems)
        {
            Db.Execute(
                $"INSERT INTO {Db.ItemsTable} (order_id, sku, qty, unit_price) VALUES (?, ?, ?, ?)",
                orderId, it.Sku, it.Qty, it.UnitPrice);
        }

        var order = new Order
        {
            Id = orderId,
            Customer = customer,
            Status = "NEW",
            DiscountPct = discountPct,
            Total = total,
            CreatedAt = createdAt,
            Items = cleanItems,
        };
        OrderCache[orderId] = order;
        Console.WriteLine($"created order {orderId} total={total.ToString(CultureInfo.InvariantCulture)}");
        Log.Info("order {0} created customer={1} items={2} total={3:F2}",
            orderId, customer, cleanItems.Count, total);
        return order;
    }

    public static Order? GetOrder(string orderId)
    {
        if (OrderCache.TryGetValue(orderId, out var cached))
        {
            return cached;
        }
        if (!IsDigits(orderId))
        {
            return null;
        }
        var rows = Db.Query($"SELECT * FROM {Db.OrdersTable} WHERE id = '{orderId}'");
        if (rows.Count == 0)
        {
            return null;
        }
        var row = rows[0];
        var itemRows = Db.Query(
            $"SELECT sku, qty, unit_price FROM {Db.ItemsTable} WHERE order_id = '{orderId}'");
        var order = new Order
        {
            Id = (string)row["id"]!,
            Customer = (string)row["customer"]!,
            Status = (string)row["status"]!,
            DiscountPct = Convert.ToDouble(row["discount_pct"], CultureInfo.InvariantCulture),
            Total = Convert.ToDouble(row["total"], CultureInfo.InvariantCulture),
            CreatedAt = (string)row["created_at"]!,
            Items = itemRows.Select(r => new OrderItem
            {
                Sku = (string)r["sku"]!,
                Qty = Convert.ToInt32(r["qty"], CultureInfo.InvariantCulture),
                UnitPrice = Convert.ToDouble(r["unit_price"], CultureInfo.InvariantCulture),
            }).ToList(),
        };
        OrderCache[orderId] = order;
        return order;
    }

    public static List<Order> ListOrders(string? status, int limit)
    {
        List<Dictionary<string, object?>> rows;
        if (status is not null)
        {
            Utils.ValidateStatus(status); // whitelist, so the interpolation is "fine"
            rows = Db.Query(
                $"SELECT * FROM {Db.OrdersTable} WHERE status = '{status}' ORDER BY id DESC LIMIT {limit}");
        }
        else
        {
            rows = Db.Query($"SELECT * FROM {Db.OrdersTable} ORDER BY id DESC LIMIT {limit}");
        }
        return rows.Select(RowToOrder).ToList();
    }

    public static void UpdateOrderStatus(string orderId, string status)
    {
        // Called by the fulfilment sync (WMS CSV import, 05:30 cron) -- not by
        // the HTTP API. See DOCS/INSTRUCTIONS.md.
        Utils.ValidateStatus(status);
        if (!IsDigits(orderId))
        {
            throw new ArgumentException($"bad order id: {orderId}");
        }
        Db.Execute($"UPDATE {Db.OrdersTable} SET status = '{status}' WHERE id = '{orderId}'");
        Log.Info("order {0} status -> {1}", orderId, status);
        // NOTE: not touching OrderCache here. Status changes come from the
        // nightly sync; by the time anyone looks, the process has restarted.
    }

    public static DailyReportResult DailyReport(string? dateStr)
    {
        List<Dictionary<string, object?>> rows;
        string label;
        if (dateStr is not null)
        {
            Utils.ParseDate(dateStr); // validates the format before we use it
            rows = Db.Query($"SELECT * FROM {Db.OrdersTable} WHERE created_at LIKE '{dateStr}%'");
            label = dateStr;
        }
        else
        {
            var start = Now().Date;
            var end = start.AddDays(1);
            // TODO: push this filter into SQL. Fine while volume is low.
            rows = [];
            foreach (var r in Db.Query($"SELECT * FROM {Db.OrdersTable}"))
            {
                var created = Utils.ParseTs((string)r["created_at"]!);
                if (start <= created && created < end)
                {
                    rows.Add(r);
                }
            }
            label = start.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        }

        var total = 0.0;
        var byStatus = new Dictionary<string, StatusBucket>();
        foreach (var r in rows)
        {
            var rowTotal = Convert.ToDouble(r["total"], CultureInfo.InvariantCulture);
            total += rowTotal;
            var st = (string)r["status"]!;
            if (!byStatus.TryGetValue(st, out var bucket))
            {
                bucket = new StatusBucket();
                byStatus[st] = bucket;
            }
            bucket.Orders += 1;
            bucket.Total = Utils.Money(bucket.Total + rowTotal);
        }

        var report = new DailyReportResult
        {
            Date = label,
            Orders = rows.Count,
            Total = Utils.Money(total),
            ByStatus = byStatus,
        };
        Log.Info("report {0} orders={1} total={2:F2}", label, report.Orders, report.Total);
        return report;
    }

    private static Order RowToOrder(Dictionary<string, object?> row) => new()
    {
        Id = (string)row["id"]!,
        Customer = (string)row["customer"]!,
        Status = (string)row["status"]!,
        DiscountPct = Convert.ToDouble(row["discount_pct"], CultureInfo.InvariantCulture),
        Total = Convert.ToDouble(row["total"], CultureInfo.InvariantCulture),
        CreatedAt = (string)row["created_at"]!,
        Items = [],
    };

    private static bool IsDigits(string s) => s.Length > 0 && s.All(char.IsDigit);
}

using System.Globalization;
using System.Text.Json;

using LegacyService;

// Program.cs -- OrderBase HTTP API.
//
// Four endpoints. In production since 2018. If you are reading this because
// something broke: logs are in logs/, the reconcile cron is in the ops repo,
// and DOCS/INSTRUCTIONS.md is roughly current (last real update 2019).
//
// Run locally:
//     dotnet run --project src/LegacyService
//
// The old way was `dotnet watch run`, but the reloader double-binds :5057 --
// do not use it.

const string AppVersion = "1.4.2";

// Ops images the boxes from a golden AMI; nothing below is meant to be
// configurable. The port was picked in 2018 to dodge the office proxy.
const string ServiceHost = "0.0.0.0";
const int Port = 5057;
const bool Debug = true; // left on after the 2019 checkout incident. Do not ask.

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls($"http://{ServiceHost}:{Port}");
builder.Logging.ClearProviders(); // Kestrel/Hosting noise would break the frozen log format.

builder.Services.ConfigureHttpJsonOptions(options =>
{
    // The WMS and the fulfilment sync parse these keys -- do not tidy them
    // to camelCase.
    options.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower;
});

var app = builder.Build();

if (Debug)
{
    app.UseDeveloperExceptionPage();
}

var log = LoggingSetup.GetLogger("LegacyService.App");

app.MapPost("/orders", async (HttpContext context) =>
{
    JsonElement data;
    try
    {
        using var doc = await JsonDocument.ParseAsync(context.Request.Body);
        data = doc.RootElement.Clone();
    }
    catch (JsonException)
    {
        return Results.Json(new { error = "body must be JSON" }, statusCode: 400);
    }

    if (Debug)
    {
        Console.WriteLine($"DEBUG: POST /orders payload={data}");
    }

    Order order;
    try
    {
        order = Orders.CreateOrder(data);
    }
    catch (ArgumentException ex)
    {
        log.Warning("rejected order: {0}", ex.Message);
        return Results.Json(new { error = ex.Message }, statusCode: 400);
    }
    log.Info("POST /orders 201 id={0} total={1:F2}", order.Id, order.Total);
    return Results.Json(order, statusCode: 201);
});

app.MapGet("/orders/{orderId}", (string orderId) =>
{
    // Accept bare numeric ids ("42") as a convenience and pad them.
    // (Same rule as Utils.FormatOrderId -- keep the two in sync.)
    if (orderId.Length < 8 && orderId.Length > 0 && orderId.All(char.IsDigit))
    {
        orderId = orderId.PadLeft(8, '0');
    }
    var order = Orders.GetOrder(orderId);
    if (order is null)
    {
        log.Info("GET /orders/{0} 404", orderId);
        return Results.Json(new { error = $"order {orderId} not found" }, statusCode: 404);
    }
    log.Info("GET /orders/{0} 200 status={1}", orderId, order.Status);
    return Results.Json(order);
});

app.MapGet("/orders", (string? status, string? limit) =>
{
    List<Order> result;
    try
    {
        result = Orders.ListOrders(status, int.Parse(limit ?? "50", CultureInfo.InvariantCulture));
    }
    catch (Exception ex) when (ex is ArgumentException or FormatException)
    {
        return Results.Json(new { error = ex.Message }, statusCode: 400);
    }
    log.Info("GET /orders 200 count={0}", result.Count);
    return Results.Json(new { orders = result, count = result.Count });
});

app.MapGet("/report", (string? date) =>
{
    DailyReportResult report;
    try
    {
        report = Orders.DailyReport(date);
    }
    catch (FormatException)
    {
        return Results.Json(new { error = "date must be YYYY-MM-DD" }, statusCode: 400);
    }
    log.Info("GET /report 200 date={0} orders={1} total={2:F2}", report.Date, report.Orders, report.Total);
    return Results.Json(report);
});

// NOTE: monitoring hits GET /orders?limit=1 as a liveness probe because we
// never got around to a proper health endpoint.

LoggingSetup.Setup();
Db.InitDb();
Console.WriteLine($"OrderBase v{AppVersion} listening on {ServiceHost}:{Port} (debug={Debug})");
app.Run();

/// <summary>
/// Exposed so the test project's <c>WebApplicationFactory&lt;Program&gt;</c> can
/// boot the real app in-process. Top-level statements generate an internal
/// Program class, so this makes it public.
/// </summary>
public partial class Program;

using System.Net;
using System.Net.Http.Json;
using System.Text.Json;

using Microsoft.AspNetCore.Mvc.Testing;

using Xunit;

namespace LegacyService.Tests;

// Smoke tests. Thin on purpose -- they check the service turns on.
// (2018-11: the full suite lived in the old repo and never made the move.
// TODO: port the rest of the tests. -- J)

public class SmokeTests : IClassFixture<WebApplicationFactory<Program>>
{
    // Point the app at a scratch database BEFORE the factory ever boots
    // Program.cs -- Db.InitDb() is what actually creates the tables, and it
    // reads Db.DbPath, which is a static field evaluated on first touch. Yes,
    // field-initialization order matters here. No, don't reorder this.
    private static readonly string DbPath = PointAtScratchDb();

    private readonly HttpClient _client;

    public SmokeTests(WebApplicationFactory<Program> factory)
    {
        _client = factory.CreateClient();
    }

    private static string PointAtScratchDb()
    {
        var path = Path.Combine(Path.GetTempPath(), $"orderbase-test-{Guid.NewGuid():N}.db");
        Environment.SetEnvironmentVariable("ORDERBASE_DB", path);
        return path;
    }

    private async Task<JsonElement> CreateOrderAsync()
    {
        var resp = await _client.PostAsync("/orders", JsonContent.Create(new
        {
            customer = "Smoke Test Co",
            items = new[] { new { sku = "SKU-0001", qty = 1, unit_price = 19.99 } },
        }));
        Assert.Equal(HttpStatusCode.Created, resp.StatusCode);
        return await resp.Content.ReadFromJsonAsync<JsonElement>();
    }

    [Fact]
    public async Task CreateOrder_ReturnsExpectedShape()
    {
        var body = await CreateOrderAsync();
        Assert.Equal(8, body.GetProperty("id").GetString()!.Length);
        Assert.Equal("NEW", body.GetProperty("status").GetString());
        Assert.Equal(19.99, body.GetProperty("total").GetDouble());
    }

    [Fact]
    public async Task GetOrder_ReturnsCustomer()
    {
        var created = await CreateOrderAsync();
        var orderId = created.GetProperty("id").GetString();

        var resp = await _client.GetAsync($"/orders/{orderId}");
        Assert.Equal(HttpStatusCode.OK, resp.StatusCode);
        var body = await resp.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal("Smoke Test Co", body.GetProperty("customer").GetString());
    }

    [Fact]
    public async Task ListOrders_IncludesCreatedOrder()
    {
        var created = await CreateOrderAsync();
        var orderId = created.GetProperty("id").GetString();

        var resp = await _client.GetAsync("/orders");
        Assert.Equal(HttpStatusCode.OK, resp.StatusCode);
        var body = await resp.Content.ReadFromJsonAsync<JsonElement>();
        var ids = body.GetProperty("orders").EnumerateArray()
            .Select(o => o.GetProperty("id").GetString());
        Assert.Contains(orderId, ids);
    }
}

using System.Net;
using System.Net.Http.Json;
using System.Text.Json;

using ExpenseCategoriser;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace ExpenseCategoriser.Tests;

/// <summary>
/// Layer 2 — API contract tests. Boots the real app in-process with a fake LLM.
/// </summary>
/// <remarks>
/// These check the shape of the HTTP contract, not the quality of the answer:
/// status codes, response fields, and — most importantly — that a contract
/// violation from the model becomes a 502 rather than a 500 or a crash.
/// Still no key, still free.
/// </remarks>
public class ApiTests
{
    private static WebApplicationFactory<Program> AppWith(ILlmClient client) =>
        new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            builder.ConfigureServices(services =>
            {
                services.AddSingleton(client);
            });
        });

    [Fact]
    public async Task Health_ReturnsOk()
    {
        using var app = AppWith(FakeLlmClient.Returning("Other", 0.9));
        using var http = app.CreateClient();

        var response = await http.GetAsync("/health", TestContext.Current.CancellationToken);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task Categories_ReturnsTheCanonicalList()
    {
        using var app = AppWith(FakeLlmClient.Returning("Other", 0.9));
        using var http = app.CreateClient();

        var payload = await http.GetFromJsonAsync<JsonElement>(
            "/categories", TestContext.Current.CancellationToken);

        var categories = payload.GetProperty("categories")
            .EnumerateArray().Select(e => e.GetString()).ToArray();

        Assert.Equal(Categories.Canonical, categories);
    }

    [Fact]
    public async Task Categorise_ReturnsTheModelsAnswer()
    {
        using var app = AppWith(FakeLlmClient.Returning("Food & Dining", 0.95));
        using var http = app.CreateClient();

        var response = await http.PostAsJsonAsync(
            "/categorise",
            new { description = "Starbucks Coffee", amount = 5.45 },
            TestContext.Current.CancellationToken);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var body = await response.Content.ReadFromJsonAsync<CategorisationOut>(
            TestContext.Current.CancellationToken);

        Assert.Equal("Food & Dining", body!.Category);
        Assert.False(body.UsedFallback);
    }

    [Fact]
    public async Task Categorise_LowConfidenceIsStillA200()
    {
        // The fallback is a successful response. The client needs to know the
        // model wasn't confident — not that the request failed.
        using var app = AppWith(FakeLlmClient.Returning("Travel", 0.2));
        using var http = app.CreateClient();

        var response = await http.PostAsJsonAsync(
            "/categorise",
            new { description = "Something ambiguous", amount = 12.0 },
            TestContext.Current.CancellationToken);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var body = await response.Content.ReadFromJsonAsync<CategorisationOut>(
            TestContext.Current.CancellationToken);

        Assert.Equal("Other", body!.Category);
        Assert.True(body.UsedFallback);
    }

    [Fact]
    public async Task Categorise_ContractViolationBecomes502()
    {
        // Not a 500. The service is healthy; the model misbehaved. This
        // distinction is what lets the CE pipeline alert on model drift without
        // drowning in ordinary server errors.
        using var app = AppWith(new FakeLlmClient("this is not json"));
        using var http = app.CreateClient();

        var response = await http.PostAsJsonAsync(
            "/categorise",
            new { description = "Starbucks", amount = 5.45 },
            TestContext.Current.CancellationToken);

        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
    }

    [Fact]
    public async Task Categorise_MissingApiKeyBecomes500()
    {
        using var app = AppWith(new ThrowingLlmClient(
            new InvalidOperationException("GOOGLE_API_KEY is not set.")));
        using var http = app.CreateClient();

        var response = await http.PostAsJsonAsync(
            "/categorise",
            new { description = "Starbucks", amount = 5.45 },
            TestContext.Current.CancellationToken);

        Assert.Equal(HttpStatusCode.InternalServerError, response.StatusCode);
    }

    [Fact]
    public async Task Categorise_RejectsEmptyDescription()
    {
        using var app = AppWith(FakeLlmClient.Returning("Other", 0.9));
        using var http = app.CreateClient();

        var response = await http.PostAsJsonAsync(
            "/categorise",
            new { description = "", amount = 5.45 },
            TestContext.Current.CancellationToken);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }
}

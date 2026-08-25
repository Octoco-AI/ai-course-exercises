using System.Diagnostics;

using ExpenseCategoriser;

// ASP.NET Core Minimal API exposing the categoriser.
//
// Run locally:
//     dotnet run --project src/ExpenseCategoriser
//
// Test:
//     curl -X POST http://localhost:5080/categorise \
//          -H "Content-Type: application/json" \
//          -d '{"description": "Whole Foods", "amount": 45.23}'

var builder = WebApplication.CreateBuilder(args);

DotEnv.Load();

// One client for the process, so repeated requests reuse the HTTP connection.
// Registered through the interface so the tests can swap in a fake.
builder.Services.AddSingleton<ILlmClient>(_ => new GeminiClient());

var app = builder.Build();

/// Liveness probe.
app.MapGet("/health", () => Results.Ok(new { status = "ok" }));

/// The canonical category list. Useful for API consumers and tests.
app.MapGet("/categories", () => Results.Ok(new { categories = Categories.Canonical }));

// Categorise a single expense.
//
// Returns 502 if the LLM returns malformed output (contract violation). The
// confidence-threshold fallback (returning "Other" with used_fallback=true) is a
// SUCCESSFUL response, not an error — the client needs to know the model wasn't
// confident, not that everything failed.
app.MapPost("/categorise", async (
    ExpenseIn expense,
    ILlmClient client,
    ILoggerFactory loggerFactory,
    CancellationToken cancellationToken) =>
{
    var logger = loggerFactory.CreateLogger("ExpenseCategoriser.Api");

    if (string.IsNullOrWhiteSpace(expense.Description) || expense.Description.Length > 500)
    {
        return Results.ValidationProblem(new Dictionary<string, string[]>
        {
            ["description"] = ["description must be between 1 and 500 characters"],
        });
    }

    var stopwatch = Stopwatch.StartNew();
    CategorisationOut result;

    try
    {
        result = await Core.CategoriseAsync(
            expense.Description, expense.Amount, client, cancellationToken: cancellationToken);
    }
    catch (ContractViolationException ex)
    {
        // Worth logging loudly — this is the "model started misbehaving" signal
        // the CE pipeline watches for.
        logger.LogWarning("Contract violation from LLM: {Message}", ex.Message);
        return Results.Problem(
            detail: $"LLM returned unparseable output: {ex.Message}",
            statusCode: StatusCodes.Status502BadGateway);
    }
    catch (InvalidOperationException ex)
    {
        // Missing API key, etc. — configuration problem.
        return Results.Problem(detail: ex.Message, statusCode: StatusCodes.Status500InternalServerError);
    }

    stopwatch.Stop();
    logger.LogInformation(
        "categorised {Description} -> {Category} (conf={Confidence:F2}, fallback={UsedFallback}, {Elapsed}ms)",
        expense.Description, result.Category, result.Confidence, result.UsedFallback,
        stopwatch.ElapsedMilliseconds);

    return Results.Ok(result);
});

app.Run();

/// <summary>
/// Exposed so the test project's <c>WebApplicationFactory&lt;Program&gt;</c> can
/// boot the real app in-process. Top-level statements generate an internal
/// Program class, so this makes it public.
/// </summary>
public partial class Program;

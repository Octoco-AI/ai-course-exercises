using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Serialization;

using ExpenseCategoriser;
using Xunit;

namespace ExpenseCategoriser.Tests.Evals;

/// <summary>
/// Layer 3 — the eval suite. This is the "third layer" from Herman's blog.
/// </summary>
/// <remarks>
/// <para>Run locally:</para>
/// <code>dotnet test --filter "Category=Evals"</code>
/// <para>In CI:</para>
/// <code>.github/workflows/evals.yml runs this on every PR with the GOOGLE_API_KEY
/// secret. A failing eval blocks the merge.</code>
/// <para>What's being tested:</para>
/// <list type="number">
/// <item><b>Acceptance accuracy</b> — across the golden dataset, the rate of
/// "chose an acceptable category" must be at least <see cref="AccuracyThreshold"/>.</item>
/// <item><b>Zero catastrophics</b> — no case may be categorised as one of its
/// explicitly unacceptable categories. This is a hard gate.</item>
/// <item><b>Latency</b> — p95 per-request latency below a ceiling.</item>
/// <item><b>Confidence distribution</b> — most high-confidence predictions should
/// actually be correct (rough calibration check).</item>
/// </list>
/// <para>
/// Costs real money: every case is a Gemini call. Keep the dataset small (~20
/// cases) for the fast-feedback CI loop; expand to 100+ for nightly runs.
/// </para>
/// <para>
/// The thresholds and the dataset are identical to the Python and TypeScript
/// versions of this exercise, on purpose — a cross-language debrief is only
/// interesting if everyone is measuring the same thing.
/// </para>
/// </remarks>
[Trait("Category", "Evals")]
public class CategorisationQualityTests : IAsyncLifetime
{
    // ---- thresholds (the spec's acceptance criteria turned into CE gates) ----

    private const double AccuracyThreshold = 0.85;        // >= 85% of cases must be acceptable
    private const int CatastrophicThreshold = 0;          // ZERO cases may hit an unacceptable category
    private const double P95LatencySeconds = 3.0;         // generous; tighten once we have a baseline
    private const double MinHighConfAcceptable = 0.90;    // of high-conf (>=0.8), at least 90% acceptable

    private List<EvalResult> _results = [];
    private bool _skipped;

    /// <summary>
    /// Run every case through the real categoriser, once, and cache the results.
    /// This is the only expensive step — all four gates below read from it, so
    /// they share a single full pass of the dataset.
    /// </summary>
    public async ValueTask InitializeAsync()
    {
        DotEnv.Load(FindRepoRoot());

        if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("GOOGLE_API_KEY")))
        {
            // Explicit opt-in required. A missing key is a skip, not a failure —
            // otherwise every developer without a key sees a red suite.
            _skipped = true;
            return;
        }

        var cases = LoadDataset();
        using var client = new GeminiClient();

        foreach (var evalCase in cases)
        {
            var stopwatch = Stopwatch.StartNew();
            try
            {
                var output = await Core.CategoriseAsync(evalCase.Description, evalCase.Amount, client);
                stopwatch.Stop();
                _results.Add(new EvalResult(evalCase, output, stopwatch.Elapsed.TotalSeconds, null));
            }
            catch (Exception ex)
            {
                stopwatch.Stop();
                // Record and keep going — one failure shouldn't hide the rest.
                _results.Add(new EvalResult(evalCase, null, stopwatch.Elapsed.TotalSeconds, ex.Message));
            }
        }
    }

    public ValueTask DisposeAsync() => ValueTask.CompletedTask;

    private void SkipIfNoKey() =>
        Assert.SkipWhen(_skipped, "GOOGLE_API_KEY not set — eval suite skipped (explicit opt-in required)");

    // ---- the gates ----------------------------------------------------------

    [Fact]
    public void AccuracyAboveThreshold()
    {
        SkipIfNoKey();

        var total = _results.Count;
        var acceptable = _results.Count(r => r.IsAcceptable);
        var accuracy = (double)acceptable / total;

        var failures = _results
            .Where(r => !r.IsAcceptable)
            .Select(r => $"  - '{r.Case.Description}' -> {r.Output?.Category ?? "ERROR"} "
                       + $"(acceptable: {string.Join(", ", r.Case.Acceptable)})");

        Assert.True(accuracy >= AccuracyThreshold,
            $"Accuracy {accuracy:P1} below threshold {AccuracyThreshold:P1}.\n"
            + "Failing cases:\n" + string.Join("\n", failures));
    }

    [Fact]
    public void ZeroCatastrophicFailures()
    {
        SkipIfNoKey();

        var catastrophics = _results.Where(r => r.IsCatastrophic).ToList();

        Assert.True(catastrophics.Count <= CatastrophicThreshold,
            $"{catastrophics.Count} catastrophic failure(s):\n"
            + string.Join("\n", catastrophics.Select(r =>
                $"  - '{r.Case.Description}' -> {r.Output!.Category} "
                + $"(explicitly unacceptable: {string.Join(", ", r.Case.Unacceptable)})")));
    }

    [Fact]
    public void P95LatencyBelowCeiling()
    {
        SkipIfNoKey();

        var latencies = _results.Select(r => r.Elapsed).OrderBy(x => x).ToList();
        var p95 = latencies[(int)(latencies.Count * 0.95)];

        Assert.True(p95 <= P95LatencySeconds,
            $"p95 latency {p95:F2}s exceeds ceiling {P95LatencySeconds}s. "
            + $"mean={latencies.Average():F2}s median={latencies[latencies.Count / 2]:F2}s "
            + $"max={latencies.Max():F2}s");
    }

    [Fact]
    public void HighConfidencePredictionsAreReliable()
    {
        SkipIfNoKey();

        var highConf = _results.Where(r => r.Output is { Confidence: >= 0.8 }).ToList();
        Assert.SkipWhen(highConf.Count == 0, "No high-confidence predictions in this run");

        var acceptable = highConf.Count(r => r.IsAcceptable);
        var rate = (double)acceptable / highConf.Count;

        Assert.True(rate >= MinHighConfAcceptable,
            $"High-confidence acceptance rate {rate:P1} below threshold "
            + $"{MinHighConfAcceptable:P1}. The model is overconfident.");
    }

    /// <summary>
    /// Not a gate — prints a summary so facilitators can eyeball what the model
    /// actually did. Always passes.
    /// </summary>
    [Fact]
    public void PrintEvalSummary()
    {
        SkipIfNoKey();

        var total = _results.Count;
        var latencies = _results.Select(r => r.Elapsed).OrderBy(x => x).ToList();

        Console.WriteLine("\n=== Eval summary ===");
        Console.WriteLine($"  total cases:       {total}");
        Console.WriteLine($"  acceptable:        {_results.Count(r => r.IsAcceptable)} "
                        + $"({(double)_results.Count(r => r.IsAcceptable) / total:P1})");
        Console.WriteLine($"  catastrophic:      {_results.Count(r => r.IsCatastrophic)}");
        Console.WriteLine($"  errors:            {_results.Count(r => r.Output is null)}");
        Console.WriteLine($"  latency p50/p95:   {latencies[latencies.Count / 2]:F2}s / "
                        + $"{latencies[(int)(latencies.Count * 0.95)]:F2}s");
        Console.WriteLine();
    }

    // ---- dataset ------------------------------------------------------------

    private static List<EvalCase> LoadDataset()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "Evals", "eval_dataset.json");
        var json = File.ReadAllText(path);

        return JsonSerializer.Deserialize<List<EvalCase>>(json)
               ?? throw new InvalidOperationException($"eval dataset at {path} is empty or unparseable");
    }

    /// <summary>Walk up to the directory holding a .env, so tests find it from bin/.</summary>
    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (File.Exists(Path.Combine(dir.FullName, ".env"))) return dir.FullName;
            dir = dir.Parent;
        }
        return Directory.GetCurrentDirectory();
    }

    private sealed record EvalCase(
        [property: JsonPropertyName("description")] string Description,
        [property: JsonPropertyName("amount")] double Amount,
        [property: JsonPropertyName("acceptable")] string[] Acceptable,
        [property: JsonPropertyName("unacceptable")] string[] Unacceptable);

    private sealed record EvalResult(
        EvalCase Case, CategorisationOut? Output, double Elapsed, string? Error)
    {
        public bool IsAcceptable =>
            Output is not null && Case.Acceptable.Contains(Output.Category, StringComparer.Ordinal);

        public bool IsCatastrophic =>
            Output is not null && Case.Unacceptable.Contains(Output.Category, StringComparer.Ordinal);
    }
}

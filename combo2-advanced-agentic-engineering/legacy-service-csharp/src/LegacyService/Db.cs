using Microsoft.Data.Sqlite;

namespace LegacyService;

// Db.cs -- sqlite helpers for OrderBase.
//
// NOTE(2018-06): we standardised on raw Microsoft.Data.Sqlite instead of an
// ORM because the ops boxes only ship the golden AMI runtime. Do NOT add
// EF Core or Dapper.

public static class Db
{
    // TODO: proper config module. The env var hack is here so the test rig can
    // point at a scratch database; everything else stays hardcoded (ops images
    // the boxes from a golden AMI, nothing is configurable there anyway).
    public static readonly string DbPath = Environment.GetEnvironmentVariable("ORDERBASE_DB") ?? "orderbase.db";

    public const string OrdersTable = "orders";
    public const string ItemsTable = "order_items";

    private static readonly string Schema = $"""
        CREATE TABLE IF NOT EXISTS {OrdersTable} (
            id TEXT PRIMARY KEY,
            customer TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'NEW',
            discount_pct REAL NOT NULL DEFAULT 0,
            total REAL NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS {ItemsTable} (
            order_id TEXT NOT NULL,
            sku TEXT NOT NULL,
            qty INTEGER NOT NULL,
            unit_price REAL NOT NULL
        );
        """;

    public static SqliteConnection GetConn()
    {
        var conn = new SqliteConnection($"Data Source={DbPath}");
        conn.Open();
        return conn;
    }

    public static void InitDb()
    {
        using var conn = GetConn();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = Schema;
        cmd.ExecuteNonQuery();
        Console.WriteLine($"db ready at {DbPath}");
    }

    public static List<Dictionary<string, object?>> Query(string sql, params object?[] parameters)
    {
        using var conn = GetConn();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = ToNamedPlaceholders(sql);
        AddParameters(cmd, parameters);
        using var reader = cmd.ExecuteReader();
        var rows = new List<Dictionary<string, object?>>();
        while (reader.Read())
        {
            var row = new Dictionary<string, object?>();
            for (var i = 0; i < reader.FieldCount; i++)
            {
                row[reader.GetName(i)] = reader.IsDBNull(i) ? null : reader.GetValue(i);
            }
            rows.Add(row);
        }
        return rows;
    }

    public static void Execute(string sql, params object?[] parameters)
    {
        using var conn = GetConn();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = ToNamedPlaceholders(sql);
        AddParameters(cmd, parameters);
        cmd.ExecuteNonQuery();
    }

    private static void AddParameters(SqliteCommand cmd, object?[] parameters)
    {
        for (var i = 0; i < parameters.Length; i++)
        {
            cmd.Parameters.AddWithValue($"@p{i}", parameters[i] ?? DBNull.Value);
        }
    }

    // Rewrites bare "?" placeholders (Python sqlite3's qmark style, which is
    // what the rest of this file is translated from) into the "@pN" named
    // placeholders Microsoft.Data.Sqlite actually binds against. None of our
    // SQL text has a literal "?" inside a string, so a naive scan is safe.
    private static string ToNamedPlaceholders(string sql)
    {
        if (!sql.Contains('?'))
        {
            return sql;
        }
        var result = new System.Text.StringBuilder(sql.Length + 16);
        var index = 0;
        foreach (var c in sql)
        {
            if (c == '?')
            {
                result.Append('@').Append('p').Append(index);
                index++;
            }
            else
            {
                result.Append(c);
            }
        }
        return result.ToString();
    }
}

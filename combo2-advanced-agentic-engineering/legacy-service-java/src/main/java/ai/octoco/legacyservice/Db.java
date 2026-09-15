package ai.octoco.legacyservice;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Db.java -- sqlite helpers for OrderBase.
 *
 * <p>NOTE(2018-06): we standardised on raw JDBC ({@code sqlite-jdbc}) instead
 * of an ORM because the ops boxes only ship the golden AMI runtime. Do NOT
 * add Spring Data JPA or Hibernate.
 */
public final class Db {

    // TODO: proper config module. The env var hack is here so the test rig can
    // point at a scratch database; everything else stays hardcoded (ops images
    // the boxes from a golden AMI, nothing is configurable there anyway).
    //
    // Java can't mutate its own process environment the way the C# port's test
    // rig calls Environment.SetEnvironmentVariable, so tests fall back to a
    // system property of the same name -- see LegacyServiceSmokeTests.
    public static final String DB_PATH = resolveDbPath();

    public static final String ORDERS_TABLE = "orders";
    public static final String ITEMS_TABLE = "order_items";

    private static final String SCHEMA = """
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                customer TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'NEW',
                discount_pct REAL NOT NULL DEFAULT 0,
                total REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS order_items (
                order_id TEXT NOT NULL,
                sku TEXT NOT NULL,
                qty INTEGER NOT NULL,
                unit_price REAL NOT NULL
            );
            """;

    private Db() {}

    private static String resolveDbPath() {
        String fromEnv = System.getenv("ORDERBASE_DB");
        if (fromEnv != null && !fromEnv.isBlank()) {
            return fromEnv;
        }
        String fromProperty = System.getProperty("ORDERBASE_DB");
        if (fromProperty != null && !fromProperty.isBlank()) {
            return fromProperty;
        }
        return "orderbase.db";
    }

    public static Connection getConn() {
        try {
            return DriverManager.getConnection("jdbc:sqlite:" + DB_PATH);
        } catch (SQLException e) {
            throw new IllegalStateException("could not open " + DB_PATH, e);
        }
    }

    public static void initDb() {
        try (Connection conn = getConn(); Statement stmt = conn.createStatement()) {
            for (String statement : SCHEMA.split(";")) {
                if (!statement.isBlank()) {
                    stmt.execute(statement);
                }
            }
            System.out.println("db ready at " + DB_PATH);
        } catch (SQLException e) {
            throw new IllegalStateException("could not initialise " + DB_PATH, e);
        }
    }

    /** Run a SELECT and return each row as an ordered column-name -> value map. */
    public static List<Map<String, Object>> query(String sql, Object... parameters) {
        try (Connection conn = getConn();
                PreparedStatement stmt = conn.prepareStatement(sql)) {
            bind(stmt, parameters);
            try (ResultSet rs = stmt.executeQuery()) {
                return readRows(rs);
            }
        } catch (SQLException e) {
            throw new IllegalStateException("query failed: " + sql, e);
        }
    }

    /** Run an INSERT/UPDATE/DELETE. */
    public static void execute(String sql, Object... parameters) {
        try (Connection conn = getConn();
                PreparedStatement stmt = conn.prepareStatement(sql)) {
            bind(stmt, parameters);
            stmt.executeUpdate();
        } catch (SQLException e) {
            throw new IllegalStateException("execute failed: " + sql, e);
        }
    }

    private static void bind(PreparedStatement stmt, Object[] parameters) throws SQLException {
        for (int i = 0; i < parameters.length; i++) {
            stmt.setObject(i + 1, parameters[i]);
        }
    }

    private static List<Map<String, Object>> readRows(ResultSet rs) throws SQLException {
        ResultSetMetaData meta = rs.getMetaData();
        int columnCount = meta.getColumnCount();
        List<Map<String, Object>> rows = new ArrayList<>();
        while (rs.next()) {
            Map<String, Object> row = new LinkedHashMap<>();
            for (int i = 1; i <= columnCount; i++) {
                row.put(meta.getColumnLabel(i), rs.getObject(i));
            }
            rows.add(row);
        }
        return rows;
    }
}

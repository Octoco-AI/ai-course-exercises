package ai.octoco.legacyservice;

import java.util.LinkedHashMap;
import java.util.Map;

public class DailyReportResult {
    public String date = "";
    public int orders;
    public double total;
    public Map<String, StatusBucket> byStatus = new LinkedHashMap<>();
}

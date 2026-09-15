package ai.octoco.legacyservice;

import java.util.ArrayList;
import java.util.List;

// The order itself. Mutable and reference-typed on purpose -- see the
// orderCache comment on Orders.getOrder below. NOT a record: a record's
// value-equality and copy-on-write "with" semantics would quietly fix the
// cache's reference-bleed bug.
public class Order {
    public String id = "";
    public String customer = "";
    public String status = "NEW";
    public double discountPct;
    public double total;
    public String createdAt = "";
    public List<OrderItem> items = new ArrayList<>();
}

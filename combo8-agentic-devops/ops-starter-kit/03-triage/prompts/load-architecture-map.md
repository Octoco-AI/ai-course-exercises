# Prompt — load an architecture map as triage context

Cross-stack triage goes wrong when the agent does not know what talks to what: it chases the node because the node was loud. An architecture map fixes that, as long as you load **the neighbourhood of the affected service** and not the whole estate.

## Get the map out

Most teams already have one somewhere: a graph database, a CMDB, a service catalogue, or the Argo CD application list plus the Helm values. Export **nodes and edges** with `kind`, `name`, `owner`, host or cluster, and the edge type. The synthetic example is `sample-data/architecture-map.json`.

For a graph database (Cypher), take two hops around the affected service:

```cypher
MATCH p = (s {name: $service})-[*1..2]-(n)
RETURN p
LIMIT 200
```

Export the result as JSON, or as two CSVs (`nodes.csv`, `edges.csv`). VERIFY: export procedures differ by product and plugin (for example APOC's JSON export). Use whatever your graph database offers, read-only. If you have no graph store, a hand-written YAML of the same shape is fine to start with.

## The prompt

---

Read the architecture map at **<PATH_TO_EXPORT>** (exported **<EXPORT_DATE>**). The affected service is **<SERVICE_NAME>**.

1. Extract only the nodes within **two hops** of <SERVICE_NAME>. Discard the rest. Do not summarise nodes you discarded.
2. Write the neighbourhood as a compact adjacency list, one line per edge:
   `orders-api --READS_WRITES--> ordersdb (db01.example.internal, max_connections 300)`
3. Group the nodes by layer: **network** (load balancers, ingress, nodes, DNS), **app** (deployments, jobs, queues), **db** (databases, caches, storage). These groups are what each investigator sub-agent is handed.
4. Flag staleness. If the export is more than 30 days older than the incident, say so at the top. Treat any edge the evidence contradicts as suspect rather than true.
5. List the owners of each node in the neighbourhood. The triage note needs to know who to ask.

Output the adjacency list, the three layer groups and the owner list. Nothing else. Keep it under 60 lines. This block goes into the case file and is passed to every investigator.

---

## Why two hops

One hop misses shared dependencies: two services hammering the same database. Three hops usually pulls in half the estate, and the investigators start reasoning about systems that have nothing to do with the incident. Two is the default. Widen it only with a reason you can write down.

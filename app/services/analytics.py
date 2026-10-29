from pymongo import DESCENDING

from ..database import get_issues


# Helper: pipeline stages to $group by a field and $sort by count descending
def _count_by(field):
    return [
        {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
        {"$sort":  {"count": -1, "_id": 1}},
    ]


# Count issues grouped by a single field
def count_by_field(field_name):
    rows = get_issues().aggregate(_count_by(field_name))
    return [{field_name: r["_id"], "count": r["count"]} for r in rows]


# Multi-facet dashboard summary: runs 5 sub-pipelines in a single pass over the collection
def summary():
    pipeline = [{"$facet": {
        "total":       [{"$count": "n"}],
        "by_category": _count_by("category"),
        "by_status":   _count_by("status"),
        "by_priority": _count_by("priority"),
        "by_city":     _count_by("location.city"),
    }}]
    result = next(get_issues().aggregate(pipeline), {})

    def fmt(rows, key):
        return [{key: r["_id"], "count": r["count"]} for r in rows]

    return {
        "total_issues": result["total"][0]["n"] if result.get("total") else 0,
        "by_category":  fmt(result.get("by_category", []), "category"),
        "by_status":    fmt(result.get("by_status",   []), "status"),
        "by_priority":  fmt(result.get("by_priority", []), "priority"),
        "by_city":      fmt(result.get("by_city",     []), "city"),
    }


# Calculate average hours taken to resolve issues per category
def resolution_time():
    pipeline = [
        {"$match": {"status": "resolved"}},
        {"$project": {"category": 1, "hours": {"$divide": [
            {"$subtract": [{"$last": "$status_history.changed_at"}, "$created_at"]},
            3_600_000,  # convert milliseconds to hours
        ]}}},
        {"$group": {"_id": "$category", "resolved_count": {"$sum": 1}, "avg_hours": {"$avg": "$hours"}}},
        {"$project": {"_id": 0, "category": "$_id", "resolved_count": 1, "avg_hours": {"$round": ["$avg_hours", 2]}}},
        {"$sort": {"avg_hours": -1}},
    ]
    return list(get_issues().aggregate(pipeline))


# Inspect query execution plan (compare indexed scan vs forced collection scan)
def explain_query(filter_dict, force_collection_scan=False):
    cursor = get_issues().find(filter_dict).sort([("created_at", DESCENDING)])
    if force_collection_scan:
        cursor = cursor.hint([("$natural", 1)])  # force COLLSCAN
    plan  = cursor.explain()
    stats = plan["executionStats"]
    stages, indexes = [], []
    _walk(plan["queryPlanner"]["winningPlan"], stages, indexes)
    return {
        "filter":                 filter_dict,
        "forced_collection_scan": force_collection_scan,
        "plan_stages":            stages,
        "indexes_used":           indexes,
        "n_returned":             stats["nReturned"],
        "total_keys_examined":    stats["totalKeysExamined"],
        "total_docs_examined":    stats["totalDocsExamined"],
        "execution_time_ms":      stats["executionTimeMillis"],
    }


# Helper: traverse plan tree to collect stage names and index names
def _walk(node, stages, indexes):
    if isinstance(node, dict):
        if "stage"     in node: stages.append(node["stage"])
        if "indexName" in node: indexes.append(node["indexName"])
        for k, v in node.items():
            if k != "slotBasedPlan":
                _walk(v, stages, indexes)
    elif isinstance(node, list):
        for item in node:
            _walk(item, stages, indexes)

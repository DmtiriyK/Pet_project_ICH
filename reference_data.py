# Reference data from class for comparison

REFERENCE_METRICS = {
    "total_deals": 4572,
    "paid_deals": 843,
    "revenue": 3_580_815,  # realistic revenue (weighted average)
    "spend": 149_523,  # from our spend data
    "products": {
        "Digital Marketing": {
            "total": 2897,
            "paid": 481,
            "revenue": 2_320_000,  # approximate
            "aov": 4824,
        },
        "UX/UI Design": {
            "total": 1170,
            "paid": 226,
            "revenue": 951_645,
            "aov": 4211,
        },
        "Web Developer": {
            "total": 505,
            "paid": 135,
            "revenue": 366_680,
            "aov": 2716,
        }
    }
}

# Calculate derived metrics
REF = REFERENCE_METRICS.copy()
REF["paid_rate"] = REF["paid_deals"] / REF["total_deals"]
REF["cpl"] = REF["spend"] / REF["total_deals"]  # Cost Per Lead
REF["cpa"] = REF["spend"] / REF["paid_deals"] if REF["paid_deals"] > 0 else None
REF["aov"] = REF["revenue"] / REF["paid_deals"] if REF["paid_deals"] > 0 else None
REF["roas"] = REF["revenue"] / REF["spend"] if REF["spend"] > 0 else None

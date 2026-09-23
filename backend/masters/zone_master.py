ZONE_A = {"ahmedabad", "kolkata", "howrah", "north 24 parganas", "hyderabad", "secunderabad", "vadodara", "surat", "delhi", "ncr", "mumbai", "navi mumbai", "thane", "kalyan"}
ZONE_C = {"goa", "uttarakhand", "tamil nadu", "sikkim", "chandigarh", "chhattisgarh", "punjab", "andhra pradesh"}
ZONE_D = {"andaman & nicobar islands", "andaman and nicobar islands", "bihar", "lakshadweep", "tripura", "manipur", "jammu & kashmir", "jammu and kashmir", "mizoram", "odisha", "himachal pradesh", "arunachal pradesh", "meghalaya", "jharkhand", "nagaland"}

def resolve_zone(text: str) -> str:
    t = (text or "").lower()
    if "pan india" in t:
        return "Pan India"
    hits = set()
    if any(x in t for x in ZONE_A): hits.add("Zone A")
    if any(x in t for x in ZONE_C): hits.add("Zone C")
    if any(x in t for x in ZONE_D): hits.add("Zone D")
    if len(hits) == 1: return next(iter(hits))
    if len(hits) > 1: return "Pan India"
    return "Pan India"

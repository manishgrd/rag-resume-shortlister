from typing import List, Dict

# Adjustable weights for each criterion
WEIGHTS = {
    "Degree & Experience (CS Master OR CS Bachelor + 2y)": 0.25,
    "Python & OCR (>=5 years)": 0.35,
    "OOP Language: C++ or Java": 0.20,
    "SQL & Cloud (Azure/AWS/GCP)": 0.20,
}

def normalize_score(x):
    try:
        val = float(x)
    except Exception:
        return 0.0
    if val < 0: return 0.0
    if val > 100: return 100.0
    return val

def compute_weighted_scores(per_criterion: List[Dict]):
    total = 0.0
    details = []
    for item in per_criterion:
        name = item.get("criterion")
        score = normalize_score(item.get("score_percent", 0))
        w = WEIGHTS.get(name, 0.0)
        total += (score * w)
        details.append({"criterion": name, "score": score, "weight": w})
    overall_percent = round(total, 2)
    # Basic summary
    strengths = [d["criterion"] for d in details if d["score"] >= 70]
    gaps = [d["criterion"] for d in details if d["score"] < 70]
    summary = {
        "strengths": strengths,
        "gaps": gaps,
        "overall_comment": (
            "Strong match" if overall_percent >= 75 else
            "Moderate match" if overall_percent >= 55 else
            "Weak match"
        )
    }
    return {"overall_percent": overall_percent, "details": details, "weights": WEIGHTS, "summary": summary}

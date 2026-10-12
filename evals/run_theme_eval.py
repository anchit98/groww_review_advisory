"""Offline eval of a stored Phase 2 run (no API calls).
Labels (supporting-review relevance, uncovered-negative sample) were assigned by Claude acting as
annotator, single pass, and are listed below so they can be audited / overridden by a human.
Run: python run_theme_eval.py
"""
import json, random, pathlib
RUN = pathlib.Path(__file__).resolve().parent.parent / "phase-2/output/phase2-2026-05-21-a592cc6c"
cr = json.load(open(RUN/"consolidation_response.json"))
work = json.load(open(RUN/"working_review_set.json"))
meta = json.load(open(RUN/"run_metadata.json"))
pulse = json.load(open(RUN/"weekly_pulse.json"))
by_id = {r["review_id_hash"]: r for r in work}

# Reviews whose assigned theme is NOT a good fit (all other supporting reviews judged relevant)
IRRELEVANT = {
 "theme_1": {"964ac4", "916897"},                                   # refund/sell issue; fraud rant
 "theme_2": {"18f7ed","36dcb0","39dc50","5de93e","950b53","951568","a2fc53","a6afcd","ca7486","f2e614","a9d6cb"},  # brokerage/charges, not technical
 "theme_4": {"116a88"},                                             # F&O feature request
}
PARTIAL = {"theme_2": {"721965", "f23829"}}                         # vague 'unreliable' / mixed interface+brokerage

print("== Precision of theme assignment (supporting reviews)")
tot=ok=ok_lenient=0
for t in cr["final_themes"]:
    ids=t["supporting_review_ids"]; bad={i for i in ids if i[:6] in IRRELEVANT.get(t["final_theme_id"],set())}
    part={i for i in ids if i[:6] in PARTIAL.get(t["final_theme_id"],set())}
    good=len(ids)-len(bad)-len(part)
    tot+=len(ids); ok+=good; ok_lenient+=good+len(part)
    print(f'{t["final_theme_id"]} {t["final_theme_name"]:40s} n={len(ids):2d} strict={good/len(ids):.0%} lenient={(good+len(part))/len(ids):.0%}')
print(f"overall strict={ok}/{tot}={ok/tot:.1%} lenient={ok_lenient}/{tot}={ok_lenient/tot:.1%}")

print("\n== Duplication across themes")
from collections import Counter
c=Counter(i for t in cr["final_themes"] for i in t["supporting_review_ids"])
dup=[i for i,v in c.items() if v>1]
print(f"{len(dup)} review IDs appear in >1 theme; unique supported reviews={len(c)} of {tot} slots")

print("\n== Coverage of unexplained negative reviews (random sample, seed=7, n=40, 1 vague excluded)")
UNCOVERED = {"4cb6a6":"login/KYC/onboarding","7cc904":"order execution/limit-GTT","17b0d8":"mis-selling/trust","52577f":"funds/withdrawal",
 "d4de68":"trust (vague)","da0b62":"funds/withdrawal","5d8da7":"data accuracy","2560fb":"privacy","e8db5d":"MF settlement/holiday",
 "2ae887":"MF consent/behaviour","6a8f10":"trust/cheating","ae7cdc":"login/KYC/onboarding","55af62":"funds/withdrawal/trust",
 "2d22f2":"MF expense ratio","27eb18":"login/KYC/onboarding","7b86f5":"data accuracy"}
VAGUE={"88b231"}
neg=[r for r in work if r["rating"]<=2 and r["review_id_hash"] not in c]
random.seed(7); s=random.sample(neg,40)
cov=sum(1 for r in s if r["review_id_hash"][:6] not in UNCOVERED and r["review_id_hash"][:6] not in VAGUE)
den=40-len(VAGUE)
print(f"fit one of the 5 final themes: {cov}/{den}={cov/den:.0%}; uncovered {len(UNCOVERED)}/{den}")
print(Counter(UNCOVERED.values()).most_common())

print("\n== Pipeline sampling / reporting")
rc=meta["review_counts"]
print(f"reviews analysed vs ingested: {rc['working_set_reviews']}/{rc['normalized_reviews']}; discovery saw {rc['discovery_evidence_reviews']} ({rc['discovery_evidence_reviews']/rc['normalized_reviews']:.1%} of ingested)")
print(f"final themes={rc['final_themes']}, themes surfaced in weekly pulse={len(pulse['top_themes'])}")

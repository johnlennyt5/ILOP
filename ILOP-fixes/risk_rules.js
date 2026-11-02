var v = (typeof vars !== "undefined" && vars) ? vars
  : (typeof args !== "undefined" && args && args.vars) ? args.vars
  : (typeof input !== "undefined" && input && input.vars) ? input.vars : {};
var isLoan = v.category == "LOAN";
function pick(f) { return isLoan ? v[f + "2"] : v[f]; }
function num(x) {
  if (x === null || x === undefined || x === "") return null;
  var n = Number(String(x).replace(/[$,%\s]/g, ""));
  return isFinite(n) ? n : null;
}
function r2(x) { return Math.round(x * 1000) / 1000; }
var score = 50, pos = [], neg = [], gaps = [], path = ["start 50"], core = 0;
function add(pts, label) {
  score += pts;
  path.push(label + " " + (pts >= 0 ? "+" : "") + pts);
  if (pts > 0) pos.push(label); else if (pts < 0) neg.push(label);
}

var dti = num(v.dtiRatio2);
var income = num(pick("grossAnnualIncome")), debts = num(pick("totalMonthlyDebts"));
if (dti === null && income && income > 0 && debts !== null) dti = debts / (income / 12);
if (dti !== null && dti > 1.5 && dti <= 100) dti = dti / 100;
if (dti === null) gaps.push("DTI not computable");
else {
  core++;
  var d = "DTI " + r2(dti);
  if (dti < 0.28) add(20, d); else if (dti <= 0.36) add(10, d); else if (dti <= 0.43) add(0, d); else add(-20, d);
}

var yrs = num(pick("yearsEmployed"));
if (yrs === null) gaps.push("yearsEmployed");
else {
  core++;
  var t = "employed " + yrs + " yrs";
  if (yrs >= 5) add(10, t); else if (yrs >= 2) add(5, t); else add(-5, t);
}

if (isLoan) {
  var dp = num(v.downPayment2), pp = num(v.purchasePrice2);
  if (dp === null || !pp) gaps.push("down payment ratio (downPayment / purchasePrice)");
  else {
    core++;
    var dr = dp / pp, l = "down payment " + Math.round(dr * 100) + "%";
    if (dr > 0.20) add(10, l); else if (dr >= 0.10) add(5, l); else add(-5, l);
  }
} else {
  var amt = num(v.requestedLoanAmount), val = num(v.estimatedPropertyValue) || num(v.purchasePrice);
  if (!amt || !val) gaps.push("loan-to-value (requestedLoanAmount / estimatedPropertyValue)");
  else {
    core++;
    var ltv = amt / val, lt = "LTV " + r2(ltv);
    if (ltv < 0.70) add(15, lt); else if (ltv <= 0.80) add(10, lt); else if (ltv <= 0.95) add(0, lt); else add(-15, lt);
  }
}

var cs = num(pick("creditScore")), hasCredit = cs !== null && cs > 0;
if (!hasCredit) gaps.push("creditScore");
else {
  var c = "credit score " + cs;
  if (cs >= 740) add(15, c); else if (cs >= 680) add(8, c); else if (cs >= 620) add(0, c); else add(-15, c);
}

score = Math.max(0, Math.min(100, score));
var tier = score >= 70 ? "LOW" : score >= 45 ? "MODERATE" : "HIGH";
var confidence = Math.round((0.6 + 0.1 * core + (hasCredit ? 0.05 : 0)) * 100) / 100;
var agentScore = num(v.riskScore2);

return {
  riskScore: score,
  riskTier: tier,
  confidence: confidence,
  factorsPositive: pos,
  factorsNegative: neg,
  dataGaps: gaps,
  dtiRatio: dti === null ? null : r2(dti),
  agentRiskScore: agentScore,
  reasoning: "Rules score " + score + " (" + path.join(", ") + "). Agent estimate " +
    (agentScore === null ? "n/a" : agentScore) + ". " + String(v.reasoning2 || "")
};

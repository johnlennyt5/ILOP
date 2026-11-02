(function () {
  var name = String((vars.category == "LOAN" ? vars.applicantName2 : vars.applicantName) || "Applicant");
  var product = vars.category == "MORTGAGE" ? "mortgage" : "loan";
  var plain = {
    PRODUCT_NOT_OFFERED: "The requested amount or term is outside the products we offer",
    PROPERTY_OUT_OF_FOOTPRINT: "The property is outside our lending area (Rhode Island, Massachusetts, Connecticut)",
    INELIGIBLE_OCCUPANCY: "We do not finance the stated occupancy type",
    IDENTITY_DATA_CONFLICT: "We could not verify consistent identity information in the application"
  };
  var reasons = (vars.vetoCodes2 || []).map(function (c) { return plain[c] || c; });
  if (vars.Activity_arK2rt_reviewerComment) { reasons.push(String(vars.Activity_arK2rt_reviewerComment)); }
  if (!reasons.length) { reasons.push("The application did not meet our credit criteria"); }
  return "<p>Dear " + name + ",</p>" +
    "<p>Thank you for applying for a " + product + " with Harborview Financial Group. After reviewing your application, we are unable to approve it at this time.</p>" +
    "<p><b>Principal reason(s):</b></p><ul><li>" + reasons.join("</li><li>") + "</li></ul>" +
    "<p>The federal Equal Credit Opportunity Act prohibits creditors from discriminating against credit applicants on the basis of race, color, religion, national origin, sex, marital status, or age (provided the applicant has the capacity to enter into a binding contract); because all or part of the applicant's income derives from any public assistance program; or because the applicant has in good faith exercised any right under the Consumer Credit Protection Act. The federal agency that administers compliance with this law concerning this creditor is the Consumer Financial Protection Bureau, 1700 G Street NW, Washington, DC 20552.</p>" +
    "<p>If you have questions, reply to this email and a loan officer will follow up.</p>" +
    "<p>Sincerely,<br>Harborview Financial Group Lending Team</p>";
})()

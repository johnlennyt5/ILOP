(function () {
  var name = String((vars.category == "LOAN" ? vars.applicantName2 : vars.applicantName) || "Applicant");
  var product = vars.category == "MORTGAGE" ? "mortgage" : "loan";
  var amount = Number((vars.category == "LOAN" ? vars.requestedLoanAmount2 : vars.requestedLoanAmount) || 0);
  var amountText = amount ? " for $" + amount.toLocaleString("en-US") : "";
  return "<p>Dear " + name + ",</p>" +
    "<p>Good news: your " + product + " application" + amountText + " with Harborview Financial Group has been conditionally approved.</p>" +
    "<p>A loan officer will contact you within two business days to confirm your documents and final terms. Final approval depends on verifying the information in your application.</p>" +
    "<p>If you have questions, reply to this email.</p>" +
    "<p>Sincerely,<br>Harborview Financial Group Lending Team</p>";
})()

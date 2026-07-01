import type { ChatResponse } from "../api/types";

export const MOCK_RESPONSES: Record<string, ChatResponse> = {
  fees: {
    answer:
      "The simulated policy states that standard online equity and ETF trades have no commission, but some account activity can still create fees. Examples include outgoing wire transfers, overnight check delivery, certain foreign securities transactions, paper statement preferences, and specialized service requests. Before submitting a transaction, the customer should review the fee schedule shown in the account workflow.",
    sources: [
      {
        text: "Online domestic equity and ETF orders are listed as commission-free in the standard retail schedule. Service fees may still apply for non-standard requests or delivery methods.",
        source_document: "FEE-SCH-031",
        page_number: 1,
        score: 0.91,
        title: "Retail brokerage fee schedule",
        section: "§1.2",
      },
      {
        text: "Outgoing bank wires, overnight mail, returned checks, foreign settlement activity, and selected paper document services may generate account-level charges.",
        source_document: "BROK-SVC-118",
        page_number: 3,
        score: 0.87,
        title: "Special handling fees",
        section: "§3.5",
      },
      {
        text: "Digital workflows should display applicable fees before the customer confirms an order, transfer, or account service request.",
        source_document: "DISCLOSURE-009",
        page_number: 1,
        score: 0.83,
        title: "Fee confirmation disclosure",
      },
    ],
  },
  ira: {
    answer:
      "According to the Fidelity policy documents, early withdrawals from a traditional IRA before age 59½ are subject to ordinary income tax plus a 10% early withdrawal penalty in most cases. Certain exceptions apply, including death, disability, substantially equal periodic payments (Rule 72t), and specific medical or educational expenses. The penalty is assessed by the IRS, not Fidelity, and must be reported on your tax return.",
    sources: [
      {
        text: "Distributions from a traditional IRA prior to age 59½ are generally subject to a 10% additional tax penalty under IRC §72(t), in addition to ordinary income tax on the distributed amount.",
        source_document: "IRA-POL-042",
        page_number: 2,
        score: 0.93,
        title: "Early IRA distribution penalty",
        section: "§2.1",
      },
      {
        text: "Exceptions to the 10% early withdrawal penalty include distributions made on account of death, disability, or as part of a series of substantially equal periodic payments.",
        source_document: "IRA-POL-042",
        page_number: 4,
        score: 0.88,
        title: "Penalty exception criteria",
        section: "§4.3",
      },
    ],
  },
  rmd: {
    answer:
      "Required Minimum Distributions from traditional IRAs must generally begin by April 1st of the year following the year you turn 73, per the SECURE 2.0 Act. Failure to take the full RMD results in a 25% excise tax on the shortfall, reduced to 10% if corrected within two years.",
    sources: [
      {
        text: "Under SECURE 2.0, the required beginning date for RMDs from traditional IRAs is April 1 of the calendar year following the year the account holder reaches age 73.",
        source_document: "RMD-GUIDE-2026",
        page_number: 1,
        score: 0.95,
        title: "RMD required beginning date",
        section: "§1.1",
      },
      {
        text: "Failure to withdraw the full RMD amount by the required deadline triggers a 25% excise tax on the shortfall, which may be reduced to 10% if the error is corrected within a two-year correction window.",
        source_document: "RMD-GUIDE-2026",
        page_number: 3,
        score: 0.84,
        title: "RMD excise tax and corrections",
        section: "§3.2",
      },
    ],
  },
  transfer: {
    answer:
      "Electronic fund transfers from Fidelity to an external bank account linked via EFT typically take 1–3 business days to settle. Wire transfers are generally available same-day if submitted before the daily cutoff. Check delivery varies by mail speed selected.",
    sources: [
      {
        text: "Standard electronic fund transfers (EFT) initiated before 4 PM ET on a business day are processed that day and typically settle in one to three business days at the receiving institution.",
        source_document: "TRANS-POL-017",
        page_number: 2,
        score: 0.9,
        title: "EFT processing timeline",
        section: "§2.4",
      },
    ],
  },
  beneficiary: {
    answer:
      "Beneficiary designations on Fidelity retirement accounts can be updated at any time through the Fidelity website or by submitting a Beneficiary Designation form. Changes take effect upon receipt and processing by Fidelity. Beneficiary designations on retirement accounts supersede instructions in a will.",
    sources: [
      {
        text: "Account holders may update beneficiary designations for IRA and retirement plan accounts at any time by completing the appropriate form or using the Fidelity online portal.",
        source_document: "BENEF-POL-008",
        page_number: 1,
        score: 0.92,
        title: "Updating beneficiary designations",
        section: "§1.3",
      },
      {
        text: "Beneficiary designations on retirement accounts and IRAs take precedence over contrary instructions in a will or trust agreement.",
        source_document: "BENEF-POL-008",
        page_number: 2,
        score: 0.8,
        title: "Beneficiary precedence over will",
        section: "§2.1",
      },
    ],
  },
  margin: {
    answer:
      "If a margin call is issued, the client must deposit additional funds or securities within 3 business days. Failure to satisfy the call may result in Fidelity liquidating positions in the account without prior notice, at its discretion, to meet the maintenance margin requirement.",
    sources: [
      {
        text: "If a margin call is issued, the client must deposit funds within 3 days.",
        source_document: "MARGIN-RULES-2026",
        page_number: 12,
        score: 0.94,
        title: "Margin call deposit requirement",
        section: "§12.1",
      },
      {
        text: "The firm reserves the right to liquidate securities without prior notice if margin requirements are not satisfied within the prescribed period.",
        source_document: "MARGIN-RULES-2026",
        page_number: 14,
        score: 0.81,
        title: "Forced liquidation policy",
        section: "§14.2",
      },
    ],
  },
  default: {
    answer:
      "Based on the available Fidelity policy documents, I could not find a specific passage that directly answers your question. Please try rephrasing, or ask about IRA withdrawals, RMDs, account fees, fund transfers, or beneficiary changes.",
    sources: [],
  },
};

export function getMockResponse(message: string): ChatResponse {
  const lower = message.toLowerCase();
  if (lower.includes("fee") || lower.includes("cost") || lower.includes("charge") || lower.includes("brokerage account")) return MOCK_RESPONSES.fees;
  if (lower.includes("ira") || lower.includes("59") || lower.includes("withdraw") || lower.includes("early")) return MOCK_RESPONSES.ira;
  if (lower.includes("rmd") || lower.includes("required minimum") || lower.includes("distribution")) return MOCK_RESPONSES.rmd;
  if (lower.includes("transfer") || lower.includes("how long") || lower.includes("fund")) return MOCK_RESPONSES.transfer;
  if (lower.includes("beneficiar")) return MOCK_RESPONSES.beneficiary;
  if (lower.includes("margin")) return MOCK_RESPONSES.margin;
  return MOCK_RESPONSES.default;
}

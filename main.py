import os
import csv
import re
from tqdm import tqdm

def parse_mt940(filename):
    """
    Parses an MT940 file according to the standard (see e.g. 
    https://www.sepaforcorporates.com/swift-for-corporates/account-statement-mt940-file-format-overview/)
    and returns a list of transactions.

    Extracted fields:
      - TranDescription
      - TranValueDate
      - TranEntryDate
      - TranAmount
      - TranTransactionType
      - TranReference
      - TranDebitCredit
      - TranAccountServicingReference
      - StmAccount
      - StmClosingAvailableBalanceAmount
      - StmClosingAvailableBalanceCurrency
      - StmClosingAvailableBalanceDebitCredit
      - StmClosingAvailableBalanceEntryDate
      - StmClosingBalanceAmount
      - StmClosingBalanceCurrency
      - StmClosingBalanceDebitCredit
      - StmClosingBalanceEntryDate
      - StmOpeningBalanceAmount
      - StmOpeningBalanceCurrency
      - StmOpeningBalanceDebitCredit
      - StmOpeningBalanceEntryDate
      - StmSequenceNumber
      - StmStatementNumber
      - StmTransactionReference
    """
    with open(filename, "r") as f:
        lines = f.readlines()

    transactions = []
    current_statement = {}
    current_transaction = None

    # Helper: merge current transaction info with the current statement info.
    def finalize_transaction():
        nonlocal current_transaction
        if current_transaction is not None:
            # Create a merged copy so that later changes to current_statement don't affect this record
            merged = dict(current_statement)
            merged.update(current_transaction)
            # Clean extra whitespace in description
            merged["TranDescription"] = " ".join(merged.get("TranDescription", "").split())
            transactions.append(merged)
            current_transaction = None

    # Iterate through each line in the file (no progress bar here)
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # Statement-level fields
        if line.startswith(":20:"):
            # Tag 20 – Transaction Reference Number
            current_statement["StmTransactionReference"] = line[4:].strip()
        elif line.startswith(":25:"):
            # Tag 25 – Account Identification
            current_statement["StmAccount"] = line[4:].strip()
        elif line.startswith(":28C:"):
            # Tag 28C – Statement Number/Sequence Number (format NNN[/NNN])
            val = line[5:].strip()
            if "/" in val:
                stm_statement, stm_sequence = val.split("/", 1)
            else:
                stm_statement = val
                stm_sequence = ""
            current_statement["StmStatementNumber"] = stm_statement
            current_statement["StmSequenceNumber"] = stm_sequence
        elif line.startswith(":60F:") or line.startswith(":60M:"):
            # Tag 60F or 60M – Opening Balance
            info = line[5:].strip()
            current_statement["StmOpeningBalanceDebitCredit"] = info[0]
            date_val = info[1:7]
            current_statement["StmOpeningBalanceEntryDate"] = "20" + date_val[0:2] + "-" + date_val[2:4] + "-" + date_val[4:6]
            current_statement["StmOpeningBalanceCurrency"] = info[7:10]
            current_statement["StmOpeningBalanceAmount"] = info[10:].replace(",", ".")
        elif line.startswith(":62F:") or line.startswith(":62M:"):
            # Tag 62F/M – Closing Balance (Booked Funds)
            info = line[5:].strip()
            current_statement["StmClosingBalanceDebitCredit"] = info[0]
            date_val = info[1:7]
            current_statement["StmClosingBalanceEntryDate"] = "20" + date_val[0:2] + "-" + date_val[2:4] + "-" + date_val[4:6]
            current_statement["StmClosingBalanceCurrency"] = info[7:10]
            current_statement["StmClosingBalanceAmount"] = info[10:].replace(",", ".")
        elif line.startswith(":64:"):
            # Tag 64 – Closing Available Balance
            info = line[4:].strip()
            current_statement["StmClosingAvailableBalanceDebitCredit"] = info[0]
            date_val = info[1:7]
            current_statement["StmClosingAvailableBalanceEntryDate"] = "20" + date_val[0:2] + "-" + date_val[2:4] + "-" + date_val[4:6]
            current_statement["StmClosingAvailableBalanceCurrency"] = info[7:10]
            current_statement["StmClosingAvailableBalanceAmount"] = info[10:].replace(",", ".")
        
        # Transaction-level fields (start with tag :61:)
        elif line.startswith(":61:"):
            # Finalize any active transaction before starting a new one.
            finalize_transaction()
            content = line[4:].strip()
            # TranValueDate: first 6 digits (YYMMDD)
            tran_value_date_raw = content[:6]
            tran_value_date = "20" + tran_value_date_raw[0:2] + "-" + tran_value_date_raw[2:4] + "-" + tran_value_date_raw[4:6]
            # Check for an optional 4-digit entry date (MMDD)
            idx = 6
            tran_entry_date = ""
            if len(content) >= 10 and content[6:10].isdigit():
                entry_date_raw = content[6:10]  # MMDD
                tran_entry_date = "20" + tran_value_date_raw[0:2] + "-" + entry_date_raw[:2] + "-" + entry_date_raw[2:4]
                idx = 10
            # Next: debit/credit indicator. It may be 2 characters if it starts with "R".
            if content[idx] == "R":
                tran_debit_credit = content[idx:idx+2]
                idx += 2
            else:
                tran_debit_credit = content[idx]
                idx += 1
            if "C" in tran_debit_credit:
                tran_debit_credit = "Credit"
            elif "D" in tran_debit_credit:
                tran_debit_credit = "Debit"
            # Optional: funds code (if the next character is non‑digit and not a comma or dot)
            if idx < len(content) and not content[idx].isdigit() and content[idx] not in [",", "."]:
                funds_code = content[idx]
                idx += 1
            else:
                funds_code = ""
            # TranAmount: match amount (digits with comma or dot)
            amt_match = re.match(r"([\d,\.]+)", content[idx:])
            if amt_match:
                tran_amount = amt_match.group(1).replace(",", ".")
                idx += len(amt_match.group(1))
            else:
                tran_amount = ""
            # TranTransactionType: next 4 characters (1 letter + 3 alphanumerics)
            tran_transaction_type = content[idx:idx+4]
            idx += 4
            # The remainder: customer reference and bank reference separated by "//"
            remaining = content[idx:]
            if "//" in remaining:
                parts = remaining.split("//", 1)
                tran_reference = parts[0].strip()
                tran_account_servicing_reference = parts[1].strip()
            else:
                tran_reference = remaining.strip()
                tran_account_servicing_reference = ""
            # Initialize current transaction dictionary
            current_transaction = {
                "TranValueDate": tran_value_date,
                "TranEntryDate": tran_entry_date,
                "TranDebitCredit": tran_debit_credit,
                "TranAmount": tran_amount,
                "TranTransactionType": tran_transaction_type,
                "TranReference": tran_reference,
                "TranAccountServicingReference": tran_account_servicing_reference,
                "TranDescription": ""  # To be appended from tag :86:
            }
        elif line.startswith(":86:"):
            # Tag 86 – Transaction Description / Information to Account Owner.
            if current_transaction is not None:
                desc = line[4:].strip()
                current_transaction["TranDescription"] += desc + " "

    # Finalize any pending transaction at the end of the file.
    finalize_transaction()

    # Back-fill closing information for all transactions
    closing_keys = [
        "StmClosingAvailableBalanceAmount",
        "StmClosingAvailableBalanceCurrency",
        "StmClosingAvailableBalanceDebitCredit",
        "StmClosingAvailableBalanceEntryDate",
        "StmClosingBalanceAmount",
        "StmClosingBalanceCurrency",
        "StmClosingBalanceDebitCredit",
        "StmClosingBalanceEntryDate",
    ]
    for transaction in transactions:
        for key in closing_keys:
            # If a particular closing field is missing in the transaction, add it from the final statement info.
            transaction[key] = current_statement.get(key, transaction.get(key, ""))
    return transactions

def main():
    """
    Processes all MT940 files in the data folder and writes the extracted data to results.csv.
    """
    files = [file for file in os.listdir("data") if file.lower().endswith(".txt")]
    all_transactions = []
    # Use tqdm to iterate over files in the data folder
    for file in tqdm(files, desc="Processing files", unit="file"):
        file_transactions = parse_mt940(os.path.join("data", file))
        all_transactions += file_transactions
    
    header = [
        "TranDescription",
        "TranValueDate",
        "TranEntryDate",
        "TranAmount",
        "TranTransactionType",
        "TranReference",
        "TranDebitCredit",
        "TranAccountServicingReference",
        "StmAccount",
        "StmClosingAvailableBalanceAmount",
        "StmClosingAvailableBalanceCurrency",
        "StmClosingAvailableBalanceDebitCredit",
        "StmClosingAvailableBalanceEntryDate",
        "StmClosingBalanceAmount",
        "StmClosingBalanceCurrency",
        "StmClosingBalanceDebitCredit",
        "StmClosingBalanceEntryDate",
        "StmOpeningBalanceAmount",
        "StmOpeningBalanceCurrency",
        "StmOpeningBalanceDebitCredit",
        "StmOpeningBalanceEntryDate",
        "StmSequenceNumber",
        "StmStatementNumber",
        "StmTransactionReference"
    ]
    
    with open("results.csv", "w", newline="") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(header)
        for transaction in all_transactions:
            row = [transaction.get(field, "") for field in header]
            writer.writerow(row)
    print("CSV export complete.")

if __name__ == "__main__":
    main()

import os
import csv
import json
import requests
from progress.spinner import MoonSpinner, PixelSpinner

NBP_API_URL = "http://api.nbp.pl/api/exchangerates/rates/A/{}/{}/"


def get_exchange_rate(currency, date):
    """
    Retrieves exchange rate for a given currency and date from the NBP API.

    Args:
      currency: Currency code (e.g. USD, EUR).
      date: Date in the format YYYY-MM-DD.

    Returns:
      Exchange rate for the given currency and date according to PLN.
    """
    url = NBP_API_URL.format(currency, date)
    try:
        response = requests.get(url)
        decoded_data = response.text.encode().decode("utf-8-sig")
        data = json.loads(decoded_data)
        return data["rates"][0]["mid"]
    except Exception as e:
        print(f"Error while fetching exchange rate ❌")
        return None


def parse_mt940(filename):
    """
    Parses a PKO BP MT940 file and returns a list of transactions.

    Args:
      filename: Path to the MT940 file.

    Returns:
      A list of dictionaries containing transaction information.
    """
    with open(filename, "r") as f:
        lines = f.readlines()

    # Initialize variables
    transactions = []
    account = None
    transaction_date = None
    transaction_amount = None
    transaction_currency = None
    transaction_currency_rate = None
    transaction_id = None
    transaction_title = ""
    with MoonSpinner(" Processing ") as bar:
        for line in lines:
            if line.startswith(":25:"):
                # Account name
                account = line[5:7].strip() + " " + line[7:].strip()
            elif line.startswith(":60F:"):
                # Transaction currency
                transaction_currency = line[12:15:].strip()
            elif line.startswith(":61:"):
                # Transaction date
                transaction_date = (
                    line[8:10].strip()
                    + "-"
                    + line[6:8].strip()
                    + "-"
                    + "20"
                    + line[4:6].strip()
                )
                # Transaction amount
                transaction_sign = "+" if line[14].strip() == "D" else "-"
                transaction_amount = transaction_sign + line.split("N")[0][
                    15:
                ].strip().replace(",", ".")

                date = (
                    "20"
                    + line[4:6].strip()
                    + "-"
                    + line[6:8].strip()
                    + "-"
                    + line[8:10].strip()
                )
                transaction_currency_rate = get_exchange_rate(
                    transaction_currency, date
                )

            elif line.startswith(":86:"):
                # Transaction id
                transaction_id = line[10:].strip()
            elif line.startswith("~"):
                subfield = int(line[1:3])
                if subfield > 19 and subfield < 26:
                    transaction_title = transaction_title + line[3:].strip().replace(
                        "˙", ""
                    )

            # Save transaction to list
            if line.startswith("~63"):
                transactions.append(
                    {
                        "account": account,
                        "transaction_date": transaction_date,
                        "transaction_amount": transaction_amount,
                        "transaction_currency": transaction_currency,
                        "transaction_currency_rate": transaction_currency_rate,
                        "transaction_id": transaction_id,
                        "transaction_title": " ".join(transaction_title.split()),
                    }
                )
                transaction_title = ""
            bar.next()
        return transactions


def main():
    """
    Processes all MT940 files in the data folder and saves the data to the results.csv file.
    """
    files = os.listdir("data")
    transactions = []

    for file in files:
        if file.lower().endswith(".txt"):
            print("File: " + file)
            transactions += parse_mt940(os.path.join("data", file))
            print("  Done ✔️")

    with open("results.csv", "w", newline="") as f:
        writer = csv.writer(f, delimiter="|")
        writer.writerow(
            [
                "Account",
                "Transaction date",
                "Transaction amount",
                "Transaction currency",
                "Currency rate (to PLN)",
                "Transaction ID",
                "Transaction title",
            ]
        )
        for transaction in transactions:
            writer.writerow(
                [
                    transaction["account"],
                    transaction["transaction_date"],
                    transaction["transaction_amount"],
                    transaction["transaction_currency"],
                    transaction["transaction_currency_rate"],
                    transaction["transaction_id"],
                    transaction["transaction_title"],
                ]
            )


if __name__ == "__main__":
    main()

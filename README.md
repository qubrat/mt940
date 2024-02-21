# Simple MT940 to CSV Converter

## Description

This project contains the `process.py` script, which performs processing of transaction info provided by a bank. Files need to be located in ./data folder. The script will read the files, process the data and save the results in a CSV file.

Output fields:
- `Account`
- `Transaction date`
- `Transaction amount`
- `Transaction currency `
- `Currency rate (to PLN)`
- `Transaction ID`
- `Transaction title`

Currency rate is obtained from the NBP API and references values according to PLN. Reference  [here](https://api.nbp.pl/).



## Usage

To use the `process.py` script, follow these steps:

1. Clone the repository to your local machine:

```bash
git clone https://github.com/qubrat/mt940.git
```

2. Navigate to the project directory:

```bash
cd mt940_to_csv
```

3. Install the required modules:

```bash
pip install -r requirements.txt
```

4. Run the `process.py` script:

```bash
python process.py
```


## Return Value

The `process.py` script returns results in a csv file `results.csv` located in the root folder.

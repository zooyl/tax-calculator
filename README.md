# tax-calculator
Calculate your tax liability from IB statement or your own input in seconds.
This tool search for withholding tax and dividend table in your IB activity statement.
It takes two tables and calculate your liability tax to "Urzad Skarbowy" according to mid nbp rate (D-1) including W-8BEN form.
If you don't use this broker, you can input your own data to "local_input.csv" file.
Polish business days calendar is included in calculations

### Single executable file for Windows
Drag IB statement to folder containing the program or edit "local_input.csv" then open
```calculator.exe```  

### Dev environment

Create virtual environment on your machine, then install requirements using:

```
pip install -r requirements.txt
```

### Contributing
Feel free to fork this repo and add new features

## Built With

* [Python](https://www.python.org/)
* [Pandas](https://pandas.pydata.org/)
* [PyInstaller](https://pypi.org/project/pyinstaller/)

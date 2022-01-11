import requests
import holidays
import pdfplumber
import pandas as pd

from pandas.tseries.offsets import CustomBusinessDay
from pandas.tseries.holiday import AbstractHolidayCalendar, Holiday, previous_workday
from datetime import datetime
from math import ceil

from local_settings import pdf_file
# pdf_file = "path/to/file.pdf"

# Settings
year = 2021
polish_tax = 0.19
currency = "usd"
withholdin_table = "Withholding Tax"
dividends_table = "Dividends"
country = holidays.Poland

class CustomHolidayCalendar(AbstractHolidayCalendar):
    rules = []
    for date, name in sorted(country(years=year).items()):
        rules.append(Holiday(name, year=date.year, month=date.month, day=date.day, observance=previous_workday))
 
customBD = CustomBusinessDay(calendar=CustomHolidayCalendar())

def main():
    
    pdf_tax_table = []
    pdf_div_table = []
    with pdfplumber.open(pdf_file) as pdf:
        pages = pdf.pages
        for i,pg in enumerate(pages):
            tables = pages[i].extract_tables()
            for j in tables:
                if j[0][0] == withholdin_table:
                    pdf_tax_table.append(j)
                if j[0][0] == dividends_table:
                    pdf_div_table.append(j)
    
    for i, j in zip(pdf_tax_table, pdf_div_table):
        df_tax = pd.DataFrame(i)
        df_name = df_tax[df_tax.columns[0]][0]
        df_date = df_tax[df_tax.columns[0]][3:-2]
        df_withholding_tax = df_tax[df_tax.columns[2]][3:-2]
        df_div = pd.DataFrame(j)
        df_div_amount = df_div[df_div.columns[2]][3:-2]
        
    previous_b_day = previous_day(df_date)
    previous_b_day_series = pd.Series(previous_b_day)
    
    cached_rate = cache_nb_rate(previous_b_day_series)
    # cached_rate = [3.9676, 3.8035, 3.9925, 4.1088]
    
    pln_tax_paid_usa = tax_calc(df_name, cached_rate, df_withholding_tax)
    div_pln = div_calc(df_div_amount, cached_rate)
    pol_tax = polish_tax_calc(div_pln)
    diff = diff_to_pay(pol_tax, pln_tax_paid_usa)
    print(display_info(pln_tax_paid_usa, div_pln, pol_tax, diff, cached_rate))
        
        
def previous_day(df_date):
    previous_day = []
    for i in df_date:
        datetime_object = convert_date_str_to_timeobject(i)
        previous_day.append(datetime_object - customBD)
    return previous_day
  
def convert_date_str_to_timeobject(str_date):
    obj_date = datetime.strptime(str_date, "%Y-%m-%d")
    return obj_date
      
def cache_nb_rate(previous_b_day_series):
    nb_rate_list = []
    for i in previous_b_day_series:
            nb_rate_list.append(get_nb_mid_rate(currency, i.date()))
    return nb_rate_list

def get_nb_mid_rate(currency, date):
    try:
        response = requests.get(
            f"https://api.nbp.pl/api/exchangerates/rates/a/{currency}/{date}/?format=json"
        )
        response.raise_for_status()
        nb_json = response.json()
        for i in nb_json["rates"]:
            mid = i["mid"]
            return mid
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)

def tax_calc(df_name, cached_rate, df_withholding_tax):
    pln_tax_paid_usa = []
    if (df_name == withholdin_table):
        for i, j in zip(df_withholding_tax, cached_rate):
            pln_tax_paid_usa.append(round(abs(float(i)) * j, 2))
        return pln_tax_paid_usa
           
def div_calc(df_div_amount, cached_rate):
    div_in_pln = []
    for i, j in zip(df_div_amount, cached_rate):
        div_in_pln.append(round(float(i) * j, 2))
    return div_in_pln
   
def polish_tax_calc(div_pln):
    pol = []
    for i in div_pln:
        pol.append(round(i * polish_tax, 2))
    return pol
             
def diff_to_pay(pol_tax, pln_tax_paid_usa):
    diff = []
    if len(pol_tax) == len(pln_tax_paid_usa):
        for tax_pl, tax_paid in zip(pol_tax, pln_tax_paid_usa):
            difference = tax_pl - tax_paid
            diff.append(round(difference, 2))
        return diff
    
def display_info(pln_tax_paid_usa, div_pln, pol_tax, diff, cached_rate):
    for i, j, k, l, m in zip(pln_tax_paid_usa, div_pln, pol_tax, diff, cached_rate):
            print("-------")
            print("NBP RATE: " + str(m))
            print("DIVIDEND PLN: " + str(j))
            print("FULL PL TAX: " + str(k))
            print("PLN TAX PAID IN USA: " + str(i))
            print("TAX DIFF: " + str(l))
            print("ROUND UP: " + str(ceil(l)))
    
    
if __name__ == "__main__":
    main()

# Sources

# https://api.nbp.pl/
# https://pypi.org/project/holidays/
# https://stackoverflow.com/questions/2224742/most-recent-previous-business-day-in-python
# https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#custom-business-days
# https://datagy.io/pandas-select-columns/

import requests
import holidays
import pdfplumber
import pandas as pd

from pandas.tseries.offsets import CustomBusinessDay
from pandas.tseries.holiday import AbstractHolidayCalendar, Holiday, previous_workday
from datetime import datetime
from math import ceil

from local_settings import pdf_file

# Settings
year = 2021
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
    
    with pdfplumber.open(pdf_file) as pdf:
        page = pdf.pages[5].find_tables()
        # t1_content = page[0].extract(x_tolerance = 5)
        t2_content = page[1].extract()
        t3_content = page[2].extract()
        # print(t2_content)
        # print(t3_content)
        df_2 = pd.DataFrame(t2_content)
        df_name = df_2[df_2.columns[0]][0]
        df_date = df_2[df_2.columns[0]][3:-2]
        df_withholding_tax = df_2[df_2.columns[2]][3:-2]
        
        df_3 = pd.DataFrame(t3_content)
        # df_name = df_3[df_3.columns[0]][0]
        # df_date = df_3[df_3.columns[0]][3:-2]
        df_amount = df_3[df_3.columns[2]][3:-2]
        
        previous_b_day = previous_day(df_date)
        previous_b_day_series = pd.Series(previous_b_day)
        # cached_rate = cache_nb_rate(previous_b_day_series)
        cached_rate = [3.9676, 3.8035, 3.9925, 4.1088]
        
        pln_tax_paid_usa = tax_calc(df_name, cached_rate, df_withholding_tax)
        div_pln = div_calc(df_amount, cached_rate)
        pol_tax = polish_tax(div_pln)
        diff = diff_to_pay(pol_tax, pln_tax_paid_usa)
        print(display_info(pln_tax_paid_usa, div_pln, pol_tax, diff, cached_rate))
        
            
def display_info(pln_tax_paid_usa, div_pln, pol_tax, diff, cached_rate):
    for i, j, k, l, m in zip(pln_tax_paid_usa, div_pln, pol_tax, diff, cached_rate):
            print("-------")
            print("NBP RATE: " + str(m))
            print("PLN TAX PAID IN USA: " + str(i))
            print("DIVIDEND PLN: " + str(j))
            print("FULL PL TAX: " + str(k))
            print("TAX DIFF: " + str(l))
            print("ROUND UP: " + str(ceil(l)))
    
        
def cache_nb_rate(previous_b_day_series):
    nb_rate_list = []
    for i in previous_b_day_series:
            nb_rate_list.append(get_nb_mid_rate(currency, i.date()))
    return nb_rate_list
          
          
def previous_day(df_date):
    previous_day = []
    for i in df_date:
        datetime_object = convert_date_str_to_timeobject(i)
        previous_day.append(datetime_object - customBD)
    return previous_day


def tax_calc(df_name, cached_rate, df_withholding_tax):
    pln_tax_paid_usa = []
    if (df_name == withholdin_table):
        for i, j in zip(df_withholding_tax, cached_rate):
            pln_tax_paid_usa.append(abs(float(i)) * j)
        return pln_tax_paid_usa
        
        
def div_calc(df_amount, cached_rate):
    div_in_pln = []
    for i, j in zip(df_amount, cached_rate):
        div_in_pln.append(float(i) * j)
    return div_in_pln

        
def polish_tax(div_pln):
    pol = []
    for i in div_pln:
        pol.append(i * 0.19)
    return pol
        
        
def diff_to_pay(pol_tax, pln_tax_paid_usa):
    diff = []
    if len(pol_tax) == len(pln_tax_paid_usa):
        for tax_pl, tax_paid in zip(pol_tax, pln_tax_paid_usa):
            difference = tax_pl - tax_paid
            diff.append(difference)
        return diff


def convert_date_str_to_timeobject(str_date):
    obj_date = datetime.strptime(str_date, "%Y-%m-%d")
    return obj_date


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
    

if __name__ == "__main__":
    main()


# Sources

# https://api.nbp.pl/
# https://pypi.org/project/holidays/
# https://stackoverflow.com/questions/2224742/most-recent-previous-business-day-in-python
# https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#custom-business-days
# https://datagy.io/pandas-select-columns/

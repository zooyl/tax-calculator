# Tax-calculator
# Calculate your tax liability from IB statement or your own input in seconds
# Copyright (C) 2021 by Zooyl
# https://github.com/zooyl

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import os.path
import requests
import holidays
import pdfplumber
import pandas as pd
import sys

from pandas.tseries.offsets import CustomBusinessDay
from pandas.tseries.holiday import AbstractHolidayCalendar, Holiday, previous_workday
from datetime import datetime
from math import ceil

# Settings
year = datetime.now().year - 1
polish_tax = 0.19
currency = "usd"
withholdin_table = "Withholding Tax"
dividends_table = "Dividends"
country = holidays.Poland
prompt = "Press anything to exit"


class CustomHolidayCalendar(AbstractHolidayCalendar):
    rules = []
    for date, name in sorted(country(years=year).items()):
        rules.append(Holiday(name, year=date.year, month=date.month,
                             day=date.day, observance=previous_workday))


customBD = CustomBusinessDay(calendar=CustomHolidayCalendar())


def main():

    custom_csv_exists = os.path.exists('input.csv')
    ib_exists = os.path.exists('ib.pdf')

    if custom_csv_exists:
        print("Custom csv detected")
        with open('input.csv') as file:
            df = pd.read_csv(file)
            for i in df:
                df_date = df[df.columns[0]]
                df_div_amount = df[df.columns[1]]
                df_withholding_tax = df[df.columns[2]]

    elif ib_exists and custom_csv_exists == False:
        print("IB pdf detected")
        pdf_tax_table = []
        pdf_div_table = []
        with pdfplumber.open("ib.pdf") as pdf:
            pages = pdf.pages
            for i, pg in enumerate(pages):
                tables = pages[i].extract_tables()
                for j in tables:
                    if j[0][0] == withholdin_table:
                        pdf_tax_table.append(j)
                    if j[0][0] == dividends_table:
                        pdf_div_table.append(j)
            if len(pdf_tax_table) == 0 or len(pdf_div_table) == 0:
                print(
                    f"Cant find '{withholdin_table}' or '{dividends_table}' table in ib.pdf")
                quit_program()

            for i, j in zip(pdf_tax_table, pdf_div_table):
                df_tax = pd.DataFrame(i)
                df_date = df_tax[df_tax.columns[1]][3:-2]
                df_withholding_tax = df_tax[df_tax.columns[3]][3:-2]
                df_div = pd.DataFrame(j)
                df_div_amount = df_div[df_div.columns[3]][3:-2]
    else:
        print("ib.pdf or input.csv doesn't exist")
        quit_program()

    previous_b_day = previous_day(df_date)
    previous_b_day_series = pd.Series(previous_b_day)
    cached_rate = cache_nb_rate(currency, previous_b_day_series)
    pln_tax_paid_usa = tax_calc(cached_rate, df_withholding_tax)
    div_pln = div_calc(df_div_amount, cached_rate)
    pol_tax = polish_tax_calc(div_pln)
    diff = diff_to_pay(pol_tax, pln_tax_paid_usa)
    results = display_info(df_date, df_div_amount, df_withholding_tax, previous_b_day,
                           pln_tax_paid_usa, div_pln, pol_tax, diff, cached_rate)
    print(results)
    user_input = input_yesno("Do you want to save results?")
    if user_input:
        save_results(results)
        quit_program()
    else:
        quit_program()


def previous_day(df_date):
    previous_day = []
    for i in df_date:
        datetime_object = convert_date_str_to_timeobject(i)
        previous_day.append(datetime_object - customBD)
    return previous_day


def convert_date_str_to_timeobject(str_date):
    try:
        obj_date = datetime.strptime(str_date, "%Y-%m-%d")
        return obj_date
    except ValueError as e:
        print(f'{e}')
        quit_program()


def cache_nb_rate(currency, previous_b_day_series):
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


def tax_calc(cached_rate, df_withholding_tax):
    pln_tax_paid_usa = []
    for i, j in zip(df_withholding_tax, cached_rate):
        pln_tax_paid_usa.append(ceil(abs(float(i)) * j))
    return pln_tax_paid_usa


def div_calc(df_div_amount, cached_rate):
    div_in_pln = []
    for i, j in zip(df_div_amount, cached_rate):
        div_in_pln.append(ceil(float(i) * j))
    return div_in_pln


def polish_tax_calc(div_pln):
    pol = []
    for i in div_pln:
        pol.append(ceil(i * polish_tax))
    return pol


def diff_to_pay(pol_tax, pln_tax_paid_usa):
    diff = []
    if len(pol_tax) == len(pln_tax_paid_usa):
        for tax_pl, tax_paid in zip(pol_tax, pln_tax_paid_usa):
            difference = tax_pl - tax_paid
            diff.append(difference)
        return diff


def display_info(df_date, df_div_amount, df_withholding_tax, previous_b_day,
                 pln_tax_paid_usa, div_pln, pol_tax, diff, cached_rate):
    results = {"DIVIDEND DATE": df_date,
               "DIVIDEND AMOUNT": df_div_amount,
               "DIVIDEND TAX (W-8BEN 15%)": abs(df_withholding_tax.astype(float)),
               "D-1 DATE": previous_b_day,
               "D-1 NBP RATE": cached_rate,
               "DIVIDEND IN PLN": div_pln,
               "POLISH 19% TAX": pol_tax,
               "PLN TAX PAID IN USA": pln_tax_paid_usa,
               "TAX DIFFERENCE": diff
               }
    df = pd.DataFrame(results)
    total = df.iloc[:, 5:].sum()
    df = df.append(total, ignore_index=True)
    return df


def save_results(df):
    df.to_csv('results.csv', index=False)
    csv_exist = os.path.exists('results.csv')
    if csv_exist:
        print("'results.csv' created")
    else:
        print("Error creating file")
    return


def input_yesno(prompt: str) -> bool:
    full_prompt = f'{prompt} (yes/no): '
    while True:
        answer = input(full_prompt).strip()
        if answer == '':
            return True
        answer = answer[0].lower()
        if answer == 'y':
            return True
        if answer == 'n':
            return False
        print('error')


def quit_program():
    input(prompt)
    sys.exit()


if __name__ == "__main__":
    main()

# Sources

# https://api.nbp.pl/
# https://pypi.org/project/holidays/
# https://stackoverflow.com/questions/2224742/most-recent-previous-business-day-in-python
# https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#custom-business-days
# https://datagy.io/pandas-select-columns/

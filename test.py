from datetime import datetime
import unittest
import requests
import calculator

class TestAPI(unittest.TestCase):
    
    def test_nb_api_valid(self):
        currency = "usd"
        date = "2021-02-15"
        response = requests.get(
            f"https://api.nbp.pl/api/exchangerates/rates/a/{currency}/{date}/?format=json"
        )
        self.assertEqual(response.status_code, 200)
        
    def test_nb_api_invalid_currency(self):
        currency = "xpl"
        date = "2021-02-15"
        response = requests.get(
            f"https://api.nbp.pl/api/exchangerates/rates/a/{currency}/{date}/?format=json"
        )
        self.assertEqual(response.status_code, 404)    
        
    def test_nb_api_invalid_date(self):
        currency = "usd"
        date = "2021-15-12"
        response = requests.get(
            f"https://api.nbp.pl/api/exchangerates/rates/a/{currency}/{date}/?format=json"
        )
        self.assertEqual(response.status_code, 404)
    
class TestFunctions(unittest.TestCase):
    
    def setUp(self):
        self.b_day = "2021-05-12"
        self.wrong_date = "2021-15-15"
        
    def test_convert_str_to_datetime(self):
        self.assertIsInstance(self.b_day, str)
        function = calculator.convert_date_str_to_timeobject(self.b_day)        
        self.assertIsInstance(function, datetime)
        self.assertEqual(self.b_day, f'{function.year}-0{function.month}-{function.day}')
      
if __name__ == '__main__':
    unittest.main()
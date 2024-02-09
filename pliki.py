#Importy bibliotek
import requests
import json
from datetime import datetime
from datetime import timedelta
from pathlib import Path
import re
import traceback
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
#Inicializacja konsoli
console = Console()
 
def read_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        return None

def read_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        return None
 
def get_cached_data(currency, date):
    try:
        with open('cache.json', 'r') as file:
            data = json.load(file)
            if currency in data and date in data[currency]:
                return data[currency][date]
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return None
 
def get_data_from_api(currency, date):
    date = datetime.strptime(date, "%Y-%m-%d")
    attempts = 0
    while attempts < 7:
        try:
            formatted_date = date.strftime("%Y-%m-%d")
            response = requests.get(f"http://api.nbp.pl/api/exchangerates/rates/a/{currency}/{formatted_date}/?format=json")
            response.raise_for_status()
            data = response.json()
            return data["rates"][0]["mid"]
        except requests.exceptions.HTTPError:
            date -= timedelta(days=1)
            attempts += 1
        except requests.exceptions.ConnectionError as errc:
            raise Exception("Error Connecting:",errc)
        except requests.exceptions.Timeout as errt:
            raise Exception("Timeout Error:",errt)
        except requests.exceptions.RequestException as err:
            raise Exception("Something went wrong",err)
    raise Exception("Błąd HTTP: Brak danych dla podanej daty i 6 poprzednich dni.")
 
def save_data_to_cache(currency, date, rate):
    try:
        with open('cache.json', 'r') as file:
            cache_data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        cache_data = {}
 
    if currency not in cache_data:
        cache_data[currency] = {}
    cache_data[currency][date] = rate
 
    with open('cache.json', 'w') as file:
        json.dump(cache_data, file)
 
def get_exchange_rate_for_date(currency, date):
    cached_data = get_cached_data(currency, date)
    if cached_data is not None:
        return cached_data
 
    rate = get_data_from_api(currency, date)
    save_data_to_cache(currency, date, rate)
 
    return rate
 
def get_exchange_rate(currency, date_issue, date_payment):
    if currency.upper() == 'PLN':
        return 1, 1
    issue_rate = get_exchange_rate_for_date(currency, date_issue)
    payment_rate = issue_rate if date_issue == date_payment else get_exchange_rate_for_date(currency, date_payment)
    return issue_rate, payment_rate
 
def calculate_exchange_rate_difference(invoice_amount, currency, date_issue, date_payment):
    #Funkcja obliczająca różnicę kursową na podstawie podanych parametrów, zwraza różnicę kursową.
 
    issue_rate, payment_rate = get_exchange_rate(currency, date_issue, date_payment)
 
    #Zmienna invoice_amount jest typu string, konwersja na float jest wymagana do poprawnego działania funkcji.
    invoice_amount = float(invoice_amount)
 
    amount_in_pln_issue = invoice_amount * issue_rate
    amount_in_pln_payment = invoice_amount * payment_rate
    return amount_in_pln_payment - amount_in_pln_issue
 
def save_invoice_data(invoice_data, file_path='data.json'):
    #Funkcja zapisująca dane faktury do pliku JSON.
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []
    data.append(invoice_data)
    with open(file_path, 'w') as file:
        json.dump(data, file)
 
def validate_invoice_number(existing_invoices):
    #Funkcja walidująca numer faktury, zwraca poprawny numer faktury.
    invoice_number = Prompt.ask("Nr. faktury: ")
    while not re.match(r"^[a-zA-Z0-9-/]+$", invoice_number) or any(invoice['invoice_number'] == invoice_number for invoice in existing_invoices):
        invoice_number = Prompt.ask("Nieprawidłowy numer faktury lub numer faktury już istnieje. Wprowadź ponownie: ")
    return invoice_number
 
def validate_value():
    #Funkcja walidująca wartość faktury, zwraca poprawną wartość faktury.
    value = Prompt.ask("Wartość faktury: ")
    while True:
        try:
            return float(value)
        except ValueError:
            value = Prompt.ask("Nieprawidłowa wartość faktury. Wprowadź ponownie: ")
 
def validate_currency():
    #Funkcja walidująca walutę, zwraca poprawną walutę.
    currency = Prompt.ask("Waluta(EUR, USD, GBP, PLN): ")
    while currency not in ['EUR', 'USD', 'GBP', 'PLN']:
        currency = Prompt.ask("Nieprawidłowa waluta. Dozwolone waluty to EUR, USD, GBP i PLN. Wprowadź ponownie: ")
    return currency
 
def validate_date(prompt_message, earliest_date=None):
    #Funkcja walidująca datę, zwraca poprawną datę.
    date_str = Prompt.ask(prompt_message)
    while True:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            if earliest_date and date < earliest_date:
                raise ValueError
            return date_str
        except ValueError:
            date_str = Prompt.ask("Nieprawidłowa data. Wprowadź ponownie: ")
 
def validate_payment_value():
    while True:
        try:
            payment_value = float(input("Proszę podać kwotę płatności: "))
            if payment_value <= 0:
                print("Kwota płatności musi być liczbą dodatnią. Proszę spróbować ponownie.")
            else:
                return payment_value
        except ValueError:
            print("Nieprawidłowa wartość. Proszę wprowadzić liczbę.")
 
def get_invoice_data():
    #Funkcja pobierająca dane faktury od użytkownika, zwraca słownik z danymi faktury.
    invoice_data = {}
    invoice_data['payments'] = []
 
    with open('data.json', 'r') as file:
        existing_invoices = json.load(file)
 
    invoice_data['invoice_number'] = validate_invoice_number(existing_invoices)
    invoice_data['value'] = validate_value()
    invoice_data['currency'] = validate_currency()
    invoice_data['issue_date'] = validate_date("Data wystawienia (YYYY-MM-DD): ")
 
    while True:
        payment_value = validate_payment_value()
        payment_date = validate_date("Data płatności (YYYY-MM-DD): ")
        invoice_data['payments'].append({'date': payment_date, 'value': payment_value})
 
        total_payments = sum(payment['value'] for payment in invoice_data['payments'])
        if total_payments > invoice_data['value']:
            print("Uwaga: suma płatności przekracza wartość faktury.")
            break
        elif total_payments == invoice_data['value']:
            break
        else:
            print("Płatność jest mniejsza niż wartość faktury. Proszę podać datę i kwotę kolejnej płatności.")
 
    return invoice_data
 
def display_results(invoices):
    #Funkcja wyświetlająca wyniki w tabeli.
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Numer faktury")
    table.add_column("Waluta")
    table.add_column("Wartość")
    table.add_column("Kurs w dniu\nwystawienia")
    table.add_column("Data i kurs waluty\nw dniu płatności")
    table.add_column("Różnica kursowa:")
    table.add_column("Status")
    table.add_column("Nadpłata/\nNiedopłata")
    table.add_column("Suma różnic\n kursowych")
 
    for invoice in invoices:
        # Pętla przetwarzająca dane faktury i dodająca wyniki do tabeli.
        total_payments, results = process_invoice(invoice)
        if results is None:
            print_error("Błąd przetwarzania faktury. Pominięto wynik.\n")
            continue
        total_difference = 0
        payment_dates_rates = []
        differences = []
        for result in results:
            issue_rate, payment_date, payment_rate, difference = result
            payment_dates_rates.append(payment_date + " Kurs: " + str(payment_rate))
            difference_str = str(round(difference, 2)) + " PLN"
            total_difference += difference
            if difference > 0:
                difference_str = f"[red]{difference_str}[/red]"
            else:
                difference_str = f"[green]{difference_str}[/green]"
            differences.append(difference_str)
        payment_status_value = invoice['value'] - total_payments  # Obliczamy status płatności.
        if payment_status_value < 0:
            payment_status = "[blue]NADPŁATA[/blue]"
        elif payment_status_value > 0:
            payment_status = "[yellow]NIEDOPŁATA[/yellow]"
        else:
            payment_status = "[green][bold]OK[/bold][/green]"
        total_difference_str = str(round(total_difference, 2)) + " PLN"
        if total_difference > 0:
            total_difference_str = f"[red]{total_difference_str}[/red]"
        else:
            total_difference_str = f"[green]{total_difference_str}[/green]"
        table.add_row(str(invoice['invoice_number']), invoice['currency'], str(invoice['value']), str(issue_rate), '\n'.join(payment_dates_rates), '\n'.join(differences), payment_status, str(payment_status_value), total_difference_str)
        table.add_row("-", "-", "-", "-", "-", "-", "-", "-", "-")  # Dodajemy pusty wiersz jako separator.
    console.print(table)
 
def print_error(msg):
    #Funkcja wyświetlająca komunikat o błędzie.
    console.print(msg, style="bold red")
 
def process_invoice(invoice_data):
    currency = invoice_data['currency']
    issue_date = invoice_data['issue_date']
    payments = invoice_data['payments']
    value = invoice_data['value']
 
    results = []
    total_payments = 0  # Dodajemy zmienną do przechowywania sumy płatności
 
    try:
        for payment in payments:
            payment_date = payment['date']
            payment_value = payment['value']
            total_payments += payment_value  # Aktualizujemy sumę płatności
            issue_rate, payment_rate = get_exchange_rate(currency, issue_date, payment_date)
            if issue_rate is None or payment_rate is None:
                print_error("Nie udało się pobrać kursów walut. Spróbuj ponownie.\n")
                return None
            difference = calculate_exchange_rate_difference(payment_value, currency, issue_date, payment_date)
            results.append((issue_rate, payment_date, payment_rate, difference))
    except Exception as e:
        print_error(f"Wystąpił błąd: {e}")
        return None
 
    return total_payments, results  # Zwracamy sumę płatności oraz wyniki
 
def validate_database(data, required_keys=['invoice_number', 'value', 'currency', 'issue_date', 'payments']):
    missing_keys = []
    for record in data:
        for key in required_keys:
            if key not in record:
                missing_keys.append(key)
    return missing_keys
 
def validate_data(data):
    # Sprawdzenie, czy odczyt pliku był poprawny
    if data is None:
        print_error("Nieprawidłowy format pliku JSON lub plik nie został znaleziony. Spróbuj ponownie.")
        return False
 
    # Walidacja kluczy
    missing_keys = validate_database(data)
    if missing_keys:
        print_error(f"Plik nie zawiera wymaganych kluczy: {', '.join(missing_keys)} Spróbuj ponownie.")
        return False
 
    return True
 
def validate_data(data):
    # Sprawdzenie, czy odczyt pliku był poprawny
    if data is None:
        print_error("Nieprawidłowy format pliku JSON lub plik nie został znaleziony. Spróbuj ponownie.")
        return False

    # Walidacja kluczy
    missing_keys = validate_database(data)
    if missing_keys:
        print_error(f"Plik nie zawiera wymaganych kluczy: {', '.join(missing_keys)} Spróbuj ponownie.")
        return False

    return True

def run_interactive_mode():
    #Funkcja uruchamiająca tryb interaktywny.
    while True:
        invoice_data = get_invoice_data()
        if invoice_data is None:
            continue
        while True:
            correct_input = Prompt.ask("Czy poprawnie wprowadziłeś dane? (t/n) ")
            if correct_input.lower() == 't':
                save_invoice_data(invoice_data)
                display_results([invoice_data]) 
                break
        continue_input = Prompt.ask("Czy chcesz wprowadzić kolejną fakturę? (t/n) ")
        if continue_input.lower() != 't':
            break
 
def run_batch_mode():
    # Funkcja uruchamiająca tryb wsadowy.
    while True:
        file_path = Prompt.ask("Podaj ścieżkę do pliku z danymi: ")
 
        # Sprawdzenie, czy podana ścieżka istnieje
        if not Path(file_path).exists():
            print_error("Podana ścieżka do pliku nie istnieje. Spróbuj ponownie.")
            continue
 
        # Odczyt pliku
        data = read_file(file_path)
 
        # Walidacja i wyświetlanie wyników
        if validate_data(data):
            display_results(data)
            break  # Przerywa pętlę, jeśli plik został wczytany poprawnie
 
    console.input("Naciśnij Enter, aby kontynuować...\n")
 
def main():
    #Funkcja główna programu. Wyświetla menu wyboru trybu pracy.
    console.print("Witaj w programie do obliczania różnic kursowych!\n")
    console.print("Wybierz tryb pracy:\n")
    console.print("1. Tryb interaktywny\n")
    console.print("2. Tryb wsadowy\n")
 
    mode = Prompt.ask("Wybór: ")
    while mode not in ["1", "2"]:
        mode = Prompt.ask("Nieprawidłowy wybór. Wprowadź ponownie: ")
 
    if mode == "1":
        run_interactive_mode()
    elif mode == "2":
        run_batch_mode()
 
if __name__ == '__main__':
    #Wywołanie funkcji głównej programu.
    try:
        main()
    except Exception:
        console.print("Wystąpił błąd:")
        console.print(traceback.format_exc())

        
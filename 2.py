import requests
import csv
import time
import yfinance as yf
from datetime import datetime
import pytz

def fetch_nifty_current_price():
    """Fetches the current NIFTY price using yfinance."""
    ticker = "^NSEI"
    try:
        nifty = yf.Ticker(ticker)
        data = nifty.history(period="1d")
        current_price = data['Close'].iloc[-1]
        return current_price
    except Exception as e:
        print(f"Error fetching NIFTY price: {e}")
        return None

def fetch_option_chain_data():
    """Fetches the option chain data from NSE using web scraping."""
    url = "https://www.nseindia.com/option-chain"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nseindia.com',
    }

    session = requests.Session()
    session.headers.update(headers)

    try:
        response = session.get(url)
        cookies = response.cookies.get_dict()

        option_chain_url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
        response = session.get(option_chain_url, headers=headers, cookies=cookies)
        response.raise_for_status()
        data = response.json()
        return data['records']['data']
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred: {req_err}")
    except ValueError:
        print("Response content is not valid JSON.")
    print("Failed to fetch option chain data after multiple attempts.")
    return None

def filter_strike_prices(option_chain_data, current_price, strike_range, expiry_date):
    """Filters the option chain data to include specified ranges of strike prices."""
    strike_prices = sorted(set([data['strikePrice'] for data in option_chain_data]))
    filtered_data = {}
    for x in strike_range:
        filtered_strikes = [price for price in strike_prices if current_price - x * 50 <= price <= current_price + x * 50]
        filtered_data[x] = [data for data in option_chain_data if data['strikePrice'] in filtered_strikes and data['expiryDate'] == expiry_date]
    return filtered_data

def calculate_pcr(filtered_data):
    """Calculates the PCR (Put-Call Ratio) for different ranges from the filtered option chain data."""
    pcr_values = {}
    difference_values = {}  # New dictionary to store differences

    for x, data in filtered_data.items():
        call_data = [d['CE'] for d in data if 'CE' in d]
        put_data = [d['PE'] for d in data if 'PE' in d]

        total_pe_open_interest = sum(float(d["changeinOpenInterest"]) for d in put_data)
        total_ce_open_interest = sum(float(d["changeinOpenInterest"]) for d in call_data)

        pcr = total_pe_open_interest / total_ce_open_interest if total_ce_open_interest != 0 else 0
        difference = total_pe_open_interest - total_ce_open_interest  # Calculate the difference

        pcr_values[f'pcr{x}'] = pcr
        difference_values[f'difference{x}'] = difference  # Store the difference

    return pcr_values, difference_values  # Return both dictionaries

def calculate_support_resistance(option_chain_data):
    """Calculates the support and resistance levels (s1, s2, s3, r1, r2, r3)."""
    put_data = [data['PE'] for data in option_chain_data if 'PE' in data]
    call_data = [data['CE'] for data in option_chain_data if 'CE' in data]

    put_data.sort(key=lambda d: float(d['openInterest']), reverse=True)
    call_data.sort(key=lambda d: float(d['openInterest']), reverse=True)

    s1 = put_data[0]['strikePrice'] if put_data else None
    s2 = put_data[1]['strikePrice'] if len(put_data) > 1 else None
    s3 = put_data[2]['strikePrice'] if len(put_data) > 2 else None

    r1 = call_data[0]['strikePrice'] if call_data else None
    r2 = call_data[1]['strikePrice'] if len(call_data) > 1 else None
    r3 = call_data[2]['strikePrice'] if len(call_data) > 2 else None

    return s1, s2, s3, r1, r2, r3

def append_to_csv(file_path, pcr_values, difference_values, timestamp, s1, s2, s3, r1, r2, r3):
    """Appends the PCR values, differences, timestamp, and strike prices to a CSV file."""
    try:
        with open(file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            if file.tell() == 0:
                headers = ['Timestamp'] + list(pcr_values.keys()) + list(difference_values.keys()) + ['s1', 's2', 's3', 'r1', 'r2', 'r3']
                writer.writerow(headers)
            row = [timestamp] + list(pcr_values.values()) + list(difference_values.values()) + [s1, s2, s3, r1, r2, r3]
            writer.writerow(row)
        print(f"Data has been appended to {file_path}")
    except IOError:
        print("I/O error")

def print_latest_data(pcr_values, difference_values, s1, s2, s3, r1, r2, r3, prev_pcr_values=None):
    """Prints the latest data and the difference from the previous data."""
    print("\nLatest Data:")
    print(f"Support levels: S1={s1}, S2={s2}, S3={s3}")
    print(f"Resistance levels: R1={r1}, R2={r2}, R3={r3}")

    for key, value in pcr_values.items():
        print(f"{key}: {value:.4f}", end="")
        if prev_pcr_values and key in prev_pcr_values:
            diff = value - prev_pcr_values[key]
            print(f" (Change: {diff:.4f})")
        else:
            print()

    for key, value in difference_values.items():
        print(f"{key}: {value:.4f}")

def main():
    """Main function to fetch, filter, calculate ratios, and write option chain data to a CSV file periodically."""
    current_price = fetch_nifty_current_price()
    if current_price is None:
        print("Failed to fetch current NIFTY price. Exiting...")
        return

    print(f"Current NIFTY Price: {current_price}")

    option_chain_data = fetch_option_chain_data()
    if option_chain_data is None:
        print("Failed to fetch option chain data. Exiting...")
        return

    expiry_dates = sorted(set(data['expiryDate'] for data in option_chain_data))
    print(f"Expiry Dates: {expiry_dates}")

    expiry_date_input = input(f"Please enter your desired expiry date from the list above (YYYY-MM-DD): ")
    if expiry_date_input not in expiry_dates:
        print("Invalid expiry date. Please enter a valid date from the list.")
        return

    current_date = datetime.now().strftime('%Y-%m-%d')
    output_file_path = f'realtime_pcr_data_{current_date}_expiry_{expiry_date_input}.csv'

    strike_ranges = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30]

    prev_pcr_values = None

    while True:
        option_chain_data = fetch_option_chain_data()
        if option_chain_data is None:
            print("Failed to fetch option chain data. Exiting...")
            return

        filtered_data = filter_strike_prices(option_chain_data, current_price, strike_ranges, expiry_date_input)

        pcr_values, difference_values = calculate_pcr(filtered_data)

        s1, s2, s3, r1, r2, r3 = calculate_support_resistance(option_chain_data)

        ist = pytz.timezone('Asia/Kolkata')
        timestamp = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')

        print_latest_data(pcr_values, difference_values, s1, s2, s3, r1, r2, r3, prev_pcr_values)

        append_to_csv(output_file_path, pcr_values, difference_values, timestamp, s1, s2, s3, r1, r2, r3)

        prev_pcr_values = pcr_values.copy()

        time.sleep(30)

if __name__ == "__main__":
    main()

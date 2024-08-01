import requests
import csv
import time
from datetime import datetime
import pytz

def fetch_nifty_data():
    """Fetches NIFTY data including volume from NSE."""
    url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
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
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching NIFTY data: {e}")
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
    difference_values = {}

    for x, data in filtered_data.items():
        call_data = [d['CE'] for d in data if 'CE' in d]
        put_data = [d['PE'] for d in data if 'PE' in d]

        total_pe_open_interest = sum(float(d["changeinOpenInterest"]) for d in put_data)
        total_ce_open_interest = sum(float(d["changeinOpenInterest"]) for d in call_data)

        pcr = total_pe_open_interest / total_ce_open_interest if total_ce_open_interest != 0 else 0
        difference = total_pe_open_interest - total_ce_open_interest

        pcr_values[f'pcr{x}'] = pcr
        difference_values[f'difference{x}'] = difference

    return pcr_values, difference_values

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

def calculate_vwap(nifty_data):
    """Calculates VWAP from NIFTY data."""
    if not nifty_data or 'data' not in nifty_data or len(nifty_data['data']) == 0:
        return None
    
    data = nifty_data['data'][0]
    if 'lastPrice' not in data or 'totalTradedVolume' not in data or 'totalTradedValue' not in data:
        return None
    
    total_traded_value = float(data['totalTradedValue'])
    total_traded_volume = float(data['totalTradedVolume'])
    
    vwap = total_traded_value / total_traded_volume if total_traded_volume != 0 else None
    
    return vwap

def append_to_csv(file_path, pcr_values, difference_values, timestamp, s1, s2, s3, r1, r2, r3, current_price, vwap):
    """Appends the PCR values, differences, timestamp, strike prices, current price, and VWAP to a CSV file."""
    try:
        with open(file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            if file.tell() == 0:
                headers = ['Timestamp'] + list(pcr_values.keys()) + list(difference_values.keys()) + ['s1', 's2', 's3', 'r1', 'r2', 'r3', 'Price', 'VWAP']
                writer.writerow(headers)
            row = [timestamp] + list(pcr_values.values()) + list(difference_values.values()) + [s1, s2, s3, r1, r2, r3, current_price, vwap]
            writer.writerow(row)
        print(f"Data has been appended to {file_path}")
    except IOError:
        print("I/O error")

def print_latest_data(pcr_values, difference_values, s1, s2, s3, r1, r2, r3, current_price, vwap, prev_pcr_values=None):
    """Prints the latest data and the difference from the previous data."""
    print("\nLatest Data:")
    print(f"Current Price: {current_price}")
    print(f"VWAP: {vwap}")
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
    nifty_data = fetch_nifty_data()
    if nifty_data is None or 'data' not in nifty_data or len(nifty_data['data']) == 0:
        print("Failed to fetch NIFTY data. Exiting...")
        return

    current_price = float(nifty_data['data'][0]['lastPrice'])
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
    ist_price = float(nifty_data['data'][0]['lastPrice'])
    old_vwap = calculate_vwap(nifty_data)


    while True:
        nifty_data = fetch_nifty_data()
        if nifty_data is None or 'data' not in nifty_data or len(nifty_data['data']) == 0:
            print("Failed to fetch NIFTY data. Skipping this iteration...")
            time.sleep(30)
            continue

        current_price = float(nifty_data['data'][0]['lastPrice'])
        option_chain_data = fetch_option_chain_data()
        if option_chain_data is None:
            print("Failed to fetch option chain data. Skipping this iteration...")
            time.sleep(30)
            continue

        filtered_data = filter_strike_prices(option_chain_data, current_price, strike_ranges, expiry_date_input)

        pcr_values, difference_values = calculate_pcr(filtered_data)

        s1, s2, s3, r1, r2, r3 = calculate_support_resistance(option_chain_data)

        vwapdiff = calculate_vwap(nifty_data)
        vwap = (old_vwap - vwapdiff) + ist_price
        if vwap is None:
            print("Unable to calculate VWAP")
            vwap_value = "N/A"
        else:
            print(f"VWAP: {vwap:.2f}")
            vwap_value = vwap

        ist = pytz.timezone('Asia/Kolkata')
        timestamp = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')

        print_latest_data(pcr_values, difference_values, s1, s2, s3, r1, r2, r3, current_price, vwap_value, prev_pcr_values)

        append_to_csv(output_file_path, pcr_values, difference_values, timestamp, s1, s2, s3, r1, r2, r3, current_price, vwap_value)

        prev_pcr_values = pcr_values.copy()

        time.sleep(30)

if __name__ == "__main__":
    main()
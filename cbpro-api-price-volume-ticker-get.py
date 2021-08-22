#!/usr/bin/python
#title			:cbpro-api-price-volume-ticker-get.py
#description	:This code pulls in price and volume to a csv
# file set in defines.py. Uses the Coinbase Pro API.
#author			:Erick Clasen
#date			:20210822
#version		:0.1
#usage			:cbpro-api-price-volume-ticker-get.py

#notes			: Outputs to a csv determined by defines.py
#python_version	: 2.7.6
#python_version	: Python 3.4.3
#==============================================================================
import cbpro
import csv
import time
import json
import warnings
import random
import debugtrace as dt

#from defines import key
#from defines import b64secret
#from defines import passphrase

warnings.filterwarnings("ignore")
#ticker_filename = "test.csv" #"/home/erick/www/btc/cbpro_crypto_price_volume_file.csv"

from defines import ticker_filename


def robust_ticker_get(product):
        ''' Take in the product in prodcuct id form and robustly gets the ticker.
            Tries up to MAX_RETRIES, if it still fails it will impute the values.
            It also allows a random sleep time between retries. RTNS: ticker dict'''    

        count = 0   #1
        ticker = None
        MAX_RETRIES = 30
        impute = False

        # Try to keep getting the ticker up to 30 times with a sleep in between.
        while count < MAX_RETRIES: # and ticker == None:
                print(count)
                ticker = auth_client.get_product_ticker(product_id=product)

                # For now just retry over again on a message without price and volume...
                if 'message' in ticker and ('price' not in ticker or 'volume' not in ticker):
                        dt.d_trace('MESSAGE_DEBUG',(product,count,ticker))
                        #impute = True
                        count += 1
                        time.sleep(random.random())
                        #raise Exception('MESSAGE_DEBUG',(product,count,ticker))
                        #quit()
                       
                elif 'price' in ticker and 'volume' in ticker: # Good to go bail out of while.
                        print(product,ticker['price'],ticker['size'],ticker['volume'])
                        count = MAX_RETRIES + 1
                else: # All else just keep trying again.
                        dt.d_trace('ELSE_CASE_DEBUG',(product,count,ticker))
                        count += 1
                        time.sleep(random.random())
        
                time.sleep(random.random()/5)

                #except: # Key Error
                #        print("Retry, Fail Read: ",product,count,ticker)
                #        count += 1
                #        time.sleep(random.random())
                #        # Hack to record failures.
                #        live_dict['RETRY_DEBUG'] = (product,count)
                #        dt.d_trace('RETRY_DEBUG',(product,count,ticker))

                # If the count has hit the maximum number of retries then impute the value from the
                # past value.
                if (count == MAX_RETRIES or impute == True) and ('price' not in ticker or 'volume' not in ticker):

                        count = MAX_RETRIES

                        # Self healing, impute the missing value.
                        # The only time this is not done is if the time can't be read, then we assume
                        # failure and stay in a loop trying to read the time.
                        live_dict['IMPUTE_DEBUG'] = product
                        dt.d_trace('IMPUTE_DEBUG',(product,count,ticker))

                        ticker['price'] = live_dict[product][0]
                        ticker['volume'] = live_dict[product][1]
                        print("This is the ticker at impute",ticker)
                        print("Comm failure at:",product) # Impute value from last history.
                        # Hack to record failures.

        print(count)

        return ticker


def live_dict_read():
    ''' Reads in a dictionary of live values plus debug keys and values if present.
        This dictionary will be used to impute values if there is a failure to get
        in a price or volume. RTNS the live dict. '''
        
    live_dict = {}
    # If the file exists read it in, if not just create it on the first pass through.
    try:
            with open("live_dict.json") as f_obj:
                    live_dict = json.load(f_obj)
    except:
            #with open(filename, 'w') as f_obj:
            #        json.dump(ichimoku_state,f_obj)
            print("Missing FIle for live dict. Need to create a live dict. Will create of first run through.")        

    return live_dict    


def live_dict_write(live_dict):
        ''' Takes in the live dict and does a json dump to file to save for use next round. '''
        with open("live_dict.json", 'w') as f_obj:
                json.dump(live_dict,f_obj)


def get_time_from_cbpro_robust():
        ''' Robust retrieval of the ticker time from CBPRO. It will stay in a loop for up to
            MAX_RETRIES. Returns the time. '''
        cbp_time = None
        debug_time_ct = 0
        MAX_RETRIES = 100

        # Robust time read keep trying to read in until hits MAX_RETRIES, then end.
        while cbp_time == None and debug_time_ct < MAX_RETRIES:
                try:
                        cbp_time = auth_client.get_time()
                except:
                        time.sleep(random.random()*10)
                        debug_time_ct +=1
                        # Set and save a debug...
                        live_dict['TIME_DEBUG'] = debug_time_ct
                        live_dict_write(live_dict)
                        dt.d_trace('TIME_DEBUG',debug_time_ct)

                        raise Exception("Can't get CBPro Time. No connection.",debug_time_ct)


        return cbp_time


def output_price_volume_csv(out_list):
        with open(ticker_filename, mode='a') as outfile:
                output_writer = csv.writer(outfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

                output_writer.writerow(out_list)

#-------------------------------------- main. -----------------------------------

# THe out list is what is built up by appending to it and will get saved as a CSV file.
out_list = []

# Live value dict. This is used to impute a value in case of a comm failure.
live_dict = {}

# Pull in the live dict in case values need imputing.
live_dict = live_dict_read()

public_client = cbpro.PublicClient()
auth_client = public_client
#auth_client = cbpro.AuthenticatedClient(key, b64secret, passphrase)
#public_client = auth_client
#products = public_client.get_products()
#print(products)




# Grab the official cbpro timestamp and use the iso of it below.
cbp_time =  get_time_from_cbpro_robust()

# Print the time to show what CBPRO time is.
print(cbp_time['iso'])
print('\n')

# Append the items to the outlist for saving to the CSV file.
# Time
out_list.append(cbp_time['iso'])



# Get the product ticker for a specific product.
#print("\nBTC Ticker ---------------------------------------------------------")
''' This is the entire btc_ticker dictionary for an example to work off of {u'bid': u'6680', u'volume': u'5173.11329291', u'trade_id': 49678579, u'time': u'2018-08-26T23:16:52.652000Z', u'ask': u'6680.01', u'price': u'6680.01000000', u'size': u'0.01432357'}  '''


# FIRST do the legacy products as they are not the same format as the rest of the coins.
product_list = ['BTC-USD','BCH-USD','ETC-USD','ETH-USD','LTC-USD']

# Legacy, the first 5 products have prices followed by volumes.
print("Legacy Price\n")
for product in product_list:

        ticker = robust_ticker_get(product)

        out_list.append(ticker['price'])
        #out_list.append(ticker['volume'])
        live_dict[product] = (ticker['price'],0)



print("Legacy Volume\n")
for product in product_list:

        ticker = robust_ticker_get(product)

        #out_list.append(ticker['price'])
        out_list.append(ticker['volume'])

# Now do the regular coins by first getting a revised product_list.
product_list = ['BAND-USD','DAI-USD','XLM-USD','LINK-USD','ALGO-USD','ATOM-USD','OXT-USD','ZEC-USD','BAT-USDC','CVC-USDC','GNT-USDC','MANA-USDC','LOOM-USDC','CGLD-USD','KNC-USD','OMG-USD','ZRX-USD','FIL-USD','NU-USD','NMR-USD','UMA-USD','ADA-USD','UNI-USD','EOS-USD','AAVE-USD','XTZ-USD','MKR-USD','COMP-USD','YFI-USD','SNX-USD','OGN-USD','LRC-USD','REN-USD','BAL-USD','GRT-USD','BNT-USD','NKN-USD','MATIC-USD','SKL-USD','ANKR-USD','STORJ-USD']
print("Current Coins\n")

for product in product_list:

        ticker = robust_ticker_get(product)

        out_list.append(ticker['price'])
        out_list.append(ticker['volume'])
        live_dict[product] = (ticker['price'],ticker['volume'])

print("\n\n",out_list)
print("\n\n",live_dict)


# Open the CSV file and output a row using the out_list
output_price_volume_csv(out_list)

# Store a copy of the prices and volumes in a dict with the product label as the key, in 
# case a read fails the next time, the values will then be imputed as the previoud one
# from the live dict.
live_dict_write(live_dict)



quit()

# New ones as of 10/1/2019
# XLM-USD''LINK-USD''ALGO-USD'

# New Ones as of 2/18/2020
#ATOM-USD'
# New Ones as of 8/14/2020
#OXT-USD''ZEC-BTC'

#'BAT-USDC''CVC-USDC''GNT-USDC''MANA-USDC''LOOM-USDC''CGLD-USD'

# 11/12/2020, OMG, OX and Kyer coins for USD and BTC trading pairs.
#'KNC-USD''OMG-USD''ZRX-USD'

# 12/28/2020, FIL and NU coins for USD and BTC trading pairs.
#'FIL-USD''NU-USD'


# 2/22/2021, ns for USD and BTC pairs
#'NMR-USD''UMA-USD'

# 4/02/2021. CBPRO has added like 15 or so coins. Not going to add all of them.
# Just adding ones in the top 30ish on Coinmarketcap for now.
#'ADA-USD''UNI-USD''EOS-USD''AAVE-USD''XTZ-USD'

# ADD a few more that trade at a decent $ amount for good meause

#'MKR-USD''COMP-USD'YFI-USD''SNX-USD'
  

# Newer ones, new format
#out_list.append(xrp_ticker['price'])
#out_list.append(xrp_ticker['volume'])
# XRP REMOVED
#out_list.append(0)
#out_list.append(0)

#out_list.append(dai_ticker['price'])
#out_list.append(dai_ticker['volume'])

# 10/1/2019
#out_list.append(xlm_ticker['price'])
#out_list.append(xlm_ticker['volume'])
# Open the CSV file and output a row using the out_list

with open(ticker_filename, mode='a') as outfile:
    output_writer = csv.writer(outfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

    output_writer.writerow(out_list)


dt.d_trace('RETRY_DEBUG',(product,count))


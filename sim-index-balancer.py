#!/usr/bin/python
#title			:sim-index-balancer.py
#description	:This code allows an automatically balanced index fund with risk management to be run using the Coinbase Pro API.
#author			:Erick Clasen
#date			:20210822
#version		:0.1
#usage			:python sim-index-balancer.py key b64secret passphrase
#notes			:
#python_version	: 2.7.6
#python_version	: Python 3.4.3
#==============================================================================
import sys
import cbpro
import pprint
import json
import csv


import coretamodule as cm   # Core module, holds all the common code used for the ensemble of trading algorithms
import cbpro_buy_sell as cbs


from defines import ticker_filename
from defines import FILL_SCALER # 1.0 is normal 100% fill, reduce to trim portfolio.                          

# Soft stop loss fades out trades if below the fade u of index value to complete off below
# fade l. It scales the fill scaler.
from defines import FADE_U
from defines import FADE_L
from defines import NO_BUY_ZONE_U

# FOR A-B TEST Over ride these.
FADE_U,FADE_L,NO_BUY_ZONE_U = -1,-1,-1


from datetime import datetime


def record_round_trip_transaction(time_string,action,currency,underlying,currency_price,asset_held,idx_target,trade_amount,index_value,trans_string):

    out_list = []

    # Summary File Name, all in one log. Code with the first 6 chars of key and the filename too.
    sfilename = "summary-"+key[:6]+"-"+this_file+".log"

    # Record it...
    # Tag it with the first 6 characters of the auth key and then the filename...       

    if action == 'SELL':
        filename = key[:6]+"-"+this_file+"-sell-"+underlying[1]+".log"
    elif action == 'BUY':
        filename = key[:6]+"-"+this_file+"-buy-"+underlying[0]+".log"
    else:
        raise Exception("BAD BS FLAG")

    # Logs are stored in a standard format of time,action (BUY or SELL) and the currency price. This is follo$
    #and lastly the dictionaries, that the exchange reports back.

    out_list.append(time_string)
    out_list.append(action)
    out_list.append(currency+"-"+underlying[0]+":"+underlying[1])
    out_list.append(str(round(currency_price,10)))
    out_list.append(str(round(asset_held,2)))
    out_list.append(str(round(idx_target,2)))
    out_list.append(str(round(trade_amount,2)))
    out_list.append(str(round(index_value,2)))

    # If there is a message from cbpro, show it.
    if 'message' in trans_string:
        out_list.append(trans_string)


    #Open the CSV file and output a row using the out_list
    with open(filename, mode='a') as outfile:
        output_writer = csv.writer(outfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        output_writer.writerow(out_list)

    # Ditto for summary log file.
    with open(sfilename, mode='a') as outfile:
        output_writer = csv.writer(outfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        output_writer.writerow(out_list)


    out_list.append("")
    out_list.append("")
    out_list.append("                     ")
    out_list.append(trans_string)



    # Open the CSV file and output a row using the out_list
    with open('verbose-'+filename, mode='a') as outfile:
        output_writer = csv.writer(outfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        output_writer.writerow(out_list)



def cbpro_read_available(price_dict,auth_client):

    accts = ''

    # Keeping score with these vars which will be running totals
    total_avail = 0
    total_held = 0

    accts = auth_client.get_accounts()

    #print(accts)
    #quit()     
    # Header
    asset_dict = {}   

    print("")
    print('Currency',' Price',"\t", 'Available',' Hold',"\t",'Avail in USD',' Held in USD')
    
    for j in range(0,len(accts)):


        # If not a fiat, then calculate the availavle and held and make a running total.
        # Then print out a formatted summary.
        if accts[j]['currency'] != 'USDC' and accts[j]['currency'] != 'USD':

                try:
                        asset_avail = price_dict[accts[j]['currency']+" Price"] * float(accts[j]['available'])
                except KeyError:
                        continue

                asset_held = price_dict[accts[j]['currency']+" Price"] * float(accts[j]['hold'])
                total_avail += asset_avail
                total_held += asset_held

                if asset_held > 0:               
                        print(accts[j]['currency'],round(price_dict[accts[j]['currency']+" Price"],6),"\t\t", round(float(accts[j]['available']),2),round(float(accts[j]['hold']),2),"\t\t\t",round(asset_avail,2),round(asset_held,2))
                else:
                        print(accts[j]['currency'],round(price_dict[accts[j]['currency']+" Price"],6),"\t\t", round(float(accts[j]['available']),2),round(float(accts[j]['hold']),2),"\t\t\t",round(asset_avail,2))



        else: # SPecial case for FIAT's where the price is a unit of 1 and not read in at all from the price list of dicts.   
            print(accts[j]['currency'],"\t\t\t",round(float(accts[j]['available']),2),round(float(accts[j]['hold']),2))
            asset_avail = float(accts[j]['available'])
            asset_held = float(accts[j]['hold'])
            total_avail += asset_avail
            total_held += asset_held            

        # Total tied to asset.
        total_for_asset = asset_avail # + asset_held, can't use asset held, gets it out of balance.
        # Save it in a dictionary for use later on in the main code to adjust from.
        asset_dict[accts[j]['currency']] = total_for_asset 
        
    # Print out a summary of the available and held and the total
    print("")
    print("Total Available in USD: ",round(total_avail,2))
    print("Total Held in USD: ",round(total_held,2))
    print("Portfolio Size in USD: ",round(total_held+total_avail,2))
    print("Average size of asset in USD",round((total_held+total_avail)/len(accts),2))  
    return round(total_held+total_avail,2),asset_dict


def cbpro_limit_order_gtt_1(auth_client,side,f_price,f_size,product_label='BTC-USD'):
    '''Place a limit order by specifying price of asset and size to sell. 
       Alternatively, `size` could be used to specify quantity in BTC amount.'''
    record = auth_client.place_limit_order(product_label,
                                  side,
                                  price=str(f_price),
                                  size=str(f_size),
                                  time_in_force='GTT',
                                  cancel_after='hour')
    return record

def index_value_get(price_list):
        ''' Take in a list of prices and compute the index value as a basket of assets. '''
        # The index scaler as calculated on 02/01/2021 via the index-scaler.py code
        index_scaler = {'BTC': 1.2948351898809769e-06, 'BCH': 0.00010715265395693321, 'ETC': 0.005779378023337128, 'ETH': 3.303819215012555e-05, 'LTC': 0.0003332689013457398, 'DAI': 0.04345870445256156, 'XLM': 0.1368368305634366, 'LINK': 0.0019502758831010096, 'ALGO': 0.06871860418771174, 'ATOM': 0.005323651386012638, 'OXT': 0.12584156546907443, 'ZEC': 0.000498396916813309, 'BAT': 0.14554708164274333, 'CVC': 0.2871046102971217, 'GNT': 0.2645354981507646, 'MANA': 0.2889746629905236, 'LOOM': 0.6658232904987016, 'CGLD': 0.015614947877303985, 'KNC': 0.03362587847607519, 'OMG': 0.012470818285212602, 'ZRX': 0.06480732296826613, 'FIL': 0.001938890438924079, 'NU': 0.14377731769036117}
        index_value = 0
        for key in index_scaler:
                #print(price_dict[key+" Price"]*new_dict[key]) # Debug
                index_value += price_list[key+" Price"]*index_scaler[key]

        return index_value


def soft_stop_loss(FILL_SCALER,index_value,FADE_L,FADE_U):
        ''' Tunable lower limit under which the index balancer will scale out to zero.
            Mostly for emergency protection in hot mkts. Passes FILL SCLAER through
            modifies it if needed on the way through.'''

        # IF the index_value is in the bounds fade u to l, use linear scaling across.
        # fade u and l by subtracting fade l from the index value and normalizing by
        # dividing the size of the fade u to l range into it. This gives a linear 
        # decrease from the full index value near zero across the range.
        if index_value > FADE_L and index_value < FADE_U:
                FILL_SCALER = FILL_SCALER * (index_value - FADE_L) /(FADE_U-FADE_L)
                print("\n\t**** Fading Fill scaler:",round(index_value,2),round(FILL_SCALER,2))

        elif index_value < FADE_L: # KILL trading below this FADE_L index level.
                FILL_SCALER = 0
                print("\n\t**** Stopped Out Low Index V below FADE_L:",round(index_value,2),FADE_L)

        return FILL_SCALER


def stddev(list):
    ''' Calculate the standard deviation for a list using the last period of values.
        Typical usage is to take the stddev of the last period items in a price list'''
    variance = 0

    mean = sum(list)/len(list) # Mean avg

    # Calculate the variance aas a summation across the list of the difference of the value from the mean.
    # Sqaured.          
    for n in range(0,len(list),1):
        variance += pow((list[n] - mean),2)

    # The stddev is the average variance squared.
    return pow(variance/len(list),0.5)



def average_price(currency,price_list_of_dicts):
    ''' Calculate the average price of an asset for a time period denoted by PERIOD.
        Takes in the price list of dictionaries for all prices and parses out a list of
        prices for a currency, then does the return ratio math and returns the result. '''

    
    currency_price_list = []
    
    # Pull out the prices from the list
    for line in price_list_of_dicts:
        currency_price_list.append(line[currency+" Price"])

    # Return the mean average of the prices.    
    return sum(currency_price_list)/len(currency_price_list)



def return_ratio(currency,price_list_of_dicts):
    ''' Calculate the return ration of an asset for a time period denoted by PERIOD.
        Takes in the price list of dictionaries for all prices and parses out a list of
        prices for a currency, then does the return ratio math and returns the result. '''

    
    currency_price_list = []
    
    # Pull out the prices from the list.
    for line in price_list_of_dicts:
        if line != 'USD':
            currency_price_list.append(line[currency+" Price"])

    # Returns the last price divided by the first price.
    # Choose a safe value here, if there is a div/0 potential from unit'd coins.
    # Use 1 as a rtn ratio if there is an issue.
    if currency_price_list[0] > 0:
	    rtn = currency_price_list[-1]/currency_price_list[0]
    else:
	    rtn = 1	

    #print('stddev',stddev(currency_price_list))      

    # Divide the returns by the std dev.
    return rtn/stddev(currency_price_list) # Return the return ratio
        
#def return_ratio_of_idx(price_list_of_dicts):
#    ''' Calculate the return ratio of the index for a time period denoted by PERIOD.
#        Takes in the price list of dictionaries for all prices and parses out a list of
#        prices for a currency, then does the return ratio math and returns the result. '''
#
#    
#    currency_price_list = []
#    
#    # Pull out the prices
#    for line in price_list_of_dicts:
#        currency_price_list.append(index_value_get(line))
#
#    rtn = currency_price_list[-1]/currency_price_list[0]
#
#    #print('stddev',stddev(currency_price_list))      
#
#    return rtn/stddev(currency_price_list) # Return the return ratio


def risk_scaling(price_list_of_dicts,asset_dict,PERIOD=720):
    ''' Take the asset dict and calculate the returns for each asset and stuff into a dictionary for 
         a risk scaler which is normalized by multiplying by price. Note: prob don't need to norm it.
        As the risk norm const prob would do it for us.

        Then a risk norm const needs to be made which is the sum of the risk scaler values divided by
        the length of the dict.

        Create a final normed risk scaler by dividing all of the dict risk scaler values by the norm
        const, so that they are normalized. Store in a final dict to be used and returned.'''

    risk_scaler = {}

    # Calculate out a dictionary full of return ratios for a time period
    for asset in asset_dict:
        if asset != 'USD':
            rr_asset = return_ratio(asset,price_list_of_dicts[-PERIOD:])

            avg_asset_price = average_price(asset,price_list_of_dicts[-PERIOD:])

            #print(asset+" Scaled:",rr_asset*avg_asset_price)
            risk_scaler[asset] = rr_asset*avg_asset_price


    # Take the average for the normalization. By summing the dict values and div by length.
    # This will normalize the values in the risk_scaler dict for all assets.
    risk_norm_const = sum(risk_scaler.values())/len(risk_scaler)

    #print(risk_scaler)

    # Finally normalize a dict full of risk scaler values to be used via rtn to the fxn of origin.      
    normed_risk_scaler = {}
    # Do the normalization by taking the risk scaler and normalizing it via the const derived previosuly.
    for asset in risk_scaler:
        normed_risk_scaler[asset] = risk_scaler[asset]/risk_norm_const


    #print(normed_risk_scaler)

    return normed_risk_scaler
    


def trend_scaler(price_list,currency):
        ''' This fxn takes in the currency price list and then uses an ensemble of
        moving avgs to score a bullish trend and increase the commitment to the trade
        by progressivly scaling in. Returns the scaler value and a debug icon list
        that will indicate what is sctive as far as scaling in. '''

        currency_price_list = []

        # Slice out a list from the list of dictionaries using a loop. Might be a b$
        for line in price_list:
                currency_price_list.append(line[currency+' Price'])



        # A list for the averages to be held in.
        sma = []

        # Pull out the various moving averages to be used to create the scaler value.
        for n in (10*24,20*24,50*24,60*24):
                #print(cm.simple_mov_avg(currency_price_list,n))
                sma.append(cm.simple_mov_avg(currency_price_list,n))

        # How much to push up the scaler per unit of bullish trend score.
        SCALE_STEP = 0.17

        # Base value to start out with
        scaler_value = 0.2


        # This forms the icon that is shown. Preload with zeros
        scaler_icon = [0,0,0,0,0]

        # Test all of the smas that make sense to check for a bull trend on each
        # and scale in the value for each score of bullishness. Plue make a debug icon
        # that shows which ones are active.
        # This method allows boosting as well, going above unity.
        if sma[0] > sma[1]: # 10>20
                scaler_value += SCALE_STEP
                scaler_icon[0] = 1

        if sma[0] > sma[2]: # 10>50
                scaler_value += SCALE_STEP
                scaler_icon[1] = 1

        if sma[0] > sma[3]: # 10 > 60
                scaler_value += SCALE_STEP
                scaler_icon[2] = 1

        if sma[1] > sma[2]: # 20 > 50
                scaler_value += SCALE_STEP
                scaler_icon[3] = 1

        if sma[1] > sma[3]: # 20 > 60
                scaler_value += SCALE_STEP
                scaler_icon[4] = 1


        return scaler_value,scaler_icon


# --------------- main. ----------------            
TARGET_DEADBAND = 0.1
BUY_THRESHOLD_SCALER = 1 - TARGET_DEADBAND
SELL_THRESHOLD_SCALER = 1 + TARGET_DEADBAND
TRADE_SCALE_TEST = 1 + TARGET_DEADBAND

ORDER_AMT_SCALER = 0.97
PERIOD = 720 # Period over which the risk/reward is scaled 30 days.

# Get in the name of this file along with the credentials for authorized trading on cbpro.
# This will error out if anything is missing, no traps just regular errors.
this_file,key,b64secret,passphrase = sys.argv

# Pull in the data.
price_list_of_dicts = cm.read_lines_from_csv_file(ticker_filename)




# Only need the last line of the data for this algo. Print a summary too.
current_prices = price_list_of_dicts[-1]
print(current_prices)

# Get teh index value and show it.
index_value = index_value_get(current_prices)
print("\n"+key[:6]+" Key Code \tIndex Value:",round(index_value,2))

# Authorize with keys...
auth_client = cbpro.AuthenticatedClient(key, b64secret, passphrase)

# What is the total amount of assets held in USD. Asset dict is the holds by individual asset.
total,asset_dict = cbpro_read_available(current_prices,auth_client)

# XRP is MIA from now on.
print("\nRemove XRP and DAI")
del asset_dict['XRP']
del asset_dict['DAI']

print("\n\n-----Index Fund Balancing-----\n")
# DO a sanity check
print("\n\nTotal by regular calc vs total by sum of dict values:",total,sum(asset_dict.values()),"\n",asset_dict)

# Create a 'sort of' target that has ALL in, including USDC.
idx_target = total/len(asset_dict)
print("\nPrint Target (with USD+USDC) and How Many Assets:",round(idx_target,2),len(asset_dict))

# Remove the underlying's after daving the amounts off to check for availability when making a trade
usd_avail = asset_dict['USD']
usdc_avail = asset_dict['USDC']
print("\nUSD and USDC Available:",round(usd_avail,2), round(usdc_avail,2))

# Remove USDC that way USD is the only underlying present in the target calculation
del asset_dict['USDC']

print("\nHow much in holds including USD: ",round(sum(asset_dict.values()),2))

# OPtional scaling of fill scaler if the index value falls below a target into a band where it
# will fade out to a full stop loss.
FILL_SCALER = soft_stop_loss(FILL_SCALER,index_value,FADE_L,FADE_U)



# Get the real target, with USD only and the cryptos in it.
idx_target = FILL_SCALER * sum(asset_dict.values())/(len(asset_dict)+1) # ??? plus 1 ???


#idx_target = sum(asset_dict.values())/len(asset_dict)
print("\nPrint Target (with USD) and How Many Assets:",round(idx_target,2),len(asset_dict))

# Now remove USD as we can't self trade with it.
del asset_dict['USD']

# Primary list of coins that   MUST   trade under USDC.
usdc_list_manditory = ['BAT','CVC','GNT','LOOM','MANA']
# Expanded list of coins that   CAN   trade under USDC.
usdc_list_optional = ['BTC','ETH','ZEC']
print("\nTrading via USDC underlying: ",usdc_list_manditory,usdc_list_optional)

# Find the ratio of the count of the assets that are trading #USDC/USD and how
# much is available in each one to trade.
usdc_asset_len = len(usdc_list_manditory) + len(usdc_list_optional)
usdc_usd_asset_count_ratio = usdc_asset_len/(len(asset_dict)-usdc_asset_len) # The ratio of USDC assets to USD, a count
usdc_usd_avail_ratio = usdc_avail/usd_avail # Ratio of amounts avail.
print("\nRatios, USDC/USD counts and USDC/USD avail",round(usdc_usd_asset_count_ratio,2),round(usdc_usd_avail_ratio,2))
print() # Whitespace


#del asset_dict['BTC'] # BTC @ 0.001 is to big of a trade now, do it manually, not by algo.

for asset in asset_dict:

        print()

        # The trend scaler will scale in the trade more when in a bull trend.
        trend_s,trend_icon = trend_scaler(price_list_of_dicts,asset)
        print(asset+" Trend Scaler: ",round(trend_s,2),trend_icon)

        idx_target_f = idx_target * trend_s * risk_scaling(price_list_of_dicts,asset_dict)[asset]
        #print(idx_target_f)
        print(asset+" Risk Scaler: ",round(risk_scaling(price_list_of_dicts,asset_dict)[asset],2),round(idx_target_f,2))
        

        if asset in usdc_list_optional:
                if usdc_usd_asset_count_ratio < usdc_usd_avail_ratio:
                        underlying = ("USDC","USD") # SCALE IN
                        underlying_avail = usdc_avail # Buy via USDC
                        print("\tScale IN")
                else:
                        underlying = ("USD","USDC") # SCALE OUT
                        underlying_avail = usd_avail # Buy via USD.
                        print("\tScale OUT")


                #underlying = ("USDC","USDC") # Normal
                #underlying_avail = usdc_avail # Buy via USDC

                #underlying = ("USD","USD") # Only if all into USD
                #underlying_avail = usd_avail # Buy via USD.


        elif asset in usdc_list_manditory:
                underlying = ("USDC","USDC")
                underlying_avail = usdc_avail
        else:
                underlying = ("USD","USD")
                underlying_avail = usd_avail


        current_price = current_prices[asset+" Price"]


        # BUY if below the index target by lets day 10%, only if the index value is above the no buy zone.
        if asset_dict[asset] < idx_target_f * BUY_THRESHOLD_SCALER and index_value > NO_BUY_ZONE_U:
                action = "BUY"
                print(asset,round(asset_dict[asset],2),"\t",action)
                trade_amount = (idx_target_f - asset_dict[asset]) * ORDER_AMT_SCALER

        elif asset_dict[asset] > idx_target_f * SELL_THRESHOLD_SCALER:
                action = "SELL"

                print(asset,round(asset_dict[asset],2),"\t",action)
                trade_amount = (asset_dict[asset]  - idx_target_f) * ORDER_AMT_SCALER
        elif index_value < NO_BUY_ZONE_U: # NOOP
                print("NO BUY ZONE: ",asset,round(asset_dict[asset],2))
                action = "" # NOOP
        else: # NOOP
                print(asset,round(asset_dict[asset],2))
                action = "" # NOOP


        
        # At this point do a buy or sell.
        if action == 'BUY':
            # Check if enough underlying is available.
            if underlying_avail < trade_amount:
                    print("Not enough "+underlying+" available, break! ",underlying_avail)
                    continue
            size,buy_price,sell_price = cbs.calculate_trade_size_and_price(asset,current_prices[asset+" Price"],trade_amount,asset_dict[asset])
            # Have to do a final test to check on the trade size to make sure it is not out of bounds.
            # This was seen on BTC only trades at 0.001 size or larger.
            if buy_price * size > trade_amount * TRADE_SCALE_TEST:
                print(asset+" Trade size is too large "+str(buy_price*size)+" to buy now: ",buy_price,size,trade_amount * TRADE_SCALE_TEST)                    
                continue
            #cbpro_rtn_dict = cbs.cbpro_limit_order_gtt(auth_client,action.lower(),buy_price,size,product_label=asset+"-"+underlying[0]) # TAG-BUY

        elif action == 'SELL':
            # Check if enough underlying is available.
            if asset_dict[asset] < trade_amount:
                    print("Not enough "+asset+"-"+underlying+" available, break! ",underlying_avail)
                    continue
            size,buy_price,sell_price = cbs.calculate_trade_size_and_price(asset,current_prices[asset+" Price"],trade_amount,asset_dict[asset])
            # Have to do a final test to check on the trade size to make sure it is not out of bo$
            # This was seen on BTC only trades at 0.001 size or larger.
            if sell_price * size > trade_amount * TRADE_SCALE_TEST:
                print(asset+" Trade size is too large "+str(sell_price*size)+" to sell now: ",sell_price,size,trade_amount * TRADE_SCALE_TEST)
                continue
            #cbpro_rtn_dict = cbs.cbpro_limit_order_gtt(auth_client,action.lower(),sell_price,size,product_label=asset+"-"+underlying[1]) # TAG-SELL
        # If action is active, some transaction occured, record it.
        #if action != "":
        #        record_round_trip_transaction(str(datetime.now()),action,asset,underlying,current_price,asset_dict[asset],idx_target_f,trade_amount,index_value,cbpro_rtn_dict) # TAG-REC



# Save this to be used by the records.

with open("portfolio_size.json", 'w') as f_obj:
    json.dump(total,f_obj)

# Now that these risk scaling values are calculated, share with other algos that may benefit from them.
# Do this using an if to check for my personal key code so it only happens once.
#print(risk_scaling(price_list_of_dicts,asset_dict))
if key[:6] == 'cb36b1':
        with open("/tmp/risk_scaling_dict.json", 'w') as f_obj:
            json.dump(risk_scaling(price_list_of_dicts,asset_dict),f_obj)

#print(a)
# Format example
''' {u'available': u'0', u'balance': u'0.0000000000000000', u'profile_id': u'c9dbb516-181c-4f76-89c0-37cc63f41004', u'currency': u'BCH', u'hold': u'0.0000000000000000', u'id': u'a7667476-1207-4ed6-a1a7-fa5cf64c34cd'}
 '''

'''
0(u'LTC', u'0', u'0.0000000000000000')
1(u'BTC', u'0.0122494', u'0.0300000000000000')
2(u'USD', u'366.4013870112286', u'0.0000000000000000')
3(u'ETH', u'0.42951279', u'0.0000000000000000')
4(u'ETC', u'2.05145879', u'0.0000000000000000')
5(u'BCH', u'0', u'0.0000000000000000')

'''

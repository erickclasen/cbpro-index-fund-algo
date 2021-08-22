# cbpro-index-fund-algo

This set of Python files allows operations on Coinbase Pro (CBPRO) that allows
the creation of an index fund of 45 ( as of Aug 2021 ) cryptocurrencies.

The index is derived from 25 cryptocurrencies that were available for trading
on CBPRO as of 02/01/2021. On this date the index was normalized to 1.0. When the code runs the index value is printed out and it is also logged in the log files.

By using this code ( index-balancer.py or index-balancer-TEST.py) one can set up a trading/investing system that will stay in
the market and re-balance the portfolio automatically.

## How it works
Basically the index-balancer.py code reads the gross amount of money in terms of crypto and USD
and USDC available and divides it evenly to produce a target hold amount.
This is then adjusted by using the return ratio to scale some cryptos above
the target and scale others under the target based on performance.

The return ratio for this code is defined as the returns over
a set period of time divided by the standard deviation of prices over the 
same interval. It uses the return ratio as a Risk Scaler. The Risk Scaler is 
normalized across all the currencies to allow the best ones in terms of 
return ratio to be more heavily invested in and others that are not 
performing as well over a predefined interval to be invested in at a lower 
amount.

The index-balancer.py code will buy or sell an asset whenever it is +/- 10% away from the 
target determined by the error between amount held and the calculated 
target. Note the target is not a target price but, in fact the amount of
crypto held in terms of USD/USDC.

The index-balancer.py code will trade against USD and USDC depending on what coins can be
traded against the USD or USDC underlying. It uses logic to scale in and out
of certain coins that can use BOTH as an underlying to attempt to keep a
correct ratio of a "pool" of USDC and USD. It treats the "pool" of USD and
USDC as yet another currency and will balance against it as well.

## Parameters
There are a few adjustable parameters for the index-balancer.py code that are stored outside of
the main file in a file called defines.py

for example....

```python
ticker_filename = '/home/erick/www/btc/cbpro_crypto_price_volume_file.csv'
FILL_SCALER = 0.35 #0.9 # 1.0 is normal 100% fill, reduce to trim portfolio.                          

# Soft stop loss fades out trades if below the fade u of index value to complete off below
# fade l. It scales the fill scaler.
NO_BUY_ZONE_U = 2.29
FADE_U = 2.1
FADE_L = 1.8
```

The ****ticker_filename**** is where it will get the price data from.
The FILL_SCALER is the amount that it will hold where 0 is nothing and 1.0 the
max, a 100% of the target and the portfolio will be fully funded.

****NO_BUY_ZONE**** is a number in terms of index value below which it will not buy
any crypto. This works similar to a buy stop and prevents buying below
the index value. It can be used to catch a breakout for example.

****FADE_U and FADE_L**** are fade upper and fade lower. This provides a stop loss
zone over which the amount of assets held will be faded from the full value
determined by the FILL_SCALER to 0 at the FADE_L value in terms of the index.
It is a stop loss that is linearly faded across these values.

### Parameters within the index-balancer.py code itself
The following parameters are within the main body of code and do not generally require 
adjusting except in rare cases.
All parameters are in capital letters to help set them apart from non-constants.

****TARGET_DEADBAND**** - This is the dead-band around the target value within which the algorithm will not
take action to re-balance. Keeps it from making many small transactions constantly. It is set to 0.1
which means that the dead-band is +/- 10%. So if the target is $100 the algorithm will allow the 
asset amount go as low as $90 before refilling it to target of $100, same with selling it will wait until 
the amount of asset held is $100.

****ORDER_AMT_SCALER**** - Set to 0.97. This is a multiplier on the amount that will e bought and sold. So if the target is $100 and the amount falls below $90 it will not buy $10 but $9.7. Due to the granularity of some cryptos and the finite amounts that they can buy and sell in the idea is to stay a bit shy of the target as to not overshoot. This overshoot might result in dither back and forth where the algorithm will buy and sell repeatedly in sequence and oscillate around the target. In practice it
has been found to be a non-issue as the dead-band of 10% is wide enough to preclude this but, might be of concern with tighter dead-bands.

****PERIOD**** - Period is the look-back time used in calculation of items such as moving averages and 
calculations of the risk/reward are calculated assuming a tick of 1 hour in the price/volume csv
data file. It is set at 720, around 30 days of data to compute with.


## Experimental Dual Moving Average Ensemble Trend Scaler

In the index-balancer-TEST.py file there is an experimental enhancement to the code.
Multiple moving averages of the price are calculated and used in an 
ensemble to determine how much of an asset is held depending on the trend.
This scaler is applied on top of the target and the Risk Scaler based on the
return ratio.

Basically it is using a Dual Moving Average Crossover (DMAC). Where if the short
moving average of the pair is above the long moving average of the pair on
a price chart, a fixed amount of the asset is scaled in. If the pair of
averages reverses, a fixed amount of the asset is scaled out.

Currently it is set to always allow 0.2 to be in at all times, each average
will add 0.37 to this for a max of 1.05. A small amount of "overdrive" above
1.0 is allowed right now as part of the test to see how it will perform.
If they are all "hot" and at 1.05 there is a chance that the USD or USDC pool
will become depleted if the FILL_SCALER is set to 1.0. Part of the test
has been to see how the code copes with this. There is logic in the code
to check to see if there is any balance left to buy or sell from an asset, so
it will skip the trade if it can't perform it due to insufficient funds.

- This code requires a backlog of price/volume data to operate properly.
  It will not crash without this but the ensemble averages won't work enough warmup
  data is available. It will just do nothing until those build up. There is a test 2 line CSV
  file that can be used for dry run sanity testing... cbpro_crypto_price_volume_file_TEST.csv
  code will run off this without errors, try using the sim-index-balancer.py so no live trades occur.

****TBD: Paper Describing The Theory and Testing of the Dual Moving Average Ensemble****


## Order Type
The code uses limit orders set with a GTT - Good Till Time of 1 hour.
The presumption is that this code will be called on a regular basis via a 
script and CRON (see example.sh), so if an order fails to fill it will just make it up on the 
next call. Using GTT orders prevents hanging orders from occurring that could
build up and just sit there doing nothing forever. 
Additionally this code uses a push out system. This means when it sets orders
it will adjust the buy and sell price of the limit order by 0.1%. Example, if
an order is for 100 sell it will set a limit order at 100.1 and conversely
for a buy it will set the order at 99.9. This gives a little boost by buying
at a discount and selling at a slight premium every time, offsetting trading
fees slightly. Almost always an order is filled like this within an hour as 
price tends to have some random noise to allows it to drift into the limit
order price.

## Logs
This code produces logs of it's behavior which are fairly self explanatory.

The first 6 characters of the key is used as an ID for the log files.

The summary covers all buys and sells in brief...

summary-0083ff-index-balancer.py.log

There are verbose sell and buy logs as well that will show the actual orders as acknowledged by CBPRO via a return from the API call.

verbose-0083ff-index-balancer.py-buy-USDC.log

verbose-0083ff-index-balancer.py-buy-USD.log

verbose-0083ff-index-balancer.py-sell-USDC.log

verbose-0583fb-index-balancer.py-sell-USD.log




## How to Call the Code
```bash
index-balancer.py key b64secret passphrase
```
Where the CBPRO API key b64secret and passphrase are passed as command line
args to the code.

It can called periodically via CRON to manage trading/investing on the Coinbase Pro Exchange 
- example.sh - An example of how to call the code in a script.

The code uses raw Python without any libs, with the exception of the requirement of installing the cbpro module.

This code was made a straightforward as possible to minimize the amount of libraries needed and
the "heaviness" of overhead so it can be deployed easily and on lightweight hardware such as
a Raspberry Pi.

Note: Access the Coinbase Pro API via cbpro requires Python3 to work with SSL.

## Reminder
Although this code has been used in production successfully, there is no guarantee that it is
bug free and will always remain in working order.
 Always consider the risk when using code that transacts using real money that can be lost.
 No one can be responsible for the operation of the code or financial transactions
other than the end user of this code. A person on r/Wallstreetbets said it best when they had
the following comment in their post signature...
"Don't take what I have as financial advice as I am totally high right now." We might not all
be high but we are human and suffer from all kinds of failure modes. The fate of Long Term
Capital Management comes to mind, look it up, it is a worthy tale of a brilliant but epic fail.

## Operations

The code is operated algoritmically and performs it's functions automatically.
It will automatically hold the scaled target value of assets across 45
cryptos.

## Requirements
Requires the Python client code for the Coinbase Pro API provided by Daniel Paquin
https://github.com/danpaquin/coinbasepro-python

For reference ...
- https://docs.pro.coinbase.com/

- You may manually install the project or use ```pip```:
```python
pip install cbpro
#or
pip install git+git://github.com/danpaquin/coinbasepro-python.git
```

## Key, Passphrase and b64secret
You must pass them as setup via Coinbase Pro API as command line parameters.
- Permissions to read the accounts and buy and sell must be ticked off in the checkboxes when setting up keys.

https://help.coinbase.com/en/pro/other-topics/api/how-do-i-create-an-api-key-for-coinbase-pro

## Ticker data
###cbpro-api-price-volume-ticker-get.py
The ticker filename is required for the location of the price/volume data to be pulled in from CBPRO.
The ticker price and volume can be pulled down by calling...

cbpro-api-price-volume-ticker-get.py


...on an hourly basis (or whatever other reasonable choice) to create the ticker csv file.
A seed file to start from is kept updated at...

http://heart-centered-living.org/public/cbpro-data/cbpro_crypto_price_volume_file.csv




- Note: It is possible to operate this code with a bare minimum of backlog data.
  At least 2 lines of data in the CSV ticker file are needed at minimum to prevent a crash.
  For the TEST version with the moving average ensemble, it will not trade
  until enough historical data is present for the average ensemble to work.
  So it would have a warmup period where nothing would happen.

- A test file called cbpro_crypto_price_volume_file_TEST.csv is provided in
  this repo for a basic sanity test of the code as it will run with this alone.
  Use this with the sim version to check for errors.  

## Support files used as modules by the code

***coretamodule.py*** - Required by the index-balancer code as an included file, contains many components to perform technical analysis and etc. Worth a look through. It is basically the library file for most of the algorithm and command line code that I have developed for trading.

***cbpro_buy_sell.py*** - A thin layer of code between the code such as index-balancer and the CBPRO API. This code is there to provide an interface layer, hopefully makes the code portable to other API's other than CBPRO.

**debugtrace.py** - This is imported in cbpro-api-price-volume-ticker-get.py as dt. It is used as a tracer for debugging and produces a log file when the code is sun. It is used for simple breadcrumb trail
style debugging. Can be used in any other python file as one wishes.

## Other Support Files
**sim-index-balancer.py** - This is a version of the index-balancer.py with the API calls commented out. This allows for a dry run without any trades occurring for testing.

**portfolio-size-cp.py** - This code takes the portfolio_size.json file which is created by the index-balancer.py code and puts the value into a log. This way a running account of the portfolio balance is created to monitor algorithm performance over time.

**defines.py** - Holds Ticker Filename and adjustable parameters.

**cbpro-api-price-volume-ticker-get.py** - Gets price and volume data from CBPRO via the API. Stores it
in a CSV which is named in defines.py. This file is consumed by the index-balancer.py code in order to 
get a history of price and volume data. This ticker has to be updated periodically, hourly or other time frame. cbpro-api-price-volume-ticker-get.py called perodically via CRON is the way to keep the 
ticker data current. This file will create a live_dict.json as another output as well. This file keeps a copy of the most recent data and uses it to impute missing values should a failure to grab data occurs.

**cbpro_crypto_price_volume_file_TEST.csv** - A 2 line ticker file to sanity check the code with.
Set the path in defines.py to this file and the code will run.
Test using the sim-index-balancer.py and it should run through it and make
no trades but, will prove all is in place to run fully.

**example.sh** - An example of how to call the code in a script. Calls the portfolio-cp code first to store away the current amount in the portfolio, this is optional.

## Information
The code in this repo is generally compatable with the cbpro-cli-tools repo and both can function
together. Note that the cbpro-api-price-volume-ticker-get.py  is newer that the ticker grab code
in that repo also be careful with the coretamodule and the cbpro_buy_sell.py as they are 
possiblly newer as well as more cryptos get added to CBPRO occasionally.



	EX: python3 cbpro-api-price-volume-ticker-5-cryptos-csv.py

## Action 
These pieces of code perform an action and will perform the action automatically without prompting by the user. When caled via a script it is often desirable to pipe the output to a file such as index-balancer.out for debug and monitoring.
- See example.sh for a gist of a script that can be used as a template.




##Glossary:
action = buy or sell.

currency = the currency to buy into or sell from.

underlying = the asset that is to be bought from or sold to, think BTC-USD, USD as the underlying.




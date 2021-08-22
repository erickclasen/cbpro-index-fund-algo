#ticker_filename = '/home/erick/www/btc/cbpro_crypto_price_volume_file.csv'
ticker_filename = '/tmp/cbpro_crypto_price_volume_file.csv'


FILL_SCALER = 0.3 #0.9 # 1.0 is normal 100% fill, reduce to trim portfolio.                          

# Soft stop loss fades out trades if below the fade u of index value to complete off below
# fade l. It scales the fill scaler.
NO_BUY_ZONE_U = 2.23
FADE_U = 2.0
FADE_L = 1.8

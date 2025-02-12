import sys
import time
import pkg_resources
from datetime import datetime

from .nightscout import NightscoutApi
from .parser.nightscout import BASAL_EVENTTYPE, BOLUS_EVENTTYPE

try:
    __version__ = pkg_resources.require("tconnectsync")[0].version
except Exception:
    __version__ = "UNKNOWN"

"""
Attempts to authenticate with each t:connect API,
and returns the output of a sample API call from each.
Also attempts to connect to the Nightscout API.
"""
def check_login(tconnect, time_start, time_end, verbose=False):
    errors = 0

    loglines = []
    def log(*args):
        print(*args)
        loglines.append(" ".join([str(i) for i in args]) + "\n")

    def debug(*args):
        if verbose:
            print(*args)
        loglines.append(" ".join([str(i) for i in args]) + "\n")

    log("tconnectsync version %s" % __version__)
    log("Python version %s" % sys.version)
    log("System platform %s" % sys.platform)
    log("Running checks with time range %s to %s" % (time_start, time_end))
    log("Current time: %s" % datetime.now())
    log("time.tzname: %s" % str(time.tzname))

    log("Loading secrets...")
    try:
        from .secret import TCONNECT_EMAIL, TCONNECT_PASSWORD, PUMP_SERIAL_NUMBER, NS_URL, NS_SECRET, TIMEZONE_NAME
    except ImportError as e:
        log("Error: Unable to load config file. Please check your .env file or environment variables")
        log(e)
    
    if not TCONNECT_EMAIL or TCONNECT_EMAIL == 'email@email.com':
        log("Error: You have not specified a TCONNECT_EMAIL")
        errors += 1
    
    if not TCONNECT_PASSWORD or TCONNECT_PASSWORD == 'password':
        log("Error: You have not specified a TCONNECT_PASSWORD")
        errors += 1
    
    if not PUMP_SERIAL_NUMBER or PUMP_SERIAL_NUMBER == '11111111':
        log("Error: You have not specified a PUMP_SERIAL_NUMBER")
        errors += 1
    
    if not NS_URL or NS_URL == 'https://yournightscouturl/':
        log("Error: You have not specified a NS_URL")
        errors += 1
    
    if not NS_SECRET or NS_SECRET == 'apisecret':
        log("Error: You have not specified a NS_SECRET")
        errors += 1

    log("TIMEZONE_NAME: %s" % TIMEZONE_NAME)

    log("-----")

    log("Logging in to t:connect ControlIQ API...")
    try:
        summary = tconnect.controliq.dashboard_summary(time_start, time_end)
        debug("ControlIQ dashboard summary: %s" % summary)
    except Exception as e:
        log("Error occurred querying ControlIQ API:")
        log(e)
        errors += 1
    
    log("Querying ControlIQ therapy_timeline...")
    try:
        tt = tconnect.controliq.therapy_timeline(time_start, time_end)
        debug("ControlIQ therapy_timeline: %s" % tt)
    except Exception as e:
        log("Error occurred querying ControlIQ therapy_timeline:")
        log(e)
        errors += 1
    
    log("-----")

    log("Logging in to t:connect WS2 API...")
    try:
        summary = tconnect.ws2.basaliqtech(time_start, time_end)
        debug("WS2 basaliq status: %s" % summary)
    except Exception as e:
        log("Error occurred querying WS2 API:")
        log(e)
        errors += 1
    
    log("Querying WS2 therapy_timeline_csv...")
    try:
        ttcsv = tconnect.ws2.therapy_timeline_csv(time_start, time_end)
        debug("therapy_timeline_csv: %s", ttcsv)
    except Exception as e:
        log("Error occurred querying WS2 therapy_timeline_csv:")
        log(e)
        errors += 1
    
    log("-----")

    log("Logging in to t:connect Android API...")
    try:
        summary = tconnect.android.user_profile()
        debug("Android user profile: %s" % summary)
        event = tconnect.android.last_event_uploaded(PUMP_SERIAL_NUMBER)
        debug("Android last uploaded event: %s" % event)
    except Exception as e:
        log("Error occurred querying Android API:")
        log(e)
        errors += 1
    
    log("Querying Android therapy_events...")
    try:
        androidevents = tconnect.android.therapy_events(time_start, time_end)
        debug("android therapy_events: %s" % androidevents)
    except Exception as e:
        log("Error occurred querying Android therapy_events:")
        log(e)
        errors += 1
    
    log("-----")

    log("Logging in to Nightscout...")
    try:
        nightscout = NightscoutApi(NS_URL, NS_SECRET)
        status = nightscout.api_status()
        debug("Nightscout status: %s" % status)

        last_upload_basal = nightscout.last_uploaded_entry(BASAL_EVENTTYPE)
        debug("Nightscout last uploaded basal: %s" % last_upload_basal)

        last_upload_bolus = nightscout.last_uploaded_entry(BOLUS_EVENTTYPE)
        debug("Nightscout last uploaded bolus: %s" % last_upload_bolus)
    except Exception as e:
        log("Error occurred querying Nightscout API:")
        log(e)
        errors += 1

    log("-----")

    if errors == 0:
        log("No API errors returned!")
    else:
        log("API errors occurred. Please check the errors above.")
    

    with open('tconnectsync-check-output.log', 'w') as f:
        f.writelines(loglines)

    print("Created file tconnectsync-check-output.log containing additional debugging information.")
    print("For support, you can upload this file to https://github.com/jwoglom/tconnectsync/issues/new")
    print("Before uploading, look through the file and remove any sensitive data, such as")
    print("Nightscout URL and pump serial number.")
